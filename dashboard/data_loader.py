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

@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_assets():          return _read("raw/assets.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_alarms():          return _read("raw/alarms.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_tickets():         return _read("raw/tickets.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_logs():            return _read("raw/logs.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_features():        return _read("processed/features.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_predictions():     return _read("models/predictions.parquet")
@st.cache_data(ttl=300, show_spinner="Loading ...")
def load_feat_importance(): return _read("models/feature_importance.parquet")
