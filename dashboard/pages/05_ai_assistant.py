import streamlit as st
import anthropic
import boto3
import io
import os
import pandas as pd

st.title("🤖 AI Assistant — المساعد الذكي")
st.caption("Ask anything about AITD infrastructure in English or Arabic | اسأل عن بنية أرامكو التحتية بالعربي أو الإنجليزي")
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
    preds  = read_s3("models/predictions.parquet")
    assets = read_s3("raw/assets.parquet")
    df     = preds.merge(
        assets[["asset_id","division","device_type","battery_age_yrs"]],
        on="asset_id", how="left"
    )

    # Company summary
    total    = len(df)
    critical = (df["risk_level"]=="CRITICAL").sum()
    high     = (df["risk_level"]=="HIGH").sum()
    medium   = (df["risk_level"]=="MEDIUM").sum()
    low      = (df["risk_level"]=="LOW").sum()
    ups_due  = df[(df["device_type"]=="UPS") &
                  (df["battery_age_yrs"]>=3.5)].shape[0]

    # Division summary
    div_summary = df.groupby("division").agg(
        total=("asset_id","count"),
        critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
        high=("risk_level",     lambda x: (x=="HIGH").sum()),
        medium=("risk_level",   lambda x: (x=="MEDIUM").sum()),
    ).reset_index().to_string(index=False)

    # Device type summary
    type_summary = df.groupby("device_type").agg(
        total=("asset_id","count"),
        critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
        high=("risk_level",     lambda x: (x=="HIGH").sum()),
    ).reset_index().to_string(index=False)

    # Top critical assets
    top_critical = df[df["risk_level"]=="CRITICAL"]\
        .sort_values("failure_probability", ascending=False)\
        .head(10)[["asset_id","division","device_type",
                   "failure_probability","recommended_action"]]\
        .to_string(index=False)

    context = f"""
You are an expert AI assistant for Aramco's AIT Department (AITD).
You help IT operations teams and executives understand infrastructure health
across 8 divisions: Abqaiq, Dhahran, RasTanura, Riyadh, Yanbu, Jizan, Tanajib, Adhailiya.

Device types monitored: Routers, Switches, UPS (Uninterruptible Power Supply)

CURRENT INFRASTRUCTURE STATUS:
Total devices: {total:,}
CRITICAL (Emergency — L3): {critical} devices
HIGH (Urgent — L2): {high} devices
MEDIUM (Schedule — L1): {medium} devices
LOW (Healthy): {low} devices
UPS batteries due replacement: {ups_due}

DIVISION BREAKDOWN:
{div_summary}

DEVICE TYPE BREAKDOWN:
{type_summary}

TOP CRITICAL ASSETS:
{top_critical}

INSTRUCTIONS:
- Answer in the same language the user asks (Arabic or English)
- Be concise and give specific actionable recommendations
- Always mention division and device type when relevant
- For UPS questions focus on battery health and replacement
- For network questions focus on CPU, memory, packet loss
- Use simple language — avoid technical jargon
- If asked in Arabic respond fully in Arabic
"""
    return context

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Quick questions ───────────────────────────────────────────
st.caption("Quick questions — click to ask:")
col1, col2 = st.columns(2)

english_examples = [
    "Which division needs most urgent attention?",
    "How many UPS batteries need replacement?",
    "What are the top network issues today?",
    "Which routers are about to fail?",
]
arabic_examples = [
    "أي قسم يحتاج تدخل فوري؟",
    "كم عدد بطاريات UPS التي تحتاج استبدال؟",
    "ما هي أبرز مشاكل الشبكة اليوم؟",
    "أي الأجهزة الأكثر خطورة في أبقيق؟",
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

# ── Chat ──────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about AITD infrastructure... | اسأل عن البنية التحتية..."):
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

if st.session_state.messages:
    if st.button("🗑️ Clear conversation | مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()
