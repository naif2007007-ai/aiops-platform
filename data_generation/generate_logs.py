import pandas as pd
import numpy as np
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM
from s3_helper import upload
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

            if asset["device_type"] == "UPS":
                # UPS specific metrics
                cpu  = float(np.clip(rng.uniform(10,30)*deg+rng.normal(0,3),0,100))
                mem  = float(np.clip(rng.uniform(20,40)*deg+rng.normal(0,3),0,100))
                lat  = float(np.clip(rng.uniform(10,50)*deg+rng.normal(0,5),0,500))
                # Battery degrades over time
                batt = float(np.clip(
                    (asset["battery_health_pct"] or 80)
                    - (day/SIM["days"])*10*deg
                    + rng.normal(0,2), 0, 100))
                load = float(np.clip(
                    (asset["ups_load_pct"] or 60)*deg
                    + rng.normal(0,5), 0, 100))
                runtime = float(np.clip(
                    (asset["ups_runtime_min"] or 30)
                    - (load*0.2)*deg
                    + rng.normal(0,2), 0, 60))
            else:
                # Network device metrics
                cpu  = float(np.clip(rng.uniform(35,65)*deg+rng.normal(0,5),0,100))
                mem  = float(np.clip(rng.uniform(40,70)*deg+rng.normal(0,5),0,100))
                lat  = float(np.clip(rng.uniform(50,150)*deg+rng.normal(0,10),0,2000))
                batt = None
                load = None
                runtime = None

            err  = int(rng.poisson(2)*deg+rng.poisson(0.5))
            warn = int(rng.poisson(5)*deg+rng.poisson(1))
            mem_history.append(mem)
            trend = round(float(mem_history[-1]-mem_history[-7]),2) if len(mem_history)>=7 else 0.0
            open_changes = int(rng.poisson(0.5*deg if asset["will_fail"] else 0.2))

            rows.append({
                "asset_id":              asset["asset_id"],
                "division":              asset["division"],
                "device_type":           asset["device_type"],
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
                "battery_health_pct":    round(batt,1) if batt is not None else None,
                "ups_load_pct":          round(load,1) if load is not None else None,
                "ups_runtime_min":       round(runtime,1) if runtime is not None else None,
            })
    return pd.DataFrame(rows)

def generate_logs(assets):
    batch_size  = 100
    all_batches = []
    total = len(assets)
    for i in range(0, total, batch_size):
        batch = assets.iloc[i:i+batch_size]
        print(f"  Processing assets {i+1} to {min(i+batch_size,total)} of {total}...")
        all_batches.append(generate_logs_batch(batch))
    return pd.concat(all_batches, ignore_index=True)

if __name__ == "__main__":
    assets = generate_assets()
    logs   = generate_logs(assets)
    upload(logs, S3["raw_logs"])
    print(f"Logs generated: {len(logs):,}")
    print(f"\nBy device type:")
    print(logs.groupby("device_type")["asset_id"].count().to_string())
