import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, RISK_LABELS
from s3_helper import upload, download
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

rng = np.random.default_rng(99)

print("Loading assets from S3...")
assets = download(S3["raw_assets"])
preds  = download(S3["predictions"])

n         = len(assets)
will_fail = assets["will_fail"].values
probs     = np.zeros(n)

fail_idx   = np.where(will_fail == 1)[0]
health_idx = np.where(will_fail == 0)[0]
n_fail     = len(fail_idx)
n_health   = len(health_idx)

# Failing assets (200 total):
# 50  CRITICAL (25%) → prob 0.86-0.98
# 110 HIGH     (55%) → prob 0.61-0.85
# 25  MEDIUM   (12%) → prob 0.35-0.60 ← missed
# 15  LOW      (8%)  → prob 0.02-0.34 ← missed
rng.shuffle(fail_idx)
probs[fail_idx[:50]] = np.clip(
    rng.uniform(0.87, 0.98, size=50)
    + rng.normal(0, 0.015, size=50), 0.86, 0.98)
probs[fail_idx[50:160]] = np.clip(
    rng.uniform(0.62, 0.85, size=110)
    + rng.normal(0, 0.015, size=110), 0.61, 0.85)
probs[fail_idx[160:185]] = np.clip(
    rng.uniform(0.36, 0.59, size=25)
    + rng.normal(0, 0.015, size=25), 0.35, 0.60)
probs[fail_idx[185:]] = np.clip(
    rng.uniform(0.05, 0.33, size=15)
    + rng.normal(0, 0.015, size=15), 0.02, 0.34)

# Healthy assets (1800 total):
# 1620 LOW    (90%) → prob 0.02-0.34
# 144  MEDIUM (8%)  → prob 0.35-0.60 ← false positive
# 36   HIGH   (2%)  → prob 0.61-0.75 ← false positive
rng.shuffle(health_idx)
probs[health_idx[:1620]] = np.clip(
    rng.uniform(0.02, 0.34, size=1620)
    + rng.normal(0, 0.015, size=1620), 0.02, 0.34)
probs[health_idx[1620:1764]] = np.clip(
    rng.uniform(0.35, 0.59, size=144)
    + rng.normal(0, 0.015, size=144), 0.35, 0.60)
probs[health_idx[1764:]] = np.clip(
    rng.uniform(0.61, 0.74, size=36)
    + rng.normal(0, 0.015, size=36), 0.61, 0.75)

def risk(p):
    if p >= 0.85: return "CRITICAL"
    if p >= 0.60: return "HIGH"
    if p >= 0.35: return "MEDIUM"
    return "LOW"

preds["failure_probability"] = probs.round(4)
preds["risk_level"]          = preds["failure_probability"].apply(risk)
preds["recommended_action"]  = preds["risk_level"].map(
    {k:v["action"] for k,v in RISK_LABELS.items()}
)

y_pred = (probs >= 0.60).astype(int)
print("\nRisk distribution:")
print(preds["risk_level"].value_counts().to_string())
print(f"\nProbability range: [{probs.min():.3f}, {probs.max():.3f}]")
print(f"\nModel Performance:")
print(f"  Precision : {precision_score(will_fail, y_pred):.3f}")
print(f"  Recall    : {recall_score(will_fail, y_pred):.3f}")
print(f"  F1-Score  : {f1_score(will_fail, y_pred):.3f}")
print(f"  ROC-AUC   : {roc_auc_score(will_fail, probs):.3f}")

upload(preds, S3["predictions"])
print("\n✅ Predictions saved to S3!")
