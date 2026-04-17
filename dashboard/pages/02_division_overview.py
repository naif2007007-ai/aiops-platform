import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_alarms, load_tickets

st.title("🔍 Division Overview")
st.caption("Select any of the 8 AITD divisions to see its complete health status")
st.divider()

assets  = load_assets()
preds   = load_predictions()
alarms  = load_alarms()
tickets = load_tickets()

alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
tickets["open_time"] = pd.to_datetime(tickets["open_time"])

df = preds.merge(assets[["asset_id","division","device_type",
                          "battery_health_pct","battery_age_yrs",
                          "lifecycle_age_yrs","days_since_maintenance"]],
                 on="asset_id", how="left")

# ── Division selector ─────────────────────────────────────────
divisions = sorted(df["division"].unique().tolist())
selected  = st.selectbox(
    "Select Division",
    divisions,
    help="Choose an AITD division to see its detailed health status"
)

div_df   = df[df["division"]==selected]
div_alrm = alarms[alarms["division"]==selected] if "division" in alarms.columns else alarms
div_tick = tickets[tickets["division"]==selected] if "division" in tickets.columns else tickets

st.divider()

# ── Division KPIs ─────────────────────────────────────────────
st.subheader(f"📊 {selected} Division — Health Summary")

total    = len(div_df)
critical = (div_df["risk_level"]=="CRITICAL").sum()
high     = (div_df["risk_level"]=="HIGH").sum()
medium   = (div_df["risk_level"]=="MEDIUM").sum()
low      = (div_df["risk_level"]=="LOW").sum()
open_t   = div_tick[div_tick["status"].isin(["Open","In Progress"])].shape[0]
ups_due  = div_df[(div_df["device_type"]=="UPS") &
                  (div_df["battery_age_yrs"]>=3.5)].shape[0]

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Total Devices",  f"{total:,}")
c2.metric("🟣 Emergency",   f"{critical:,}", delta="L3 now"   if critical>0 else "none", delta_color="inverse")
c3.metric("🔴 Urgent",      f"{high:,}",     delta="L2 today" if high>0    else "none", delta_color="inverse")
c4.metric("🟡 Schedule",    f"{medium:,}")
c5.metric("🔋 UPS Replace", f"{ups_due:,}",  delta="due"      if ups_due>0 else "none", delta_color="inverse")
c6.metric("Open Tickets",   f"{open_t:,}")

if critical > 0:
    st.error(f"🚨 {critical} devices in {selected} need EMERGENCY L3 response NOW")
if high > 0:
    st.warning(f"⚠️ {high} devices in {selected} need L2 escalation today")
st.divider()

# ── Device type breakdown ─────────────────────────────────────
st.subheader(f"🔌 {selected} — Device Type Breakdown")
col_a, col_b = st.columns([1,2])

with col_a:
    type_risk = div_df.groupby("device_type")["risk_level"].value_counts().reset_index()
    type_risk.columns = ["Device Type","Risk Level","Count"]
    type_risk["Risk Level"] = type_risk["Risk Level"].map({
        "CRITICAL":"🟣 Emergency",
        "HIGH":    "🔴 Urgent",
        "MEDIUM":  "🟡 Schedule",
        "LOW":     "🟢 Healthy"
    })
    fig = px.bar(
        type_risk, x="Device Type", y="Count",
        color="Risk Level",
        color_discrete_map={
            "🟣 Emergency":"#7B2D8B",
            "🔴 Urgent":   "#E24B4A",
            "🟡 Schedule": "#EF9F27",
            "🟢 Healthy":  "#639922"
        },
        barmode="stack", height=300,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="", yaxis_title="Devices"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("📋 Device Summary")
    summary = div_df.groupby("device_type").agg(
        Total=("asset_id","count"),
        Emergency=("risk_level", lambda x: (x=="CRITICAL").sum()),
        Urgent=("risk_level",    lambda x: (x=="HIGH").sum()),
        Schedule=("risk_level",  lambda x: (x=="MEDIUM").sum()),
        Healthy=("risk_level",   lambda x: (x=="LOW").sum()),
    ).reset_index()
    summary.columns = ["Type","Total","🟣 Emergency","🔴 Urgent","🟡 Schedule","🟢 Healthy"]
    st.dataframe(summary, use_container_width=True, hide_index=True)

    ups_div = div_df[div_df["device_type"]=="UPS"]
    if len(ups_div) > 0 and "battery_age_yrs" in ups_div.columns:
        st.subheader("🔋 UPS Battery Status")
        good    = (ups_div["battery_age_yrs"] < 2.0).sum()
        monitor = ((ups_div["battery_age_yrs"]>=2.0) & (ups_div["battery_age_yrs"]<3.5)).sum()
        replace = (ups_div["battery_age_yrs"] >= 3.5).sum()
        bc1,bc2,bc3 = st.columns(3)
        bc1.success(f"✅ Good: {good}")
        bc2.warning(f"⚠️ Monitor: {monitor}")
        bc3.error(f"🔴 Replace: {replace}")

st.divider()

# ── Alert trend ───────────────────────────────────────────────
st.subheader(f"📈 {selected} — Alert Trend Last 30 Days")
st.caption("Higher bars = more problems that day")

if "division" in alarms.columns:
    recent = div_alrm[div_alrm["timestamp"] >= div_alrm["timestamp"].max() - pd.Timedelta(days=30)]
else:
    recent = alarms[alarms["asset_id"].isin(div_df["asset_id"])]
    recent = recent[recent["timestamp"] >= recent["timestamp"].max() - pd.Timedelta(days=30)]

daily = recent.set_index("timestamp").resample("D").size().reset_index()
daily.columns = ["Date","Alerts"]
avg   = daily["Alerts"].mean()

fig2 = px.bar(daily, x="Date", y="Alerts",
              color_discrete_sequence=["#E24B4A"], height=250)
fig2.add_hline(y=avg, line_dash="dash", line_color="orange",
               annotation_text=f"Average: {avg:.0f}/day")
fig2.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0)
)
st.plotly_chart(fig2, use_container_width=True)
st.divider()

# ── Action required table ─────────────────────────────────────
st.subheader(f"📋 {selected} — All Devices Requiring Action")
st.caption("Sorted by urgency — start from the top")

action = div_df[div_df["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])]\
    .sort_values("failure_probability", ascending=False)

action["Failure Risk"] = (action["failure_probability"]*100).round(1).astype(str)+"%"
action["Age (yrs)"]    = action["lifecycle_age_yrs"].round(1)
action["Status"]       = action["risk_level"].map({
    "CRITICAL":"🟣 Emergency",
    "HIGH":    "🔴 Urgent",
    "MEDIUM":  "🟡 Schedule"
})
display = action[["asset_id","device_type","criticality","Age (yrs)",
                  "Failure Risk","Status","recommended_action"]].copy()
display.columns = ["Device","Type","Importance","Age (yrs)",
                   "Failure Risk","Status","What To Do"]
st.caption(f"Showing {len(display):,} devices needing action in {selected}")
st.dataframe(display, use_container_width=True, hide_index=True, height=400)
