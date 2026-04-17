import streamlit as st
import time

st.set_page_config(
    page_title="Aramco AITD — AIOps Platform",
    page_icon="🔮",
    layout="wide"
)

PAGES = {
    "🏢 AITD Command Center":           "pages/01_company_overview.py",
    "🔍 Division Overview":             "pages/02_division_overview.py",
    "📡 Routers, Switches & UPS":       "pages/03_routers_switches_ups.py",
    "⚠️ Predicted Failures & Actions":  "pages/04_predicted_failures.py",
    "🤖 AI Assistant — المساعد":        "pages/05_ai_assistant.py",
}

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("Aramco AITD")
st.sidebar.caption("AI-Powered IT Infrastructure Operations")
st.sidebar.caption("عمليات البنية التحتية المدعومة بالذكاء الاصطناعي")
st.sidebar.divider()

# Live indicator
from datetime import datetime
now = datetime.utcnow().strftime("%H:%M:%S UTC")
st.sidebar.markdown(f"""
<div style="
    background:#0F6E56;
    border-radius:8px;
    padding:10px 14px;
    margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:8px;">
        <div style="
            width:12px;height:12px;
            background:#4AE09A;
            border-radius:50%;
            animation:pulse 1.5s infinite;">
        </div>
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

# Auto refresh
st.sidebar.divider()
st.sidebar.caption("⚙️ Settings")
auto_refresh = st.sidebar.toggle("Auto-refresh every 15 min", value=True)
if auto_refresh:
    st.markdown("""
    <script>
    setTimeout(function() { window.location.reload(); }, 900000);
    </script>
    """, unsafe_allow_html=True)

# ── Load selected page ────────────────────────────────────────
import importlib.util, os
path = os.path.join(os.path.dirname(__file__), PAGES[sel])
spec = importlib.util.spec_from_file_location("page", path)
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
