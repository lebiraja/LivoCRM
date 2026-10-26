"""Turn LivoCRM appointment rows into the anonymised CSV that the ETL Lambda reads.

Input: a CSV exported from the app database with the SOURCE columns below (raw database ids).
Output: the LivoCRM header read by cloud/lambdas/etl (livocrm_etl.transform).

Privacy rules enforced in code:
  - only the whitelisted source columns are read; names, phones, emails and notes are never copied
  - appointment and patient ids become HMAC-SHA256 digests keyed by EXPORT_HASH_KEY
  - rows without an outcome (booked, confirmed, cancelled, rescheduled) are skipped

Usage:
  EXPORT_HASH_KEY=<secret, 16+ chars> python export_anonymised.py \
      --input appointments.csv --output livocrm_export.csv --label demo
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OUTPUT_COLUMNS = [
    "appointment_id",
    "patient_id",
    "scheduled_at",
    "appointment_at",
    "age",
    "reminder_sent",
    "no_show",
    "data_label",
]
OUTCOME_STATUSES = {"completed", "no_show"}
DIGEST_CHARS = 32
MIN_KEY_CHARS = 16


class SourceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    appointment_id: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)
    scheduled_at: datetime
    appointment_at: datetime
    age: int | None = Field(default=None, ge=0, le=130)
    reminder_sent: bool
    status: Literal["booked", "confirmed", "completed", "no_show", "cancelled", "rescheduled"]


class ExportRow(BaseModel):
    appointment_id: str
    patient_id: str
    scheduled_at: datetime
    appointment_at: datetime
    age: int | None
    reminder_sent: bool
    no_show: bool
    data_label: str


def digest(key: bytes, value: str) -> str:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:DIGEST_CHARS]


def to_export_row(source: SourceRow, key: bytes, label: str) -> ExportRow:
    return ExportRow(
        appointment_id=digest(key, source.appointment_id),
        patient_id=digest(key, source.patient_id),
        scheduled_at=source.scheduled_at,
        appointment_at=source.appointment_at,
        age=source.age,
        reminder_sent=source.reminder_sent,
        no_show=source.status == "no_show",
        data_label=label,
    )


def export_rows(rows: Iterable[dict[str, Any]], key: bytes, label: str) -> tuple[list[ExportRow], int]:
    exported: list[ExportRow] = []
    skipped = 0
    for raw in rows:
        cleaned = {**raw, "age": raw.get("age") or None}
        source = SourceRow.model_validate(cleaned)
        if source.status not in OUTCOME_STATUSES:
            skipped += 1
            continue
        exported.append(to_export_row(source, key, label))
    return exported, skipped


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _hash_key() -> bytes:
    key = os.environ.get("EXPORT_HASH_KEY", "")
    if len(key) < MIN_KEY_CHARS:
        raise SystemExit(f"EXPORT_HASH_KEY must be set and at least {MIN_KEY_CHARS} characters")
    return key.encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the anonymised LivoCRM appointment CSV for the ETL")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", choices=["demo", "synthetic", "anonymised"], default="demo")
    args = parser.parse_args(argv)

    key = _hash_key()
    with args.input.open(newline="", encoding="utf-8") as source:
        exported, skipped = export_rows(csv.DictReader(source), key, args.label)

    with args.output.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in exported:
            writer.writerow({column: _csv_value(value) for column, value in row.model_dump().items()})

    print(f"exported={len(exported)} skipped_without_outcome={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
