# ============================================================
# config.py — Central Configuration
# All S3 paths, thresholds, and global constants live here.
# Edit BUCKET_NAME before running.
# ============================================================

import os

# ── AWS ─────────────────────────────────────────────────────
BUCKET_NAME = os.getenv("AIOPS_S3_BUCKET", "aiops-platform-poc")
AWS_REGION   = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

# ── S3 Key Prefixes ──────────────────────────────────────────
S3 = {
    # Raw simulated data
    "raw_assets":   f"s3://{BUCKET_NAME}/raw/assets.parquet",
    "raw_alarms":   f"s3://{BUCKET_NAME}/raw/alarms.parquet",
    "raw_tickets":  f"s3://{BUCKET_NAME}/raw/tickets.parquet",
    "raw_logs":     f"s3://{BUCKET_NAME}/raw/logs.parquet",

    # Processed / engineered features
    "features":     f"s3://{BUCKET_NAME}/processed/features.parquet",

    # Model outputs
    "predictions":  f"s3://{BUCKET_NAME}/models/predictions.parquet",
    "feat_importance": f"s3://{BUCKET_NAME}/models/feature_importance.parquet",
}

# ── Simulation Parameters ────────────────────────────────────
SIM = {
    "n_assets":           200,
    "days":               90,        # days of history to simulate
    "alarm_rate_normal":  0.05,      # alarms per asset-day (normal)
    "alarm_rate_failing": 0.40,      # alarms per asset-day (pre-failure)
    "failure_pct":        0.15,      # fraction of assets that will fail
    "random_seed":        42,
}

# ── ML Thresholds ────────────────────────────────────────────
ML = {
    "anomaly_contamination": 0.12,   # IsolationForest contamination
    "risk_high":    0.70,
    "risk_medium":  0.40,
    "test_size":    0.25,
}

# ── Risk Labels ──────────────────────────────────────────────
RISK_LABELS = {
    "HIGH":   {"color": "#E24B4A", "action": "Immediate maintenance — escalate to L2"},
    "MEDIUM": {"color": "#EF9F27", "action": "Schedule maintenance within 48 h"},
    "LOW":    {"color": "#639922", "action": "Monitor — standard patrol cycle"},
}
