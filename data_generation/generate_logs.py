import pandas as pd
import numpy as np
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM
from s3_helper import upload, download
from generate_assets import generate_assets

rng = np.random.default_rng(SIM["random_seed"]+3)

def generate_logs_batch(assets_batch):
    rows  = []
    start = datetime.today() - timedelta(days=SIM["days"])
    for _, asset in assets_batch.iterrows():
        mem_history = []
        for day in range(SIM["days"]):
            date = (start + timedelta(days=day)).strftime("%Y-%m-%d")
            dte  = SIM["days"] - day
            deg  = 1.0+(30-dte)/30*4.0 if asset["will_fail"] and dte<=30 else 1.0
            cpu  = float(np.clip(rng.uniform(35,65)*deg+rng.normal(0,5),0,100))
            mem  = float(np.clip(rng.uniform(40,70)*deg+rng.normal(0,5),0,100))
            lat  = float(np.clip(rng.uniform(50,150)*deg+rng.normal(0,10),0,2000))
            err  = int(rng.poisson(2)*deg+rng.poisson(0.5))
            warn = int(rng.poisson(5)*deg+rng.poisson(1))
            mem_history.append(mem)
            if len(mem_history) >= 7:
                trend = round(float(mem_history[-1] - mem_history[-7]), 2)
            else:
                trend = 0.0
            open_changes = int(rng.poisson(0.5*deg if asset["will_fail"] else 0.2))
            rows.append({
                "asset_id":              asset["asset_id"],
                "date":                  date,
                "error_count":           err,
                "warning_count":         warn,
                "avg_cpu_pct":           round(cpu,2),
                "avg_mem_pct":           round(mem,2),
                "avg_latency_ms":        round(lat,1),
                "auth_failure_count":    int(rng.poisson(0.5*deg)),
                "anomaly_spike":         bool(cpu>85 or mem>90 or lat>400 or err>10),
                "memory_pressure_trend": trend,
                "open_change_requests":  open_changes,
            })
    return pd.DataFrame(rows)

def generate_logs(assets):
    batch_size = 200
    all_batches = []
    total = len(assets)
    for i in range(0, total, batch_size):
        batch = assets.iloc[i:i+batch_size]
        print(f"  Processing assets {i+1} to {min(i+batch_size, total)} of {total}...")
        df_batch = generate_logs_batch(batch)
        all_batches.append(df_batch)
    return pd.concat(all_batches, ignore_index=True)

if __name__ == "__main__":
    assets = generate_assets()
    logs   = generate_logs(assets)
    upload(logs, S3["raw_logs"])
    print(f"Logs generated: {len(logs):,}")
