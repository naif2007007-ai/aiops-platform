import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3
from s3_helper import upload, download

def build_alarm_features(alarms):
    alarms["timestamp"] = pd.to_datetime(alarms["timestamp"])
    cut = alarms["timestamp"].max() - pd.Timedelta(days=30)
    g   = alarms.groupby("asset_id")
    return pd.DataFrame({
        "alarm_count_total":        g.size(),
        "alarm_count_critical":     alarms[alarms["severity"]=="Critical"].groupby("asset_id").size(),
        "alarm_count_30d":          alarms[alarms["timestamp"]>=cut].groupby("asset_id").size(),
        "alarm_recurrence_avg":     g["recurrence_count"].mean().round(2),
        "alarm_unacknowledged_pct": (~alarms["acknowledged"]).groupby(alarms["asset_id"]).sum()/g.size()*100,
        "avg_packet_loss_pct":      g["packet_loss_pct"].mean().round(2),
    }).fillna(0).reset_index()

def build_ticket_features(tickets):
    g = tickets.groupby("asset_id")
    return pd.DataFrame({
        "ticket_count":           g.size(),
        "ticket_p1_count":        tickets[tickets["priority"]=="P1 - Critical"].groupby("asset_id").size(),
        "ticket_unresolved":      tickets[tickets["status"].isin(["Open","In Progress"])].groupby("asset_id").size(),
        "avg_resolution_hrs":     g["resolution_time_hrs"].mean().round(2),
        "ticket_recurrence_avg":  g["recurrence_within_30d"].mean().round(2),
        "reopened_pct":           tickets[tickets["reopened"]].groupby("asset_id").size()/g.size()*100,
        "days_since_last_change": g["days_since_last_change"].min(),
    }).fillna(0).reset_index()

def build_log_features(logs):
    g = logs.groupby("asset_id")
    features = pd.DataFrame({
        "log_anomaly_days":         g["anomaly_spike"].sum(),
        "log_error_total":          g["error_count"].sum(),
        "log_warning_total":        g["warning_count"].sum(),
        "avg_cpu":                  g["avg_cpu_pct"].mean().round(2),
        "avg_mem":                  g["avg_mem_pct"].mean().round(2),
        "avg_latency":              g["avg_latency_ms"].mean().round(1),
        "auth_failures_total":      g["auth_failure_count"].sum(),
        "anomaly_spike_count":      g["anomaly_spike"].sum(),
        "memory_pressure_trend":    g["memory_pressure_trend"].mean().round(2),
        "open_change_requests":     g["open_change_requests"].sum(),
    }).fillna(0).reset_index()

    # UPS specific features
    if "battery_health_pct" in logs.columns:
        ups_features = pd.DataFrame({
            "avg_battery_health":  g["battery_health_pct"].mean().round(2),
            "min_battery_health":  g["battery_health_pct"].min().round(2),
            "avg_ups_load":        g["ups_load_pct"].mean().round(2),
            "avg_ups_runtime":     g["ups_runtime_min"].mean().round(2),
        }).fillna(0).reset_index()
        features = features.merge(ups_features, on="asset_id", how="left")

    return features

def build_features():
    print("Loading raw datasets from S3 ...")
    assets  = download(S3["raw_assets"])
    alarms  = download(S3["raw_alarms"])
    tickets = download(S3["raw_tickets"])
    logs    = download(S3["raw_logs"])
    print(f"  assets={len(assets):,} alarms={len(alarms):,} tickets={len(tickets):,} logs={len(logs):,}")

    print("Building features ...")
    crit_map = {"Critical":4,"High":3,"Medium":2,"Low":1}
    type_map = {"Router":3,"Switch":2,"UPS":1}

    base = assets[[
        "asset_id","division","device_type","lifecycle_age_yrs",
        "days_since_maintenance","maintenance_count","criticality",
        "will_fail","mtbf_days","failure_history_count",
        "battery_health_pct","battery_age_yrs",
        "ups_load_pct","ups_runtime_min","fail_score"
    ]].copy()
    base["criticality_score"] = base["criticality"].map(crit_map)
    base["device_type_score"] = base["device_type"].map(type_map)

    af = build_alarm_features(alarms)
    tf = build_ticket_features(tickets)
    lf = build_log_features(logs)

    feat = (base
            .merge(af, on="asset_id", how="left")
            .merge(tf, on="asset_id", how="left")
            .merge(lf, on="asset_id", how="left"))

    feat["alarm_to_ticket_ratio"] = (
        feat["ticket_count"]/feat["alarm_count_total"].replace(0,np.nan)
    ).fillna(0).round(4)

    num_cols = feat.select_dtypes(include=[np.number]).columns
    feat[num_cols] = feat[num_cols].fillna(0)

    print(f"  Feature table: {feat.shape[0]:,} assets x {feat.shape[1]} columns")
    return feat

if __name__ == "__main__":
    feat = build_features()
    upload(feat, S3["features"])
    print("Pipeline complete.")
