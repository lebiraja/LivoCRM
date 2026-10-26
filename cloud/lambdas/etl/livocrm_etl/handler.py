"""Lambda entry point: S3 ObjectCreated on raw/ and the nightly EventBridge schedule."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote_plus

import boto3

from livocrm_etl.transform import curated_key, run_pipeline, to_parquet_bytes

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
LIVOCRM_EXPORT_PREFIX = "raw/livocrm/"


def _newest_livocrm_export(bucket: str) -> str:
    listing = s3.list_objects_v2(Bucket=bucket, Prefix=LIVOCRM_EXPORT_PREFIX)
    objects = listing.get("Contents", [])
    if not objects:
        raise FileNotFoundError(f"no export found under s3://{bucket}/{LIVOCRM_EXPORT_PREFIX}")
    return max(objects, key=lambda obj: obj["LastModified"])["Key"]


def _source_keys(event: dict[str, Any], bucket: str) -> list[str]:
    if event.get("source") == "aws.events":
        return [_newest_livocrm_export(bucket)]
    return [unquote_plus(record["s3"]["object"]["key"]) for record in event["Records"]]


def _process(bucket: str, curated_prefix: str, raw_key: str, run_at: datetime) -> dict[str, Any]:
    body = s3.get_object(Bucket=bucket, Key=raw_key)["Body"].read().decode("utf-8")
    frame, report = run_pipeline(body)
    out_key = curated_key(curated_prefix, report.source, raw_key, run_at)
    s3.put_object(Bucket=bucket, Key=out_key, Body=to_parquet_bytes(frame), ServerSideEncryption="AES256")
    logger.info(report.model_dump_json())
    return {"raw_key": raw_key, "curated_key": out_key, **report.model_dump()}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    bucket = os.environ["DATA_BUCKET"]
    curated_prefix = os.environ["CURATED_PREFIX"]
    run_at = datetime.now(UTC)
    processed = [_process(bucket, curated_prefix, key, run_at) for key in _source_keys(event, bucket)]
    return {"processed": processed}
