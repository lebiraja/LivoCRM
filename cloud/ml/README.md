# No-show model: SageMaker training

`train.py` trains two candidates on the curated appointment Parquet written by the ETL Lambda:

- `logistic_regression` (baseline, `class_weight="balanced"`)
- `hist_gradient_boosting` (candidate)

Both use the same stratified 80/20 split (`--seed`). The better candidate by test AUC is saved as
`model.joblib` for the score Lambda. Every metric is logged as `<model> test_<metric>=<value>` and the
full comparison is written to `metrics.json`.

Placeholders: `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` (the data bucket, `livocrm-data-<ACCOUNT_ID>-<REGION>`),
`<SAGEMAKER_ROLE_ARN>`. Replace them locally. Do not commit real values.

## 0. One-time setup (AWS console, manual)

1. IAM > Roles > create `livocrm-sagemaker-exec` with trust `sagemaker.amazonaws.com`. Attach an inline
   policy that allows `s3:GetObject` on `arn:aws:s3:::<BUCKET>/curated/*`, `s3:PutObject` on
   `arn:aws:s3:::<BUCKET>/models/no-show/*`, and the CloudWatch Logs write actions. Do not attach
   `AmazonSageMakerFullAccess`.
2. Note the role ARN: `arn:aws:iam::<ACCOUNT_ID>:role/livocrm-sagemaker-exec`.
3. Confirm the curated data exists: `aws s3 ls s3://<BUCKET>/curated/appointments/ --recursive`.

## 1. Check the script locally (Docker, no AWS calls)

Run from the repository root. Point `--train` at a local folder that holds curated Parquet files
(copy them out of S3 with `aws s3 sync` if you want real data).

```bash
docker run --rm --network host --dns 127.0.0.53 -v "$PWD/cloud":/w -w /w python:3.12-slim \
  sh -c "pip install -q -r ml/requirements.txt && python ml/train.py --train ml/local-curated --model-dir ml/out/model --output-data-dir ml/out/output"
```

`ml/local-curated` and `ml/out` are local scratch paths; do not commit them.

## 2. Launch the SageMaker training job

Use a virtualenv outside the repository. Do not install the SDK into the system Python.

```bash
python3 -m venv ~/.venvs/livocrm-sm
~/.venvs/livocrm-sm/bin/pip install -r cloud/ml/launch-requirements.txt
~/.venvs/livocrm-sm/bin/python cloud/ml/launch_training_job.py \
  --region <REGION> --bucket <BUCKET> --role-arn <SAGEMAKER_ROLE_ARN>
```

The script prints the `model_data` S3 URI at the end. Watch the job in the console under SageMaker >
Training jobs, or follow the log stream in CloudWatch. Instance: `ml.m5.large`, one instance. Cost is
an estimate; see `docs/cloud/architecture.md`.

## 3. Read the metrics

The SageMaker output archive lands at `s3://<BUCKET>/models/no-show/<JOB_NAME>/output/output.tar.gz`.

```bash
aws s3 cp s3://<BUCKET>/models/no-show/<JOB_NAME>/output/output.tar.gz - | tar -xzO metrics.json
```

Copy the numbers into `docs/cloud/report-outline.md` only after you have read them from your own run.

## 4. Promote the model for the score Lambda

The score Lambda reads `MODEL_KEY` (default `models/no-show/current/model.tar.gz`). Promote the
trained artifact to that key:

```bash
aws s3 cp s3://<BUCKET>/models/no-show/<JOB_NAME>/output/model.tar.gz \
  s3://<BUCKET>/models/no-show/current/model.tar.gz --sse AES256
```

Each warm Lambda container caches the model, so the new artifact is picked up on the next cold start.
To force that, change any function environment variable or redeploy with `sam deploy`.

## Notes

- `requirements.txt` in this folder is installed into the SageMaker scikit-learn container at start-up.
  Its pins match `cloud/lambdas/score/requirements.txt`, so the pickled pipeline loads the same way in
  the scorer.
- The feature list is fixed in `train.py` and `livocrm_score/scoring.py`. The parity test in
  `cloud/tests/test_feature_parity.py` fails if they drift.
- The artifact is a pickle. Only the score Lambda loads it, and only from the data bucket.
