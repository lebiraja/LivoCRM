# Notebook outline: metrics comparison

Purpose: compare the logistic-regression baseline with the gradient-boosting candidate on the same
curated data, and decide which model the app's no-show chip uses. Build the notebook as a
SageMaker Studio or local Jupyter notebook, `cloud/ml/metrics_comparison.ipynb`, outside the
Lambda packages. Every number in the report must come from your own run; this outline contains no results.

## 1. Load the curated data

- Query the curated table through Athena (see `docs/cloud/architecture.md`, section "Athena table"),
  or read the Parquet files with `pandas.read_parquet` after `aws s3 sync`.
- Print row count, positive rate (`no_show` mean), and the date range of `scheduled_at`.
- State the data label (`data_label` column). Rows labelled `kaggle_public` (the public dataset) and
  `demo` or `synthetic` (LivoCRM exports) must be reported separately, never pooled into one number.

## 2. Split exactly as the training job does

- Stratified 80/20 split on `no_show`, `random_state=42`, same feature list as `FEATURE_COLUMNS` in
  `cloud/ml/train.py`.
- Assert the split sizes equal `rows_train` and `rows_test` in the `metrics.json` from the training job.

## 3. Baseline

- Logistic regression with one-hot `age_band` and `class_weight="balanced"`.
- Report AUC, precision and recall at threshold 0.5.

## 4. Candidate

- Histogram gradient boosting, same preprocessing, `random_state=42`.
- Same three metrics at threshold 0.5.

## 5. Results table (fill from your run)

| Model | Test AUC | Precision @0.5 | Recall @0.5 | Notes |
|---|---|---|---|---|
| logistic_regression | | | | baseline |
| hist_gradient_boosting | | | | candidate |

Add one more row pair for precision and recall at the top 20% of predicted risk. The reminder team
can only call a limited number of patients, so this is the operational number.

## 6. Checks before deciding

- Calibration: reliability curve (10 bins) for the chosen model. Report if predicted risk is far from observed rate.
- Error by segment: AUC or positive rate by `age_band` and by `lead_time_days` bucket. Note any segment with very few rows.
- Leakage check: confirm `prior_no_shows` only counts appointments scheduled before the row (the ETL sorts by `scheduled_at`).
- Sensitivity: re-run with two other seeds and report the spread, not just one number.

## 7. Decision and limits

- Keep the candidate only if its test AUC beats the baseline by more than the seed spread from step 6.
- Write down the limits: public Kaggle data has no appointment times (`scheduled_hour` is the booking
  hour), and LivoCRM outcome labels only exist once the app has real or seeded appointment outcomes.
  Say which of the two your numbers come from.
- Save the chosen threshold and the metrics table into the report. Do not copy numbers from this outline.
