import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_alarms, load_tickets

try:
    assets  = load_assets()
    preds   = load_predictions()
    alarms  = load_alarms()
    tickets = load_tickets()

    alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
    tickets["open_time"] = pd.to_datetime(tickets["open_time"])

    asset_cols = [c for c in ["asset_id","division","device_type","model",
                  "lifecycle_age_yrs","days_since_maintenance","criticality",
                  "battery_health_pct","battery_age_yrs","ups_load_pct",
                  "ups_runtime_min"] if c in assets.columns]
    df = preds.merge(assets[asset_cols], on="asset_id", how="left")

    # ── Core calculations ─────────────────────────────────────
    critical  = (df["risk_level"]=="CRITICAL").sum()
    high      = (df["risk_level"]=="HIGH").sum()
    medium    = (df["risk_level"]=="MEDIUM").sum()
    crit_divs = df[df["risk_level"]=="CRITICAL"]["division"].nunique()

    # Division risk score
    div_stats = df.groupby("division").agg(
        total=("asset_id","count"),
        critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
        high=("risk_level",     lambda x: (x=="HIGH").sum()),
        medium=("risk_level",   lambda x: (x=="MEDIUM").sum()),
    ).reset_index()
    div_stats["risk_score"] = (
        (div_stats["critical"]*1.0 +
         div_stats["high"]*0.6 +
         div_stats["medium"]*0.3) /
        div_stats["total"] * 100
    ).round(1)
    div_stats = div_stats.sort_values("risk_score", ascending=False).reset_index(drop=True)
    top3 = div_stats.head(3)

    # Per division insights
    def get_division_insight(division):
        div_df   = df[df["division"]==division]
        ups_risk = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        net_risk = div_df[(div_df["device_type"].isin(["Router","Switch"])) &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        ups_old  = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["battery_age_yrs"]>=3.5)].shape[0] \
                   if "battery_age_yrs" in div_df.columns else 0
        crit_c   = (div_df["risk_level"]=="CRITICAL").sum()
        high_c   = (div_df["risk_level"]=="HIGH").sum()

        if ups_risk >= net_risk:
            issue   = "UPS battery degradation"
            insight = f"AI model detected {ups_old} UPS units past replacement threshold with declining battery health trend."
            action  = "Replace degraded UPS batteries immediately — engage Facilities team and power engineers."
        else:
            issue   = "Network device failures"
            insight = f"AI model detected abnormal alarm frequency and CPU pressure on {net_risk} network devices."
            action  = "Escalate to Network-Ops team — inspect high-load routers and switches for hardware faults."

        return {
            "critical": crit_c,
            "high":     high_c,
            "issue":    issue,
            "insight":  insight,
            "action":   action,
        }

    # Device category
    ups_at_risk = (df[(df["device_type"]=="UPS") &
                      (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0])
    net_at_risk = (df[(df["device_type"].isin(["Router","Switch"])) &
                      (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0])
    top_cat     = "UPS Systems" if ups_at_risk >= net_at_risk else "Network Devices"
    top_cat_n   = ups_at_risk if top_cat=="UPS Systems" else net_at_risk

    now = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")

    # ── 1. HEADER ─────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                padding-bottom:16px;border-bottom:2px solid #E8EEF4;margin-bottom:20px;">
        <div>
            <div style="font-size:26px;font-weight:700;color:#0A2540;">
                AITD Command Center
            </div>
            <div style="font-size:13px;color:#4A6580;margin-top:4px;">
                AI-Powered IT Infrastructure Predictive Monitoring
            </div>
        </div>
        <div style="text-align:right;">
            <div style="background:#E8F5E9;border:1px solid #4CAF50;border-radius:20px;
                        padding:5px 14px;display:inline-block;margin-bottom:4px;">
                <span style="color:#2E7D32;font-size:12px;font-weight:600;">
                    ● LIVE &nbsp;|&nbsp; Predictive Model Active
                </span>
            </div>
            <div style="color:#6B8299;font-size:11px;">Last update: {now}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 2. SYSTEM RISK BANNER ─────────────────────────────────
    st.markdown(f"""
    <div style="background:#FFF5F5;border-left:5px solid #D32F2F;border-radius:6px;
                padding:14px 18px;margin-bottom:20px;">
        <div style="font-size:15px;font-weight:600;color:#B71C1C;margin-bottom:4px;">
            🔴 System Risk Status
        </div>
        <div style="font-size:13px;color:#C62828;line-height:1.7;">
            <strong>{critical} assets are predicted to fail within 48 hours</strong>
            across {crit_divs} critical AITD divisions.
            An additional {high} assets require L2 escalation within 24 hours.
            Immediate intervention required to prevent service disruption.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. KPI CARDS ──────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    kpi_style = [
        ("#FFF5F5","#FFCDD2","#D32F2F","#B71C1C",
         str(critical),"🔴 Immediate Risk Assets","Predicted failure within 48 hours"),
        ("#FFF8E1","#FFE082","#E65100","#BF360C",
         str(high),"🟠 High Risk Assets","Require escalation within 24 hours"),
        ("#FFFDE7","#FFF176","#F57F17","#E65100",
         str(medium),"🟡 Planned Maintenance","Upcoming maintenance required"),
        ("#E3F2FD","#90CAF9","#1565C0","#0D47A1",
         str(crit_divs),"⚡ Divisions Impacted","Divisions with critical risk assets"),
    ]
    for col,(bg,bc,vc,tc,val,label,desc) in zip([k1,k2,k3,k4],kpi_style):
        col.markdown(f"""
        <div style="background:{bg};border:1px solid {bc};border-radius:8px;
                    padding:16px;text-align:center;margin-bottom:16px;">
            <div style="font-size:38px;font-weight:700;color:{vc};">{val}</div>
            <div style="font-size:12px;font-weight:600;color:{tc};margin:4px 0;">{label}</div>
            <div style="font-size:11px;color:{vc};">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── 4. PRIORITY DIVISIONS ─────────────────────────────────
    st.subheader("🚨 Priority Divisions Requiring Immediate Action")

    icons    = ["🔴","🟠","🟡"]
    priority = ["Highest Priority","High Priority","Elevated Priority"]
    borders  = ["red","orange","#F57F17"]

    for i, (_, row) in enumerate(top3.iterrows()):
        info = get_division_insight(row["division"])

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            with c1:
                st.markdown(f"**{icons[i]} {i+1}. {row['division']} Division**")
                st.caption(f"🏷️ {priority[i]}")
            with c2:
                st.metric("Risk Score", f"{row['risk_score']:.0f}%")
                st.caption(f"{int(info['critical'])} critical | {int(info['high'])} urgent")
            with c3:
                st.markdown("**Primary Issue**")
                st.markdown(f"_{info['issue']}_")
                st.caption("Prediction: 24–48 hours")
            with c4:
                st.markdown("**Required Action**")
                st.caption(info['action'])

            st.markdown(f"🤖 **AI Insight:** {info['insight']}")

    st.divider()

    # ── 5. SUPPORTING CHART ───────────────────────────────────
    st.markdown("""
    <div style="font-size:15px;font-weight:600;color:#0A2540;margin-bottom:12px;">
        📊 Division Risk Comparison (Supporting Priority Ranking)
    </div>
    """, unsafe_allow_html=True)

    top3_names = top3["division"].tolist()
    chart_data = div_stats.copy()
    chart_data["at_risk"] = chart_data["critical"] + chart_data["high"]
    chart_data["safe"]    = chart_data["total"] - chart_data["at_risk"]
    chart_data["color"]   = chart_data["division"].apply(
        lambda d: "#D32F2F" if d==top3_names[0]
        else "#E65100" if d==top3_names[1]
        else "#F57F17" if d==top3_names[2]
        else "#E0E0E0"
    )
    threshold = chart_data["at_risk"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="At Risk",
        x=chart_data["division"],
        y=chart_data["at_risk"],
        marker_color=chart_data["color"].tolist(),
        text=chart_data["at_risk"],
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        name="Healthy",
        x=chart_data["division"],
        y=chart_data["safe"],
        marker_color="#F5F5F5",
        marker_line_color="#E0E0E0",
        marker_line_width=1,
    ))
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="#1565C0",
        line_width=1.5,
        annotation_text=f"Average risk threshold: {threshold:.0f} devices",
        annotation_position="top right",
        annotation_font_color="#1565C0",
        annotation_font_size=11,
    )
    fig.update_layout(
        barmode="stack",
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20,b=10,l=0,r=0),
        legend=dict(orientation="h", y=-0.25, font_size=11),
        xaxis_title="", yaxis_title="Number of Devices",
        font=dict(size=11)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 6. DEVICE CATEGORY INSIGHT ────────────────────────────
    st.markdown(f"""
    <div style="background:#F8F9FA;border:1px solid #E0E0E0;border-radius:8px;
                padding:14px 18px;margin:16px 0;">
        <span style="font-size:13px;font-weight:600;color:#0A2540;">⚡ Highest Risk Device Category &nbsp;—&nbsp;</span>
        <span style="font-size:13px;color:#4A6580;">
            <strong>{top_cat}</strong> represent the highest risk category
            with <strong>{top_cat_n} assets</strong> at critical or high risk
            requiring immediate intervention.
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── 7. TOP CRITICAL ASSETS TABLE ─────────────────────────
    st.markdown("""
    <div style="font-size:15px;font-weight:600;color:#0A2540;margin-bottom:4px;">
        🚨 Immediate Action Required — Top Critical Assets
    </div>
    <div style="font-size:12px;color:#6B8299;margin-bottom:12px;">
        Assets with highest failure probability — sorted by risk
    </div>
    """, unsafe_allow_html=True)

    top_assets = df[df["risk_level"].isin(["CRITICAL","HIGH"])]\
        .sort_values("failure_probability", ascending=False).head(10).copy()

    top_assets["Risk %"]  = (top_assets["failure_probability"]*100).round(1).astype(str)+"%"
    top_assets["Action"]  = top_assets["risk_level"].map({
        "CRITICAL": "🔴 Predicted Failure — Act Now",
        "HIGH":     "🟠 Escalate to L2 — Urgent"
    })

    disp = top_assets[["asset_id","division","device_type","Risk %","Action"]].copy()
    disp.columns = ["Asset ID","Division","Device Type","Risk %","Required Action"]
    st.dataframe(disp, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Data temporarily unavailable. Please try again in a few moments.")
    st.stop()
