# Docker

Source of truth: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `nginx/nginx.conf`,
`frontend/nginx.conf`, `.env.example`. Architecture: `docs/architecture.md`.

## Services

| Service | Image / build | Host port | Healthcheck | Starts after | Profile |
|---|---|---|---|---|---|
| `nginx` | `nginx:1.27-alpine` | `3500 -> 80` | `wget /healthz` every 10 s | frontend, backend healthy | default |
| `frontend` | build `frontend/` (node:20 build, `nginx:alpine` runtime) | none | `wget http://127.0.0.1/` every 10 s | backend started | default |
| `backend` | build `backend/`, target `runtime` | none (internal `:8000`) | `GET /api/health` every 10 s, start period 20 s | db, redis healthy | default |
| `db` | `postgres:16.15-alpine` | none | `pg_isready` every 5 s | - | default |
| `redis` | `redis:7.4.11-alpine` | none | authenticated `PING` every 5 s | - | default |
| `pgadmin` | `dpage/pgadmin4:9.18` | `127.0.0.1:5050 -> 80` | none | db healthy | `dev` |
| `db-test` | `postgres:16.15-alpine`, tmpfs data | none | `pg_isready -d livocrm_test` every 2 s | - | `test` |
| `backend-test` | build `backend/`, target `test` | none | none (one-shot) | db-test healthy | `test` |

Networks: `livocrm` (bridge, default services) and `livocrm-test` (internal, test profile only).

Volumes: `pgdata` (Postgres data), `redisdata` (mounted at `/data`, but Redis runs with `--save ''
--appendonly no`, so nothing persists across restarts), `pgadmin_data`.

Only `nginx` publishes a port by default. `db` and `redis` are never published. `db` gets no `env_file`,
so the database container cannot read app secrets. `scripts/check_compose_policy.py` enforces this and
checks healthchecks, dev-port binding and `${VAR}` references for secrets.

Container details:

- `backend` runs as uid 10001 (`app`). Code and `ml/model.pkl` are root-owned and read-only to it. The
  image builds the lead-score model at build time (`ml/generate_data.py`, `ml/train_scorer.py`).
- Start command: `alembic upgrade head`, then `uvicorn app.main:app --proxy-headers
  --forwarded-allow-ips='*'`. One worker, so the in-process WebSocket registry and the Groq key pool
  are per process. Scaling out needs `ENABLE_SCHEDULER=false` on all but one instance (see below).
- `frontend` serves the built SPA on port 80 inside the network. Nothing reaches it except through nginx.
- `nginx` routes `/api/` and `/ws/` to `backend:8000` and `/` to `frontend:80`. `client_max_body_size 1m`.

## Environment

Create `.env` from the example and replace every `change-me`. Compose reads `.env` for interpolation
(`POSTGRES_*`, `REDIS_*`, `PGADMIN_*`) and passes the whole file to `backend` via `env_file`.

```bash
cp .env.example .env
openssl rand -hex 32   # use the output as SECRET_KEY
```

| Variable | Example / default | Read by | Purpose |
|---|---|---|---|
| `POSTGRES_USER` | `livocrm_user` | db | Database role |
| `POSTGRES_PASSWORD` | `change-me` | db | Database password |
| `POSTGRES_DB` | `livocrm` | db | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://livocrm_user:change-me@db:5432/livocrm` | backend | Must match the three values above |
| `REDIS_PASSWORD` | `change-me` | redis, healthcheck | `requirepass` |
| `REDIS_URL` | `redis://:change-me@redis:6379/0` | backend | Must embed `REDIS_PASSWORD` |
| `REDIS_MAXMEMORY` | `128mb` | redis | `maxmemory`, policy `allkeys-lru` |
| `SECRET_KEY` | `change-me` | backend | JWT signing key, 32+ characters, required |
| `ALGORITHM` | `HS256` | backend | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | backend | Browser session token lifetime |
| `AUTH_COOKIE_SECURE` | `false` (Cloudflare prod override: `true`) | backend | Require HTTPS before sending the session cookie |
| `ALLOW_REGISTRATION` | `true` (Cloudflare prod override: `false`) | backend | Public account creation; production account creation uses the CLI |
| `CORS_ORIGINS` | `http://localhost:3500,http://localhost:5173` | backend | Comma-separated allowed origins |
| `ENABLE_DOCS` | `false` | backend | Serve `/api/docs` and `/api/openapi.json` when `true` |
| `LOG_LEVEL` | `INFO` | backend | Root log level |
| `ENABLE_SCHEDULER` | `false` | backend | Run the 60 s recovery generator in-process; keep `false` with several workers |
| `PGADMIN_DEFAULT_EMAIL` | `admin@livocrm.com` | pgadmin | Login (dev profile only) |
| `PGADMIN_DEFAULT_PASSWORD` | `change-me` | pgadmin | Login (dev profile only) |
| `LLM_PROVIDER` | `groq` | backend | `groq` (default) or `bedrock` (legacy) |
| `GROQ_API_KEYS` | empty | backend | One key, or several comma-separated keys. Empty means the AI runs on fallbacks |
| `GROQ_MODEL_FAST` | `openai/gpt-oss-20b` | backend | Classification, extraction, questions, drafts, titles |
| `GROQ_MODEL_SMART` | `openai/gpt-oss-120b` | backend | Dashboard insights |
| `AWS_ACCESS_KEY_ID` | empty | backend | Bedrock only (`LLM_PROVIDER=bedrock`) |
| `AWS_SECRET_ACCESS_KEY` | empty | backend | Bedrock only |
| `AWS_DEFAULT_REGION` | `us-east-1` | backend | Bedrock only |
| `BEDROCK_LLM_MODEL` | `us.meta.llama4-scout-17b-instruct-v1:0` | backend | Bedrock only |
| `VITE_API_URL` | `http://localhost:8000` | frontend build | Not passed by compose (see note) |

Read by `backend/app/config.py` but not in `.env.example` (defaults in code): `GROQ_API_KEY` (single-key
fallback, empty), `GROQ_BASE_URL` (`https://api.groq.com/openai/v1`), `LLM_TIMEOUT_S` (`15.0`),
`LLM_TEMPERATURE` (`0.2`), `BEDROCK_ENABLED` (`true`), `BEDROCK_MAX_TOKENS` (`220`), `BEDROCK_TEMPERATURE` (`0.2`).

Notes:

- **Groq keys.** `GROQ_API_KEYS` takes 1 to N keys. The pool spreads calls across keys, cools a key
  after a 429 and disables one after a 401 or 403. Groq rate limits are per organisation, and keys from
  one organisation share one bucket. Adding a second key from the same organisation does not add
  throughput. Extra keys help only when they belong to different organisations. Behaviour: `docs/ai.md`.
- **`VITE_API_URL`.** Compose does not pass it to the frontend build, so the SPA uses `/api` through
  nginx. The example value `http://localhost:8000` points at a port that compose does not publish. Set it
  only for a local `vite` dev server that reads `frontend/.env`.
- **Secrets.** `.env` is gitignored. Use `env_file`/interpolation only. Never hardcode a credential in
  `docker-compose.yml`.

## Run

```bash
docker compose up -d --build                  # build and start the default services
docker compose ps                             # all services should show (healthy)
curl -fsS http://localhost:3500/api/health    # {"status":"ok"}
```

Open `http://localhost:3500`, register an account, then load the clinic demo data for it:

```bash
docker compose exec backend python -m app.cli seed-demo --email you@example.com
```

The seed is idempotent per patient. It adds up to 12 demo patients (`DEMO_PATIENTS` in
`backend/app/services/demo_seed.py`), each with one past and one upcoming appointment, all tagged `DEMO`.
Running it again adds only patients that are missing. The command exits with an error if no account has
that email.

Optional pgAdmin (dev profile, this machine only):

```bash
docker compose --profile dev up -d pgadmin    # http://127.0.0.1:5050
```

Stop: `docker compose down` keeps volumes. `docker compose down -v` deletes the database. Confirm
before running it.

Production with Cloudflare Tunnel: use `docker-compose.cloudflare.yml` with this file. It disables
Nginx's host port and serves the app through `cloudflared`; see `cloud/deploy/cloudflare-server.md`.
The AWS EC2 deployment path remains in `cloud/deploy/README.md` and uses its Caddy override.

## Tests

Backend (pytest, against a throwaway Postgres on tmpfs):

```bash
docker compose run --rm --build backend-test pytest
```

The `test` profile holds `db-test` and `backend-test`, and `backend-test` depends on a healthy `db-test`.
CI uses the explicit form `docker compose --profile test run --rm --build backend-test pytest`
(`.github/workflows/deploy.yml`). Whether the short form enables the profile on its own was not
checked here [?]. The test image also contains `ruff` and `mypy` (`backend/requirements-dev.txt`).

Other suites, with no compose service:

```bash
# Cloud Lambdas, ML and export (venv outside the repo)
python3 -m venv ~/.venvs/livocrm-cloud
~/.venvs/livocrm-cloud/bin/pip install -r cloud/requirements-test.txt
(cd cloud && ~/.venvs/livocrm-cloud/bin/pytest -q)

# Frontend (vitest): run in a throwaway container [?] not run for this doc
docker run --rm -v "$PWD/frontend:/app" -w /app node:20-alpine sh -c "npm ci && npm test"

# Compose policy (needs the docker CLI)
python3 scripts/check_compose_policy.py
```

Suite counts and coverage: `docs/testing.md`.

## Build troubleshooting

If a build step fails with DNS errors during `pip install` or `npm ci` (typical on networks that block
Docker's default bridge DNS), build the image with the host network:

```bash
docker build --network host --target runtime -t livocrm-backend:local backend
docker build --network host -t livocrm-frontend:local frontend
```

`docker compose build` runs on the default network, so these standalone builds are a fallback for a
machine where it cannot resolve DNS. Compose will still rebuild its own images when `--build` is given.
