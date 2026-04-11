import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform"))
from dashboard.data_loader import load_alarms, load_tickets, load_predictions

st.title("🔗 Alerts to Tickets Analysis")
st.caption("Understanding which alerts cause the most problems and cost the most time")
st.divider()

alarms  = load_alarms()
tickets = load_tickets()
preds   = load_predictions()

tickets["open_time"]  = pd.to_datetime(tickets["open_time"])
tickets["close_time"] = pd.to_datetime(tickets["close_time"])

# ── KPI row ───────────────────────────────────────────────────
total_alarms  = len(alarms)
total_tickets = len(tickets)
p1_tickets    = (tickets["priority"]=="P1 - Critical").sum()
avg_fix_time  = tickets["resolution_time_hrs"].mean()
reopened      = tickets["reopened"].sum()

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Alerts",        f"{total_alarms:,}")
c2.metric("Total Tickets",       f"{total_tickets:,}")
c3.metric("Emergency P1 Tickets",f"{p1_tickets:,}")
c4.metric("Avg Fix Time",        f"{avg_fix_time:.1f} hrs")
c5.metric("Reopened Tickets",    f"{reopened:,}")
st.divider()

# ── Top problem types ─────────────────────────────────────────
st.subheader("🔥 Which Alert Types Cause the Most Problems?")
st.caption("These are the most common alert types — fixing the root cause will reduce tickets significantly")

event_counts = alarms.groupby("event_type").size().reset_index(name="Alert Count")
event_counts = event_counts.sort_values("Alert Count", ascending=False).head(10)
event_counts["event_type"] = event_counts["event_type"].map({
    "LinkDown":        "Network Link Failure",
    "HighCPU":         "High CPU Usage",
    "HighMemory":      "High Memory Usage",
    "DiskFull":        "Disk Full",
    "PacketLoss":      "Network Packet Loss",
    "LatencySpike":    "Response Time Spike",
    "AuthFailure":     "Login Failure",
    "HardwareError":   "Hardware Error",
    "ConfigChange":    "Configuration Change",
    "ReachabilityLost":"Device Unreachable",
}).fillna(event_counts["event_type"])

fig = px.bar(
    event_counts.sort_values("Alert Count"),
    x="Alert Count", y="event_type",
    orientation="h",
    color_discrete_sequence=["#E24B4A"],
    height=350,
    text="Alert Count",
    labels={"event_type":"Alert Type","Alert Count":"Number of Alerts"}
)
fig.update_traces(textposition="outside")
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    xaxis_title="Number of Alerts",
    yaxis_title=""
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Ticket priority breakdown ─────────────────────────────────
st.subheader("📊 Ticket Urgency Breakdown")
st.caption("How urgent are the tickets being raised?")
col_a, col_b = st.columns(2)

with col_a:
    pri_counts = tickets["priority"].value_counts().reset_index()
    pri_counts.columns = ["Priority","Count"]
    pri_counts["Priority"] = pri_counts["Priority"].map({
        "P1 - Critical": "🔴 Emergency (P1)",
        "P2 - High":     "🟠 Urgent (P2)",
        "P3 - Medium":   "🟡 Normal (P3)",
        "P4 - Low":      "🟢 Low (P4)",
    })
    fig2 = px.pie(
        pri_counts, values="Count", names="Priority",
        hole=0.5, height=300,
        color="Priority",
        color_discrete_map={
            "🔴 Emergency (P1)":"#E24B4A",
            "🟠 Urgent (P2)":   "#EF9F27",
            "🟡 Normal (P3)":   "#639922",
            "🟢 Low (P4)":      "#378ADD",
        }
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0)
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("⏱️ Average Fix Time by Priority")
    st.caption("How long does it take to fix each type?")
    fix_time = tickets.groupby("priority")["resolution_time_hrs"].mean().reset_index()
    fix_time.columns = ["Priority","Avg Hours to Fix"]
    fix_time["Priority"] = fix_time["Priority"].map({
        "P1 - Critical": "🔴 Emergency",
        "P2 - High":     "🟠 Urgent",
        "P3 - Medium":   "🟡 Normal",
        "P4 - Low":      "🟢 Low",
    })
    fix_time["Avg Hours to Fix"] = fix_time["Avg Hours to Fix"].round(1)
    fig3 = px.bar(
        fix_time, x="Priority", y="Avg Hours to Fix",
        color_discrete_sequence=["#378ADD"],
        height=280, text="Avg Hours to Fix"
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="", yaxis_title="Hours"
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Devices with most tickets ─────────────────────────────────
st.subheader("📋 Devices with Most Open Tickets")
st.caption("These devices keep generating tickets — they need root cause investigation")

open_t = tickets[tickets["status"].isin(["Open","In Progress"])]
top_t  = (open_t.groupby("asset_id").size()
          .reset_index(name="Open Tickets")
          .sort_values("Open Tickets", ascending=False)
          .head(10))
top_t  = top_t.merge(preds[["asset_id","risk_level","recommended_action"]], on="asset_id", how="left")
top_t["risk_level"] = top_t["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Monitor",
    "LOW":      "🟢 Healthy"
})
top_t.columns = ["Device ID","Open Tickets","Risk Status","Recommended Action"]
st.dataframe(top_t, use_container_width=True, hide_index=True)
