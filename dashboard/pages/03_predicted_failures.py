import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform"))
from dashboard.data_loader import load_predictions, load_features

st.title("⚠️ Predicted Failures")
st.caption("Devices the AI predicts will fail — ranked by urgency")
st.divider()

preds = load_predictions()
feat  = load_features()
df    = preds.merge(
    feat[["asset_id","alarm_count_30d","ticket_p1_count",
          "log_anomaly_days","avg_cpu","days_since_maintenance"]],
    on="asset_id", how="left"
)

# ── Summary banner ────────────────────────────────────────────
critical = (df["risk_level"]=="CRITICAL").sum()
high     = (df["risk_level"]=="HIGH").sum()
medium   = (df["risk_level"]=="MEDIUM").sum()

st.error(f"🟣 {critical} devices need EMERGENCY response — engage L3 and vendor immediately")
st.warning(f"🔴 {high} devices need URGENT attention — escalate to L2 within 24 hours")
st.info(f"🟡 {medium} devices need maintenance — schedule within 48 hours")
st.divider()

# ── Filters ───────────────────────────────────────────────────
col1, col2 = st.columns(2)
risk_filter = col1.multiselect(
    "Show risk levels",
    ["CRITICAL","HIGH","MEDIUM","LOW"],
    default=["CRITICAL","HIGH","MEDIUM"]
)
crit_filter = col2.multiselect(
    "Device importance",
    df["criticality"].unique().tolist(),
    default=df["criticality"].unique().tolist()
)

view = df[
    (df["risk_level"].isin(risk_filter)) &
    (df["criticality"].isin(crit_filter))
].sort_values("failure_probability", ascending=False)

st.caption(f"Showing {len(view):,} devices")
st.divider()

# ── Risk distribution bar ─────────────────────────────────────
st.subheader("📊 How Many Devices at Each Risk Level?")
rc = view["risk_level"].value_counts().reset_index()
rc.columns = ["Risk Level","Count"]
rc["Risk Level"] = rc["Risk Level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule Soon",
    "LOW":      "🟢 Healthy"
})
fig = px.bar(rc, x="Risk Level", y="Count",
             color="Risk Level",
             color_discrete_map={
                 "🟣 Emergency":    "#7B2D8B",
                 "🔴 Urgent":       "#E24B4A",
                 "🟡 Schedule Soon":"#EF9F27",
                 "🟢 Healthy":      "#639922"
             }, height=280,
             text="Count")
fig.update_traces(textposition="outside")
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    showlegend=False,
    xaxis_title="", yaxis_title="Number of Devices"
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Action table ──────────────────────────────────────────────
st.subheader("📋 Full Device List — Sorted by Urgency")
st.caption("Start from the top — these devices need attention first")

disp = view[[
    "asset_id","criticality","lifecycle_age_yrs",
    "failure_probability","days_since_maintenance",
    "alarm_count_30d","avg_cpu","risk_level","recommended_action"
]].copy()

disp["failure_probability"]    = (disp["failure_probability"]*100).round(1).astype(str)+"%"
disp["lifecycle_age_yrs"]      = disp["lifecycle_age_yrs"].round(1)
disp["days_since_maintenance"] = disp["days_since_maintenance"].astype(int)
disp["avg_cpu"]                = disp["avg_cpu"].round(1).astype(str)+"%"
disp["alarm_count_30d"]        = disp["alarm_count_30d"].astype(int)
disp["risk_level"]             = disp["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Soon",
    "LOW":      "🟢 Healthy"
})

disp.columns = [
    "Device ID","Importance","Age (yrs)",
    "Failure Risk","Days Since Service",
    "Alerts (30d)","CPU Usage","Status","Action Required"
]
st.dataframe(disp, use_container_width=True, hide_index=True)
