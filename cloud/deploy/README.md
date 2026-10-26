# Deploy runbook: LivoCRM on one EC2 host

Placeholders: `<ACCOUNT_ID>`, `<REGION>`, `<BUCKET>` (`livocrm-data-<ACCOUNT_ID>-<REGION>`),
`<APP_DOMAIN>`, `<OWNER>/<REPO>`, `<INSTANCE_ID>`, `<ELASTIC_IP>`. Replace them in your own notes,
never in committed files.

What the stack looks like on the host:

```
Internet :80/:443 -> Caddy (TLS, Let's Encrypt) -> nginx :80 -> frontend (static SPA) / backend (FastAPI)
                                                                     |-> db (Postgres, no host port)
                                                                     |-> redis (no host port)
```

## 1. Host sizing

| Option | vCPU / RAM | EBS | Use |
|---|---|---|---|
| t3.small | 2 / 2 GiB | 20 GiB gp3 | cheapest; add 2 GiB swap, expect slow `docker compose build` (we build in CI, not on the host) |
| t3.medium | 2 / 4 GiB | 20 GiB gp3 | recommended for the demo: Postgres, Redis, backend, nginx and Caddy together |

Pricing is an estimate; see `docs/cloud/architecture.md`. Allocate an Elastic IP and point
`<APP_DOMAIN>` at it with an A record before first boot, so Caddy can get a certificate.

## 2. Network

- Security group (created by `cloud/template.yaml`, `AppSecurityGroup`): inbound 80 and 443 from
  `0.0.0.0/0` only. No port 22. Shell access is through SSM Session Manager (`aws ssm start-session`),
  which needs the `AppInstanceRole` policy `AmazonSSMManagedInstanceCore`.
- Postgres (5432) and Redis (6379) are not published in `docker-compose.yml` and stay that way in prod.
- Only Caddy publishes host ports; nginx's `:3500` mapping is removed by `docker-compose.prod.yml`.

## 3. Secrets (SSM Parameter Store)

Create these once, from files so the values stay out of shell history:

```bash
# app environment: DATABASE_URL, REDIS_URL, SECRET_KEY, GROQ keys, CORS_ORIGINS, APP_DOMAIN, BACKUP settings
aws ssm put-parameter --region <REGION> --name /livocrm/prod/dotenv --type SecureString \
  --value file://./prod.env --overwrite
# read-only GitHub deploy key for the repo clone on the host
aws ssm put-parameter --region <REGION> --name /livocrm/prod/github_deploy_key --type SecureString \
  --value file://./deploy_key --overwrite
```

Then delete the local `prod.env` and `deploy_key` files. Set `CORS_ORIGINS=https://<APP_DOMAIN>` and
`ENABLE_DOCS=false` in `prod.env`. Rotate any secret that was ever committed to git. The
`AppInstanceRole` can read only `/livocrm/prod/*`.

## 4. First boot

1. Launch an Amazon Linux 2023 instance in the VPC with: the `AppInstanceProfileName` output as the
   instance profile, the `AppSecurityGroupId` output as the security group, and the Elastic IP attached.
   Under Advanced details, set Metadata version to "V2 only (token required)" (IMDSv2).
2. Paste `cloud/deploy/user-data.sh` into User data after replacing `<REGION>`, `<OWNER>/<REPO>` and
   `<BUCKET>`. It installs Docker, the Compose v2 plugin (pinned version; check its sha256), git and cron,
   clones the repo to `/opt/livocrm`, writes `.env` from SSM and installs the nightly backup cron.
3. Confirm the Compose plugin is at least 2.24.4: `docker compose version`.
4. Run the first deploy: push to `main` (GitHub Actions does it), or run `deploy.sh` by hand (section 6).
5. Check: `curl -fsS https://<APP_DOMAIN>/api/health`. Caddy fetches the certificate on the first HTTPS
   request, so the first call can take a few seconds.

## 5. GitHub Actions wiring

These are repository variables, not secrets (Settings > Secrets and variables > Actions > Variables).
The workflow reads them; no account id or role ARN is written in `.github/workflows/deploy.yml`.

| Variable | Value |
|---|---|
| `AWS_REGION` | `<REGION>` |
| `ECR_REGISTRY` | `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com` |
| `AWS_ECR_SSM_ROLE_ARN` | output `GitHubEcrSsmRoleArn` |
| `AWS_SAM_ROLE_ARN` | output `GitHubSamRoleArn` |
| `APP_INSTANCE_ID` | the EC2 instance id |
| `APP_URL` | `https://<APP_DOMAIN>` |
| `SAM_STACK_NAME` | `livocrm-ia3` (stack names must start with `livocrm-` for the deploy role) |
| `SAM_ARTIFACT_BUCKET` | a bucket you create once named `livocrm-sam-artifacts-<ACCOUNT_ID>-<REGION>` |
| `OIDC_PROVIDER_ARN` | ARN of the existing GitHub OIDC provider in IAM |
| `VPC_ID` | the VPC for the security group |
| `BUDGET_EMAIL` | address for budget alerts |

The OIDC provider for `token.actions.githubusercontent.com` is created once per account in IAM
(console: IAM > Identity providers > Add provider > OpenID Connect, audience `sts.amazonaws.com`).

## 6. Deploy, redeploy and roll back

Normal path: merge to `main`. The `deploy` workflow runs `test`, `build-push`, `deploy-app`,
`smoke-test` and `sam-deploy`.

Manual redeploy of an earlier commit, from a machine with AWS credentials that can run SSM:

```bash
aws ssm send-command --region <REGION> --instance-ids <INSTANCE_ID> \
  --document-name AWS-RunShellScript \
  --parameters '{"commands":["/opt/livocrm/cloud/deploy/deploy.sh <FULL_40_CHAR_SHA> <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com <REGION>"]}'
```

Rollback is the same command with the previous good sha. ECR keeps the last 20 image tags per repo
(`cloud/template.yaml` lifecycle policy). Check the logs of the run with
`aws ssm list-command-invocations --instance-id <INSTANCE_ID> --details`.

Database migrations run at backend start (`alembic upgrade head`). Rolling back the code does not roll
back the schema. If a release added a migration, restore the database from the last backup (section 7)
or downgrade with Alembic before redeploying the older image.

## 7. Backups

`cloud/deploy/backup-pg.sh` runs from `/etc/cron.d/livocrm-backup` at 20:30 UTC (02:00 IST). It streams
`pg_dump` through gzip into `s3://<BUCKET>/backups/postgres/`. The object is written with SSE-S3, and a
lifecycle rule in `cloud/template.yaml` expires backups after 30 days. The host role can only write to
that prefix.

Restore into a scratch database first:

```bash
aws s3 cp s3://<BUCKET>/backups/postgres/<FILE>.sql.gz - | gunzip \
  | docker compose -f docker-compose.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Test a restore once before the demo. A backup you have never restored is not a backup.

## 8. Cost alarm

`cloud/template.yaml` creates the `livocrm-monthly-cap` AWS Budget. It emails `BUDGET_EMAIL` at 80%
of actual spend and at 100% of forecast spend. The cap is the `BudgetLimitUsd` parameter (default 10 USD).
Budget alerts follow AWS's cost data, which arrives with a delay. Check Cost Explorer for the current spend.

## 9. Health and logs

```bash
cd /opt/livocrm
docker compose -f docker-compose.yml -f cloud/deploy/docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f cloud/deploy/docker-compose.prod.yml logs --tail=100 backend
```

Every service has a healthcheck; `ps` shows `healthy` or `unhealthy`.

## 10. Teardown

Stop the stack with `docker compose ... down` (volumes are kept). To remove AWS resources, delete the
`livocrm-ia3` CloudFormation stack. The data bucket and the ECR repositories have `DeletionPolicy: Retain`,
so empty and delete them by hand if you really want them gone.
