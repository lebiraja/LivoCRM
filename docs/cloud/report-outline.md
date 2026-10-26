# Cloud Computing IA3 report outline (AWS, Health domain)

Skeleton only. Write in your own words (plagiarism must stay under 10%), cite every source, and fill each `TO FILL` with a real result from your own AWS run. Do not claim anything that was not deployed. Code and runbook: `cloud/`, `cloud/deploy/README.md`, `docs/cloud/architecture.md`.

## 1. Problem statement, dataset and cloud visualisation (5)
- Real-world problem: missed appointments (no-shows) cost small clinics revenue; cite 2-3 sources. TO FILL.
- Dataset: public Medical Appointment No-Shows (Kaggle, cite licence) in S3 `raw/`; anonymised LivoCRM export. Rows, columns, class balance: TO FILL.
- Dashboard: Athena over curated S3 plus QuickSight (screenshots). TO FILL.

## 2. Cloud architecture and pipeline implementation (10)
- Diagram (Mermaid in `docs/cloud/architecture.md`), Docker images in ECR, EC2 with Caddy TLS.
- Serverless: ETL Lambda (S3 event and EventBridge) and nightly scoring Lambda.
- ETL steps and features; CI/CD with GitHub Actions and OIDC; IaC with SAM. Deployment evidence (URLs, run logs, screenshots): TO FILL.

## 3. Result analysis with managed cloud ML (5)
- SageMaker training job, logistic-regression baseline, metrics table (AUC, precision, recall): TO FILL.
- Model used in the app (no-show risk). Limitations and bias notes.

## 4. Report quality (5)
References, figures from the real deployment, cost table (actual bill, TO FILL), security (least privilege IAM, no PII leaves the app), lessons learned.
