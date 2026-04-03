# ============================================================
# Page 2 — Operations Monitoring
# Real-time alarm and log view with severity breakdown.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import load_alarms, load_logs, load_assets

st.title("📡 Operations Monitoring")
st.caption("Live view of alarms, log anomalies, and resource utilisation")
st.divider()

alarms = load_alarms()
logs   = load_logs()
assets = load_assets()

alarms["timestamp"] = pd.to_datetime(alarms["timestamp"])

# ── Filters ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    severities = st.multiselect(
        "Severity", alarms["severity"].unique().tolist(),
        default=["Critical","Major"]
    )
with col2:
    locations = st.multiselect(
        "Location", alarms["location"].unique().tolist(),
        default=alarms["location"].unique().tolist()
    )
with col3:
    days_back = st.slider("Days back", 7, 90, 30)

# ── Filter ────────────────────────────────────────────────────
cutoff = alarms["timestamp"].max() - pd.Timedelta(days=days_back)
filtered = alarms[
    (alarms["severity"].isin(severities)) &
    (alarms["location"].isin(locations)) &
    (alarms["timestamp"] >= cutoff)
].copy()

st.caption(f"Showing {len(filtered):,} alarms")

# ── Severity heatmap over time ────────────────────────────────
st.subheader("Alarm Frequency by Severity")
pivot = (
    filtered.set_index("timestamp")
    .resample("D")["severity"]
    .value_counts()
    .unstack(fill_value=0)
    .reset_index()
)
# Melt for plotly
melted = pivot.melt(id_vars="timestamp", var_name="Severity", value_name="Count")
sev_colors = {
    "Critical":"#E24B4A","Major":"#EF9F27",
    "Minor":"#639922","Warning":"#378ADD","Informational":"#888780"
}
fig = px.area(
    melted, x="timestamp", y="Count", color="Severity",
    color_discrete_map=sev_colors, height=320,
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── CPU / Memory / Latency sparklines ─────────────────────────
st.subheader("Infrastructure Health Metrics (average across all assets)")
logs["date"] = pd.to_datetime(logs["date"])
log_daily = logs.groupby("date")[["avg_cpu_pct","avg_mem_pct","avg_latency_ms"]].mean().reset_index()

col_a, col_b, col_c = st.columns(3)
for col, metric, label, color in [
    (col_a, "avg_cpu_pct",   "Avg CPU %",      "#D85A30"),
    (col_b, "avg_mem_pct",   "Avg Memory %",   "#378ADD"),
    (col_c, "avg_latency_ms","Avg Latency (ms)","#9C9A92"),
]:
    fig_s = px.line(log_daily, x="date", y=metric, height=200,
                    color_discrete_sequence=[color])
    fig_s.update_layout(
        title_text=label, title_font_size=13,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30,b=0,l=0,r=0), showlegend=False,
        yaxis_title="", xaxis_title="",
    )
    col.plotly_chart(fig_s, use_container_width=True)

# ── Top noisy assets ─────────────────────────────────────────
st.subheader("Top 15 Noisiest Assets")
top_noisy = (
    filtered.groupby("asset_id").size()
    .reset_index(name="alarm_count")
    .sort_values("alarm_count", ascending=False)
    .head(15)
)
fig_bar = px.bar(
    top_noisy, x="asset_id", y="alarm_count",
    color_discrete_sequence=["#E24B4A"], height=280,
    labels={"asset_id":"Asset","alarm_count":"Alarms"},
)
fig_bar.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_bar, use_container_width=True)
