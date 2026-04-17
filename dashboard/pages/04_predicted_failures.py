import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions

st.title("⚠️ Predicted Failures & Actions")
st.caption("AI-predicted failures ranked by urgency — your complete action list")
st.divider()

assets = load_assets()
preds  = load_predictions()

df = preds.merge(
    assets[["asset_id","division","device_type","model",
            "lifecycle_age_yrs","days_since_maintenance",
            "battery_age_yrs","criticality"]],
    on="asset_id", how="left"
)

# ── Summary banners ───────────────────────────────────────────
critical = (df["risk_level"]=="CRITICAL").sum()
high     = (df["risk_level"]=="HIGH").sum()
medium   = (df["risk_level"]=="MEDIUM").sum()
low      = (df["risk_level"]=="LOW").sum()

st.error(f"🟣 {critical} devices — EMERGENCY: Engage L3 and vendor immediately")
st.warning(f"🔴 {high} devices — URGENT: Escalate to L2 within 24 hours")
st.info(f"🟡 {medium} devices — SCHEDULE: Assign to L1 within 48 hours")
st.success(f"🟢 {low} devices — HEALTHY: No action needed")
st.divider()

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Filter the List")
col1, col2, col3 = st.columns(3)
risk_filter = col1.multiselect(
    "Risk Level",
    ["CRITICAL","HIGH","MEDIUM","LOW"],
    default=["CRITICAL","HIGH","MEDIUM","LOW"]
)
div_filter = col2.multiselect(
    "Division",
    sorted(df["division"].unique().tolist()),
    default=sorted(df["division"].unique().tolist())
)
type_filter = col3.multiselect(
    "Device Type",
    ["Router","Switch","UPS"],
    default=["Router","Switch","UPS"]
)

view = df[
    (df["risk_level"].isin(risk_filter)) &
    (df["division"].isin(div_filter)) &
    (df["device_type"].isin(type_filter))
].sort_values("failure_probability", ascending=False)

st.caption(f"Showing {len(view):,} devices")
st.divider()

# ── Risk distribution ─────────────────────────────────────────
st.subheader("📊 Risk Distribution by Division and Device Type")
col_a, col_b = st.columns(2)

with col_a:
    st.caption("Risk levels by division")
    div_risk = view.groupby(["division","risk_level"]).size().reset_index(name="count")
    div_risk["risk_level"] = div_risk["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    fig = px.bar(div_risk, x="division", y="count",
                 color="risk_level",
                 color_discrete_map={
                     "🟣 Emergency":"#7B2D8B","🔴 Urgent":"#E24B4A",
                     "🟡 Schedule":"#EF9F27","🟢 Healthy":"#639922"
                 },
                 barmode="stack", height=300,
                 labels={"division":"Division","count":"Devices"})
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="", yaxis_title="Devices"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.caption("Risk levels by device type")
    type_risk = view.groupby(["device_type","risk_level"]).size().reset_index(name="count")
    type_risk["risk_level"] = type_risk["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    fig2 = px.bar(type_risk, x="device_type", y="count",
                  color="risk_level",
                  color_discrete_map={
                      "🟣 Emergency":"#7B2D8B","🔴 Urgent":"#E24B4A",
                      "🟡 Schedule":"#EF9F27","🟢 Healthy":"#639922"
                  },
                  barmode="stack", height=300,
                  labels={"device_type":"Device Type","count":"Devices"})
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="", yaxis_title="Devices"
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Complete action table ─────────────────────────────────────
st.subheader("📋 Complete Action List — All Devices")
st.caption("Sorted by urgency — Rank 1 needs attention first")

view["Failure Risk"]        = (view["failure_probability"]*100).round(1).astype(str)+"%"
view["Age (yrs)"]           = view["lifecycle_age_yrs"].round(1)
view["Days Since Service"]  = view["days_since_maintenance"].astype(int)
view["Status"]              = view["risk_level"].map({
    "CRITICAL":"🟣 Emergency",
    "HIGH":    "🔴 Urgent",
    "MEDIUM":  "🟡 Schedule Soon",
    "LOW":     "🟢 Healthy"
})

# Add battery warning for UPS
def get_action(row):
    action = row["recommended_action"]
    if row["device_type"] == "UPS" and row.get("battery_age_yrs", 0) >= 3.5:
        action = "⚡ REPLACE BATTERY + " + action
    return action

view["What To Do"] = view.apply(get_action, axis=1)

disp = view[[
    "asset_id","division","device_type","criticality",
    "Age (yrs)","Failure Risk","Days Since Service",
    "Status","What To Do"
]].copy()

disp.columns = [
    "Device","Division","Type","Importance",
    "Age (yrs)","Failure Risk","Days Since Service",
    "Status","What To Do"
]

st.dataframe(disp, use_container_width=True, hide_index=True, height=500)
