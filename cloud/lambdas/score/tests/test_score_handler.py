from __future__ import annotations

import json
from typing import Any

import pytest

from livocrm_score import handler

UPCOMING = {
    "appointments": [
        {
            "appointment_id": "appt-1",
            "scheduled_at": "2026-01-05T09:00:00",
            "appointment_at": "2026-01-07T10:30:00",
            "age": 34,
            "reminder_sent": True,
            "prior_no_shows": 2,
        }
    ]
}


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class FakeS3:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.reads: list[str] = []
        self.puts: dict[str, bytes] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.reads.append(Key)
        return {"Body": FakeBody(self.objects[Key])}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str, ServerSideEncryption: str) -> None:
        self.puts[Key] = Body


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BUCKET", "livocrm-data-test")
    monkeypatch.setenv("MODEL_KEY", "models/no-show/current/model.tar.gz")
    monkeypatch.setenv("UPCOMING_KEY", "scoring/upcoming/latest.json")
    monkeypatch.setenv("RESULTS_KEY", "scoring/results/latest.json")
    handler._bundle.cache_clear()


def test_direct_invoke_returns_scores_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, env: None, model_artifact: bytes
) -> None:
    fake = FakeS3({"models/no-show/current/model.tar.gz": model_artifact})
    monkeypatch.setattr(handler, "s3", fake)

    response = handler.lambda_handler(UPCOMING, None)

    assert response["model_key"] == "models/no-show/current/model.tar.gz"
    (score,) = response["scores"]
    assert score["appointment_id"] == "appt-1"
    assert 0.0 <= score["no_show_risk"] <= 1.0
    assert fake.puts == {}


def test_scheduled_run_reads_upcoming_batch_and_writes_results(
    monkeypatch: pytest.MonkeyPatch, env: None, model_artifact: bytes
) -> None:
    fake = FakeS3(
        {
            "models/no-show/current/model.tar.gz": model_artifact,
            "scoring/upcoming/latest.json": json.dumps(UPCOMING).encode("utf-8"),
        }
    )
    monkeypatch.setattr(handler, "s3", fake)

    response = handler.lambda_handler({"source": "aws.events", "detail-type": "Scheduled Event"}, None)

    written = json.loads(fake.puts["scoring/results/latest.json"])
    assert written == response
    assert written["scores"][0]["appointment_id"] == "appt-1"


def test_model_is_downloaded_once_per_container(
    monkeypatch: pytest.MonkeyPatch, env: None, model_artifact: bytes
) -> None:
    fake = FakeS3({"models/no-show/current/model.tar.gz": model_artifact})
    monkeypatch.setattr(handler, "s3", fake)

    handler.lambda_handler(UPCOMING, None)
    handler.lambda_handler(UPCOMING, None)

    assert fake.reads == ["models/no-show/current/model.tar.gz"]


def test_invalid_payload_is_rejected_before_inference(
    monkeypatch: pytest.MonkeyPatch, env: None, model_artifact: bytes
) -> None:
    fake = FakeS3({"models/no-show/current/model.tar.gz": model_artifact})
    monkeypatch.setattr(handler, "s3", fake)

    with pytest.raises(ValueError):
        handler.lambda_handler({"appointments": [{"appointment_id": ""}]}, None)
    assert fake.reads == []
