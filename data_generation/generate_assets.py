import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM
from s3_helper import upload

rng = np.random.default_rng(SIM["random_seed"])
MODELS = ["Cisco-ASR-9001","Cisco-ASR-9006","Juniper-MX240","Dell-R740",
          "HPE-DL380","NetApp-AFF-A400","Palo-Alto-5220","F5-BIG-IP-i5800","Arista-7050CX3"]
LOCATIONS   = ["DC-East-A1","DC-East-A2","DC-West-B1","DC-West-B2","DC-Central-C1"]
CRITICALITY = ["Critical","High","Medium","Low"]
CRIT_W      = [0.15,0.25,0.40,0.20]

def generate_assets(n=SIM["n_assets"]):
    install_dates = pd.to_datetime("today") - pd.to_timedelta(rng.integers(180,3650,size=n), unit="D")
    lifecycle_age = ((pd.Timestamp("today") - install_dates).days / 365).round(2)
    days_since    = rng.integers(1,400,size=n)
    last_maint    = pd.to_datetime("today") - pd.to_timedelta(days_since, unit="D")
    maint_count   = np.clip((lifecycle_age * rng.uniform(0.8,2.5,size=n)).astype(int),0,20)
    fail_score    = (0.4*(lifecycle_age/lifecycle_age.max())
                    +0.3*(days_since/days_since.max())
                    +0.3*rng.uniform(0,1,size=n))
    threshold     = np.percentile(fail_score,100*(1-SIM["failure_pct"]))
    will_fail     = (fail_score>=threshold).astype(int)
    return pd.DataFrame({
        "asset_id":               [f"ASSET-{str(i).zfill(4)}" for i in range(1,n+1)],
        "serial_number":          [f"SN-{rng.integers(100000,999999)}" for _ in range(n)],
        "model":                  rng.choice(MODELS,size=n),
        "location":               rng.choice(LOCATIONS,size=n),
        "install_date":           install_dates.strftime("%Y-%m-%d"),
        "lifecycle_age_yrs":      lifecycle_age,
        "criticality":            rng.choice(CRITICALITY,size=n,p=CRIT_W),
        "last_maintenance_date":  last_maint.strftime("%Y-%m-%d"),
        "maintenance_count":      maint_count,
        "days_since_maintenance": days_since,
        "will_fail":              will_fail,
    })

if __name__ == "__main__":
    assets = generate_assets()
    upload(assets, S3["raw_assets"])
