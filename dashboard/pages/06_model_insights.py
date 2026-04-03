# ============================================================
# Page 6 — Model Insights
# Feature importance, model performance, and explainability.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import load_feat_importance, load_predictions, load_features

st.title("🧠 Model Insights")
st.caption("Explainability, feature importance, and model performance")
st.divider()

fi       = load_feat_importance()
preds    = load_predictions()
features = load_features()

# ── Feature importance bar ────────────────────────────────────
st.subheader("Top Features Driving Failure Predictions")
top_fi = fi.head(20).sort_values("importance")
fig_fi = px.bar(
    top_fi, x="importance", y="feature", orientation="h",
    color="importance",
    color_continuous_scale=["#9FE1CB","#1D9E75","#085041"],
    height=450,
    labels={"importance":"Importance Score","feature":"Feature"},
)
fig_fi.update_layout(
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    coloraxis_showscale=False,
)
st.plotly_chart(fig_fi, use_container_width=True)

# ── Distribution of failure probabilities ────────────────────
st.subheader("Failure Probability Distribution")
fig_hist = px.histogram(
    preds, x="failure_probability", nbins=30,
    color="risk_level",
    color_discrete_map={"HIGH":"#E24B4A","MEDIUM":"#EF9F27","LOW":"#639922"},
    barmode="overlay",
    opacity=0.75,
    labels={"failure_probability":"Failure Probability"},
    height=300,
)
fig_hist.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_hist, use_container_width=True)

# ── Anomaly score vs failure probability density ──────────────
st.subheader("Anomaly Score vs Failure Probability Density")
fig_d = px.density_heatmap(
    preds, x="anomaly_score", y="failure_probability",
    nbinsx=25, nbinsy=25,
    color_continuous_scale="Plasma",
    height=340,
)
fig_d.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_d, use_container_width=True)

# ── Model info card ───────────────────────────────────────────
st.divider()
st.subheader("Model Configuration")
col1, col2 = st.columns(2)
with col1:
    st.info("""
**Model 1 — Isolation Forest**
- Type: Unsupervised anomaly detection
- Estimators: 200
- Contamination: 12%
- Output: anomaly_score ∈ [0, 1]
""")
with col2:
    st.info("""
**Model 2 — Random Forest Classifier**
- Type: Supervised binary classification
- Estimators: 300
- Max depth: 8
- Class weights: balanced
- Output: failure_probability ∈ [0, 1]
""")
