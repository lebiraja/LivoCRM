from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from ml.train import FEATURE_COLUMNS, train


def _curated_frame(rows: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    lead = rng.integers(0, 30, rows)
    no_show = (rng.random(rows) < (lead / 60 + 0.05)).astype(int)
    return pd.DataFrame(
        {
            "lead_time_days": lead,
            "weekday": rng.integers(0, 7, rows),
            "scheduled_hour": rng.integers(8, 18, rows),
            "prior_no_shows": rng.integers(0, 3, rows),
            "reminder_sent": rng.integers(0, 2, rows),
            "age_band": rng.choice(["0-17", "18-34", "35-49", "50-64", "65+", "unknown"], rows),
            "no_show": no_show,
        }
    )


def test_train_writes_model_and_metrics_for_both_candidates(tmp_path: Path) -> None:
    channel = tmp_path / "curated" / "source=livocrm"
    channel.mkdir(parents=True)
    _curated_frame().to_parquet(channel / "part-0.parquet", index=False)

    report = train(tmp_path / "curated", tmp_path / "model", tmp_path / "out", test_size=0.25, seed=7)

    assert set(report["metrics"]) == {"logistic_regression", "hist_gradient_boosting"}
    assert report["best_model"] in report["metrics"]
    for metrics in report["metrics"].values():
        assert set(metrics) == {"auc", "precision", "recall"}
        assert all(0.0 <= value <= 1.0 for value in metrics.values())
    assert report["rows_test"] == 50

    saved = joblib.load(tmp_path / "model" / "model.joblib")
    assert saved["features"] == FEATURE_COLUMNS
    assert saved["name"] == report["best_model"]
    written = json.loads((tmp_path / "out" / "metrics.json").read_text(encoding="utf-8"))
    assert written["best_model"] == report["best_model"]


def test_missing_columns_fail_fast(tmp_path: Path) -> None:
    frame = _curated_frame().drop(columns=["no_show"])
    frame.to_parquet(tmp_path / "part-0.parquet", index=False)

    with pytest.raises(ValueError, match="no_show"):
        train(tmp_path, tmp_path / "model", tmp_path / "out", test_size=0.2, seed=1)


def test_empty_channel_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        train(tmp_path, tmp_path / "model", tmp_path / "out", test_size=0.2, seed=1)
