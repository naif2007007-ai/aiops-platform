import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_features

st.title("📡 Device Health & Predicted Failures")
st.caption("Network and UPS health metrics combined with AI failure predictions")
st.divider()

assets = load_assets()
preds  = load_predictions()
feat   = load_features()

# Safe merge
asset_cols = [c for c in ["asset_id","division","device_type","model",
              "lifecycle_age_yrs","days_since_maintenance","criticality",
              "battery_health_pct","battery_age_yrs",
              "ups_load_pct","ups_runtime_min"] if c in assets.columns]
df = preds.merge(assets[asset_cols], on="asset_id", how="left")

feat_cols = [c for c in ["asset_id","avg_cpu","avg_mem","avg_latency",
             "avg_packet_loss_pct","alarm_count_30d","avg_battery_health",
             "avg_ups_load","avg_ups_runtime"] if c in feat.columns]
df = df.merge(feat[feat_cols], on="asset_id", how="left")

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Filter the View")
col1, col2, col3 = st.columns(3)
div_filter = col1.multiselect(
    "Division",
    sorted(df["division"].dropna().unique().tolist()),
    default=sorted(df["division"].dropna().unique().tolist())
)
type_filter = col2.multiselect(
    "Device Type",
    ["Router","Switch","UPS"],
    default=["Router","Switch","UPS"]
)
risk_filter = col3.multiselect(
    "Risk Level",
    ["CRITICAL","HIGH","MEDIUM","LOW"],
    default=["CRITICAL","HIGH","MEDIUM","LOW"]
)

view = df[
    (df["division"].isin(div_filter)) &
    (df["device_type"].isin(type_filter)) &
    (df["risk_level"].isin(risk_filter))
]
st.caption(f"Showing {len(view):,} devices")
st.divider()

# ── Summary banners ───────────────────────────────────────────
critical = (view["risk_level"]=="CRITICAL").sum()
high     = (view["risk_level"]=="HIGH").sum()
medium   = (view["risk_level"]=="MEDIUM").sum()
low      = (view["risk_level"]=="LOW").sum()

if critical > 0:
    st.error(f"🟣 {critical} devices — EMERGENCY: Engage L3 and vendor immediately")
if high > 0:
    st.warning(f"🔴 {high} devices — URGENT: Escalate to L2 within 24 hours")
if medium > 0:
    st.info(f"🟡 {medium} devices — SCHEDULE: Assign to L1 within 48 hours")
st.divider()

# ── Network health metrics ────────────────────────────────────
net = view[view["device_type"].isin(["Router","Switch"])]
if len(net) > 0:
    st.subheader("🌐 Network Health Metrics — Routers & Switches")
    st.caption("Average performance across all selected network devices")

    na,nb,nc,nd = st.columns(4)
    avg_cpu  = net["avg_cpu"].mean() if "avg_cpu" in net.columns else 0
    avg_mem  = net["avg_mem"].mean() if "avg_mem" in net.columns else 0
    avg_lat  = net["avg_latency"].mean() if "avg_latency" in net.columns else 0
    avg_loss = net["avg_packet_loss_pct"].mean() if "avg_packet_loss_pct" in net.columns else 0

    na.metric("Avg CPU Usage",     f"{avg_cpu:.1f}%",
              delta="⚠️ High" if avg_cpu>80 else "✅ Normal",
              delta_color="inverse" if avg_cpu>80 else "normal")
    nb.metric("Avg Memory Usage",  f"{avg_mem:.1f}%",
              delta="⚠️ High" if avg_mem>85 else "✅ Normal",
              delta_color="inverse" if avg_mem>85 else "normal")
    nc.metric("Avg Response Time", f"{avg_lat:.0f}ms",
              delta="⚠️ Slow" if avg_lat>400 else "✅ Normal",
              delta_color="inverse" if avg_lat>400 else "normal")
    nd.metric("Avg Packet Loss",   f"{avg_loss:.2f}%",
              delta="⚠️ High" if avg_loss>1 else "✅ Normal",
              delta_color="inverse" if avg_loss>1 else "normal")

    st.divider()

# ── UPS health metrics ────────────────────────────────────────
ups = view[view["device_type"]=="UPS"]
if len(ups) > 0:
    st.subheader("🔋 UPS Health Metrics — Power Protection")
    st.caption("Battery health and power status across all UPS devices")

    ua,ub,uc,ud = st.columns(4)
    avg_batt    = ups["battery_health_pct"].mean() if "battery_health_pct" in ups.columns else 0
    avg_load    = ups["ups_load_pct"].mean() if "ups_load_pct" in ups.columns else 0
    avg_runtime = ups["ups_runtime_min"].mean() if "ups_runtime_min" in ups.columns else 0
    ups_replace = (ups["battery_age_yrs"]>=3.5).sum() if "battery_age_yrs" in ups.columns else 0

    ua.metric("Avg Battery Health",  f"{avg_batt:.1f}%",
              delta="⚠️ Low" if avg_batt<80 else "✅ Good",
              delta_color="inverse" if avg_batt<80 else "normal")
    ub.metric("Avg UPS Load",        f"{avg_load:.1f}%",
              delta="⚠️ High" if avg_load>80 else "✅ Normal",
              delta_color="inverse" if avg_load>80 else "normal")
    uc.metric("Avg Runtime",         f"{avg_runtime:.0f} min",
              delta="⚠️ Low" if avg_runtime<10 else "✅ OK",
              delta_color="inverse" if avg_runtime<10 else "normal")
    ud.metric("🔴 Batteries to Replace", f"{ups_replace:,}",
              delta="urgent" if ups_replace>0 else "none",
              delta_color="inverse" if ups_replace>0 else "normal")

    # Battery status pie chart
    if "battery_age_yrs" in ups.columns:
        col_x, col_y = st.columns(2)
        with col_x:
            st.caption("Battery age status")
            ups_copy = ups.copy()
            ups_copy["Battery Status"] = ups_copy["battery_age_yrs"].apply(
                lambda x: "🟢 Good (<2 yrs)" if x<2
                else "🟡 Monitor (2-3.5 yrs)" if x<3.5
                else "🔴 Replace (>3.5 yrs)"
            )
            bc = ups_copy["Battery Status"].value_counts().reset_index()
            bc.columns = ["Status","Count"]
            fig_pie = px.pie(bc, values="Count", names="Status",
                             hole=0.5, height=250,
                             color="Status",
                             color_discrete_map={
                                 "🟢 Good (<2 yrs)":       "#639922",
                                 "🟡 Monitor (2-3.5 yrs)": "#EF9F27",
                                 "🔴 Replace (>3.5 yrs)":  "#E24B4A",
                             })
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=10,l=0,r=0)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_y:
            st.caption("Batteries due replacement by division")
            replace_div = ups[ups["battery_age_yrs"]>=3.5]\
                .groupby("division").size().reset_index(name="Replace Now")
            if len(replace_div) > 0:
                fig_bar = px.bar(replace_div, x="division", y="Replace Now",
                                 color_discrete_sequence=["#E24B4A"],
                                 height=250, text="Replace Now")
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=10,b=10,l=0,r=0),
                    xaxis_title="", yaxis_title="UPS Units"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.success("✅ No batteries due for replacement!")

    st.divider()

# ── Risk distribution ─────────────────────────────────────────
st.subheader("📊 Risk Distribution by Division & Device Type")
col_a, col_b = st.columns(2)

with col_a:
    st.caption("By division")
    div_risk = view.groupby(["division","risk_level"]).size().reset_index(name="count")
    div_risk["risk_level"] = div_risk["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    fig1 = px.bar(div_risk, x="division", y="count",
                  color="risk_level",
                  color_discrete_map={
                      "🟣 Emergency":"#7B2D8B","🔴 Urgent":"#E24B4A",
                      "🟡 Schedule":"#EF9F27","🟢 Healthy":"#639922"
                  }, barmode="stack", height=280,
                  labels={"division":"Division","count":"Devices"})
    fig1.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="", yaxis_title="Devices"
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    st.caption("By device type")
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
                  }, barmode="stack", height=280,
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
st.subheader("📋 Complete Device List — Sorted by Urgency")
st.caption("Start from the top — these devices need attention first")

view_sorted = view.sort_values("failure_probability", ascending=False).copy()
view_sorted["Failure Risk"] = (view_sorted["failure_probability"]*100).round(1).astype(str)+"%"
view_sorted["Status"]       = view_sorted["risk_level"].map({
    "CRITICAL":"🟣 Emergency",
    "HIGH":    "🔴 Urgent",
    "MEDIUM":  "🟡 Schedule",
    "LOW":     "🟢 Healthy"
})

# Build display safely
disp = view_sorted[["asset_id","division","device_type"]].copy()
disp.columns = ["Device","Division","Type"]

if "criticality" in view_sorted.columns:
    disp["Importance"] = view_sorted["criticality"]
if "lifecycle_age_yrs" in view_sorted.columns:
    disp["Age (yrs)"] = view_sorted["lifecycle_age_yrs"].round(1)
if "days_since_maintenance" in view_sorted.columns:
    disp["Days Since Service"] = view_sorted["days_since_maintenance"].astype(int)

disp["Failure Risk"] = view_sorted["Failure Risk"]
disp["Status"]       = view_sorted["Status"]
disp["What To Do"]   = view_sorted["recommended_action"]

st.caption(f"Total: {len(disp):,} devices")
st.dataframe(disp, use_container_width=True, hide_index=True, height=500)
