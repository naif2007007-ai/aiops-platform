import streamlit as st
import pandas as pd
import boto3
import io
import os

BUCKET = os.getenv("AIOPS_S3_BUCKET", "aiops-platform-poc")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

def _read(key):
    client = boto3.client("s3",
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
    buf = io.BytesIO()
    client.download_fileobj(BUCKET, key, buf)
    buf.seek(0)
    return pd.read_parquet(buf)

def _read_live_folder(prefix):
    client = boto3.client("s3",
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
    response = client.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    if "Contents" not in response:
        return None
    files = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)
    latest = files[0]["Key"]
    buf = io.BytesIO()
    client.download_fileobj(BUCKET, latest, buf)
    buf.seek(0)
    last_updated = files[0]["LastModified"]
    return pd.read_parquet(buf), last_updated

@st.cache_data(ttl=300, show_spinner="Loading assets ...")
def load_assets():       return _read("raw/assets.parquet")

@st.cache_data(ttl=60, show_spinner="Loading live alarms ...")
def load_alarms():
    result = _read_live_folder("live/alarms/")
    if result:
        df, updated = result
        st.session_state["alarms_updated"] = updated
        return df
    return _read("raw/alarms.parquet")

@st.cache_data(ttl=300, show_spinner="Loading tickets ...")
def load_tickets():      return _read("raw/tickets.parquet")

@st.cache_data(ttl=60, show_spinner="Loading live logs ...")
def load_logs():
    result = _read_live_folder("live/logs/")
    if result:
        df, updated = result
        st.session_state["logs_updated"] = updated
        return df
    return _read("raw/logs.parquet")

@st.cache_data(ttl=300, show_spinner="Loading features ...")
def load_features():     return _read("processed/features.parquet")

@st.cache_data(ttl=300, show_spinner="Loading predictions ...")
def load_predictions():  return _read("models/predictions.parquet")

@st.cache_data(ttl=300, show_spinner="Loading feature importance ...")
def load_feat_importance(): return _read("models/feature_importance.parquet")

def get_last_updated():
    updated = st.session_state.get("alarms_updated")
    if updated:
        from datetime import datetime, timezone
        now  = datetime.now(timezone.utc)
        diff = int((now - updated).total_seconds() / 60)
        return f"Last updated: {diff} minutes ago"
    return "Live data active"
