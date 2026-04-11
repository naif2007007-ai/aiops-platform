import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform"))
from dashboard.data_loader import load_predictions, load_features

st.title("📊 Device Priority List")
st.caption("All devices ranked from most urgent to healthiest — your action list for today")
st.divider()

preds = load_predictions()
feat  = load_features()

# Composite priority score
crit_w = {"Critical":4,"High":3,"Medium":2,"Low":1}
df = preds.copy()
df["importance_weight"] = df["criticality"].map(crit_w).fillna(1.0)
df["priority_score"]    = (
    df["failure_probability"] *
    df["importance_weight"] *
    (1 + df["lifecycle_age_yrs"] / df["lifecycle_age_yrs"].max() * 0.3)
).round(4)
df["priority_rank"] = df["priority_score"].rank(ascending=False).astype(int)
df = df.sort_values("priority_rank")

# ── Summary ───────────────────────────────────────────────────
st.subheader("Today's Maintenance Priority")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Devices",     f"{len(df):,}")
c2.metric("Fix Immediately",   f"{(df['risk_level'].isin(['CRITICAL','HIGH'])).sum():,}")
c3.metric("Schedule This Week",f"{(df['risk_level']=='MEDIUM').sum():,}")
c4.metric("No Action Needed",  f"{(df['risk_level']=='LOW').sum():,}")
st.divider()

# ── Filters ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
top_n   = col1.slider("Show top N devices", 10, 100, 20)
crit_f  = col2.multiselect(
    "Device importance",
    df["criticality"].unique().tolist(),
    default=df["criticality"].unique().tolist()
)
risk_f  = col3.multiselect(
    "Risk level",
    ["CRITICAL","HIGH","MEDIUM","LOW"],
    default=["CRITICAL","HIGH","MEDIUM"]
)

view = df[
    (df["criticality"].isin(crit_f)) &
    (df["risk_level"].isin(risk_f))
].head(top_n)

# ── Priority chart ────────────────────────────────────────────
st.subheader(f"🎯 Top {top_n} Devices Needing Attention")
st.caption("Longer bar = higher priority. Start from the top.")

view_chart = view.copy()
view_chart["Device"] = view_chart["asset_id"]
view_chart["Status"] = view_chart["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule Soon",
    "LOW":      "🟢 Healthy"
})

fig = px.bar(
    view_chart.sort_values("priority_score"),
    x="priority_score",
    y="Device",
    orientation="h",
    color="Status",
    color_discrete_map={
        "🟣 Emergency":    "#7B2D8B",
        "🔴 Urgent":       "#E24B4A",
        "🟡 Schedule Soon":"#EF9F27",
        "🟢 Healthy":      "#639922"
    },
    height=max(300, top_n*22),
    labels={"priority_score":"Priority Score","Device":"Device ID"}
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    yaxis=dict(tickfont=dict(size=10)),
    xaxis_title="Priority Score (higher = more urgent)",
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Priority table ────────────────────────────────────────────
st.subheader("📋 Complete Priority List")
st.caption("Use this as your daily work order — start from rank 1")

disp = view[[
    "priority_rank","asset_id","criticality",
    "lifecycle_age_yrs","failure_probability",
    "risk_level","recommended_action"
]].copy()

disp["failure_probability"] = (disp["failure_probability"]*100).round(1).astype(str)+"%"
disp["lifecycle_age_yrs"]   = disp["lifecycle_age_yrs"].round(1)
disp["risk_level"]          = disp["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule Soon",
    "LOW":      "🟢 Healthy"
})
disp.columns = [
    "Priority","Device ID","Importance",
    "Age (yrs)","Failure Risk",
    "Status","What To Do"
]
st.dataframe(disp, use_container_width=True, hide_index=True)
