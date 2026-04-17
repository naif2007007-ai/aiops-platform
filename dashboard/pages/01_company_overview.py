import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_alarms, load_tickets

st.title("🏢 AITD Command Center")
st.caption("Aramco AIT Department — All 8 Divisions Infrastructure Health")
st.divider()

assets  = load_assets()
preds   = load_predictions()
alarms  = load_alarms()
tickets = load_tickets()

alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
tickets["open_time"] = pd.to_datetime(tickets["open_time"])

df = preds.merge(assets[["asset_id","division","device_type",
                          "battery_health_pct","battery_age_yrs"]],
                 on="asset_id", how="left")

# ── Company KPIs ──────────────────────────────────────────────
st.subheader("📊 AITD Infrastructure Health Summary")
total    = len(df)
critical = (df["risk_level"]=="CRITICAL").sum()
high     = (df["risk_level"]=="HIGH").sum()
medium   = (df["risk_level"]=="MEDIUM").sum()
low      = (df["risk_level"]=="LOW").sum()
open_t   = tickets[tickets["status"].isin(["Open","In Progress"])].shape[0]
ups_df   = df[df["device_type"]=="UPS"]
ups_due  = (ups_df["battery_age_yrs"]>=3.5).sum() if "battery_age_yrs" in ups_df.columns else 0

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Total Devices",      f"{total:,}")
c2.metric("🟣 Emergency",       f"{critical:,}", delta="L3 required",  delta_color="inverse")
c3.metric("🔴 Urgent",          f"{high:,}",     delta="L2 today",     delta_color="inverse")
c4.metric("🟡 Schedule",        f"{medium:,}")
c5.metric("🔋 UPS Due Replace", f"{ups_due:,}",  delta="batteries",    delta_color="inverse")
c6.metric("Open Tickets",       f"{open_t:,}")

if critical > 0:
    st.error(f"🚨 EMERGENCY: {critical} devices across AITD divisions need L3 response NOW")
if high > 0:
    st.warning(f"⚠️ URGENT: {high} devices need L2 escalation within 24 hours")
st.divider()

# ── Division cards ────────────────────────────────────────────
st.subheader("🗂️ All 8 AITD Divisions Status")
st.caption("Traffic light shows the most critical risk level in each division")

div_summary = df.groupby("division").agg(
    total=("asset_id","count"),
    critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
    high=("risk_level",     lambda x: (x=="HIGH").sum()),
    medium=("risk_level",   lambda x: (x=="MEDIUM").sum()),
    low=("risk_level",      lambda x: (x=="LOW").sum()),
).reset_index()

cols = st.columns(4)
for i, row in div_summary.iterrows():
    col = cols[i % 4]
    if row["critical"] > 0:
        status = "🟣 Emergency"; color = "#7B2D8B"; bg = "#EEEDFE"
    elif row["high"] > 0:
        status = "🔴 Urgent";    color = "#E24B4A"; bg = "#FCEBEB"
    elif row["medium"] > 0:
        status = "🟡 Monitor";   color = "#EF9F27"; bg = "#FAEEDA"
    else:
        status = "🟢 Healthy";   color = "#639922"; bg = "#EAF3DE"

    col.markdown(f"""
    <div style="background:{bg};border-left:4px solid {color};
                border-radius:8px;padding:12px;margin-bottom:10px;">
        <div style="font-weight:600;font-size:15px;">{row['division']}</div>
        <div style="font-size:13px;color:{color};margin:4px 0;">{status}</div>
        <div style="font-size:12px;color:#666;">
            {row['total']} devices |
            {row['critical']} critical |
            {row['high']} urgent
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Division comparison chart ──────────────────────────────────
st.subheader("📈 Which Division Needs Most Attention?")
st.caption("Compare risk levels across all 8 AITD divisions")

div_risk = df.groupby(["division","risk_level"]).size().reset_index(name="count")
div_risk["risk_level"] = div_risk["risk_level"].map({
    "CRITICAL": "🟣 Emergency",
    "HIGH":     "🔴 Urgent",
    "MEDIUM":   "🟡 Schedule",
    "LOW":      "🟢 Healthy"
})
fig = px.bar(
    div_risk, x="division", y="count",
    color="risk_level",
    color_discrete_map={
        "🟣 Emergency":"#7B2D8B",
        "🔴 Urgent":   "#E24B4A",
        "🟡 Schedule": "#EF9F27",
        "🟢 Healthy":  "#639922"
    },
    barmode="stack", height=350,
    labels={"division":"Division","count":"Devices","risk_level":"Status"}
)
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    xaxis_title="", yaxis_title="Number of Devices"
)
st.plotly_chart(fig, use_container_width=True)
st.divider()

# ── Device type health ────────────────────────────────────────
st.subheader("🔌 Health by Device Type")
col_a, col_b, col_c = st.columns(3)
for col, dtype, icon in [
    (col_a,"Router","🌐"),
    (col_b,"Switch","🔀"),
    (col_c,"UPS",   "🔋"),
]:
    ddf  = df[df["device_type"]==dtype]
    crit = (ddf["risk_level"]=="CRITICAL").sum()
    hi   = (ddf["risk_level"]=="HIGH").sum()
    med  = (ddf["risk_level"]=="MEDIUM").sum()
    lo   = (ddf["risk_level"]=="LOW").sum()
    col.markdown(f"### {icon} {dtype}s")
    col.metric("Total",f"{len(ddf):,}")
    col.error(f"🟣 Emergency: {crit}")
    col.warning(f"🔴 Urgent: {hi}")
    col.info(f"🟡 Schedule: {med}")
    col.success(f"🟢 Healthy: {lo}")

st.divider()

# ── Top 10 critical assets ────────────────────────────────────
st.subheader("🚨 Top 10 Most Critical Assets — All Divisions")
st.caption("These assets need immediate attention regardless of division")

top10 = df[df["risk_level"].isin(["CRITICAL","HIGH"])]\
    .sort_values("failure_probability", ascending=False).head(10)
top10["Failure Risk"] = (top10["failure_probability"]*100).round(1).astype(str)+"%"
top10["Status"]       = top10["risk_level"].map({
    "CRITICAL":"🟣 Emergency — L3 Now",
    "HIGH":    "🔴 Urgent — L2 Today"
})
display = top10[["asset_id","division","device_type","criticality",
                 "Failure Risk","Status","recommended_action"]].copy()
display.columns = ["Device","Division","Type","Importance","Failure Risk","Status","Action"]
st.dataframe(display, use_container_width=True, hide_index=True)
