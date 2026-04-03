# ============================================================
# Page 1 — Executive Overview
# Top-level KPIs and health summary for the C-suite.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import (
    load_assets, load_alarms, load_tickets, load_predictions
)
from setup.config import RISK_LABELS

st.title("🏠 Executive Overview")
st.caption("AI-driven proactive infrastructure health at a glance")
st.divider()

# ── Load data ─────────────────────────────────────────────────
assets  = load_assets()
alarms  = load_alarms()
tickets = load_tickets()
preds   = load_predictions()

alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
tickets["open_time"] = pd.to_datetime(tickets["open_time"])

# ── KPI row ───────────────────────────────────────────────────
high   = (preds["risk_level"] == "HIGH").sum()
medium = (preds["risk_level"] == "MEDIUM").sum()
total  = len(assets)
crit_alarms = (alarms["severity"] == "Critical").sum()
open_tickets = tickets[tickets["status"].isin(["Open","In Progress"])].shape[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Assets",        f"{total:,}")
c2.metric("🔴 HIGH Risk Assets", f"{high:,}",   delta=f"+{high} urgent", delta_color="inverse")
c3.metric("🟡 MEDIUM Risk",      f"{medium:,}")
c4.metric("Critical Alarms",     f"{crit_alarms:,}")
c5.metric("Open Tickets",        f"{open_tickets:,}")

st.divider()

# ── Risk distribution donut ───────────────────────────────────
col_a, col_b = st.columns([1, 2])

with col_a:
    st.subheader("Asset Risk Distribution")
    risk_counts = preds["risk_level"].value_counts().reset_index()
    risk_counts.columns = ["Risk Level", "Count"]
    color_map = {"HIGH": "#E24B4A", "MEDIUM": "#EF9F27", "LOW": "#639922"}
    fig_donut = px.pie(
        risk_counts, values="Count", names="Risk Level",
        hole=0.55,
        color="Risk Level",
        color_discrete_map=color_map,
    )
    fig_donut.update_layout(
        showlegend=True, height=300, margin=dict(t=10, b=10, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with col_b:
    st.subheader("Daily Critical Alarms (Last 30 Days)")
    recent = alarms[alarms["severity"].isin(["Critical","Major"])]
    recent = recent[alarms["timestamp"] >= alarms["timestamp"].max() - pd.Timedelta(days=30)]
    daily  = recent.set_index("timestamp").resample("D").size().reset_index()
    daily.columns = ["Date", "Count"]
    fig_bar = px.bar(
        daily, x="Date", y="Count",
        color_discrete_sequence=["#E24B4A"],
    )
    fig_bar.update_layout(
        height=300, margin=dict(t=10,b=10,l=0,r=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Top HIGH risk assets table ────────────────────────────────
st.subheader("Top 10 High-Risk Assets — Immediate Action Required")
top_risk = preds[preds["risk_level"] == "HIGH"].sort_values(
    "failure_probability", ascending=False
).head(10)[["asset_id","criticality","lifecycle_age_yrs",
            "failure_probability","recommended_action"]].copy()

top_risk["failure_probability"] = (top_risk["failure_probability"] * 100).round(1).astype(str) + "%"
top_risk.columns = ["Asset ID","Criticality","Age (yrs)","Failure Prob.","Recommended Action"]
st.dataframe(top_risk, use_container_width=True, hide_index=True)
