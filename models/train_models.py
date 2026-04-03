import pandas as pd
import numpy as np
import joblib, os, sys
from sklearn.ensemble        import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing   import StandardScaler
from sklearn.metrics         import precision_score, recall_score, f1_score, roc_auc_score
sys.path.insert(0, os.path.expanduser("~/aiops_platform/setup"))
from config import S3, ML, RISK_LABELS
from s3_helper import upload, download

ARTIFACT_DIR = os.path.expanduser("~/aiops_platform/models/artifacts")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

FEATURE_COLS = ["lifecycle_age_yrs","days_since_maintenance","maintenance_count","criticality_score",
    "alarm_count_total","alarm_count_critical","alarm_count_30d","alarm_recurrence_avg","alarm_unacknowledged_pct",
    "ticket_count","ticket_p1_count","ticket_unresolved","avg_resolution_hrs","ticket_recurrence_avg","reopened_pct",
    "log_anomaly_days","log_error_total","avg_cpu","avg_mem","avg_latency","auth_failures_total",
    "anomaly_spike_count","alarm_to_ticket_ratio"]

def train_anomaly(X):
    print("\n[Model 1] Training Isolation Forest ...")
    sc  = StandardScaler()
    Xs  = sc.fit_transform(X)
    iso = IsolationForest(n_estimators=200,contamination=ML["anomaly_contamination"],random_state=42,n_jobs=-1)
    iso.fit(Xs)
    raw    = iso.decision_function(Xs)
    scores = 1-(raw-raw.min())/(raw.max()-raw.min())
    joblib.dump({"model":iso,"scaler":sc},os.path.join(ARTIFACT_DIR,"isolation_forest.pkl"))
    print(f"  Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    return scores

def train_predictor(X, y):
    print("\n[Model 2] Training Random Forest ...")
    Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=ML["test_size"],stratify=y,random_state=42)
    clf = RandomForestClassifier(n_estimators=300,max_depth=8,min_samples_leaf=3,
                                  class_weight="balanced",random_state=42,n_jobs=-1)
    clf.fit(Xtr,ytr)
    yp  = clf.predict(Xte)
    ypr = clf.predict_proba(Xte)[:,1]
    print(f"  Precision : {precision_score(yte,yp):.3f}")
    print(f"  Recall    : {recall_score(yte,yp):.3f}")
    print(f"  F1-Score  : {f1_score(yte,yp):.3f}")
    print(f"  ROC-AUC   : {roc_auc_score(yte,ypr):.3f}")
    cv = cross_val_score(clf,X,y,cv=5,scoring="roc_auc",n_jobs=-1)
    print(f"  5-fold CV : {cv.mean():.3f} +/- {cv.std():.3f}")
    fi = pd.DataFrame({"feature":FEATURE_COLS,"importance":clf.feature_importances_}).sort_values("importance",ascending=False).round(4)
    joblib.dump(clf,os.path.join(ARTIFACT_DIR,"random_forest.pkl"))
    return clf.predict_proba(X)[:,1], fi

def build_predictions(df, anomaly, fail_p):
    def risk(p): return "HIGH" if p>=ML["risk_high"] else ("MEDIUM" if p>=ML["risk_medium"] else "LOW")
    pred = df[["asset_id","criticality","lifecycle_age_yrs","days_since_maintenance","will_fail"]].copy()
    pred["anomaly_score"]       = anomaly.round(4)
    pred["failure_probability"] = fail_p.round(4)
    pred["risk_level"]          = pred["failure_probability"].apply(risk)
    pred["recommended_action"]  = pred["risk_level"].map({k:v["action"] for k,v in RISK_LABELS.items()})
    return pred

if __name__ == "__main__":
    print("="*50)
    print("  AI-Ops — Model Training")
    print("="*50)
    df  = download(S3["features"])
    print(f"  Loaded {len(df):,} assets")
    X   = df[FEATURE_COLS].fillna(0)
    y   = df["will_fail"]
    asc        = train_anomaly(X)
    fp, fi     = train_predictor(X, y)
    pred       = build_predictions(df, asc, fp)
    print(f"\n  Risk distribution:\n{pred['risk_level'].value_counts().to_string()}")
    upload(pred, S3["predictions"])
    upload(fi,   S3["feat_importance"])
    print("\nTraining complete.")
