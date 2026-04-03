# ============================================================
# data_loader.py — Cached S3 data loading for the dashboard.
# All heavy I/O goes through @st.cache_data so Streamlit
# only fetches once per session.
# ============================================================

import streamlit as st
import pandas as pd
import s3fs, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../setup"))
from config import S3


def _read(path: str) -> pd.DataFrame:
    fs = s3fs.S3FileSystem(anon=False)
    return pd.read_parquet(fs.open(path.replace("s3://", ""), "rb"))


@st.cache_data(ttl=300, show_spinner="Loading assets …")
def load_assets():      return _read(S3["raw_assets"])

@st.cache_data(ttl=300, show_spinner="Loading alarms …")
def load_alarms():      return _read(S3["raw_alarms"])

@st.cache_data(ttl=300, show_spinner="Loading tickets …")
def load_tickets():     return _read(S3["raw_tickets"])

@st.cache_data(ttl=300, show_spinner="Loading logs …")
def load_logs():        return _read(S3["raw_logs"])

@st.cache_data(ttl=300, show_spinner="Loading features …")
def load_features():    return _read(S3["features"])

@st.cache_data(ttl=300, show_spinner="Loading predictions …")
def load_predictions(): return _read(S3["predictions"])

@st.cache_data(ttl=300, show_spinner="Loading feature importance …")
def load_feat_importance(): return _read(S3["feat_importance"])
