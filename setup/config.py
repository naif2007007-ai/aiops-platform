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

DIVISIONS = {
    "Abqaiq":    {"routers": 45, "switches": 80, "ups": 50},
    "Dhahran":   {"routers": 40, "switches": 70, "ups": 45},
    "RasTanura": {"routers": 35, "switches": 60, "ups": 40},
    "Riyadh":    {"routers": 35, "switches": 55, "ups": 35},
    "Yanbu":     {"routers": 30, "switches": 50, "ups": 30},
    "Jizan":     {"routers": 25, "switches": 40, "ups": 25},
    "Tanajib":   {"routers": 25, "switches": 40, "ups": 25},
    "Adhailiya": {"routers": 40, "switches": 65, "ups": 40},
}

DEVICE_TYPES = ["Router", "Switch", "UPS"]

NETWORK_ALARMS = [
    "LinkDown", "HighCPU", "HighMemory", "PacketLoss",
    "InterfaceError", "BandwidthThreshold", "TemperatureHigh",
    "FirmwareVulnerability", "SpanningTreeChange"
]

UPS_ALARMS = [
    "BatteryLow", "BatteryReplace", "UPSOverload",
    "UPSOnBattery", "UPSBypass", "TemperatureHigh",
    "InputPowerFail", "SelfTestFail", "CommunicationLost"
]

SIM = {
    "n_assets":           1025,
    "days":               730,
    "alarm_rate_normal":  0.05,
    "alarm_rate_failing": 0.40,
    "failure_pct":        0.10,
    "random_seed":        42,
}

ML = {
    "anomaly_contamination": 0.10,
    "risk_critical": 0.85,
    "risk_high":     0.60,
    "risk_medium":   0.35,
    "test_size":     0.25,
}

RISK_LABELS = {
    "CRITICAL": {"color": "#7B2D8B", "action": "Emergency response — engage L3 and vendor immediately"},
    "HIGH":     {"color": "#E24B4A", "action": "Immediate maintenance — escalate to L2"},
    "MEDIUM":   {"color": "#EF9F27", "action": "Schedule maintenance within 48 hours"},
    "LOW":      {"color": "#639922", "action": "Monitor — standard patrol cycle"},
}
