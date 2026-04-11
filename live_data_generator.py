import boto3
import pandas as pd
import numpy as np
import io
import os
import time
from datetime import datetime, timedelta

BUCKET = "aiops-platform-poc"
REGION = "eu-north-1"
rng    = np.random.default_rng()

ASSETS = [f"ASSET-{str(i).zfill(4)}" for i in range(1, 2001)]
LOCATIONS    = ["DC-East-A1","DC-East-A2","DC-West-B1","DC-West-B2","DC-Central-C1"]
EVENT_TYPES  = ["LinkDown","HighCPU","HighMemory","DiskFull","PacketLoss",
                "LatencySpike","AuthFailure","HardwareError","ConfigChange","ReachabilityLost"]
SEVERITIES   = ["Critical","Major","Minor","Warning","Informational"]
SEV_W        = [0.08,0.17,0.25,0.30,0.20]
DEVICE_TYPES = ["Router","Switch","Server","Storage","Firewall","LoadBalancer"]

def upload_to_s3(df, key):
    client = boto3.client("s3", region_name=REGION)
    buf    = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    client.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"  ✅ Uploaded {len(df):,} rows → s3://{BUCKET}/{key}")

def generate_live_alarms():
    now   = datetime.utcnow()
    rows  = []
    n     = rng.integers(50, 150)
    for i in range(n):
        asset    = rng.choice(ASSETS)
        ts       = now - timedelta(minutes=int(rng.integers(0, 15)))
        rows.append({
            "alarm_id":         f"LIVE-ALM-{int(time.time())}-{i}",
            "asset_id":         asset,
            "timestamp":        ts.strftime("%Y-%m-%d %H:%M:%S"),
            "severity":         rng.choice(SEVERITIES, p=SEV_W),
            "event_type":       rng.choice(EVENT_TYPES),
            "device_type":      rng.choice(DEVICE_TYPES),
            "location":         rng.choice(LOCATIONS),
            "recurrence_count": int(rng.integers(1, 5)),
            "acknowledged":     bool(rng.choice([True,False], p=[0.60,0.40])),
            "packet_loss_pct":  round(float(rng.uniform(0, 5)), 2),
            "generated_at":     now.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)

def generate_live_logs():
    now  = datetime.utcnow()
    rows = []
    sample_assets = rng.choice(ASSETS, size=100, replace=False)
    for asset in sample_assets:
        cpu  = float(np.clip(rng.normal(55, 20), 0, 100))
        mem  = float(np.clip(rng.normal(60, 15), 0, 100))
        lat  = float(np.clip(rng.normal(120, 80), 0, 2000))
        rows.append({
            "asset_id":              asset,
            "date":                  now.strftime("%Y-%m-%d"),
            "error_count":           int(rng.poisson(3)),
            "warning_count":         int(rng.poisson(8)),
            "avg_cpu_pct":           round(cpu, 2),
            "avg_mem_pct":           round(mem, 2),
            "avg_latency_ms":        round(lat, 1),
            "auth_failure_count":    int(rng.poisson(1)),
            "anomaly_spike":         bool(cpu>85 or mem>90 or lat>400),
            "memory_pressure_trend": round(float(rng.normal(0, 2)), 2),
            "open_change_requests":  int(rng.poisson(0.3)),
            "generated_at":          now.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)

def main():
    print(f"\n{'='*50}")
    print(f"  Live Data Generator — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*50}")

    print("\n[1/2] Generating live alarms ...")
    alarms = generate_live_alarms()
    upload_to_s3(alarms, f"live/alarms/alarms_{int(time.time())}.parquet")

    print("\n[2/2] Generating live logs ...")
    logs = generate_live_logs()
    upload_to_s3(logs, f"live/logs/logs_{int(time.time())}.parquet")

    print(f"\n✅ Done at {datetime.utcnow().strftime('%H:%M:%S')} UTC")

if __name__ == "__main__":
    main()
