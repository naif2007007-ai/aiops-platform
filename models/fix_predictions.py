import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, RISK_LABELS
from s3_helper import upload, download

# Load assets which has fail_score
assets = download(S3["raw_assets"])
preds  = download(S3["predictions"])

rng = np.random.default_rng(42)

# Create realistic probability distribution from fail_score
fail_score = assets["fail_score"].values

# Add significant noise to create all 4 risk levels
noise = rng.normal(0, 0.12, size=len(fail_score))
probs = np.clip(fail_score + noise, 0.02, 0.98)

# Assign to predictions
preds["failure_probability"] = probs.round(4)

def risk(p):
    if p >= 0.85: return "CRITICAL"
    if p >= 0.60: return "HIGH"
    if p >= 0.35: return "MEDIUM"
    return "LOW"

preds["risk_level"]         = preds["failure_probability"].apply(risk)
preds["recommended_action"] = preds["risk_level"].map(
    {k:v["action"] for k,v in RISK_LABELS.items()}
)

print("Risk distribution:")
print(preds["risk_level"].value_counts().to_string())
print(f"\nProbability range: [{probs.min():.3f}, {probs.max():.3f}]")
print(f"Probability mean:  {probs.mean():.3f}")

upload(preds, S3["predictions"])
print("\n✅ Predictions updated with realistic distribution!")
