import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_alarms, load_tickets

# ── Page config ───────────────────────────────────────────────
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

# ── Calculations ──────────────────────────────────────────────
critical  = (df["risk_level"]=="CRITICAL").sum()
high      = (df["risk_level"]=="HIGH").sum()
medium    = (df["risk_level"]=="MEDIUM").sum()
low       = (df["risk_level"]=="LOW").sum()
total     = len(df)

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
div_stats = div_stats.sort_values("risk_score", ascending=False)
top3_divs = div_stats.head(3)

# Critical divisions (with CRITICAL assets)
crit_divs = df[df["risk_level"]=="CRITICAL"]["division"].nunique()

# AI Insight — auto generated from data
ups_critical = df[(df["device_type"]=="UPS") &
                  (df["risk_level"].isin(["CRITICAL","HIGH"]))]\
    .groupby("division").size().reset_index(name="count")\
    .sort_values("count", ascending=False)

net_critical = df[(df["device_type"].isin(["Router","Switch"])) &
                  (df["risk_level"].isin(["CRITICAL","HIGH"]))]\
    .groupby("division").size().reset_index(name="count")\
    .sort_values("count", ascending=False)

ups_due = df[(df["device_type"]=="UPS") &
             (df["battery_age_yrs"]>=3.5)].shape[0] if "battery_age_yrs" in df.columns else 0

# Build AI insight text
def build_ai_insight():
    insights = []
    if len(ups_critical) > 0 and ups_critical.iloc[0]["count"] > 0:
        top_ups_div = ups_critical.iloc[0]["division"]
        insights.append(f"UPS battery degradation in {top_ups_div} division")
    if len(net_critical) > 0 and net_critical.iloc[0]["count"] > 0:
        top_net_div = net_critical.iloc[0]["division"]
        insights.append(f"network device failures in {top_net_div} division")
    if ups_due > 0:
        insights.append(f"{ups_due} UPS batteries past replacement threshold")

    if insights:
        return f"Failure risk is primarily driven by {' and '.join(insights[:2])}. Immediate action recommended to prevent service disruption."
    return "Infrastructure risk is distributed across multiple divisions. Review division overview for detailed breakdown."

ai_insight = build_ai_insight()
now = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")

# ── HEADER ────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    background: white;
    border-bottom: 2px solid #E8EEF4;
    padding: 20px 0 16px 0;
    margin-bottom: 20px;
">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <h1 style="margin:0;font-size:28px;font-weight:600;color:#0A2540;">
                AITD Command Center
            </h1>
            <p style="margin:4px 0 0 0;font-size:14px;color:#4A6580;">
                AI-Powered IT Infrastructure Predictive Monitoring
            </p>
        </div>
        <div style="text-align:right;">
            <div style="
                background:#E8F5E9;
                border:1px solid #4CAF50;
                border-radius:20px;
                padding:6px 16px;
                display:inline-block;
                margin-bottom:6px;
            ">
                <span style="color:#2E7D32;font-size:13px;font-weight:500;">
                    ● LIVE &nbsp;|&nbsp; Predictive Model Active
                </span>
            </div>
            <div style="color:#6B8299;font-size:12px;">
                Last update: {now}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── EXECUTIVE RISK BANNER ─────────────────────────────────────
st.markdown(f"""
<div style="
    background:#FFF5F5;
    border-left:5px solid #D32F2F;
    border-radius:6px;
    padding:16px 20px;
    margin-bottom:20px;
">
    <div style="font-size:16px;font-weight:600;color:#B71C1C;margin-bottom:6px;">
        🔴 System Risk Status
    </div>
    <div style="font-size:14px;color:#C62828;line-height:1.6;">
        AI model predicts elevated failure risk across AITD infrastructure.
        <strong>{critical} assets are predicted to fail within 24–48 hours</strong>
        across {crit_divs} critical divisions.
        Immediate L3 intervention is required to prevent service disruption.
    </div>
</div>
""", unsafe_allow_html=True)

# ── 4 KPI CARDS ───────────────────────────────────────────────
k1,k2,k3,k4 = st.columns(4)

k1.markdown(f"""
<div style="background:#FFF5F5;border:1px solid #FFCDD2;border-radius:8px;padding:16px;text-align:center;">
    <div style="font-size:36px;font-weight:700;color:#D32F2F;">{critical}</div>
    <div style="font-size:13px;font-weight:600;color:#B71C1C;margin:4px 0;">🔴 Immediate Risk Assets</div>
    <div style="font-size:12px;color:#E57373;">Predicted failure within 48 hours</div>
</div>
""", unsafe_allow_html=True)

k2.markdown(f"""
<div style="background:#FFF8E1;border:1px solid #FFE082;border-radius:8px;padding:16px;text-align:center;">
    <div style="font-size:36px;font-weight:700;color:#E65100;">{high}</div>
    <div style="font-size:13px;font-weight:600;color:#BF360C;margin:4px 0;">🟠 High Risk Assets</div>
    <div style="font-size:12px;color:#FF8A65;">Require escalation within 24 hours</div>
</div>
""", unsafe_allow_html=True)

k3.markdown(f"""
<div style="background:#FFFDE7;border:1px solid #FFF176;border-radius:8px;padding:16px;text-align:center;">
    <div style="font-size:36px;font-weight:700;color:#F57F17;">{medium}</div>
    <div style="font-size:13px;font-weight:600;color:#E65100;margin:4px 0;">🟡 Planned Maintenance</div>
    <div style="font-size:12px;color:#FFB74D;">Upcoming maintenance required</div>
</div>
""", unsafe_allow_html=True)

k4.markdown(f"""
<div style="background:#E3F2FD;border:1px solid #90CAF9;border-radius:8px;padding:16px;text-align:center;">
    <div style="font-size:36px;font-weight:700;color:#1565C0;">{crit_divs}</div>
    <div style="font-size:13px;font-weight:600;color:#0D47A1;margin:4px 0;">⚡ Divisions Impacted</div>
    <div style="font-size:12px;color:#42A5F5;">Divisions with critical risk assets</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CRITICAL ALERTS + AI INSIGHT ─────────────────────────────
col_alert, col_insight = st.columns([1,1])

with col_alert:
    st.markdown(f"""
    <div style="background:#FFEBEE;border:1px solid #FFCDD2;border-radius:8px;padding:16px;margin-bottom:12px;">
        <div style="font-size:13px;font-weight:600;color:#B71C1C;margin-bottom:6px;">
            🔴 Critical Alert
        </div>
        <div style="font-size:13px;color:#C62828;line-height:1.6;">
            {critical} assets require immediate L3 intervention
            to prevent service disruption across AITD divisions.
        </div>
    </div>
    <div style="background:#FFF3E0;border:1px solid #FFE0B2;border-radius:8px;padding:16px;">
        <div style="font-size:13px;font-weight:600;color:#BF360C;margin-bottom:6px;">
            🟠 Urgent Alert
        </div>
        <div style="font-size:13px;color:#E65100;line-height:1.6;">
            {high} assets require L2 escalation within 24 hours
            to avoid escalation to critical status.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_insight:
    st.markdown(f"""
    <div style="
        background:#E8F4FD;
        border:1px solid #90CAF9;
        border-left:5px solid #1565C0;
        border-radius:8px;
        padding:16px;
        height:100%;
    ">
        <div style="font-size:13px;font-weight:600;color:#0D47A1;margin-bottom:10px;">
            🤖 AI Insight
        </div>
        <div style="font-size:13px;color:#1565C0;line-height:1.8;">
            {ai_insight}
        </div>
        <div style="margin-top:12px;padding-top:12px;border-top:1px solid #90CAF9;">
            <div style="font-size:11px;color:#42A5F5;">
                Model Accuracy: 79% &nbsp;|&nbsp;
                ROC-AUC: 0.94 &nbsp;|&nbsp;
                Prediction Window: 48 hours
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TOP 3 DIVISIONS + CHART ───────────────────────────────────
col_div, col_chart = st.columns([1,2])

with col_div:
    st.markdown("""
    <div style="font-size:15px;font-weight:600;color:#0A2540;margin-bottom:12px;">
        🏭 Top 3 Highest Risk Divisions
    </div>
    """, unsafe_allow_html=True)

    colors = ["#D32F2F","#E65100","#F57F17"]
    labels = ["Highest Risk","High Risk","Elevated Risk"]

    for i, (_, row) in enumerate(top3_divs.iterrows()):
        bg = ["#FFF5F5","#FFF8E1","#FFFDE7"][i]
        bc = ["#FFCDD2","#FFE082","#FFF176"][i]
        tc = colors[i]
        st.markdown(f"""
        <div style="
            background:{bg};
            border:1px solid {bc};
            border-left:4px solid {tc};
            border-radius:8px;
            padding:12px 16px;
            margin-bottom:10px;
        ">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:14px;font-weight:600;color:#0A2540;">
                        {row['division']}
                    </div>
                    <div style="font-size:12px;color:#6B8299;margin-top:2px;">
                        {int(row['critical'])} critical | {int(row['high'])} urgent
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:22px;font-weight:700;color:{tc};">
                        {row['risk_score']:.0f}%
                    </div>
                    <div style="font-size:11px;color:{tc};">{labels[i]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_chart:
    st.markdown("""
    <div style="font-size:15px;font-weight:600;color:#0A2540;margin-bottom:12px;">
        📊 Risk Distribution Across Divisions
    </div>
    """, unsafe_allow_html=True)

    chart_data = div_stats.copy()
    chart_data["at_risk"] = chart_data["critical"] + chart_data["high"]
    chart_data["safe"]    = chart_data["total"] - chart_data["at_risk"]
    threshold = chart_data["at_risk"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="At Risk",
        x=chart_data["division"],
        y=chart_data["at_risk"],
        marker_color=["#D32F2F" if r==chart_data["risk_score"].max()
                      else "#EF9F27" for r in chart_data["risk_score"]],
        text=chart_data["at_risk"],
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        name="Healthy",
        x=chart_data["division"],
        y=chart_data["safe"],
        marker_color="#E8F5E9",
    ))
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="#1565C0",
        annotation_text=f"Risk threshold: {threshold:.0f}",
        annotation_position="top right"
    )
    fig.update_layout(
        barmode="stack",
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        legend=dict(orientation="h", y=-0.2),
        xaxis_title="", yaxis_title="Devices",
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── DEVICE TYPE INSIGHT ───────────────────────────────────────
ups_emrg = (df[(df["device_type"]=="UPS") & (df["risk_level"]=="CRITICAL")].shape[0])
ups_urg  = (df[(df["device_type"]=="UPS") & (df["risk_level"]=="HIGH")].shape[0])
net_emrg = (df[(df["device_type"].isin(["Router","Switch"])) & (df["risk_level"]=="CRITICAL")].shape[0])
net_urg  = (df[(df["device_type"].isin(["Router","Switch"])) & (df["risk_level"]=="HIGH")].shape[0])

highest_risk_type = "UPS Systems" if (ups_emrg+ups_urg) >= (net_emrg+net_urg) else "Network Devices"
emrg_count = ups_emrg if highest_risk_type=="UPS Systems" else net_emrg
urg_count  = ups_urg  if highest_risk_type=="UPS Systems" else net_urg

st.markdown(f"""
<div style="
    background:#F8F9FA;
    border:1px solid #E0E0E0;
    border-radius:8px;
    padding:16px 20px;
    margin-bottom:20px;
">
    <div style="font-size:13px;font-weight:600;color:#0A2540;margin-bottom:6px;">
        ⚡ Highest Risk Device Category
    </div>
    <div style="font-size:13px;color:#4A6580;line-height:1.6;">
        <strong>{highest_risk_type}</strong> represent the highest risk category —
        <strong>{emrg_count} emergency</strong> and
        <strong>{urg_count} urgent</strong> cases require immediate attention.
    </div>
</div>
""", unsafe_allow_html=True)

# ── TOP CRITICAL ASSETS TABLE ─────────────────────────────────
st.markdown("""
<div style="font-size:15px;font-weight:600;color:#0A2540;margin-bottom:4px;">
    🚨 Immediate Action Required — Top Critical Assets
</div>
<div style="font-size:12px;color:#6B8299;margin-bottom:12px;">
    Assets with highest failure probability (sorted by risk)
</div>
""", unsafe_allow_html=True)

top_assets = df[df["risk_level"].isin(["CRITICAL","HIGH"])]\
    .sort_values("failure_probability", ascending=False).head(10).copy()

top_assets["Failure Probability"] = (top_assets["failure_probability"]*100).round(1).astype(str)+"%"
top_assets["Action"]              = top_assets["risk_level"].map({
    "CRITICAL": "🔴 Predicted Failure — Act Now",
    "HIGH":     "🟠 Escalate to L2 — Urgent"
})

disp = top_assets[["asset_id","division","device_type",
                    "criticality","Failure Probability","Action"]].copy()
disp.columns = ["Device ID","Division","Type","Importance","Failure Probability","Required Action"]

st.dataframe(disp, use_container_width=True, hide_index=True)
