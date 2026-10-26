"""The ETL, the scorer and the trainer must agree on feature names and features.

The ETL and scorer are separate Lambda packages, so the logic is duplicated on purpose;
these tests are what keep the copies from drifting apart.
"""

from __future__ import annotations

import pandas as pd

from livocrm_etl.transform import age_band as etl_age_band
from livocrm_etl.transform import run_pipeline
from livocrm_score.scoring import FEATURE_COLUMNS as SCORE_FEATURES
from livocrm_score.scoring import AppointmentIn, age_band as score_age_band, build_features
from ml.train import FEATURE_COLUMNS as TRAIN_FEATURES

LIVOCRM_CSV = """appointment_id,patient_id,scheduled_at,appointment_at,age,reminder_sent,no_show,data_label
a1,p1,2026-01-05T09:00:00+05:30,2026-01-07T10:30:00+05:30,34,true,false,demo
a2,p1,2026-01-08T11:00:00+05:30,2026-01-09T09:00:00+05:30,,false,true,demo
a3,p2,2026-01-06T23:30:00+00:00,2026-01-07T00:10:00+00:00,70,true,false,demo
"""


def test_feature_names_match_across_etl_scorer_and_trainer() -> None:
    assert TRAIN_FEATURES == SCORE_FEATURES
    assert set(TRAIN_FEATURES) <= set(run_pipeline(LIVOCRM_CSV)[0].columns)


def test_scorer_builds_the_same_features_as_the_etl() -> None:
    curated, _ = run_pipeline(LIVOCRM_CSV)
    appointments = [
        AppointmentIn(
            appointment_id=row.appointment_id,
            scheduled_at=row.scheduled_at.to_pydatetime(),
            appointment_at=row.appointment_at.to_pydatetime(),
            age=None if pd.isna(row.age) else int(row.age),
            reminder_sent=bool(row.reminder_sent),
            prior_no_shows=int(row.prior_no_shows),
        )
        for row in curated.itertuples(index=False)
    ]

    scored = build_features(appointments)

    pd.testing.assert_frame_equal(
        scored.reset_index(drop=True),
        curated[TRAIN_FEATURES].reset_index(drop=True),
        check_dtype=False,
    )


def test_age_bands_agree_at_every_boundary() -> None:
    for age in range(0, 111):
        assert etl_age_band(float(age)) == score_age_band(age), age
    assert etl_age_band(float("nan")) == score_age_band(None) == "unknown"
