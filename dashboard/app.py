import streamlit as st
import time
st.set_page_config(
    page_title="AI-Ops Platform",
    page_icon="🔮",
    layout="wide"
)

PAGES = {
    "🏠 Executive Overview":        "pages/01_executive_overview.py",
    "📡 Operations Monitoring":     "pages/02_operations_monitoring.py",
    "⚠️ Predicted Failures":        "pages/03_predicted_failures.py",
    "📊 Device Priority List":      "pages/04_asset_risk_ranking.py",
    "🔗 Alerts to Tickets":         "pages/05_alarm_ticket_correlation.py",
    "🧠 How the AI Decides":        "pages/06_model_insights.py",
    "🤖 AI Assistant — المساعد":   "pages/07_ai_assistant.py",
}

# ── Live status in sidebar ────────────────────────────────────
st.sidebar.title("AI-Ops Platform")
st.sidebar.caption("Proactive IT Infrastructure Intelligence")
st.sidebar.caption("نظام استباقي لعمليات البنية التحتية")
st.sidebar.divider()

# Live indicator
from datetime import datetime
now = datetime.utcnow().strftime("%H:%M:%S UTC")
st.sidebar.markdown(f"""
<div style="
    background: #0F6E56;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 10px;
">
    <div style="display:flex;align-items:center;gap:8px;">
        <div style="
            width:12px;height:12px;
            background:#4AE09A;
            border-radius:50%;
            animation: pulse 1.5s infinite;
        "></div>
        <span style="color:#E1F5EE;font-size:13px;font-weight:500;">
            🟢 LIVE — Data Active
        </span>
    </div>
    <div style="color:#9FE1CB;font-size:11px;margin-top:4px;">
        Updates every 15 minutes
    </div>
    <div style="color:#9FE1CB;font-size:11px;">
        Last check: {now}
    </div>
</div>
<style>
@keyframes pulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(74,224,154,0.7); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(74,224,154,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(74,224,154,0); }}
}}
</style>
""", unsafe_allow_html=True)

st.sidebar.divider()

sel = st.sidebar.radio(
    "Navigate",
    list(PAGES.keys()),
    label_visibility="collapsed"
)

# Auto refresh every 15 minutes
st.sidebar.divider()
st.sidebar.caption("⚙️ Settings")
auto_refresh = st.sidebar.toggle("Auto-refresh every 15 min", value=True)
if auto_refresh:
    st.sidebar.caption("Dashboard refreshes automatically")
    time.sleep(0)
    st.markdown("""
    <script>
    setTimeout(function() {
        window.location.reload();
    }, 900000);
    </script>
    """, unsafe_allow_html=True)

import importlib.util, os
path = os.path.join(os.path.dirname(__file__), PAGES[sel])
spec = importlib.util.spec_from_file_location("page", path)
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
