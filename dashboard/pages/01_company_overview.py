import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_assets, load_predictions

try:
    assets = load_assets()
    preds  = load_predictions()

    asset_cols = [c for c in ["asset_id","division","device_type","criticality",
                  "battery_age_yrs","lifecycle_age_yrs","days_since_maintenance",
                  "building"] if c in assets.columns]
    df = preds.merge(assets[asset_cols], on="asset_id", how="left")

    if "building" not in df.columns:
        bldgs = ["Server-01","IT-Building","Admin-Block","Operations-01","Comm-Center"]
        df["building"] = df["asset_id"].apply(
            lambda x: bldgs[int(x.split("-")[1]) % len(bldgs)]
        )

    # ── Core numbers ──────────────────────────────────────────
    critical  = int((df["risk_level"]=="CRITICAL").sum())
    high      = int((df["risk_level"]=="HIGH").sum())
    medium    = int((df["risk_level"]=="MEDIUM").sum())
    crit_divs = int(df[df["risk_level"]=="CRITICAL"]["division"].nunique())
    now       = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")

    # Global device risk counts
    ups_total_risk = int(df[(df["device_type"]=="UPS") &
                        (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0])
    net_total_risk = int(df[(df["device_type"].isin(["Router","Switch"])) &
                        (df["risk_level"].isin(["CRITICAL","HIGH"]))].shape[0])

    # Division summary
    div_stats = df.groupby("division").agg(
        critical=("risk_level", lambda x: int((x=="CRITICAL").sum())),
        high=("risk_level",     lambda x: int((x=="HIGH").sum())),
        medium=("risk_level",   lambda x: int((x=="MEDIUM").sum())),
    ).reset_index()
    div_stats = div_stats.sort_values(
        ["critical","high","medium"], ascending=False
    ).reset_index(drop=True)

    def get_status(row):
        if row["critical"] > 0: return "🔴 Critical"
        if row["high"] > 0:     return "🟠 High"
        if row["medium"] > 0:   return "🟡 Medium"
        return "🟢 Normal"

    def get_issue_summary(row):
        if row["device_type"] == "UPS":
            if row["risk_level"] == "CRITICAL": return "Battery critically degraded — replace immediately"
            elif row["risk_level"] == "HIGH":   return "Battery exceeded lifecycle threshold"
            elif row["risk_level"] == "MEDIUM": return "Battery approaching end of life"
            return "Battery in normal condition"
        elif row["device_type"] == "Router":
            if row["risk_level"] == "CRITICAL": return "Critical CPU overload and packet loss"
            elif row["risk_level"] == "HIGH":   return "High CPU load and network instability"
            elif row["risk_level"] == "MEDIUM": return "Elevated CPU — monitor closely"
            return "Normal operation"
        else:
            if row["risk_level"] == "CRITICAL": return "Critical port errors and bandwidth saturation"
            elif row["risk_level"] == "HIGH":   return "High bandwidth and port errors detected"
            elif row["risk_level"] == "MEDIUM": return "Elevated bandwidth — schedule inspection"
            return "Normal operation"

    def get_ai_insight(division):
        div_df   = df[df["division"]==division]
        ups_risk = int((div_df[(div_df["device_type"]=="UPS") &
                       (div_df["risk_level"].isin(["CRITICAL","HIGH"]))]).shape[0])
        net_risk = int((div_df[(div_df["device_type"].isin(["Router","Switch"])) &
                       (div_df["risk_level"].isin(["CRITICAL","HIGH"]))]).shape[0])
        total    = ups_risk + net_risk
        if total == 0:
            return "No critical issues detected in this division."
        ups_pct = ups_risk / total if total > 0 else 0
        net_pct = net_risk / total if total > 0 else 0
        if ups_risk > 0 and net_risk > 0:
            if ups_pct > 0.60:
                return f"Risk is driven by {ups_risk} UPS units exceeding battery lifecycle threshold, with {net_risk} network devices also requiring attention."
            elif net_pct > 0.60:
                return f"Risk is driven by {net_risk} network devices showing load instability, with {ups_risk} UPS units also requiring attention."
            else:
                return f"Risk is driven by {ups_risk} UPS units and {net_risk} network devices, all requiring immediate intervention."
        elif ups_risk > 0:
            return f"Risk is driven by {ups_risk} UPS units with battery degradation requiring immediate replacement."
        else:
            return f"Risk is driven by {net_risk} network devices showing instability requiring immediate investigation."

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
    st.caption(
        "Risk is driven by infrastructure degradation and network instability "
        "across multiple divisions."
    )

    # ── 2. IMMEDIATE FOCUS ────────────────────────────────────
    with st.expander("🎯 Immediate Focus — Key Actions Required", expanded=True):
        f1, f2 = st.columns(2)
        if ups_total_risk > 0:
            f1.warning(
                f"🔋 Replace degraded UPS batteries across all high-risk divisions "
                f"— {ups_total_risk} units require immediate attention."
            )
        if net_total_risk > 0:
            f2.warning(
                f"🌐 Investigate network instability across all affected divisions "
                f"— {net_total_risk} devices require immediate investigation."
            )

    st.divider()

    # ── 3. KPI CARDS ──────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("🔴 Critical Assets (L3)", f"{critical}",
              delta="Predicted failure within 48 hours",
              delta_color="inverse")
    k2.metric("🟠 Urgent Assets (L2)",    f"{high}",
              delta="Escalation required within 24 hours",
              delta_color="inverse")
    k3.metric("🟡 Maintenance (L1)",      f"{medium}",
              delta="Planned maintenance scheduled",
              delta_color="off")
    k4.metric("⚡ Divisions Impacted",    f"{crit_divs}",
              delta="Divisions with critical assets",
              delta_color="inverse")

    st.divider()

    # ── 4. DIVISION RISK SUMMARY ──────────────────────────────
    st.subheader("📊 Division Risk Summary")
    st.caption("All divisions sorted by highest L3 first, then L2")

    tab_view, chart_view = st.tabs(["📋 Table View", "📊 Chart View"])

    with tab_view:
        table = div_stats.copy()
        table["Status"] = table.apply(get_status, axis=1)
        table = table[["division","critical","high","medium","Status"]]
        table.columns = ["Division","Critical (L3)","Urgent (L2)","Maintenance (L1)","Status"]
        st.dataframe(table, use_container_width=True, hide_index=True)

    with chart_view:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Critical (L3)",
            x=div_stats["division"],
            y=div_stats["critical"],
            marker_color="#D32F2F",
            text=div_stats["critical"],
            textposition="auto"
        ))
        fig.add_trace(go.Bar(
            name="Urgent (L2)",
            x=div_stats["division"],
            y=div_stats["high"],
            marker_color="#E65100",
            text=div_stats["high"],
            textposition="auto"
        ))
        fig.add_trace(go.Bar(
            name="Maintenance (L1)",
            x=div_stats["division"],
            y=div_stats["medium"],
            marker_color="#F57F17",
            text=div_stats["medium"],
            textposition="auto"
        ))
        fig.update_layout(
            barmode="stack",
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10,b=10,l=0,r=0),
            legend=dict(orientation="h", y=-0.25),
            xaxis_title="", yaxis_title="Number of Assets"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 5. ALL ASSETS REQUIRING ACTION ───────────────────────
    st.subheader("📋 All Assets Requiring Action")
    st.caption("Complete asset list — sorted by priority (L3 first, then L2, then L1)")

    filter_opt = st.radio(
        "Filter by",
        ["All","🔴 L3 Critical","🟠 L2 Urgent","🟡 L1 Maintenance"],
        horizontal=True
    )

    action_df = df[df["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])].copy()

    # Sort L3 → L2 → L1
    sort_order = {"CRITICAL":0,"HIGH":1,"MEDIUM":2}
    action_df["sort_key"] = action_df["risk_level"].map(sort_order)
    action_df = action_df.sort_values(
        ["sort_key","failure_probability"],
        ascending=[True,False]
    ).drop(columns="sort_key")

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
    action_df["Required Action"] = action_df["risk_level"].map({
        "CRITICAL": "Immediate Intervention",
        "HIGH":     "Escalate within 24 hours",
        "MEDIUM":   "Schedule Maintenance"
    })

    disp = action_df[["asset_id","division","device_type",
                       "Risk Level","Required Action"]].copy()
    disp.columns = ["Asset ID","Division","Device Type","Risk Level","Required Action"]

    st.caption(f"Showing {len(disp):,} assets")
    st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

    st.divider()

    # ── 6. DIVISION ACTION VIEW ───────────────────────────────
    st.subheader("🔽 Division Action View")
    st.caption("Select a division to see its complete action plan")

    divisions = sorted(df["division"].dropna().unique().tolist())
    selected  = st.selectbox("Select Division",
                             ["— Select a Division —"] + divisions)

    if selected != "— Select a Division —":
        div_df = df[df["division"]==selected].copy()
        div_df["Issue Summary"] = div_df.apply(get_issue_summary, axis=1)

        # Single source of truth
        div_critical = int((div_df["risk_level"]=="CRITICAL").sum())
        div_high     = int((div_df["risk_level"]=="HIGH").sum())
        div_medium   = int((div_df["risk_level"]=="MEDIUM").sum())

        ups_df   = div_df[div_df["device_type"]=="UPS"]
        rtr_df   = div_df[div_df["device_type"]=="Router"]
        swt_df   = div_df[div_df["device_type"]=="Switch"]
        ups_risk = int((ups_df["risk_level"].isin(["CRITICAL","HIGH"])).sum())
        rtr_risk = int((rtr_df["risk_level"].isin(["CRITICAL","HIGH"])).sum())
        swt_risk = int((swt_df["risk_level"].isin(["CRITICAL","HIGH"])).sum())

        ai_insight = get_ai_insight(selected)

        # Section 1 — Summary
        st.markdown(f"### 📍 {selected} Division — Action Summary")
        s1,s2,s3 = st.columns(3)
        s1.error(f"🔴 Critical (L3): **{div_critical}**")
        s2.warning(f"🟠 Urgent (L2): **{div_high}**")
        s3.info(f"🟡 Maintenance (L1): **{div_medium}**")

        # Section 2 — Device breakdown
        st.markdown("**Device Category Breakdown**")
        b1,b2,b3 = st.columns(3)
        b1.metric("🔋 UPS Systems",
                  f"{ups_risk} at risk / {len(ups_df)} total")
        b2.metric("🌐 Routers",
                  f"{rtr_risk} at risk / {len(rtr_df)} total")
        b3.metric("🔀 Switches",
                  f"{swt_risk} at risk / {len(swt_df)} total")

        # Section 3 — AI Insight
        st.info(f"🤖 **AI Insight:** {ai_insight}")

        # Section 4 — Building level table
        st.markdown("**📋 Building-Level Asset Detail**")
        action_div = div_df[div_df["risk_level"].isin(["CRITICAL","HIGH","MEDIUM"])].copy()
        action_div["sort_key"] = action_div["risk_level"].map({"CRITICAL":0,"HIGH":1,"MEDIUM":2})
        action_div = action_div.sort_values(["sort_key","failure_probability"],
                                            ascending=[True,False]).drop(columns="sort_key")

        action_div["Risk Level"] = action_div["risk_level"].map({
            "CRITICAL": "🔴 L3 — Critical",
            "HIGH":     "🟠 L2 — Urgent",
            "MEDIUM":   "🟡 L1 — Maintenance"
        })
        action_div["Required Action"] = action_div["risk_level"].map({
            "CRITICAL": "Immediate Intervention",
            "HIGH":     "Escalate within 24 hours",
            "MEDIUM":   "Schedule Maintenance"
        })

        bld_table = action_div[["asset_id","building","device_type",
                                "Issue Summary","Risk Level","Required Action"]].copy()
        bld_table.columns = ["Asset ID","Building","Device Type",
                             "Issue Summary","Risk Level","Required Action"]
        st.caption(f"{len(bld_table):,} assets requiring action in {selected}")
        st.dataframe(bld_table, use_container_width=True, hide_index=True, height=350)

    else:
        st.info("👆 Select a division above to see its complete action plan.")

except Exception as e:
    st.error("Data temporarily unavailable. Please try again in a few moments.")
    st.stop()
