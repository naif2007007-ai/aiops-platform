import boto3
import io
import os
import pandas as pd

BUCKET = os.getenv("AIOPS_S3_BUCKET", "aiops-platform-poc")
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-north-1")

def upload(df, s3_path):
    key = s3_path.replace(f"s3://{BUCKET}/", "")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    boto3.client("s3", region_name=REGION).put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"  ✅ Uploaded {len(df):,} rows → s3://{BUCKET}/{key}")

def download(s3_path):
    key = s3_path.replace(f"s3://{BUCKET}/", "")
    buf = io.BytesIO()
    boto3.client("s3", region_name=REGION).download_fileobj(BUCKET, key, buf)
    buf.seek(0)
    return pd.read_parquet(buf)
