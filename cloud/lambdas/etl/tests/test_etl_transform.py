from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from livocrm_etl.transform import age_band, curated_key, detect_source, run_pipeline, to_parquet_bytes

KAGGLE_CSV = """PatientId,AppointmentID,Gender,ScheduledDay,AppointmentDay,Age,Neighbourhood,Scholarship,Hipertension,Diabetes,Alcoholism,Handcap,SMS_received,No-show
29872499824296,5642903,F,2016-04-29T18:38:08Z,2016-05-06T00:00:00Z,62,JARDIM DA PENHA,0,1,0,0,0,0,Yes
558997776694438,5642503,M,2016-04-29T16:08:27Z,2016-04-29T00:00:00Z,-1,JARDIM DA PENHA,0,0,0,0,0,0,No
29872499824296,5642504,F,2016-05-02T10:00:00Z,2016-05-09T00:00:00Z,62,JARDIM DA PENHA,0,1,0,0,0,1,No
111,5642505,F,2016-05-10T09:00:00Z,2016-05-05T00:00:00Z,30,JARDIM DA PENHA,0,0,0,0,0,0,No
222,5642504,F,2016-05-02T10:00:00Z,2016-05-09T00:00:00Z,30,JARDIM DA PENHA,0,0,0,0,0,0,No
333,5642506,F,2016-05-02T10:00:00Z,2016-05-09T00:00:00Z,30,JARDIM DA PENHA,0,0,0,0,0,0,Maybe
"""

LIVOCRM_CSV = """appointment_id,patient_id,scheduled_at,appointment_at,age,reminder_sent,no_show,data_label
a1,p1,2026-01-05T09:00:00+05:30,2026-01-07T10:30:00+05:30,34,true,false,demo
a2,p1,2026-01-08T11:00:00+05:30,2026-01-09T09:00:00+05:30,34,false,true,demo
a3,p2,2026-01-06T08:00:00+05:30,2026-01-06T17:00:00+05:30,,false,no,demo
a4,p1,2026-01-10T08:00:00+05:30,2026-01-12T09:00:00+05:30,34,true,no,demo
"""


def test_detect_source_recognises_both_headers() -> None:
    assert detect_source(list(pd.read_csv(io.StringIO(KAGGLE_CSV), nrows=0).columns)) == "kaggle"
    assert detect_source(list(pd.read_csv(io.StringIO(LIVOCRM_CSV), nrows=0).columns)) == "livocrm"


def test_detect_source_rejects_unknown_header() -> None:
    with pytest.raises(ValueError, match="unrecognised"):
        detect_source(["name", "phone"])


def test_kaggle_pipeline_drops_bad_rows_and_counts_reasons() -> None:
    frame, report = run_pipeline(KAGGLE_CSV)

    assert report.rows_in == 6
    assert report.rows_out == 3
    assert report.dropped == {"negative_lead_time": 1, "duplicate_appointment_id": 1, "bad_boolean": 1}
    assert list(frame["appointment_id"]) == ["5642503", "5642903", "5642504"]


def test_kaggle_pipeline_engineers_features() -> None:
    frame, _ = run_pipeline(KAGGLE_CSV)
    by_id = frame.set_index("appointment_id")

    assert by_id.loc["5642903", "lead_time_days"] == 7
    assert by_id.loc["5642903", "weekday"] == 4  # 2016-05-06 is a Friday
    assert by_id.loc["5642903", "scheduled_hour"] == 18
    assert by_id.loc["5642903", "age_band"] == "50-64"
    assert by_id.loc["5642503", "age_band"] == "unknown"
    assert by_id.loc["5642503", "lead_time_days"] == 0
    assert by_id.loc["5642504", "prior_no_shows"] == 1
    assert by_id.loc["5642903", "prior_no_shows"] == 0
    assert by_id.loc["5642903", "no_show"] == 1
    assert by_id.loc["5642504", "reminder_sent"] == 1
    assert set(frame["data_label"]) == {"kaggle_public"}
    assert set(frame["source"]) == {"kaggle"}


def test_livocrm_pipeline_converts_offsets_to_utc_and_counts_history() -> None:
    frame, report = run_pipeline(LIVOCRM_CSV)
    by_id = frame.set_index("appointment_id")

    assert report.source == "livocrm"
    assert report.dropped == {}
    assert by_id.loc["a1", "scheduled_at"] == datetime(2026, 1, 5, 3, 30)
    assert by_id.loc["a1", "lead_time_days"] == 2
    assert by_id.loc["a4", "prior_no_shows"] == 1
    assert by_id.loc["a3", "age_band"] == "unknown"
    assert set(frame["data_label"]) == {"demo"}


def test_age_band_boundaries() -> None:
    assert age_band(0) == "0-17"
    assert age_band(17) == "0-17"
    assert age_band(18) == "18-34"
    assert age_band(64) == "50-64"
    assert age_band(65) == "65+"
    assert age_band(None) == "unknown"
    assert age_band(float("nan")) == "unknown"


def test_curated_key_is_hive_partitioned_by_source() -> None:
    key = curated_key("curated/appointments/", "kaggle", "raw/kaggle/KaggleV2-May-2016.csv", datetime(2026, 10, 26, 3, 0, 5))
    assert key == "curated/appointments/source=kaggle/KaggleV2-May-2016-20261026T030005.parquet"


def test_parquet_round_trip_keeps_columns_and_athena_timestamps() -> None:
    frame, _ = run_pipeline(LIVOCRM_CSV)
    payload = to_parquet_bytes(frame)
    restored = pd.read_parquet(io.BytesIO(payload))

    assert list(restored.columns) == list(frame.columns)
    assert len(restored) == len(frame)
    assert pq.read_schema(io.BytesIO(payload)).field("scheduled_at").type == pa.timestamp("us")
