import streamlit as st
import anthropic
import boto3
import io
import os
import pandas as pd

st.title("🤖 AI Assistant")
st.caption("Ask anything about your infrastructure in plain English")
st.divider()

BUCKET = os.getenv("AIOPS_S3_BUCKET", "aiops-platform-poc")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

def read_s3(key):
    client = boto3.client("s3",
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
    buf = io.BytesIO()
    client.download_fileobj(BUCKET, key, buf)
    buf.seek(0)
    return pd.read_parquet(buf)

@st.cache_data(ttl=300)
def load_context():
    preds = read_s3("models/predictions.parquet")
    high  = preds[preds["risk_level"]=="HIGH"]
    med   = preds[preds["risk_level"]=="MEDIUM"]
    low   = preds[preds["risk_level"]=="LOW"]
    summary = f"""
You are an AI assistant for an IT infrastructure operations platform.
Here is the current infrastructure status:

TOTAL ASSETS: {len(preds)}
HIGH RISK: {len(high)} assets needing immediate attention
MEDIUM RISK: {len(med)} assets needing maintenance soon
LOW RISK: {len(low)} assets that are healthy

TOP 10 HIGH RISK ASSETS:
{high.sort_values('failure_probability', ascending=False).head(10)[['asset_id','criticality','lifecycle_age_yrs','failure_probability','recommended_action']].to_string(index=False)}

Answer questions clearly and concisely based on this data.
Always give a recommended action with your answer.
"""
    return summary

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

st.caption("Try asking:")
examples = ["Which assets need urgent attention?","How many high risk assets do we have?","What should I do first today?","Which asset is most likely to fail?"]
cols = st.columns(2)
for i, ex in enumerate(examples):
    if cols[i % 2].button(ex, key=f"ex_{i}"):
        st.session_state.messages.append({"role":"user","content":ex})
        st.rerun()

if prompt := st.chat_input("Ask about your infrastructure..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                context = load_context()
                client  = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                history = [{"role":m["role"],"content":m["content"]} for m in st.session_state.messages]
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=500,
                    system=context,
                    messages=history,
                )
                answer = response.content[0].text
                st.write(answer)
                st.session_state.messages.append({"role":"assistant","content":answer})
            except Exception as e:
                st.error(f"Error: {e}")
