import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM, DIVISIONS
from s3_helper import upload

rng = np.random.default_rng(SIM["random_seed"])

MODELS = {
    "Router": ["Cisco-ASR-9001","Cisco-ASR-9006","Juniper-MX240","Juniper-MX480","Cisco-NCS-5500"],
    "Switch": ["Cisco-Catalyst-9300","Cisco-Nexus-9300","Arista-7050CX3","Cisco-Catalyst-9500","Juniper-EX4300"],
    "UPS":    ["APC-Smart-UPS-3000","Eaton-9PX-6000","Vertiv-Liebert-GXT5","APC-Symmetra-LX","Eaton-5PX-3000"],
}
CRITICALITY = ["Critical","High","Medium","Low"]
CRIT_W      = [0.15,0.25,0.40,0.20]

def generate_assets():
    rows = []
    asset_num = 1

    for division, counts in DIVISIONS.items():
        for device_type, count in [
            ("Router",  counts["routers"]),
            ("Switch",  counts["switches"]),
            ("UPS",     counts["ups"])
        ]:
            for _ in range(count):
                age_days  = int(rng.integers(180,3650))
                age_yrs   = round(age_days/365, 2)
                maint_days= int(rng.integers(1,400))
                maint_cnt = int(np.clip(age_yrs*rng.uniform(0.8,2.5),0,20))

                if device_type == "UPS":
                    battery_health  = round(float(np.clip(
                        100-(age_yrs*rng.uniform(8,15))+rng.normal(0,5),10,100)),1)
                    battery_age_yrs = round(float(rng.uniform(0.5,5.0)),1)
                    load_pct        = round(float(np.clip(rng.uniform(40,95),0,100)),1)
                    runtime_min     = round(float(np.clip(
                        60-(load_pct*0.4)-(battery_age_yrs*3)+rng.normal(0,5),2,60)),1)
                else:
                    battery_health  = None
                    battery_age_yrs = None
                    load_pct        = None
                    runtime_min     = None

                fail_score = float(np.clip(
                    0.35*(age_yrs/10)
                    +0.25*(maint_days/400)
                    +0.25*rng.uniform(0,1)
                    +0.15*rng.uniform(0,1)
                    +rng.normal(0,0.15), 0, 1
                ))

                if device_type == "UPS" and battery_age_yrs and battery_age_yrs > 3.5:
                    fail_score = min(1.0, fail_score+0.2)

                rows.append({
                    "asset_id":               f"ASSET-{str(asset_num).zfill(4)}",
                    "serial_number":          f"SN-{rng.integers(100000,999999)}",
                    "division":               division,
                    "device_type":            device_type,
                    "model":                  rng.choice(MODELS[device_type]),
                    "install_date":           (pd.Timestamp("today")-pd.Timedelta(days=age_days)).strftime("%Y-%m-%d"),
                    "lifecycle_age_yrs":      age_yrs,
                    "criticality":            rng.choice(CRITICALITY,p=CRIT_W),
                    "last_maintenance_date":  (pd.Timestamp("today")-pd.Timedelta(days=maint_days)).strftime("%Y-%m-%d"),
                    "maintenance_count":      maint_cnt,
                    "days_since_maintenance": maint_days,
                    "mtbf_days":              round(float(np.clip(365/(maint_cnt+1)*rng.uniform(0.5,1.5),30,730)),1),
                    "failure_history_count":  int(np.clip(age_yrs*rng.uniform(0.1,0.8),0,10)),
                    "battery_health_pct":     battery_health,
                    "battery_age_yrs":        battery_age_yrs,
                    "ups_load_pct":           load_pct,
                    "ups_runtime_min":        runtime_min,
                    "fail_score":             round(fail_score,4),
                    "will_fail":              0,
                })
                asset_num += 1

    df = pd.DataFrame(rows)

    # Set will_fail using percentile threshold — guarantees exact failure rate
    threshold = np.percentile(df["fail_score"].values, 100*(1-SIM["failure_pct"]))
    df["will_fail"] = (df["fail_score"] >= threshold).astype(int)

    print(f"Failure rate: {df['will_fail'].mean():.1%} ({df['will_fail'].sum()} assets)")
    return df

if __name__ == "__main__":
    assets = generate_assets()
    upload(assets, S3["raw_assets"])
    print(f"Assets generated: {len(assets):,}")
    print(f"\nBy division:")
    print(assets.groupby("division")["asset_id"].count().to_string())
    print(f"\nBy device type:")
    print(assets.groupby("device_type")["asset_id"].count().to_string())
