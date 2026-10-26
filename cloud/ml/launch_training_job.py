"""Launch the no-show training job on SageMaker using the scikit-learn framework container.

Run from a virtualenv outside the repository (see cloud/ml/README.md, step 2).
Usage:
  python cloud/ml/launch_training_job.py --region <REGION> --bucket <BUCKET> --role-arn <SAGEMAKER_ROLE_ARN>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sagemaker.sklearn.estimator import SKLearn

CANDIDATES = ["logistic_regression", "hist_gradient_boosting"]
METRICS = ["auc", "precision", "recall"]
FRAMEWORK_VERSION = "1.2-1"


def metric_definitions() -> list[dict[str, str]]:
    return [
        {"Name": f"{name}:test_{metric}", "Regex": rf"{name} test_{metric}=([0-9\.]+)"}
        for name in CANDIDATES
        for metric in METRICS
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the LivoCRM no-show training job")
    parser.add_argument("--region", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--instance-type", default="ml.m5.large")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    estimator = SKLearn(
        entry_point="train.py",
        source_dir=str(Path(__file__).resolve().parent),
        framework_version=FRAMEWORK_VERSION,
        py_version="py3",
        role=args.role_arn,
        instance_type=args.instance_type,
        instance_count=1,
        output_path=f"s3://{args.bucket}/models/no-show/",
        base_job_name="livocrm-no-show",
        hyperparameters={"test-size": 0.2, "seed": 42},
        metric_definitions=metric_definitions(),
    )
    estimator.fit({"train": f"s3://{args.bucket}/curated/appointments/"}, wait=True, logs="All")
    print(f"model_data={estimator.model_data}")


if __name__ == "__main__":
    main()
