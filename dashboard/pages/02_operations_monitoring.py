import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_alarms, load_logs, load_predictions

st.title("📡 Operations Monitoring")
st.caption("A simple daily view of what is happening across all your devices")
st.divider()

alarms = load_alarms()
logs   = load_logs()
preds  = load_predictions()
alarms["timestamp"] = pd.to_datetime(alarms["timestamp"])

# ── Simple summary at top ──────────────────────────────────────
st.subheader("🔔 What Happened Today?")
today_alarms = alarms[alarms["timestamp"].dt.date == alarms["timestamp"].dt.date.max()]
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Alerts Today",    f"{len(today_alarms):,}",    help="Total number of alerts generated today")
c2.metric("Critical Alerts Today", f"{(today_alarms['severity']=='Critical').sum():,}", help="Alerts that need immediate attention")
c3.metric("Devices with Problems", f"{today_alarms['asset_id'].nunique():,}", help="Number of unique devices that generated alerts")
c4.metric("Unresponded Alerts",    f"{(~today_alarms['acknowledged']).sum():,}", help="Alerts that nobody has responded to yet")

st.divider()

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Adjust the View")
col1, col2 = st.columns(2)
with col1:
    days = st.slider(
        "How many days back to show?",
        7, 90, 30,
        help="Slide to see more or fewer days of history"
    )
with col2:
    locs = st.multiselect(
        "Which location?",
        alarms["location"].unique().tolist(),
        default=alarms["location"].unique().tolist(),
        help="Filter by data center location"
    )

cutoff   = alarms["timestamp"].max() - pd.Timedelta(days=days)
filtered = alarms[
    (alarms["location"].isin(locs)) &
    (alarms["timestamp"] >= cutoff)
]

st.divider()

# ── Alert trend ───────────────────────────────────────────────
st.subheader(f"📈 Alert Trend — Last {days} Days")
st.caption("This shows how many alerts were generated each day. If the bars are getting taller — problems are increasing.")

daily = filtered.set_index("timestamp").resample("D").size().reset_index()
daily.columns = ["Date","Number of Alerts"]
avg   = daily["Number of Alerts"].mean()

fig = px.bar(
    daily, x="Date", y="Number of Alerts",
    color_discrete_sequence=["#E24B4A"], height=280
)
fig.add_hline(
    y=avg, line_dash="dash",
    line_color="orange",
    annotation_text=f"Average: {avg:.0f} alerts/day",
    annotation_position="top right"
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    yaxis_title="Number of Alerts",
    xaxis_title=""
)
st.plotly_chart(fig, use_container_width=True)
st.caption(f"💡 Average is {avg:.0f} alerts per day. Days above this average need investigation.")
st.divider()

# ── Alert breakdown by type ────────────────────────────────────
st.subheader("🔴 What Kind of Alerts Are Happening?")
st.caption("The most common types of alerts — these tell you what problems are occurring most often")

event_map = {
    "LinkDown":         "Network Link Failure",
    "HighCPU":          "High CPU Usage",
    "HighMemory":       "High Memory Usage",
    "DiskFull":         "Disk Full",
    "PacketLoss":       "Network Packet Loss",
    "LatencySpike":     "Slow Response Time",
    "AuthFailure":      "Failed Login Attempt",
    "HardwareError":    "Hardware Problem",
    "ConfigChange":     "Configuration Change",
    "ReachabilityLost": "Device Unreachable",
}
filtered["Alert Type"] = filtered["event_type"].map(event_map).fillna(filtered["event_type"])
event_counts = filtered["Alert Type"].value_counts().reset_index()
event_counts.columns = ["Alert Type","Count"]

fig2 = px.bar(
    event_counts, x="Count", y="Alert Type",
    orientation="h",
    color_discrete_sequence=["#378ADD"],
    height=350, text="Count"
)
fig2.update_traces(textposition="outside")
fig2.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    xaxis_title="How Many Times This Happened",
    yaxis_title=""
)
st.plotly_chart(fig2, use_container_width=True)
st.divider()

# ── Resource health ───────────────────────────────────────────
st.subheader("💻 Are Devices Healthy?")
st.caption("These 3 numbers tell you the overall health of your infrastructure")

logs["date"] = pd.to_datetime(logs["date"])
ld = logs.groupby("date")[["avg_cpu_pct","avg_mem_pct","avg_latency_ms"]].mean().reset_index()

ca, cb, cc = st.columns(3)
metrics = [
    (ca, "avg_cpu_pct",    "CPU Usage",           "#E24B4A", 70, 85,  "%"),
    (cb, "avg_mem_pct",    "Memory Usage",         "#378ADD", 75, 90,  "%"),
    (cc, "avg_latency_ms", "Response Time",        "#888780", 200, 400, "ms"),
]
for col, metric, label, color, warn_th, crit_th, unit in metrics:
    latest = ld[metric].iloc[-1]
    if latest >= crit_th:
        status = "🔴 Critical"
    elif latest >= warn_th:
        status = "🟡 Warning"
    else:
        status = "🟢 Healthy"

    col.metric(
        f"{label} — {status}",
        f"{latest:.1f}{unit}",
        help=f"Green below {warn_th}{unit} | Yellow {warn_th}-{crit_th}{unit} | Red above {crit_th}{unit}"
    )
    fs = px.line(ld, x="date", y=metric, height=180,
                 color_discrete_sequence=[color])
    fs.add_hline(y=warn_th, line_dash="dash", line_color="orange")
    fs.add_hline(y=crit_th, line_dash="dash", line_color="red")
    fs.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=0,l=0,r=0),
        showlegend=False,
        yaxis_title="", xaxis_title=""
    )
    col.plotly_chart(fs, use_container_width=True)
    col.caption(f"🟢 Good: below {warn_th}{unit} | 🟡 Warning: {warn_th}-{crit_th}{unit} | 🔴 Critical: above {crit_th}{unit}")

st.divider()

# ── ALL problematic devices ────────────────────────────────────
st.subheader("📋 All Devices with Alerts")
st.caption("Every device that generated alerts — sorted by number of alerts")

device_alerts = (
    filtered.groupby("asset_id").size()
    .reset_index(name="Number of Alerts")
    .sort_values("Number of Alerts", ascending=False)
)
device_alerts = device_alerts.merge(
    preds[["asset_id","risk_level","recommended_action"]], on="asset_id", how="left"
)
device_alerts["Risk Status"] = device_alerts["risk_level"].map({
    "CRITICAL": "🟣 Emergency — Act Now",
    "HIGH":     "🔴 Urgent — Escalate Today",
    "MEDIUM":   "🟡 Schedule Maintenance",
    "LOW":      "🟢 Monitor Only"
})
device_alerts = device_alerts[["asset_id","Number of Alerts","Risk Status","recommended_action"]]
device_alerts.columns = ["Device ID","Number of Alerts","Risk Status","What To Do"]

st.caption(f"Showing all {len(device_alerts):,} devices with alerts")
st.dataframe(device_alerts, use_container_width=True, hide_index=True, height=400)
