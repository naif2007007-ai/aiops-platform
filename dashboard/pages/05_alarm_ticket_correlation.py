# ============================================================
# Page 5 — Alarm-to-Ticket Correlation
# Shows how alarms escalate into incidents.
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from dashboard.data_loader import load_alarms, load_tickets, load_predictions

st.title("🔗 Alarm-to-Ticket Correlation")
st.caption("Visualise how monitoring events escalate into incident tickets")
st.divider()

alarms  = load_alarms()
tickets = load_tickets()
preds   = load_predictions()

alarms["timestamp"]  = pd.to_datetime(alarms["timestamp"])
tickets["open_time"] = pd.to_datetime(tickets["open_time"])

# ── Event type → priority Sankey ──────────────────────────────
st.subheader("Alarm Event Type → Ticket Priority Flow")
merged = alarms.merge(
    tickets[["alarm_id","priority"]], on="alarm_id", how="inner"
)
# Build Sankey
event_types = merged["event_type"].unique().tolist()
priorities  = merged["priority"].unique().tolist()
nodes       = event_types + priorities
node_idx    = {n: i for i, n in enumerate(nodes)}

links = merged.groupby(["event_type","priority"]).size().reset_index(name="value")
sankey_fig = go.Figure(go.Sankey(
    node=dict(
        pad=15, thickness=20,
        label=nodes,
        color=["#AFA9EC"] * len(event_types) + ["#E24B4A","#EF9F27","#639922","#378ADD"],
    ),
    link=dict(
        source=[node_idx[r["event_type"]] for _, r in links.iterrows()],
        target=[node_idx[r["priority"]]   for _, r in links.iterrows()],
        value=links["value"].tolist(),
    )
))
sankey_fig.update_layout(
    height=420, paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(sankey_fig, use_container_width=True)

# ── Alarm severity vs ticket priority heatmap ─────────────────
st.subheader("Alarm Severity ↔ Ticket Priority Heatmap")
heat = merged.groupby(["severity","priority"]).size().reset_index(name="count")
heat_pivot = heat.pivot(index="severity", columns="priority", values="count").fillna(0)
fig_heat = px.imshow(
    heat_pivot,
    color_continuous_scale="RdYlGn_r",
    text_auto=True,
    aspect="auto",
    height=300,
)
fig_heat.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ── Per-asset alarm vs ticket count scatter ───────────────────
st.subheader("Asset Alarm Volume vs Ticket Volume")
alarm_counts  = alarms.groupby("asset_id").size().reset_index(name="alarms")
ticket_counts = tickets.groupby("asset_id").size().reset_index(name="tickets")
combo = alarm_counts.merge(ticket_counts, on="asset_id", how="left").fillna(0)
combo = combo.merge(preds[["asset_id","risk_level"]], on="asset_id", how="left")

fig_sc = px.scatter(
    combo, x="alarms", y="tickets",
    color="risk_level",
    hover_name="asset_id",
    color_discrete_map={"HIGH":"#E24B4A","MEDIUM":"#EF9F27","LOW":"#639922"},
    labels={"alarms":"Total Alarms","tickets":"Total Tickets"},
    height=360,
    trendline="ols",
)
fig_sc.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10,b=10,l=0,r=0),
)
st.plotly_chart(fig_sc, use_container_width=True)
