# ============================================================
# Page 3 — Predicted Failures
# ML-driven failure probability with recommended actions.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import load_predictions, load_features
from setup.config import RISK_LABELS

st.title("⚠️ Predicted Failures")
st.caption("AI-predicted failure risk with anomaly scores and recommended actions")
st.divider()

preds    = load_predictions()
features = load_features()

# Merge anomaly score etc.
df = preds.merge(
    features[["asset_id","alarm_count_total","ticket_count",
              "log_anomaly_days","avg_cpu","avg_mem"]],
    on="asset_id", how="left"
)

# ── Filters ───────────────────────────────────────────────────
col1, col2 = st.columns(2)
risk_filter = col1.multiselect("Risk Level", ["HIGH","MEDIUM","LOW"],
                                default=["HIGH","MEDIUM"])
crit_filter = col2.multiselect("Criticality", df["criticality"].unique().tolist(),
                                default=df["criticality"].unique().tolist())

view = df[
    (df["risk_level"].isin(risk_filter)) &
    (df["criticality"].isin(crit_filter))
].sort_values("failure_probability", ascending=False)

st.caption(f"{len(view):,} assets match filters")

# ── Scatter: failure_probability vs anomaly_score ─────────────
st.subheader("Failure Probability vs Anomaly Score")
fig_scatter = px.scatter(
    view,
    x="anomaly_score", y="failure_probability",
    color="risk_level",
    size="lifecycle_age_yrs",
    hover_name="asset_id",
    hover_data=["criticality","recommended_action"],
    color_discrete_map={"HIGH":"#E24B4A","MEDIUM":"#EF9F27","LOW":"#639922"},
    labels={"anomaly_score":"Anomaly Score","failure_probability":"Failure Probability"},
    height=400,
)
fig_scatter.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Full table ────────────────────────────────────────────────
st.subheader("Asset Failure Predictions")

display = view[[
    "asset_id","criticality","lifecycle_age_yrs",
    "failure_probability","anomaly_score","risk_level","recommended_action"
]].copy()

display["failure_probability"] = (display["failure_probability"] * 100).round(1).astype(str) + "%"
display["anomaly_score"]       = display["anomaly_score"].round(3)

# Colour-code risk_level via a function
def highlight_risk(val):
    colours = {"HIGH":"#5a0000","MEDIUM":"#3d2800","LOW":"#1a2e00"}
    return f"color: {colours.get(val,'')}"

styled = (
    display.rename(columns={
        "asset_id":"Asset","criticality":"Criticality",
        "lifecycle_age_yrs":"Age (yrs)","failure_probability":"Fail Prob.",
        "anomaly_score":"Anomaly Score","risk_level":"Risk",
        "recommended_action":"Action",
    })
    .style.map(highlight_risk, subset=["Risk"])
)
st.dataframe(styled, use_container_width=True, hide_index=True)
