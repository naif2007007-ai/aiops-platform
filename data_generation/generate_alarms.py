import pandas as pd
import numpy as np
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM
from s3_helper import upload
from generate_assets import generate_assets

rng = np.random.default_rng(SIM["random_seed"]+1)
SEVERITIES   = ["Critical","Major","Minor","Warning","Informational"]
SEV_W        = [0.05,0.15,0.25,0.30,0.25]
EVENT_TYPES  = ["LinkDown","HighCPU","HighMemory","DiskFull","PacketLoss",
                "LatencySpike","AuthFailure","HardwareError","ConfigChange","ReachabilityLost"]
DEVICE_TYPES = ["Router","Switch","Server","Storage","Firewall","LoadBalancer"]

def generate_alarms(assets):
    rows, seq = [], 1
    start = datetime.today() - timedelta(days=SIM["days"])
    for _, asset in assets.iterrows():
        for day in range(SIM["days"]):
            date = start + timedelta(days=day)
            dte  = SIM["days"] - day
            if asset["will_fail"]:
                ramp  = 1 + max(0,(30-dte)/30)*8
                rate  = SIM["alarm_rate_failing"]*ramp
                sev_w = [0.20,0.35,0.25,0.15,0.05] if dte<=30 else SEV_W
                # packet loss increases as asset degrades
                packet_loss = float(np.clip(
                    rng.uniform(2,15) * (1 + (SIM["days"]-dte)/SIM["days"]*3),
                    0, 100
                ))
            else:
                rate, sev_w = SIM["alarm_rate_normal"], SEV_W
                packet_loss = float(np.clip(rng.uniform(0,2), 0, 100))

            for _ in range(rng.poisson(rate)):
                ts = date + timedelta(
                    hours=int(rng.integers(0,24)),
                    minutes=int(rng.integers(0,60))
                )
                rows.append({
                    "alarm_id":         f"ALM-{str(seq).zfill(7)}",
                    "asset_id":         asset["asset_id"],
                    "timestamp":        ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "severity":         rng.choice(SEVERITIES,p=sev_w),
                    "event_type":       rng.choice(EVENT_TYPES),
                    "device_type":      rng.choice(DEVICE_TYPES),
                    "location":         asset["location"],
                    "recurrence_count": int(rng.integers(1,6)),
                    "acknowledged":     bool(rng.choice([True,False],p=[0.65,0.35])),
                    "packet_loss_pct":  round(packet_loss, 2),
                })
                seq += 1
    return pd.DataFrame(rows)

if __name__ == "__main__":
    assets = generate_assets()
    alarms = generate_alarms(assets)
    upload(alarms, S3["raw_alarms"])
    print(f"Alarms generated: {len(alarms):,}")
