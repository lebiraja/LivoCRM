from __future__ import annotations

import io
import tarfile

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from livocrm_score.scoring import FEATURE_COLUMNS


def _tiny_frame(rows: int = 60) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "lead_time_days": rng.integers(0, 30, rows),
            "weekday": rng.integers(0, 7, rows),
            "scheduled_hour": rng.integers(8, 18, rows),
            "prior_no_shows": rng.integers(0, 3, rows),
            "reminder_sent": rng.integers(0, 2, rows),
            "age_band": rng.choice(["0-17", "18-34", "35-49", "50-64", "65+", "unknown"], rows),
        },
        columns=FEATURE_COLUMNS,
    )
    target = (frame["lead_time_days"] > 15).astype(int)
    return frame, target


@pytest.fixture(scope="session")
def model_artifact() -> bytes:
    frame, target = _tiny_frame()
    pipeline = make_pipeline(
        ColumnTransformer([("age", OneHotEncoder(handle_unknown="ignore"), ["age_band"])], remainder="passthrough"),
        LogisticRegression(max_iter=500),
    )
    pipeline.fit(frame, target)

    payload = io.BytesIO()
    joblib.dump({"model": pipeline, "features": FEATURE_COLUMNS}, payload)
    body = payload.getvalue()

    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        info = tarfile.TarInfo(name="model.joblib")
        info.size = len(body)
        archive.addfile(info, io.BytesIO(body))
    return archive_bytes.getvalue()
