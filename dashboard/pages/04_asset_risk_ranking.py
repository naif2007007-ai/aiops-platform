import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_predictions

st.title("📊 Device Priority List")
st.caption("All 2,000 devices ranked from most urgent to healthiest — your complete action list")
st.divider()

preds = load_predictions()

# Priority score
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

# ── Simple explanation ────────────────────────────────────────
st.info("""
**How to use this page:**
- Rank 1 = Most urgent device — fix this first
- The higher the Priority Score — the more urgent
- Use the filters below to focus on specific groups
- Export the table to share with your team
""")

# ── Summary ───────────────────────────────────────────────────
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Devices",      f"{len(df):,}")
c2.metric("Fix Immediately",    f"{(df['risk_level'].isin(['CRITICAL','HIGH'])).sum():,}",
          help="CRITICAL + HIGH risk devices")
c3.metric("Schedule This Week", f"{(df['risk_level']=='MEDIUM').sum():,}",
          help="MEDIUM risk devices")
c4.metric("No Action Needed",   f"{(df['risk_level']=='LOW').sum():,}",
          help="LOW risk — healthy devices")
st.divider()

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Filter the List")
col1, col2, col3 = st.columns(3)
risk_f = col1.multiselect(
    "Risk Level",
    ["CRITICAL","HIGH","MEDIUM","LOW"],
    default=["CRITICAL","HIGH","MEDIUM","LOW"],
    help="Select which risk levels to show"
)
crit_f = col2.multiselect(
    "Device Importance",
    df["criticality"].unique().tolist(),
    default=df["criticality"].unique().tolist(),
    help="Filter by how critical the device is to operations"
)
search = col3.text_input(
    "Search by Device ID",
    "",
    help="Type a device ID to find it quickly"
)

view = df[
    (df["risk_level"].isin(risk_f)) &
    (df["criticality"].isin(crit_f))
]
if search:
    view = view[view["asset_id"].str.contains(search.upper(), na=False)]

st.caption(f"Showing {len(view):,} devices")
st.divider()

# ── Priority chart for top 30 ─────────────────────────────────
st.subheader("🎯 Top 30 Most Urgent Devices")
st.caption("These are your most urgent devices — the longer the bar the more urgent")

top30 = view.head(30).copy()
top30["Status"] = top30["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule Soon",
    "LOW":      "🟢 Healthy"
})
fig = px.bar(
    top30.sort_values("priority_score"),
    x="priority_score", y="asset_id",
    orientation="h",
    color="Status",
    color_discrete_map={
        "🟣 Emergency":    "#7B2D8B",
        "🔴 Urgent":       "#E24B4A",
        "🟡 Schedule Soon":"#EF9F27",
        "🟢 Healthy":      "#639922"
    },
    height=600,
    labels={"priority_score":"Priority Score","asset_id":"Device ID"}
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    yaxis=dict(tickfont=dict(size=9)),
    xaxis_title="Priority Score (higher = more urgent)",
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Complete table ────────────────────────────────────────────
st.subheader("📋 Complete Priority List — All Devices")
st.caption("Use this as your daily work order — Rank 1 = fix first")

disp = view[[
    "priority_rank","asset_id","criticality",
    "lifecycle_age_yrs","failure_probability",
    "days_since_maintenance","risk_level","recommended_action"
]].copy()

disp["failure_probability"]    = (disp["failure_probability"]*100).round(1).astype(str)+"%"
disp["lifecycle_age_yrs"]      = disp["lifecycle_age_yrs"].round(1)
disp["days_since_maintenance"] = disp["days_since_maintenance"].astype(int)
disp["risk_level"]             = disp["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule Soon",
    "LOW":      "🟢 Healthy"
})
disp.columns = [
    "Rank","Device ID","Importance",
    "Age (yrs)","Failure Risk",
    "Days Since Service","Status","What To Do"
]
st.dataframe(disp, use_container_width=True, hide_index=True, height=500)
