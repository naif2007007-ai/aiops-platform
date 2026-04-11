import os

BUCKET_NAME  = os.getenv("AIOPS_S3_BUCKET", "aiops-platform-poc")
AWS_REGION   = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

S3 = {
    "raw_assets":      f"s3://{BUCKET_NAME}/raw/assets.parquet",
    "raw_alarms":      f"s3://{BUCKET_NAME}/raw/alarms.parquet",
    "raw_tickets":     f"s3://{BUCKET_NAME}/raw/tickets.parquet",
    "raw_logs":        f"s3://{BUCKET_NAME}/raw/logs.parquet",
    "features":        f"s3://{BUCKET_NAME}/processed/features.parquet",
    "predictions":     f"s3://{BUCKET_NAME}/models/predictions.parquet",
    "feat_importance": f"s3://{BUCKET_NAME}/models/feature_importance.parquet",
    "live_alarms":     f"s3://{BUCKET_NAME}/live/alarms.parquet",
    "live_logs":       f"s3://{BUCKET_NAME}/live/logs.parquet",
}

SIM = {
    "n_assets":           2000,
    "days":               730,
    "alarm_rate_normal":  0.05,
    "alarm_rate_failing": 0.40,
    "failure_pct":        0.10,
    "random_seed":        42,
}

ML = {
    "anomaly_contamination": 0.10,
    "risk_critical": 0.90,
    "risk_high":     0.70,
    "risk_medium":   0.40,
    "test_size":     0.25,
}

RISK_LABELS = {
    "CRITICAL": {"color": "#7B2D8B", "action": "Emergency response — engage L3 and vendor immediately"},
    "HIGH":     {"color": "#E24B4A", "action": "Immediate maintenance — escalate to L2"},
    "MEDIUM":   {"color": "#EF9F27", "action": "Schedule maintenance within 48 hours"},
    "LOW":      {"color": "#639922", "action": "Monitor — standard patrol cycle"},
}
# Override risk thresholds for better distribution
ML["risk_critical"] = 0.85
ML["risk_high"]     = 0.60
ML["risk_medium"]   = 0.35
