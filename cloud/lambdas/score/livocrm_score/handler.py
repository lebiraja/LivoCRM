"""Lambda entry point: direct JSON scoring, and the nightly schedule over the upcoming batch in S3."""

from __future__ import annotations

import functools
import json
import logging
import os
from typing import Any

import boto3

from livocrm_score.scoring import ModelBundle, ScoreRequest, load_bundle, score_appointments

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


@functools.cache
def _bundle(bucket: str, key: str) -> ModelBundle:
    artifact = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    return load_bundle(artifact)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    bucket = os.environ["MODEL_BUCKET"]
    model_key = os.environ["MODEL_KEY"]
    scheduled = event.get("source") == "aws.events"
    if scheduled:
        upcoming = json.loads(s3.get_object(Bucket=bucket, Key=os.environ["UPCOMING_KEY"])["Body"].read())
    else:
        upcoming = event

    request = ScoreRequest.model_validate(upcoming)
    scores = score_appointments(_bundle(bucket, model_key), request.appointments)
    response = {"model_key": model_key, "scores": [score.model_dump() for score in scores]}
    logger.info(json.dumps({"scored": len(scores), "model_key": model_key}))

    if scheduled:
        s3.put_object(
            Bucket=bucket,
            Key=os.environ["RESULTS_KEY"],
            Body=json.dumps(response).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
    return response
