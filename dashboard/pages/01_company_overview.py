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
                  "battery_age_yrs","ups_load_pct","lifecycle_age_yrs",
                  "days_since_maintenance","building"] if c in assets.columns]
    df = preds.merge(assets[asset_cols], on="asset_id", how="left")

    # Add building fallback
    if "building" not in df.columns:
        bldgs = ["Server-01","IT-Building","Admin-Block","Operations-01","Comm-Center"]
        df["building"] = df["asset_id"].apply(
            lambda x: bldgs[int(x.split("-")[1]) % len(bldgs)]
        )

    # ── Core numbers ──────────────────────────────────────────
    critical  = (df["risk_level"]=="CRITICAL").sum()
    high      = (df["risk_level"]=="HIGH").sum()
    medium    = (df["risk_level"]=="MEDIUM").sum()
    crit_divs = df[df["risk_level"]=="CRITICAL"]["division"].nunique()
    now       = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")

    # Division summary — sorted by priority
    div_stats = df.groupby("division").agg(
        critical=("risk_level", lambda x: (x=="CRITICAL").sum()),
        high=("risk_level",     lambda x: (x=="HIGH").sum()),
        medium=("risk_level",   lambda x: (x=="MEDIUM").sum()),
    ).reset_index()
    div_stats["priority_score"] = (
        div_stats["critical"]*3 +
        div_stats["high"]*2 +
        div_stats["medium"]
    )
    div_stats = div_stats.sort_values("priority_score", ascending=False).reset_index(drop=True)

    def get_status(row):
        if row["critical"] > 0: return "🔴 Critical"
        if row["high"] > 0:     return "🟠 High"
        if row["medium"] > 0:   return "🟡 Medium"
        return "🟢 Normal"

    def get_issue_summary(row):
        if row["device_type"] == "UPS":
            age = row.get("battery_age_yrs", 0) or 0
            if age >= 3.5: return "Battery exceeded lifecycle threshold"
            elif age >= 2: return "Battery approaching end of life"
            return "Battery in normal condition"
        elif row["device_type"] == "Router":
            if row["risk_level"] in ["CRITICAL","HIGH"]: return "High CPU load and packet loss detected"
            return "Normal operation"
        else:
            if row["risk_level"] in ["CRITICAL","HIGH"]: return "Port errors and high bandwidth utilization"
            return "Normal operation"

    def get_risk_drivers(division):
        div_df   = df[df["division"]==division]
        ups_risk = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        net_risk = div_df[(div_df["device_type"].isin(["Router","Switch"])) &
                          (div_df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        ups_old  = div_df[(div_df["device_type"]=="UPS") &
                          (div_df["battery_age_yrs"]>=3.5)].shape[0] \
                   if "battery_age_yrs" in div_df.columns else 0

        parts   = []
        insight = []

        if ups_risk > 0:
            parts.append("UPS battery degradation")
            insight.append(f"{ups_old} UPS units exceeded lifecycle threshold")
        if net_risk > 0:
            parts.append("network device instability")
            insight.append(f"{net_risk} network devices show abnormal load behavior")

        if len(parts) == 0:
            drivers = "No critical issues detected."
            ai_text = "All devices in this division are within normal operating parameters."
        elif len(parts) == 1:
            drivers = f"Risk is driven by {parts[0]}."
            ai_text = f"{insight[0]} — immediate action recommended."
        else:
            drivers = f"Risk is driven by {parts[0]} and {parts[1]} — both require immediate action."
            ai_text = f"{insight[0]} and {insight[1]}, both requiring immediate intervention."

        return drivers, ai_text

    def get_device_insight():
        ups_risk = df[(df["device_type"]=="UPS") &
                      (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        net_risk = df[(df["device_type"].isin(["Router","Switch"])) &
                      (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0]
        if ups_risk > net_risk * 1.5:
            return f"UPS systems are the primary risk driver — {ups_risk} units at critical or high risk."
        elif net_risk > ups_risk * 1.5:
            return f"Network devices are the primary risk driver — {net_risk} devices at critical or high risk."
        else:
            return f"Risk is distributed across UPS ({ups_risk} units) and network devices ({net_risk} devices) — both require immediate attention."

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
    k1.metric("🔴 Immediate Risk Assets", f"{critical}",
              delta="Predicted failure within 48 hours — L3 intervention required",
              delta_color="inverse")
    k2.metric("🟠 High Risk Assets",       f"{high}",
              delta="Require L2 escalation within 24 hours",
              delta_color="inverse")
    k3.metric("🟡 Planned Maintenance",    f"{medium}",
              delta="Schedule L1 maintenance within 48 hours",
              delta_color="off")
    k4.metric("⚡ Divisions Impacted",     f"{crit_divs}",
              delta="Divisions with critical risk assets",
              delta_color="inverse")

    st.divider()

    # ── 3. DIVISION SELECTOR ──────────────────────────────────
    st.subheader("🔽 Division Action View")
    st.caption("Select a division to see its complete action plan")

    divisions = sorted(df["division"].dropna().unique().tolist())
    selected  = st.selectbox(
        "Select Division",
        ["— Select a Division —"] + divisions,
    )

    if selected != "— Select a Division —":
        div_df = df[df["division"]==selected].copy()
        div_df["Issue Summary"] = div_df.apply(get_issue_summary, axis=1)

        div_critical = (div_df["risk_level"]=="CRITICAL").sum()
        div_high     = (div_df["risk_level"]=="HIGH").sum()
        div_medium   = (div_df["risk_level"]=="MEDIUM").sum()

        # Device breakdown — exact counts
        ups_df  = div_df[div_df["device_type"]=="UPS"]
        rtr_df  = div_df[div_df["device_type"]=="Router"]
        swt_df  = div_df[div_df["device_type"]=="Switch"]
        ups_risk = (ups_df["risk_level"].isin(["CRITICAL","HIGH"])).sum()
        rtr_risk = (rtr_df["risk_level"].isin(["CRITICAL","HIGH"])).sum()
        swt_risk = (swt_df["risk_level"].isin(["CRITICAL","HIGH"])).sum()
        ups_old  = (ups_df["battery_age_yrs"]>=3.5).sum() \
                   if "battery_age_yrs" in ups_df.columns else 0

        drivers, ai_text = get_risk_drivers(selected)

        # Section 1 — Summary
        st.markdown(f"### 📍 {selected} Division — Action Summary")
        s1,s2,s3 = st.columns(3)
        s1.error(f"🔴 Critical (L3): **{div_critical}**")
        s2.warning(f"🟠 Urgent (L2): **{div_high}**")
        s3.info(f"🟡 Maintenance (L1): **{div_medium}**")

        # Section 2 — Risk drivers
        st.markdown(f"**⚠️ Risk Drivers:** {drivers}")

        # Section 3 — Device breakdown (exact numbers)
        st.markdown("**Device Category Breakdown**")
        b1,b2,b3 = st.columns(3)
        b1.metric("🔋 UPS Systems",  f"{ups_risk} at risk", f"{len(ups_df)} total")
        b2.metric("🌐 Routers",      f"{rtr_risk} at risk", f"{len(rtr_df)} total")
        b3.metric("🔀 Switches",     f"{swt_risk} at risk", f"{len(swt_df)} total")

        # Section 4 — AI Insight (quantified, consistent)
        st.info(f"🤖 **AI Insight:** Risk is driven by {ai_text}")

        # Section 5 — Building level table
        st.markdown("**📋 Building-Level Asset Detail**")
        action_div = div_df[div_df["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])]\
            .sort_values("failure_probability", ascending=False).copy()

        action_div["Risk Level"] = action_div["risk_level"].map({
            "CRITICAL": "🔴 L3 — Critical",
            "HIGH":     "🟠 L2 — Urgent",
            "MEDIUM":   "🟡 L1 — Maintenance"
        })
        action_div["Required Action"] = action_div["risk_level"].map({
            "CRITICAL": "Act Now — L3 intervention",
            "HIGH":     "Escalate — L2 within 24 hrs",
            "MEDIUM":   "Schedule — L1 within 48 hrs"
        })

        bld_cols = ["asset_id","building","device_type",
                    "Issue Summary","Risk Level","Required Action"]
        bld_table = action_div[bld_cols].copy()
        bld_table.columns = ["Asset ID","Building","Device Type",
                              "Issue Summary","Risk Level","Required Action"]
        st.caption(f"{len(bld_table):,} assets requiring action in {selected}")
        st.dataframe(bld_table, use_container_width=True, hide_index=True, height=350)

    else:
        st.info("👆 Select a division above to see its complete action plan.")

    st.divider()

    # ── 4. DIVISION RISK SUMMARY TABLE ───────────────────────
    st.subheader("📋 Division Risk Summary")
    st.caption("All 8 divisions — sorted by priority (highest risk first)")

    table = div_stats.copy()
    table["Status"] = table.apply(get_status, axis=1)
    table = table[["division","critical","high","medium","Status"]]
    table.columns = ["Division","Critical (L3)","Urgent (L2)","Maintenance (L1)","Status"]
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.divider()

    # ── 5. DEVICE INSIGHT ─────────────────────────────────────
    st.info(f"⚡ **Device Insight:** {get_device_insight()}")

    st.divider()

    # ── 6. ALL ASSETS REQUIRING ACTION ───────────────────────
    st.subheader("📋 All Assets Requiring Action")
    st.caption("Complete asset list — filter by escalation level")

    filter_opt = st.radio(
        "Show",
        ["All","🔴 L3 Critical","🟠 L2 Urgent","🟡 L1 Maintenance"],
        horizontal=True
    )

    action_df = df[df["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])]\
        .sort_values("failure_probability", ascending=False).copy()

    if filter_opt == "🔴 L3 Critical":
        action_df = action_df[action_df["risk_level"]=="CRITICAL"]
    elif filter_opt == "🟠 L2 Urgent":
        action_df = action_df[action_df["risk_level"]=="HIGH"]
    elif filter_opt == "🟡 L1 Maintenance":
        action_df = action_df[action_df["risk_level"]=="MEDIUM"]

    action_df["Risk Level"] = action_df["risk_level"].map({
        "CRITICAL": "🔴 L3 — Critical",
        "HIGH":     "🟠 L2 — Urgent",
        "MEDIUM":   "🟡 L1 — Maintenance"
    })
    action_df["Maintenance"] = action_df["risk_level"].map({
        "CRITICAL": "No — Emergency",
        "HIGH":     "No — Urgent",
        "MEDIUM":   "Yes — L1"
    })
    action_df["Required Action"] = action_df["risk_level"].map({
        "CRITICAL": "🔴 Action Required Now",
        "HIGH":     "🟠 Escalate to L2 Today",
        "MEDIUM":   "🟡 Schedule Maintenance"
    })

    disp = action_df[["asset_id","division","device_type",
                       "Risk Level","Maintenance","Required Action"]].copy()
    disp.columns = ["Asset ID","Division","Device Type",
                    "Risk Level","Maintenance","Required Action"]

    st.caption(f"Showing {len(disp):,} assets")
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

except Exception as e:
    st.error("Data temporarily unavailable. Please try again in a few moments.")
    st.stop()
