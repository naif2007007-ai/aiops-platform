import streamlit as st
import anthropic
import boto3
import io
import os
import pandas as pd

st.title("🤖 AI Assistant — المساعد الذكي")
st.caption("Ask anything about your infrastructure in English or Arabic | اسأل عن بنيتك التحتية بالعربي أو الإنجليزي")
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
    critical = preds[preds["risk_level"]=="CRITICAL"]
    high     = preds[preds["risk_level"]=="HIGH"]
    medium   = preds[preds["risk_level"]=="MEDIUM"]
    low      = preds[preds["risk_level"]=="LOW"]
    summary  = f"""
You are an expert AI assistant for an IT infrastructure operations platform at a large oil and gas company.
You help operations teams and executives understand device health and take the right actions.

CURRENT INFRASTRUCTURE STATUS:
- Total devices monitored: {len(preds):,}
- CRITICAL (Emergency — L3 required): {len(critical):,} devices
- HIGH (Urgent — L2 escalation): {len(high):,} devices  
- MEDIUM (Schedule maintenance): {len(medium):,} devices
- LOW (Healthy — monitor only): {len(low):,} devices

TOP 10 MOST CRITICAL DEVICES:
{critical.sort_values('failure_probability', ascending=False).head(10)[['asset_id','criticality','lifecycle_age_yrs','failure_probability','recommended_action']].to_string(index=False)}

TOP 10 HIGH RISK DEVICES:
{high.sort_values('failure_probability', ascending=False).head(10)[['asset_id','criticality','lifecycle_age_yrs','failure_probability','recommended_action']].to_string(index=False)}

INSTRUCTIONS:
- Answer in the same language the user asks in (Arabic or English)
- Be concise and actionable
- Always recommend a specific action
- Use simple language — avoid technical jargon
- If asked in Arabic, respond fully in Arabic
- Focus on what the user needs to DO, not just what the data shows
"""
    return summary

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Example questions ─────────────────────────────────────────
st.caption("Quick questions — click to ask:")
col1, col2 = st.columns(2)

english_examples = [
    "Which devices need attention right now?",
    "What should I do first today?",
    "How many devices will fail this week?",
    "Which location has the most problems?",
]
arabic_examples = [
    "أي الأجهزة تحتاج تدخل فوري؟",
    "ما هي أولويات العمل اليوم؟",
    "كم جهاز متوقع تعطله هذا الأسبوع؟",
    "أي موقع يعاني من أكثر المشاكل؟",
]

with col1:
    st.caption("🇬🇧 English")
    for i, ex in enumerate(english_examples):
        if st.button(ex, key=f"en_{i}"):
            st.session_state.messages.append({"role":"user","content":ex})
            st.rerun()

with col2:
    st.caption("🇸🇦 العربية")
    for i, ex in enumerate(arabic_examples):
        if st.button(ex, key=f"ar_{i}"):
            st.session_state.messages.append({"role":"user","content":ex})
            st.rerun()

# ── Chat input ────────────────────────────────────────────────
if prompt := st.chat_input("Ask in English or Arabic... | اسأل بالعربي أو الإنجليزي"):
    st.session_state.messages.append({"role":"user","content":prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking... | جاري التفكير..."):
            try:
                context  = load_context()
                client   = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                history  = [{"role":m["role"],"content":m["content"]}
                            for m in st.session_state.messages]
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=600,
                    system=context,
                    messages=history,
                )
                answer = response.content[0].text
                st.write(answer)
                st.session_state.messages.append({"role":"assistant","content":answer})
            except Exception as e:
                st.error(f"Error: {e}")

# ── Clear chat button ─────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️ Clear conversation | مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()
