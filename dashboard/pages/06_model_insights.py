import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import load_feat_importance, load_predictions

st.title("🧠 How the AI Makes Decisions")
st.caption("A plain English explanation of what the AI looks at to predict failures")
st.divider()

fi    = load_feat_importance()
preds = load_predictions()

# ── Model summary cards ───────────────────────────────────────
st.subheader("📊 Model Performance Summary")
st.caption("How accurate is the AI at predicting failures?")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Prediction Accuracy",  "81%",  help="Out of 10 predictions, 8 are correct")
c2.metric("Failures Caught",      "81%",  help="The AI catches 8 out of every 10 real failures")
c3.metric("False Alarms",         "19%",  help="19% of flagged devices turn out to be fine")
c4.metric("Overall AI Score",     "95.3%",help="ROC-AUC — how well AI separates healthy from failing")

st.divider()

# ── Plain English explanation ─────────────────────────────────
st.subheader("🔍 What Does the AI Look At?")
st.caption("The AI analyzes 28 signals from your 4 data sources to make predictions")

col_a, col_b = st.columns([3,2])

with col_a:
    # Rename features to plain English
    fi_display = fi.copy()
    name_map = {
        "alarm_count_30d":          "Recent alerts in last 30 days",
        "log_anomaly_days":         "Days with abnormal behavior",
        "ticket_p1_count":          "Emergency tickets history",
        "days_since_maintenance":   "Days since last service",
        "avg_cpu":                  "Average CPU usage",
        "days_since_last_change":   "Days since last config change",
        "mtbf_days":                "Average time between failures",
        "memory_pressure_trend":    "Memory usage trend (getting worse?)",
        "avg_packet_loss_pct":      "Network packet loss %",
        "alarm_count_critical":     "Critical alerts count",
        "ticket_unresolved":        "Unresolved tickets",
        "lifecycle_age_yrs":        "Device age in years",
        "avg_mem":                  "Average memory usage",
        "reopened_pct":             "Tickets reopened after fixing",
        "auth_failures_total":      "Failed login attempts",
        "open_change_requests":     "Pending configuration changes",
        "failure_history_count":    "Number of past failures",
        "alarm_recurrence_avg":     "How often alerts repeat",
        "avg_latency":              "Average response time",
        "ticket_recurrence_avg":    "How often same problem recurs",
        "log_error_total":          "Total errors logged",
        "alarm_unacknowledged_pct": "Alerts nobody responded to",
        "anomaly_spike_count":      "Days with serious spikes",
        "ticket_count":             "Total tickets raised",
        "avg_resolution_hrs":       "Average time to fix issues",
        "alarm_count_total":        "Total alerts ever",
        "maintenance_count":        "Number of maintenance visits",
        "criticality_score":        "How critical the device is",
        "alarm_to_ticket_ratio":    "How many alerts become tickets",
    }
    fi_display["Signal"] = fi_display["feature"].map(name_map).fillna(fi_display["feature"])
    fi_display["Source"] = fi_display["feature"].apply(lambda x:
        "Netcool" if "alarm" in x else
        "Splunk"  if any(k in x for k in ["cpu","mem","log","latency","anomaly","auth"]) else
        "Remedy"  if any(k in x for k in ["ticket","resolution","reopened","change"]) else
        "SAP"
    )
    fi_display["Importance %"] = (fi_display["importance"] * 100).round(1)
    top15 = fi_display.head(15).sort_values("importance")

    fig = px.bar(
        top15,
        x="Importance %",
        y="Signal",
        orientation="h",
        color="Source",
        color_discrete_map={
            "Netcool": "#E24B4A",
            "Splunk":  "#378ADD",
            "Remedy":  "#EF9F27",
            "SAP":     "#639922",
        },
        height=500,
        text="Importance %",
        labels={"Signal":"What the AI Looks At"}
    )
    fig.update_traces(textposition="outside", texttemplate="%{text}%")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10,b=10,l=0,r=0),
        xaxis_title="How Important This Signal Is (%)",
        yaxis_title="",
        legend_title="Data Source"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("📌 Top 5 Warning Signs")
    st.caption("If a device shows these signs — it is likely to fail soon")
    top5 = fi_display.head(5)
    for i, row in top5.iterrows():
        st.warning(f"**{row['Signal']}**\n\nImportance: {row['Importance %']}% | Source: {row['Source']}")

st.divider()

# ── Risk distribution ─────────────────────────────────────────
st.subheader("📈 How Failure Risk is Distributed")
st.caption("Most devices are healthy — the AI focuses attention on the ones that matter")

fig2 = px.histogram(
    preds, x="failure_probability",
    nbins=20,
    color="risk_level",
    color_discrete_map={
        "CRITICAL": "#7B2D8B",
        "HIGH":     "#E24B4A",
        "MEDIUM":   "#EF9F27",
        "LOW":      "#639922"
    },
    barmode="overlay",
    opacity=0.75,
    height=300,
    labels={
        "failure_probability": "Failure Risk (0% = Safe, 100% = Will Fail)",
        "risk_level":          "Risk Level"
    }
)
fig2.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
    xaxis_tickformat=".0%",
    legend_title="Risk Level"
)
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Model explanation ─────────────────────────────────────────
st.subheader("💡 How the AI Works — Simple Explanation")
col1, col2 = st.columns(2)
with col1:
    st.info("""
**Step 1 — Anomaly Detection**

The AI first looks for devices that behave differently from all others.

Example: If 1,900 devices have 5 alerts per week but one device has 45 alerts — the AI flags it as unusual.

This catches problems that are not yet obvious.
    """)
with col2:
    st.info("""
**Step 2 — Failure Prediction**

The AI then predicts which unusual devices will actually fail.

It learned from historical patterns:
- Devices that failed before shared common warning signs
- The AI now looks for those same signs in current devices

Result: A failure probability % for every device
    """)
