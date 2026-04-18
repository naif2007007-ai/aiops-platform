import streamlit as st
import pandas as pd
import numpy as np
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions, load_alarms, load_tickets

try:
    assets  = load_assets()
    preds   = load_predictions()
    alarms  = load_alarms()
    tickets = load_tickets()

    asset_cols = [c for c in ["asset_id","division","device_type","criticality",
                  "battery_age_yrs","ups_load_pct"] if c in assets.columns]
    df = preds.merge(assets[asset_cols], on="asset_id", how="left")

    # ── Core numbers ──────────────────────────────────────────
    critical  = (df["risk_level"]=="CRITICAL").sum()
    high      = (df["risk_level"]=="HIGH").sum()
    medium    = (df["risk_level"]=="MEDIUM").sum()
    crit_divs = df[df["risk_level"]=="CRITICAL"]["division"].nunique()
    now       = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")

    # Division summary
    div_stats = df.groupby("division").agg(
        critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
        high=("risk_level",     lambda x: (x=="HIGH").sum()),
        medium=("risk_level",   lambda x: (x=="MEDIUM").sum()),
    ).reset_index()
    div_stats["priority_score"] = div_stats["critical"]*3 + div_stats["high"]*2 + div_stats["medium"]
    div_stats = div_stats.sort_values("priority_score", ascending=False).reset_index(drop=True)

    def get_division_issue(division):
        div_df   = df[df["division"]==division]
        ups_risk = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        net_risk = div_df[(div_df["device_type"].isin(["Router","Switch"])) &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        ups_old  = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["battery_age_yrs"]>=3.5)].shape[0] \
                   if "battery_age_yrs" in div_df.columns else 0

        if ups_risk >= net_risk:
            return {
                "issue":   "UPS battery degradation",
                "insight": f"{ups_old} UPS units exceeded lifecycle threshold — battery health declining",
                "action":  "Replace UPS batteries within 24 hours — engage Facilities and power engineers"
            }
        else:
            return {
                "issue":   "Network device instability",
                "insight": f"{net_risk} routers/switches showing abnormal CPU pressure and alarm frequency",
                "action":  "Escalate to Network-Ops — inspect high-load routers and switches immediately"
            }

    def get_status(row):
        if row["critical"] > 0: return "🔴 Critical"
        if row["high"] > 0:     return "🟠 High"
        if row["medium"] > 0:   return "🟡 Medium"
        return "🟢 Normal"

    # ── HEADER ────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([3,1])
    with col_h1:
        st.markdown("## AITD Command Center")
        st.caption("AI-Powered IT Infrastructure Predictive Monitoring")
    with col_h2:
        st.markdown(f"""
        <div style="text-align:right;padding-top:8px;">
            <div style="background:#E8F5E9;border:1px solid #4CAF50;border-radius:20px;
                        padding:5px 14px;display:inline-block;margin-bottom:4px;">
                <span style="color:#2E7D32;font-size:12px;font-weight:600;">
                    ● LIVE | Predictive Model Active
                </span>
            </div>
            <div style="color:#6B8299;font-size:11px;">{now}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── 1. SYSTEM RISK STATUS ─────────────────────────────────
    st.error(
        f"🔴 **System Risk Status** — "
        f"{critical} assets are predicted to fail within 48 hours. "
        f"{high} assets require escalation within 24 hours. "
        f"Immediate action is required to prevent service disruption."
    )

    # ── 2. KPI CARDS ──────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("🔴 Immediate Risk Assets",  f"{critical}",
              delta="Predicted failure within 48 hours",
              delta_color="inverse")
    k2.metric("🟠 High Risk Assets",        f"{high}",
              delta="Require escalation within 24 hours",
              delta_color="inverse")
    k3.metric("🟡 Planned Maintenance",     f"{medium}",
              delta="Upcoming maintenance required",
              delta_color="off")
    k4.metric("⚡ Divisions Impacted",      f"{crit_divs}",
              delta="Divisions with critical assets",
              delta_color="inverse")

    st.divider()

    # ── 3. DIVISIONS ACTION SUMMARY ───────────────────────────
    st.subheader("🚨 Divisions Action Summary")
    st.caption("All divisions sorted by priority — highest risk first")

    for _, row in div_stats.iterrows():
        info   = get_division_issue(row["division"])
        status = get_status(row)

        if row["critical"] > 0:
            icon = "🔴"
        elif row["high"] > 0:
            icon = "🟠"
        elif row["medium"] > 0:
            icon = "🟡"
        else:
            icon = "🟢"

        with st.container(border=True):
            h1, h2, h3 = st.columns([2,1,1])
            h1.markdown(f"### {icon} {row['division']} Division")
            h2.markdown(f"**Critical (L3):** {int(row['critical'])}")
            h3.markdown(f"**Urgent (L2):** {int(row['high'])}")

            c1,c2,c3 = st.columns(3)
            c1.markdown(f"**Primary Issue**\n\n{info['issue']}")
            c2.markdown(f"**AI Insight**\n\n_{info['insight']}_")
            c3.markdown(f"**Required Action**\n\n{info['action']}")

    st.divider()

    # ── 4. DIVISION RISK SUMMARY TABLE ───────────────────────
    st.subheader("📋 Division Risk Summary")

    table = div_stats.copy()
    table["Status"] = table.apply(get_status, axis=1)
    table = table[["division","critical","high","medium","Status"]]
    table.columns = ["Division","Critical (L3)","Urgent (L2)","Maintenance (L1)","Status"]
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.divider()

    # ── 5. DEVICE INSIGHT ─────────────────────────────────────
    ups_at_risk = df[(df["device_type"]=="UPS") &
                     (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
    net_at_risk = df[(df["device_type"].isin(["Router","Switch"])) &
                     (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]

    if ups_at_risk >= net_at_risk:
        st.info("⚡ **Device Insight:** UPS systems are the primary risk driver across multiple divisions.")
    else:
        st.info("⚡ **Device Insight:** Network devices (Routers & Switches) are the primary risk driver across multiple divisions.")

    st.divider()

    # ── 6. ALL ASSETS REQUIRING ACTION ───────────────────────
    st.subheader("📋 All Assets Requiring Action")
    st.caption("Every asset at risk — filtered by escalation level")

    filter_opt = st.radio(
        "Show",
        ["All","🔴 L3 Critical Only","🟠 L2 Urgent Only"],
        horizontal=True
    )

    action_df = df[df["risk_level"].isin(["CRITICAL","HIGH"])]\
        .sort_values("failure_probability", ascending=False).copy()

    if filter_opt == "🔴 L3 Critical Only":
        action_df = action_df[action_df["risk_level"]=="CRITICAL"]
    elif filter_opt == "🟠 L2 Urgent Only":
        action_df = action_df[action_df["risk_level"]=="HIGH"]

    action_df["Risk Level"] = action_df["risk_level"].map({
        "CRITICAL": "🔴 L3 — Critical",
        "HIGH":     "🟠 L2 — Urgent"
    })
    action_df["Required Action"] = "🔴 Action Required Now"

    disp = action_df[["asset_id","division","device_type",
                       "Risk Level","Required Action"]].copy()
    disp.columns = ["Asset ID","Division","Device Type","Risk Level","Required Action"]

    st.caption(f"Showing {len(disp):,} assets")
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

except Exception as e:
    st.error("Data temporarily unavailable. Please try again in a few moments.")
    st.stop()
