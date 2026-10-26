"""Pure scoring: request validation, feature building and model inference. No AWS calls here.

The feature names and age bands must match livocrm_etl.transform and ml/train.py; the parity
tests in cloud/tests enforce that.
"""

from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

import joblib
import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

FEATURE_COLUMNS = ["lead_time_days", "weekday", "scheduled_hour", "prior_no_shows", "reminder_sent", "age_band"]
MAX_BATCH = 500


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def age_band(age: int | None) -> str:
    if age is None:
        return "unknown"
    if age < 18:
        return "0-17"
    if age < 35:
        return "18-34"
    if age < 50:
        return "35-49"
    if age < 65:
        return "50-64"
    return "65+"


class AppointmentIn(BaseModel):
    appointment_id: str = Field(min_length=1, max_length=64)
    scheduled_at: datetime
    appointment_at: datetime
    age: int | None = Field(default=None, ge=0, le=110)
    reminder_sent: bool
    prior_no_shows: int = Field(ge=0, le=1000)

    @field_validator("scheduled_at", "appointment_at")
    @classmethod
    def _normalise_to_utc(cls, value: datetime) -> datetime:
        return _to_utc_naive(value)

    @model_validator(mode="after")
    def _appointment_not_before_booking(self) -> AppointmentIn:
        if self.appointment_at < self.scheduled_at:
            raise ValueError("appointment_at is before scheduled_at")
        return self


class ScoreRequest(BaseModel):
    appointments: list[AppointmentIn] = Field(min_length=1, max_length=MAX_BATCH)


class ScoreOut(BaseModel):
    appointment_id: str
    no_show_risk: float = Field(ge=0, le=1)


@dataclass(frozen=True)
class ModelBundle:
    model: Any
    features: list[str]


def load_bundle(artifact: bytes) -> ModelBundle:
    """Unpack a SageMaker model.tar.gz. Only load artifacts from our own bucket: joblib is pickle."""
    with tarfile.open(fileobj=io.BytesIO(artifact), mode="r:gz") as archive:
        member = next((m for m in archive.getmembers() if PurePosixPath(m.name).name == "model.joblib"), None)
        if member is None:
            raise ValueError("model.joblib not found in model artifact")
        extracted = archive.extractfile(member)
        if extracted is None:
            raise ValueError("model.joblib is not a regular file")
        payload = joblib.load(io.BytesIO(extracted.read()))
    if payload["features"] != FEATURE_COLUMNS:
        raise ValueError("model feature list does not match the scorer")
    return ModelBundle(model=payload["model"], features=payload["features"])


def build_features(appointments: list[AppointmentIn]) -> pd.DataFrame:
    rows = [
        {
            "lead_time_days": (item.appointment_at.date() - item.scheduled_at.date()).days,
            "weekday": item.appointment_at.weekday(),
            "scheduled_hour": item.scheduled_at.hour,
            "prior_no_shows": item.prior_no_shows,
            "reminder_sent": int(item.reminder_sent),
            "age_band": age_band(item.age),
        }
        for item in appointments
    ]
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def score_appointments(bundle: ModelBundle, appointments: list[AppointmentIn]) -> list[ScoreOut]:
    features = build_features(appointments)
    probabilities = bundle.model.predict_proba(features[bundle.features])[:, 1]
    return [
        ScoreOut(appointment_id=item.appointment_id, no_show_risk=round(float(probability), 4))
        for item, probability in zip(appointments, probabilities, strict=True)
    ]
