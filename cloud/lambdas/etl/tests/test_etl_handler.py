from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import pytest

from livocrm_etl import handler

LIVOCRM_CSV = """appointment_id,patient_id,scheduled_at,appointment_at,age,reminder_sent,no_show,data_label
a1,p1,2026-01-05T09:00:00+05:30,2026-01-07T10:30:00+05:30,34,true,false,demo
a4,p1,2026-01-10T08:00:00+05:30,2026-01-12T09:00:00+05:30,34,true,no,demo
"""


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class FakeS3:
    """In-memory stand-in for the boto3 S3 client methods the handler uses."""

    def __init__(self, objects: dict[str, tuple[bytes, datetime]]) -> None:
        self.objects = objects
        self.puts: dict[str, bytes] = {}
        self.put_extra_args: dict[str, dict[str, Any]] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        return {"Body": FakeBody(self.objects[Key][0])}

    def list_objects_v2(self, *, Bucket: str, Prefix: str) -> dict[str, Any]:
        contents = [{"Key": key, "LastModified": modified} for key, (_, modified) in self.objects.items() if key.startswith(Prefix)]
        return {"Contents": contents}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ServerSideEncryption: str) -> None:
        self.puts[Key] = Body
        self.put_extra_args[Key] = {"ServerSideEncryption": ServerSideEncryption}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_BUCKET", "livocrm-data-test")
    monkeypatch.setenv("CURATED_PREFIX", "curated/appointments/")


def _s3_event(key: str) -> dict[str, Any]:
    return {"Records": [{"s3": {"bucket": {"name": "livocrm-data-test"}, "object": {"key": key}}}]}


def test_s3_event_writes_curated_parquet_with_sse(monkeypatch: pytest.MonkeyPatch, env: None) -> None:
    fake = FakeS3({"raw/livocrm/export.csv": (LIVOCRM_CSV.encode(), datetime(2026, 1, 13, tzinfo=UTC))})
    monkeypatch.setattr(handler, "s3", fake)

    result = handler.lambda_handler(_s3_event("raw/livocrm/export.csv"), None)

    (processed,) = result["processed"]
    assert processed["raw_key"] == "raw/livocrm/export.csv"
    assert processed["curated_key"].startswith("curated/appointments/source=livocrm/export-")
    assert processed["rows_out"] == 2
    written = pd.read_parquet(io.BytesIO(fake.puts[processed["curated_key"]]))
    assert list(written["appointment_id"]) == ["a1", "a4"]
    assert fake.put_extra_args[processed["curated_key"]] == {"ServerSideEncryption": "AES256"}


def test_s3_event_key_is_url_decoded(monkeypatch: pytest.MonkeyPatch, env: None) -> None:
    fake = FakeS3({"raw/livocrm/my export.csv": (LIVOCRM_CSV.encode(), datetime(2026, 1, 13, tzinfo=UTC))})
    monkeypatch.setattr(handler, "s3", fake)

    result = handler.lambda_handler(_s3_event("raw/livocrm/my+export.csv"), None)

    assert result["processed"][0]["raw_key"] == "raw/livocrm/my export.csv"


def test_schedule_event_processes_newest_livocrm_export(monkeypatch: pytest.MonkeyPatch, env: None) -> None:
    older = (LIVOCRM_CSV.encode(), datetime(2026, 1, 12, tzinfo=UTC))
    newer = (LIVOCRM_CSV.encode(), datetime(2026, 1, 13, tzinfo=UTC))
    fake = FakeS3({"raw/livocrm/2026-01-12.csv": older, "raw/livocrm/2026-01-13.csv": newer})
    monkeypatch.setattr(handler, "s3", fake)

    result = handler.lambda_handler({"source": "aws.events", "detail-type": "Scheduled Event"}, None)

    assert [item["raw_key"] for item in result["processed"]] == ["raw/livocrm/2026-01-13.csv"]


def test_schedule_event_without_export_fails_loudly(monkeypatch: pytest.MonkeyPatch, env: None) -> None:
    monkeypatch.setattr(handler, "s3", FakeS3({}))

    with pytest.raises(FileNotFoundError):
        handler.lambda_handler({"source": "aws.events"}, None)
