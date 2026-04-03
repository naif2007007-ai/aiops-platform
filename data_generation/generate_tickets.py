import pandas as pd
import numpy as np
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, SIM
from s3_helper import upload
from generate_assets import generate_assets
from generate_alarms import generate_alarms

rng = np.random.default_rng(SIM["random_seed"]+2)
PRIORITIES    = ["P1 - Critical","P2 - High","P3 - Medium","P4 - Low"]
PW_NORMAL     = [0.05,0.20,0.45,0.30]
PW_FAIL       = [0.30,0.40,0.20,0.10]
ASSIGN_GROUPS = ["Network-Ops","Server-Ops","Storage-Ops","Security-Ops","Application-Ops","Field-Services"]
STATUSES      = ["Closed","Resolved","Open","In Progress","On Hold"]
STATUS_W      = [0.55,0.25,0.08,0.08,0.04]
RES_HOURS     = {"P1 - Critical":(1,8),"P2 - High":(4,24),"P3 - Medium":(8,72),"P4 - Low":(24,168)}

def generate_tickets(assets, alarms):
    ta       = alarms.sample(frac=0.25, random_state=SIM["random_seed"]).copy()
    fail_map = dict(zip(assets["asset_id"], assets["will_fail"]))
    rows     = []
    for idx,(_, alarm) in enumerate(ta.iterrows()):
        wf  = fail_map.get(alarm["asset_id"],0)
        pri = rng.choice(PRIORITIES, p=PW_FAIL if wf else PW_NORMAL)
        t0  = datetime.strptime(alarm["timestamp"],"%Y-%m-%d %H:%M:%S")
        lo,hi = RES_HOURS[pri]
        res = float(rng.uniform(lo,hi))
        rows.append({"ticket_id":f"INC-{str(idx+1).zfill(7)}",
            "asset_id":alarm["asset_id"],"alarm_id":alarm["alarm_id"],
            "open_time":t0.strftime("%Y-%m-%d %H:%M:%S"),
            "close_time":(t0+timedelta(hours=res)).strftime("%Y-%m-%d %H:%M:%S"),
            "priority":pri,"status":rng.choice(STATUSES,p=STATUS_W),
            "assignment_group":rng.choice(ASSIGN_GROUPS),
            "resolution_time_hrs":round(res,2),
            "reopened":bool(rng.choice([True,False],p=[0.12,0.88]))})
    df = pd.DataFrame(rows)
    df["open_time_dt"] = pd.to_datetime(df["open_time"])
    df = df.sort_values(["asset_id","open_time_dt"])
    df["recurrence_within_30d"] = (df.groupby("asset_id")["open_time_dt"]
        .transform(lambda s: s.diff().dt.days.lt(30).cumsum()).astype(int))
    return df.drop(columns=["open_time_dt"])

if __name__ == "__main__":
    assets  = generate_assets()
    alarms  = generate_alarms(assets)
    tickets = generate_tickets(assets, alarms)
    upload(tickets, S3["raw_tickets"])
