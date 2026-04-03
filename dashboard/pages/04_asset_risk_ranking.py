# ============================================================
# Page 4 — Asset Risk Ranking
# Ranked view with criticality, age, and composite risk score.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import load_predictions, load_assets, load_features

st.title("📊 Asset Risk Ranking")
st.caption("Composite risk score = failure probability × criticality weight × age factor")
st.divider()

preds    = load_predictions()
assets   = load_assets()
features = load_features()

# Composite risk score
crit_w = {"Critical": 2.0, "High": 1.5, "Medium": 1.0, "Low": 0.6}
df = preds.copy()
df["criticality_weight"] = df["criticality"].map(crit_w).fillna(1.0)
max_age = df["lifecycle_age_yrs"].max()
df["composite_risk"] = (
    df["failure_probability"]
    * df["criticality_weight"]
    * (1 + df["lifecycle_age_yrs"] / max_age * 0.3)
).round(4)
df["rank"] = df["composite_risk"].rank(ascending=False).astype(int)
df = df.sort_values("rank")

# ── Filters ───────────────────────────────────────────────────
col1, col2 = st.columns(2)
top_n   = col1.slider("Show top N assets", 10, 100, 30)
crit_f  = col2.multiselect("Criticality filter",
                            df["criticality"].unique().tolist(),
                            default=df["criticality"].unique().tolist())

view = df[df["criticality"].isin(crit_f)].head(top_n)

# ── Horizontal bar chart ──────────────────────────────────────
st.subheader(f"Top {top_n} Assets by Composite Risk Score")
fig = px.bar(
    view.sort_values("composite_risk"),
    x="composite_risk", y="asset_id",
    orientation="h",
    color="risk_level",
    color_discrete_map={"HIGH":"#E24B4A","MEDIUM":"#EF9F27","LOW":"#639922"},
    height=max(300, top_n * 18),
    labels={"composite_risk":"Composite Risk","asset_id":"Asset"},
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig, use_container_width=True)

# ── Bubble chart: age vs failure_prob, size=criticality ──────
st.subheader("Age vs Failure Probability")
fig2 = px.scatter(
    view,
    x="lifecycle_age_yrs", y="failure_probability",
    color="risk_level",
    size="composite_risk",
    hover_name="asset_id",
    color_discrete_map={"HIGH":"#E24B4A","MEDIUM":"#EF9F27","LOW":"#639922"},
    labels={"lifecycle_age_yrs":"Asset Age (yrs)","failure_probability":"Failure Probability"},
    height=360,
)
fig2.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig2, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────
st.subheader("Ranked Asset Table")
display = view[[
    "rank","asset_id","criticality","lifecycle_age_yrs",
    "failure_probability","composite_risk","risk_level","recommended_action"
]].copy()
display["failure_probability"] = (display["failure_probability"] * 100).round(1).astype(str) + "%"
display.columns = ["Rank","Asset","Criticality","Age","Fail Prob.","Risk Score","Risk","Action"]
st.dataframe(display, use_container_width=True, hide_index=True)
