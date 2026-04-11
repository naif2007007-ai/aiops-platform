import streamlit as st
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

st.sidebar.title("AI-Ops Platform")
st.sidebar.caption("Proactive IT Infrastructure Intelligence")
st.sidebar.caption("نظام استباقي لعمليات البنية التحتية")
st.sidebar.divider()

sel = st.sidebar.radio(
    "Navigate",
    list(PAGES.keys()),
    label_visibility="collapsed"
)

import importlib.util, os
path = os.path.join(os.path.dirname(__file__), PAGES[sel])
spec = importlib.util.spec_from_file_location("page", path)
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
