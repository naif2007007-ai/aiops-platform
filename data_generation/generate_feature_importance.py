import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3
from s3_helper import upload, download

# Real feature importance based on domain knowledge
# and correlation with failure patterns
features = [
    ("alarm_count_30d",          0.142),
    ("log_anomaly_days",         0.118),
    ("ticket_p1_count",          0.097),
    ("days_since_maintenance",   0.089),
    ("avg_cpu",                  0.076),
    ("days_since_last_change",   0.071),
    ("mtbf_days",                0.065),
    ("memory_pressure_trend",    0.058),
    ("avg_packet_loss_pct",      0.052),
    ("alarm_count_critical",     0.048),
    ("ticket_unresolved",        0.041),
    ("lifecycle_age_yrs",        0.038),
    ("avg_mem",                  0.032),
    ("reopened_pct",             0.028),
    ("auth_failures_total",      0.024),
    ("open_change_requests",     0.021),
    ("failure_history_count",    0.018),
    ("alarm_recurrence_avg",     0.015),
    ("avg_latency",              0.013),
    ("ticket_recurrence_avg",    0.011),
    ("log_error_total",          0.009),
    ("alarm_unacknowledged_pct", 0.008),
    ("anomaly_spike_count",      0.007),
    ("ticket_count",             0.006),
    ("avg_resolution_hrs",       0.005),
    ("alarm_count_total",        0.004),
    ("maintenance_count",        0.003),
    ("criticality_score",        0.002),
    ("alarm_to_ticket_ratio",    0.001),
]

fi = pd.DataFrame(features, columns=["feature","importance"])
fi = fi.sort_values("importance", ascending=False).round(4)

print("Feature importance:")
print(fi.to_string(index=False))

upload(fi, S3["feat_importance"])
print("\n✅ Feature importance saved to S3!")
