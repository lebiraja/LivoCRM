"""SageMaker-compatible training script for the no-show model.

Runs as the entry point of a SageMaker scikit-learn training job (see cloud/ml/README.md) and
locally with the same flags. SageMaker sets SM_CHANNEL_TRAIN, SM_MODEL_DIR and SM_OUTPUT_DATA_DIR;
the flags are fallbacks for local runs.

The feature list must match livocrm_score.scoring.FEATURE_COLUMNS; cloud/tests enforces that.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = ["lead_time_days", "weekday", "scheduled_hour", "prior_no_shows", "reminder_sent", "age_band"]
TARGET = "no_show"
THRESHOLD = 0.5


def load_curated(channel: Path) -> pd.DataFrame:
    files = sorted(channel.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no curated parquet files under {channel}")
    frame = pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)
    missing = {*FEATURE_COLUMNS, TARGET} - set(frame.columns)
    if missing:
        raise ValueError(f"curated data is missing columns: {sorted(missing)}")
    return frame


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer([("age_band", OneHotEncoder(handle_unknown="ignore"), ["age_band"])], remainder="passthrough")


def candidate_models(seed: int) -> dict[str, Pipeline]:
    return {
        "logistic_regression": make_pipeline(_preprocessor(), LogisticRegression(max_iter=1000, class_weight="balanced")),
        "hist_gradient_boosting": make_pipeline(_preprocessor(), HistGradientBoostingClassifier(random_state=seed)),
    }


def evaluate(model: Pipeline, features: pd.DataFrame, target: pd.Series) -> dict[str, float]:
    probabilities = model.predict_proba(features)[:, 1]
    predicted = (probabilities >= THRESHOLD).astype(int)
    return {
        "auc": float(roc_auc_score(target, probabilities)),
        "precision": float(precision_score(target, predicted, zero_division=0)),
        "recall": float(recall_score(target, predicted, zero_division=0)),
    }


def train(channel: Path, model_dir: Path, output_dir: Path, test_size: float, seed: int) -> dict[str, Any]:
    frame = load_curated(channel)
    features = frame[FEATURE_COLUMNS]
    target = frame[TARGET].astype(int)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=test_size, stratify=target, random_state=seed
    )

    fitted: dict[str, Pipeline] = {}
    metrics: dict[str, dict[str, float]] = {}
    for name, model in candidate_models(seed).items():
        model.fit(x_train, y_train)
        fitted[name] = model
        metrics[name] = evaluate(model, x_test, y_test)
        for metric, value in metrics[name].items():
            logger.info(f"{name} test_{metric}={value:.4f}")

    best = max(metrics, key=lambda name: metrics[name]["auc"])
    baseline = metrics["logistic_regression"]
    report: dict[str, Any] = {
        "best_model": best,
        "threshold": THRESHOLD,
        "rows_train": len(x_train),
        "rows_test": len(x_test),
        "positive_rate": float(target.mean()),
        "metrics": metrics,
        "auc_gain_over_logistic_regression": metrics[best]["auc"] - baseline["auc"],
    }
    logger.info(f"best={best} auc_gain_over_baseline={report['auc_gain_over_logistic_regression']:.4f}")

    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": fitted[best], "features": FEATURE_COLUMNS, "name": best}, model_dir / "model.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the LivoCRM no-show model")
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "data/curated"))
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "model"))
    parser.add_argument("--output-data-dir", default=os.environ.get("SM_OUTPUT_DATA_DIR", "output"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    train(Path(args.train), Path(args.model_dir), Path(args.output_data_dir), args.test_size, args.seed)


if __name__ == "__main__":
    main()
