import sys, os, time
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3
from s3_helper import upload
from generate_assets  import generate_assets
from generate_alarms  import generate_alarms
from generate_tickets import generate_tickets
from generate_logs    import generate_logs

def main():
    t0 = time.time()
    print("="*50)
    print("  AI-Ops — Data Generation")
    print("="*50)
    print("\n[1/4] Generating ASSETS ...")
    assets = generate_assets()
    upload(assets, S3["raw_assets"])
    print("\n[2/4] Generating ALARMS ...")
    alarms = generate_alarms(assets)
    upload(alarms, S3["raw_alarms"])
    print("\n[3/4] Generating TICKETS ...")
    tickets = generate_tickets(assets, alarms)
    upload(tickets, S3["raw_tickets"])
    print("\n[4/4] Generating LOGS ...")
    logs = generate_logs(assets)
    upload(logs, S3["raw_logs"])
    print(f"\nDone in {time.time()-t0:.1f}s")
    print(f"Assets:{len(assets):,} Alarms:{len(alarms):,} Tickets:{len(tickets):,} Logs:{len(logs):,}")

if __name__ == "__main__":
    main()
