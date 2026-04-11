import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform"))
from dashboard.data_loader import load_alarms, load_logs, load_predictions

st.title("📡 Operations Monitoring")
st.caption("Live view of alerts and device health across all locations")
st.divider()

alarms = load_alarms()
logs   = load_logs()
preds  = load_predictions()
alarms["timestamp"] = pd.to_datetime(alarms["timestamp"])

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Filter the View")
col1, col2, col3 = st.columns(3)
with col1:
    days = st.slider("Show last N days", 7, 90, 30)
with col2:
    locs = st.multiselect(
        "Location",
        alarms["location"].unique().tolist(),
        default=alarms["location"].unique().tolist()
    )
with col3:
    sevs = st.multiselect(
        "Alert Severity",
        ["Critical","Major","Minor","Warning"],
        default=["Critical","Major"]
    )

cutoff   = alarms["timestamp"].max() - pd.Timedelta(days=days)
filtered = alarms[
    (alarms["severity"].isin(sevs)) &
    (alarms["location"].isin(locs)) &
    (alarms["timestamp"] >= cutoff)
]
st.caption(f"Showing {len(filtered):,} alerts from the last {days} days")
st.divider()

# ── KPI row ───────────────────────────────────────────────────
st.subheader("Alert Summary")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Alerts",      f"{len(filtered):,}")
c2.metric("Critical Alerts",   f"{(filtered['severity']=='Critical').sum():,}")
c3.metric("Unacknowledged",    f"{(~filtered['acknowledged']).sum():,}")
c4.metric("Devices Affected",  f"{filtered['asset_id'].nunique():,}")
st.divider()

# ── Alert trend ───────────────────────────────────────────────
st.subheader("📈 Alert Trend — Are Things Getting Better or Worse?")
st.caption("If bars are getting taller over time — the situation is getting worse")
daily = filtered.set_index("timestamp").resample("D").size().reset_index()
daily.columns = ["Date","Number of Alerts"]
fig = px.bar(daily, x="Date", y="Number of Alerts",
             color_discrete_sequence=["#E24B4A"], height=280)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0)
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Resource health ───────────────────────────────────────────
st.subheader("💻 Device Resource Health")
st.caption("Average CPU, Memory and Response Time across all devices")
logs["date"] = pd.to_datetime(logs["date"])
ld = logs.groupby("date")[["avg_cpu_pct","avg_mem_pct","avg_latency_ms"]].mean().reset_index()

ca, cb, cc = st.columns(3)
for col, metric, label, color, good, bad in [
    (ca, "avg_cpu_pct",    "Average CPU Usage %",        "#E24B4A", "Below 70% is healthy", "Above 85% is critical"),
    (cb, "avg_mem_pct",    "Average Memory Usage %",     "#378ADD", "Below 75% is healthy", "Above 90% is critical"),
    (cc, "avg_latency_ms", "Average Response Time (ms)", "#888780", "Below 200ms is healthy","Above 400ms is critical"),
]:
    latest = ld[metric].iloc[-1]
    fs = px.line(ld, x="date", y=metric, height=200,
                 color_discrete_sequence=[color])
    fs.update_layout(
        title_text=f"{label}: {latest:.1f}",
        title_font_size=13,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30,b=0,l=0,r=0),
        showlegend=False,
        yaxis_title="", xaxis_title=""
    )
    col.plotly_chart(fs, use_container_width=True)
    col.caption(f"✅ {good} | ⚠️ {bad}")

st.divider()

# ── Top problem devices ────────────────────────────────────────
st.subheader("🔥 Top 10 Most Problematic Devices")
st.caption("These devices are generating the most alerts — investigate first")
top = (filtered.groupby("asset_id").size()
       .reset_index(name="Alert Count")
       .sort_values("Alert Count", ascending=False)
       .head(10))
top = top.merge(preds[["asset_id","risk_level"]], on="asset_id", how="left")
top["Risk"] = top["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Monitor",
    "LOW":      "🟢 Healthy"
})
top = top[["asset_id","Alert Count","Risk"]]
top.columns = ["Device ID","Number of Alerts","Current Risk Status"]
st.dataframe(top, use_container_width=True, hide_index=True)
