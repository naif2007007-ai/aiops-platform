# ============================================================
# app.py — AI-Ops Platform Dashboard (Streamlit entry point)
# Run: streamlit run app.py
# ============================================================

import streamlit as st

st.set_page_config(
    page_title  = "AI-Ops Platform",
    page_icon   = "🔮",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Sidebar navigation ────────────────────────────────────────
PAGES = {
    "🏠 Executive Overview":         "pages/01_executive_overview.py",
    "📡 Operations Monitoring":      "pages/02_operations_monitoring.py",
    "⚠️ Predicted Failures":         "pages/03_predicted_failures.py",
    "📊 Asset Risk Ranking":         "pages/04_asset_risk_ranking.py",
    "🔗 Alarm-Ticket Correlation":   "pages/05_alarm_ticket_correlation.py",
    "🧠 Model Insights":             "pages/06_model_insights.py",
}

st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Amazon_Web_Services_Logo.svg/120px-Amazon_Web_Services_Logo.svg.png",
    width=80,
)
st.sidebar.title("AI-Ops Platform")
st.sidebar.caption("Proactive IT Infrastructure Intelligence")
st.sidebar.divider()

selection = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

# Load selected page
import importlib.util, pathlib, os

page_path = os.path.join(os.path.dirname(__file__), PAGES[selection])
spec = importlib.util.spec_from_file_location("page", page_path)
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
