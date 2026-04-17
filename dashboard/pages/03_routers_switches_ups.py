import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_features

st.title("📡 Routers, Switches & UPS Health")
st.caption("Health status for all Network and Power Protection devices across AITD divisions")
st.divider()

assets = load_assets()
preds  = load_predictions()
feat   = load_features()

df = preds.merge(
    assets[["asset_id","division","device_type","model",
            "lifecycle_age_yrs","days_since_maintenance",
            "battery_health_pct","battery_age_yrs",
            "ups_load_pct","ups_runtime_min"]],
    on="asset_id", how="left"
)

feat_cols = [c for c in ["asset_id","avg_cpu","avg_mem","avg_latency",
             "avg_packet_loss_pct","alarm_count_30d","log_anomaly_days",
             "avg_battery_health","avg_ups_load","avg_ups_runtime"]
             if c in feat.columns]
df = df.merge(feat[feat_cols], on="asset_id", how="left")

# ── Filters ───────────────────────────────────────────────────
st.subheader("🔍 Filter the View")
col1, col2 = st.columns(2)
device_filter = col1.multiselect(
    "Device Type",
    ["Router","Switch","UPS"],
    default=["Router","Switch","UPS"]
)
div_filter = col2.multiselect(
    "Division",
    sorted(df["division"].unique().tolist()),
    default=sorted(df["division"].unique().tolist())
)

view = df[
    (df["device_type"].isin(device_filter)) &
    (df["division"].isin(div_filter))
]
st.caption(f"Showing {len(view):,} devices")
st.divider()

# ── Network devices section ───────────────────────────────────
net = view[view["device_type"].isin(["Router","Switch"])]
if len(net) > 0:
    st.subheader("🌐 Network Devices — Routers & Switches")
    n1,n2,n3,n4 = st.columns(4)
    n1.metric("Total Network Devices", f"{len(net):,}")
    n2.metric("🟣 Emergency", f"{(net['risk_level']=='CRITICAL').sum():,}")
    n3.metric("🔴 Urgent",    f"{(net['risk_level']=='HIGH').sum():,}")
    n4.metric("🟢 Healthy",   f"{(net['risk_level']=='LOW').sum():,}")

    if "avg_cpu" in net.columns:
        st.subheader("💻 Network Health Metrics")
        st.caption("Average performance across all selected network devices")
        ma,mb,mc,md = st.columns(4)
        avg_cpu  = net["avg_cpu"].mean()
        avg_mem  = net["avg_mem"].mean() if "avg_mem" in net.columns else 0
        avg_lat  = net["avg_latency"].mean() if "avg_latency" in net.columns else 0
        avg_loss = net["avg_packet_loss_pct"].mean() if "avg_packet_loss_pct" in net.columns else 0

        ma.metric("Avg CPU Usage",     f"{avg_cpu:.1f}%",
                  delta="⚠️ High" if avg_cpu>80 else "✅ Normal",
                  delta_color="inverse" if avg_cpu>80 else "normal")
        mb.metric("Avg Memory Usage",  f"{avg_mem:.1f}%",
                  delta="⚠️ High" if avg_mem>85 else "✅ Normal",
                  delta_color="inverse" if avg_mem>85 else "normal")
        mc.metric("Avg Response Time", f"{avg_lat:.0f}ms",
                  delta="⚠️ Slow" if avg_lat>400 else "✅ Normal",
                  delta_color="inverse" if avg_lat>400 else "normal")
        md.metric("Avg Packet Loss",   f"{avg_loss:.2f}%",
                  delta="⚠️ High" if avg_loss>1 else "✅ Normal",
                  delta_color="inverse" if avg_loss>1 else "normal")

    st.subheader("📊 Network Risk by Division")
    net_risk = net.groupby(["division","risk_level"]).size().reset_index(name="count")
    net_risk["risk_level"] = net_risk["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    fig = px.bar(net_risk, x="division", y="count",
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
        xaxis_title="", yaxis_title="Number of Devices"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 All Network Devices")
    net_disp = net[["asset_id","division","device_type","model",
                    "lifecycle_age_yrs","failure_probability",
                    "risk_level","recommended_action"]].copy()
    net_disp["failure_probability"] = (net_disp["failure_probability"]*100).round(1).astype(str)+"%"
    net_disp["lifecycle_age_yrs"]   = net_disp["lifecycle_age_yrs"].round(1)
    net_disp["risk_level"] = net_disp["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    net_disp.columns = ["Device","Division","Type","Model",
                        "Age (yrs)","Failure Risk","Status","Action"]
    st.dataframe(net_disp, use_container_width=True, hide_index=True, height=300)
    st.divider()

# ── UPS section ───────────────────────────────────────────────
ups = view[view["device_type"]=="UPS"]
if len(ups) > 0:
    st.subheader("🔋 UPS Devices — Power Protection Status")
    u1,u2,u3,u4 = st.columns(4)
    u1.metric("Total UPS",          f"{len(ups):,}")
    u2.metric("🟣 Emergency",       f"{(ups['risk_level']=='CRITICAL').sum():,}")
    u3.metric("🔴 Replace Battery", f"{(ups['battery_age_yrs']>=3.5).sum():,}")
    u4.metric("🟢 Healthy",         f"{(ups['risk_level']=='LOW').sum():,}")

    ua,ub,uc,ud = st.columns(4)
    avg_batt    = ups["battery_health_pct"].mean() if "battery_health_pct" in ups.columns else 0
    avg_load    = ups["ups_load_pct"].mean() if "ups_load_pct" in ups.columns else 0
    avg_runtime = ups["ups_runtime_min"].mean() if "ups_runtime_min" in ups.columns else 0
    avg_age     = ups["battery_age_yrs"].mean() if "battery_age_yrs" in ups.columns else 0

    ua.metric("Avg Battery Health", f"{avg_batt:.1f}%",
              delta="⚠️ Low" if avg_batt<80 else "✅ Good",
              delta_color="inverse" if avg_batt<80 else "normal")
    ub.metric("Avg UPS Load",       f"{avg_load:.1f}%",
              delta="⚠️ High" if avg_load>80 else "✅ Normal",
              delta_color="inverse" if avg_load>80 else "normal")
    uc.metric("Avg Runtime",        f"{avg_runtime:.0f} min",
              delta="⚠️ Low" if avg_runtime<10 else "✅ OK",
              delta_color="inverse" if avg_runtime<10 else "normal")
    ud.metric("Avg Battery Age",    f"{avg_age:.1f} yrs",
              delta="⚠️ Old" if avg_age>3.5 else "✅ OK",
              delta_color="inverse" if avg_age>3.5 else "normal")

    st.subheader("🔋 Battery Status by Division")
    col_x, col_y = st.columns(2)

    with col_x:
        st.caption("Battery age status — company wide")
        ups["Battery Status"] = ups["battery_age_yrs"].apply(
            lambda x: "🟢 Good (<2 yrs)" if x<2
            else "🟡 Monitor (2-3.5 yrs)" if x<3.5
            else "🔴 Replace (>3.5 yrs)"
        )
        batt_count = ups["Battery Status"].value_counts().reset_index()
        batt_count.columns = ["Status","Count"]
        fig2 = px.pie(batt_count, values="Count", names="Status",
                      hole=0.5, height=280,
                      color="Status",
                      color_discrete_map={
                          "🟢 Good (<2 yrs)":       "#639922",
                          "🟡 Monitor (2-3.5 yrs)": "#EF9F27",
                          "🔴 Replace (>3.5 yrs)":  "#E24B4A",
                      })
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=0,r=0)
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_y:
        st.caption("UPS batteries due replacement per division")
        replace = ups[ups["battery_age_yrs"]>=3.5].groupby("division").size().reset_index(name="Replace Now")
        if len(replace) > 0:
            fig3 = px.bar(replace, x="division", y="Replace Now",
                          color_discrete_sequence=["#E24B4A"],
                          height=280, text="Replace Now")
            fig3.update_traces(textposition="outside")
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10,b=10,l=0,r=0),
                xaxis_title="", yaxis_title="UPS Units"
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.success("✅ No UPS batteries due for replacement!")

    st.subheader("📋 All UPS Devices — Battery & Power Status")
    ups_disp = ups[["asset_id","division","model","lifecycle_age_yrs",
                    "battery_age_yrs","battery_health_pct","ups_load_pct",
                    "ups_runtime_min","risk_level","recommended_action"]].copy()
    ups_disp["lifecycle_age_yrs"]  = ups_disp["lifecycle_age_yrs"].round(1)
    ups_disp["battery_age_yrs"]    = ups_disp["battery_age_yrs"].round(1)
    ups_disp["battery_health_pct"] = ups_disp["battery_health_pct"].round(1).astype(str)+"%"
    ups_disp["ups_load_pct"]       = ups_disp["ups_load_pct"].round(1).astype(str)+"%"
    ups_disp["ups_runtime_min"]    = ups_disp["ups_runtime_min"].round(0).astype(int).astype(str)+" min"
    ups_disp["risk_level"] = ups_disp["risk_level"].map({
        "CRITICAL":"🟣 Emergency","HIGH":"🔴 Urgent",
        "MEDIUM":"🟡 Schedule","LOW":"🟢 Healthy"
    })
    ups_disp.columns = ["Device","Division","Model","Age (yrs)",
                        "Battery Age","Battery Health","Load",
                        "Runtime","Status","Action"]
    st.dataframe(ups_disp, use_container_width=True, hide_index=True, height=350)
