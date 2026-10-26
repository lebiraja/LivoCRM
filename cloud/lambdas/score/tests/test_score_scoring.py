from __future__ import annotations

import io
import tarfile
from datetime import datetime

import joblib
import pytest
from pydantic import ValidationError

from livocrm_score.scoring import (
    FEATURE_COLUMNS,
    MAX_BATCH,
    AppointmentIn,
    ScoreRequest,
    build_features,
    load_bundle,
    score_appointments,
)


def _appointment(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "appointment_id": "appt-1",
        "scheduled_at": "2026-01-05T09:00:00",
        "appointment_at": "2026-01-07T10:30:00",
        "age": 34,
        "reminder_sent": True,
        "prior_no_shows": 2,
    }
    return {**base, **overrides}


def test_build_features_matches_training_columns() -> None:
    item = AppointmentIn.model_validate(_appointment())

    frame = build_features([item])

    assert list(frame.columns) == FEATURE_COLUMNS
    row = frame.iloc[0]
    assert row["lead_time_days"] == 2
    assert row["weekday"] == 2  # 2026-01-07 is a Wednesday
    assert row["scheduled_hour"] == 9
    assert row["prior_no_shows"] == 2
    assert row["reminder_sent"] == 1
    assert row["age_band"] == "18-34"


def test_aware_timestamps_are_converted_to_utc() -> None:
    item = AppointmentIn.model_validate(
        _appointment(scheduled_at="2026-01-05T09:00:00+05:30", appointment_at="2026-01-07T10:30:00+05:30")
    )

    assert item.scheduled_at == datetime(2026, 1, 5, 3, 30)
    assert item.appointment_at == datetime(2026, 1, 7, 5, 0)


def test_mixed_offset_and_naive_timestamps_compare_safely() -> None:
    item = AppointmentIn.model_validate(
        _appointment(scheduled_at="2026-01-05T09:00:00+00:00", appointment_at="2026-01-07T10:30:00")
    )

    assert item.appointment_at > item.scheduled_at


def test_appointment_before_booking_is_rejected() -> None:
    with pytest.raises(ValidationError, match="before scheduled_at"):
        AppointmentIn.model_validate(_appointment(appointment_at="2026-01-01T10:00:00"))


def test_implausible_age_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AppointmentIn.model_validate(_appointment(age=200))


def test_request_requires_between_one_and_max_batch() -> None:
    with pytest.raises(ValidationError):
        ScoreRequest.model_validate({"appointments": []})
    one = _appointment()
    with pytest.raises(ValidationError):
        ScoreRequest.model_validate({"appointments": [one] * (MAX_BATCH + 1)})


def test_scores_are_probabilities_in_request_order(model_artifact: bytes) -> None:
    bundle = load_bundle(model_artifact)
    items = [
        AppointmentIn.model_validate(_appointment(appointment_id="early", scheduled_at="2026-01-06T09:00:00", appointment_at="2026-01-07T10:00:00")),
        AppointmentIn.model_validate(_appointment(appointment_id="late", scheduled_at="2026-01-01T09:00:00", appointment_at="2026-01-25T10:00:00")),
    ]

    scores = score_appointments(bundle, items)

    assert [score.appointment_id for score in scores] == ["early", "late"]
    assert all(0.0 <= score.no_show_risk <= 1.0 for score in scores)
    assert scores[1].no_show_risk > scores[0].no_show_risk


def test_artifact_with_different_feature_list_is_rejected() -> None:
    payload = io.BytesIO()
    joblib.dump({"model": None, "features": ["lead_time_days"]}, payload)
    body = payload.getvalue()
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        info = tarfile.TarInfo(name="./model.joblib")
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))

    with pytest.raises(ValueError, match="feature list"):
        load_bundle(archive_bytes.getvalue())


def test_artifact_without_model_file_is_rejected() -> None:
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        info = tarfile.TarInfo(name="other.txt")
        info.size = 0
        archive.addfile(info, io.BytesIO(b""))

    with pytest.raises(ValueError, match="not found"):
        load_bundle(archive_bytes.getvalue())


def test_naive_timestamps_across_midnight_count_one_calendar_day() -> None:
    item = AppointmentIn.model_validate(_appointment(scheduled_at="2026-01-05T23:30:00", appointment_at="2026-01-06T00:10:00"))

    assert build_features([item]).iloc[0]["lead_time_days"] == 1
    assert item.scheduled_at.tzinfo is None
