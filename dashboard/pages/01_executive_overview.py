import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_alarms, load_tickets, load_predictions

st.title("🏠 Executive Overview")
st.caption("Infrastructure health summary — updated every 15 minutes")
st.divider()

assets  = load_assets()
alarms  = load_alarms()
tickets = load_tickets()
preds   = load_predictions()

alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
tickets["open_time"] = pd.to_datetime(tickets["open_time"])

critical = (preds["risk_level"] == "CRITICAL").sum()
high     = (preds["risk_level"] == "HIGH").sum()
medium   = (preds["risk_level"] == "MEDIUM").sum()
low      = (preds["risk_level"] == "LOW").sum()
total    = len(preds)
open_t   = tickets[tickets["status"].isin(["Open","In Progress"])].shape[0]

# ── Alert banners ─────────────────────────────────────────────
if critical > 0:
    st.error(f"🟣 EMERGENCY: {critical} devices need L3 response RIGHT NOW")
if high > 0:
    st.warning(f"🔴 URGENT: {high} devices need L2 escalation within 24 hours")
if medium > 0:
    st.info(f"🟡 SCHEDULE: {medium} devices need maintenance within 48 hours")

st.divider()

# ── KPI cards ─────────────────────────────────────────────────
st.subheader("Infrastructure Health at a Glance")
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Total Devices",    f"{total:,}")
c2.metric("🟣 Emergency L3", f"{critical:,}", delta=f"{critical} need L3 now",   delta_color="inverse")
c3.metric("🔴 Urgent L2",    f"{high:,}",     delta=f"{high} need L2 today",     delta_color="inverse")
c4.metric("🟡 Schedule L1",  f"{medium:,}")
c5.metric("🟢 Healthy",      f"{low:,}")
c6.metric("Open Tickets",    f"{open_t:,}")

st.divider()

# ── Charts ────────────────────────────────────────────────────
col_a, col_b = st.columns([1,2])

with col_a:
    st.subheader("Device Health Status")
    st.caption("How many devices need attention?")
    rc = preds["risk_level"].value_counts().reset_index()
    rc.columns = ["Status","Count"]
    rc["Status"] = rc["Status"].map({
        "CRITICAL": "🟣 Emergency L3",
        "HIGH":     "🔴 Urgent L2",
        "MEDIUM":   "🟡 Schedule L1",
        "LOW":      "🟢 Healthy"
    })
    fig = px.pie(rc, values="Count", names="Status", hole=0.6,
                 color="Status",
                 color_discrete_map={
                     "🟣 Emergency L3": "#7B2D8B",
                     "🔴 Urgent L2":    "#E24B4A",
                     "🟡 Schedule L1":  "#EF9F27",
                     "🟢 Healthy":      "#639922"
                 }, height=320)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Daily Alert Activity — Last 30 Days")
    st.caption("Higher bars = more problems detected that day")
    recent = alarms[alarms["severity"].isin(["Critical","Major"])]
    recent = recent[recent["timestamp"] >= alarms["timestamp"].max() - pd.Timedelta(days=30)]
    daily  = recent.set_index("timestamp").resample("D").size().reset_index()
    daily.columns = ["Date","Alerts"]
    fig2 = px.bar(daily, x="Date", y="Alerts",
                  color_discrete_sequence=["#E24B4A"], height=320)
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        yaxis_title="Number of Alerts",
        xaxis_title=""
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── ALL devices requiring action ──────────────────────────────
st.subheader("📋 All Devices Requiring Action — Sorted by Urgency")
st.caption("Every device that needs attention — start from the top")

action_needed = preds[preds["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])].sort_values(
    "failure_probability", ascending=False
).copy()

action_needed["Failure Risk"] = (action_needed["failure_probability"]*100).round(1).astype(str) + "%"
action_needed["Age (yrs)"]    = action_needed["lifecycle_age_yrs"].round(1)
action_needed["Status"] = action_needed["risk_level"].map({
    "CRITICAL": "🟣 Emergency — Call L3 Now",
    "HIGH":     "🔴 Urgent — Escalate to L2",
    "MEDIUM":   "🟡 Schedule — Assign to L1",
})

display = action_needed[[
    "asset_id","criticality","Age (yrs)",
    "Failure Risk","Status","recommended_action"
]].copy()
display.columns = [
    "Device ID","Importance","Age (yrs)",
    "Failure Risk","Status","What To Do"
]

st.caption(f"Showing all {len(display):,} devices that need action")
st.dataframe(display, use_container_width=True, hide_index=True, height=400)

st.divider()

# ── Bottom summary ────────────────────────────────────────────
st.subheader("📊 Summary for Management")
col1, col2, col3 = st.columns(3)
with col1:
    st.success(f"✅ {low:,} devices are healthy — no action needed")
with col2:
    st.warning(f"⏰ {medium:,} devices need maintenance this week")
with col3:
    st.error(f"🚨 {critical+high:,} devices need immediate attention today")
