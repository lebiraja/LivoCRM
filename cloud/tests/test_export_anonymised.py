from __future__ import annotations

import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from export_anonymised import OUTPUT_COLUMNS, digest, export_rows, main
from livocrm_etl.transform import run_pipeline

KEY = b"test-only-export-key-0123456789"

SOURCE_CSV = """appointment_id,patient_id,patient_name,phone,scheduled_at,appointment_at,age,reminder_sent,status,notes
APPT-42,PAT-7,Kavitha Rajan,+91 98765 43210,2026-01-05T09:00:00+05:30,2026-01-07T10:30:00+05:30,34,true,completed,called back
APPT-43,PAT-7,Kavitha Rajan,+91 98765 43210,2026-01-08T11:00:00+05:30,2026-01-09T09:00:00+05:30,34,false,no_show,
APPT-44,PAT-9,Ravi Kumar,+91 90000 11111,2026-01-06T08:00:00+05:30,2026-01-08T17:00:00+05:30,,false,cancelled,
"""


def _rows() -> list[dict[str, str]]:
    return list(csv.DictReader(SOURCE_CSV.splitlines()))


def test_digest_is_deterministic_keyed_and_truncated() -> None:
    first = digest(KEY, "APPT-42")

    assert first == digest(KEY, "APPT-42")
    assert first != digest(b"another-key-0123456789abcdef", "APPT-42")
    assert len(first) == 32
    assert all(char in "0123456789abcdef" for char in first)


def test_export_keeps_only_outcomes_and_hashes_ids() -> None:
    exported, skipped = export_rows(_rows(), KEY, "demo")

    assert skipped == 1
    assert [row.no_show for row in exported] == [False, True]
    assert all(row.appointment_id != raw for row in exported for raw in ("APPT-42", "APPT-43"))
    assert exported[0].patient_id == digest(KEY, "PAT-7") == exported[1].patient_id
    assert {row.data_label for row in exported} == {"demo"}


def test_no_names_phones_or_notes_reach_the_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "appointments.csv"
    source.write_text(SOURCE_CSV, encoding="utf-8")
    target = tmp_path / "export.csv"
    monkeypatch.setenv("EXPORT_HASH_KEY", KEY.decode("utf-8"))

    assert main(["--input", str(source), "--output", str(target), "--label", "synthetic"]) == 0

    text = target.read_text(encoding="utf-8")
    header = text.splitlines()[0].split(",")
    assert header == OUTPUT_COLUMNS
    for forbidden in ("Kavitha", "Ravi", "98765", "called back", "APPT-42", "PAT-7"):
        assert forbidden not in text


def test_output_is_consumable_by_the_etl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "appointments.csv"
    source.write_text(SOURCE_CSV, encoding="utf-8")
    target = tmp_path / "export.csv"
    monkeypatch.setenv("EXPORT_HASH_KEY", KEY.decode("utf-8"))
    main(["--input", str(source), "--output", str(target)])

    frame, report = run_pipeline(target.read_text(encoding="utf-8"))

    assert report.source == "livocrm"
    assert report.rows_out == 2
    assert list(frame["no_show"]) == [0, 1]
    assert list(frame["prior_no_shows"]) == [0, 0]


def test_missing_or_short_key_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "appointments.csv"
    source.write_text(SOURCE_CSV, encoding="utf-8")
    monkeypatch.setenv("EXPORT_HASH_KEY", "short")

    with pytest.raises(SystemExit, match="EXPORT_HASH_KEY"):
        main(["--input", str(source), "--output", str(tmp_path / "out.csv")])


def test_unknown_status_fails_loudly() -> None:
    rows = _rows()
    rows[0]["status"] = "paid"

    with pytest.raises(ValidationError):
        export_rows(rows, KEY, "demo")
