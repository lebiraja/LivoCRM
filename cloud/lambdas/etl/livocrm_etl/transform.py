"""Pure ETL steps for appointment CSVs. No AWS calls here; the handler owns all I/O."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

import pandas as pd
from pydantic import BaseModel

Source = Literal["kaggle", "livocrm"]

KAGGLE_COLUMNS = {"PatientId", "AppointmentID", "ScheduledDay", "AppointmentDay", "Age", "SMS_received", "No-show"}
LIVOCRM_COLUMNS = {"appointment_id", "patient_id", "scheduled_at", "appointment_at", "age", "reminder_sent", "no_show", "data_label"}
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n"}
MAX_PLAUSIBLE_AGE = 110
CURATED_COLUMNS = [
    "appointment_id",
    "patient_id",
    "scheduled_at",
    "appointment_at",
    "lead_time_days",
    "weekday",
    "scheduled_hour",
    "age",
    "age_band",
    "reminder_sent",
    "prior_no_shows",
    "no_show",
    "source",
    "data_label",
]


class QualityReport(BaseModel):
    source: Source
    rows_in: int
    rows_out: int
    dropped: dict[str, int]


def detect_source(columns: list[str]) -> Source:
    names = set(columns)
    if KAGGLE_COLUMNS <= names:
        return "kaggle"
    if LIVOCRM_COLUMNS <= names:
        return "livocrm"
    raise ValueError(f"unrecognised appointment CSV header: {sorted(names)}")


def age_band(age: float | None) -> str:
    if age is None or pd.isna(age):
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


def curated_key(prefix: str, source: str, raw_key: str, run_at: datetime) -> str:
    stem = PurePosixPath(raw_key).stem
    return f"{prefix}source={source}/{stem}-{run_at:%Y%m%dT%H%M%S}.parquet"


def to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    # Athena reads microsecond Parquet timestamps; pandas' nanosecond default is not portable.
    frame.to_parquet(buffer, index=False, coerce_timestamps="us")
    return buffer.getvalue()


def _to_bool(series: pd.Series) -> pd.Series:
    lowered = series.str.strip().str.lower()
    return lowered.map(lambda value: True if value in TRUE_VALUES else False if value in FALSE_VALUES else None)


def _parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce").dt.tz_localize(None)


def _normalise(raw: pd.DataFrame, source: Source) -> pd.DataFrame:
    if source == "kaggle":
        return pd.DataFrame(
            {
                "appointment_id": raw["AppointmentID"].str.strip(),
                "patient_id": raw["PatientId"].str.strip(),
                "scheduled_at": _parse_utc(raw["ScheduledDay"]),
                "appointment_at": _parse_utc(raw["AppointmentDay"]),
                "age": pd.to_numeric(raw["Age"], errors="coerce"),
                "reminder_sent": _to_bool(raw["SMS_received"]),
                "no_show": _to_bool(raw["No-show"]),
                "data_label": "kaggle_public",
            }
        )
    return pd.DataFrame(
        {
            "appointment_id": raw["appointment_id"].str.strip(),
            "patient_id": raw["patient_id"].str.strip(),
            "scheduled_at": _parse_utc(raw["scheduled_at"]),
            "appointment_at": _parse_utc(raw["appointment_at"]),
            "age": pd.to_numeric(raw["age"], errors="coerce"),
            "reminder_sent": _to_bool(raw["reminder_sent"]),
            "no_show": _to_bool(raw["no_show"]),
            "data_label": raw["data_label"].str.strip(),
        }
    )


def _drop(frame: pd.DataFrame, mask: pd.Series, reason: str, dropped: dict[str, int]) -> pd.DataFrame:
    count = int(mask.sum())
    if count:
        dropped[reason] = count
    return frame[~mask]


def run_pipeline(csv_text: str) -> tuple[pd.DataFrame, QualityReport]:
    raw = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    source = detect_source(list(raw.columns))
    frame = _normalise(raw, source)
    dropped: dict[str, int] = {}
    rows_in = len(frame)

    frame = _drop(frame, (frame["appointment_id"] == "") | (frame["patient_id"] == ""), "missing_id", dropped)
    frame = _drop(frame, frame["scheduled_at"].isna() | frame["appointment_at"].isna(), "bad_datetime", dropped)
    frame = _drop(frame, frame["no_show"].isna() | frame["reminder_sent"].isna(), "bad_boolean", dropped)
    frame = _drop(frame, frame["appointment_at"].dt.normalize() < frame["scheduled_at"].dt.normalize(), "negative_lead_time", dropped)
    frame = _drop(frame, frame["appointment_id"].duplicated(keep="first"), "duplicate_appointment_id", dropped)

    frame = frame.assign(
        age=frame["age"].where(frame["age"].between(0, MAX_PLAUSIBLE_AGE)),
        lead_time_days=(frame["appointment_at"].dt.normalize() - frame["scheduled_at"].dt.normalize()).dt.days,
        weekday=frame["appointment_at"].dt.weekday,
        scheduled_hour=frame["scheduled_at"].dt.hour,
        reminder_sent=frame["reminder_sent"].astype(bool).astype(int),
        no_show=frame["no_show"].astype(bool).astype(int),
        source=source,
    )
    frame = frame.sort_values(["scheduled_at", "appointment_id"], kind="stable").reset_index(drop=True)
    frame["prior_no_shows"] = frame.groupby("patient_id")["no_show"].transform(lambda s: s.shift(fill_value=0).cumsum())
    frame["age_band"] = frame["age"].map(age_band)
    curated = frame[CURATED_COLUMNS].astype({"prior_no_shows": int, "lead_time_days": int, "weekday": int, "scheduled_hour": int})

    report = QualityReport(source=source, rows_in=rows_in, rows_out=len(curated), dropped=dropped)
    return curated, report
