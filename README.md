# UCDC (User-Consented Distributed Compute Engine) - Skeleton

This repo contains the initial skeleton for:
- Consent Service (issue/revoke consent tokens)
- Orchestrator (validate consent and schedule jobs)
- Example Agent Adapter (capabilities + stub execution)

For active product direction, scope boundaries, and subagent guardrails, read `project-context.md` first.

## Run with Docker (Postgres)

Optional: copy `cp .env.example .env` and set `JWT_SECRET` (required for `UCDC_ENV=production`).

```bash
docker compose up --build
```

Compose reads `.env` for `${JWT_SECRET}` / `${UCDC_ENV}` substitution (defaults are dev-friendly).

Service URLs:
- Consent Service: `http://localhost:8001`
- Orchestrator: `http://localhost:8002`
- Agent Adapter: `http://localhost:8003`

**End-user style demo (browser):** open **`http://localhost:8001/ui/`** after services are up. It issues consent, schedules a job, and revokes (set orchestrator URL if not default). See `docs/onboarding-flow.md` for the flow and copy notes. CORS defaults to `*` in dev (`CORS_ORIGINS`).

The orchestrator calls the agent adapter **`POST /execute`** after scheduling a job (`AGENT_ADAPTER_BASE_URL`, default in Compose: `http://agent_adapter_service:8003`).

**Sync mode (default):** `POST /jobs` returns **200**; jobs go **`scheduled` → `running` → `completed`/`failed`** with audit events.

**Async mode:** set **`UCDC_ASYNC_JOBS=true`** on the orchestrator (`UCDC_ASYNC_JOBS` in Compose). `POST /jobs` returns **202** and jobs are **`queued`** until a worker drains them. Run **`python -m ucdc.job_worker`** (same `DATABASE_URL` / JWT / adapter URL as orchestrator), or use Compose **`--profile async`** to start `job_worker_service`.

**Manifest v2:** consent and `job_manifest` may include **`manifest_version`** (default `1`) and **`resource_spec`** (`compute_class`, `max_runtime_seconds`, `capability_tags`). They are included in the consent hash whenever the spec is non-empty or `manifest_version > 1` (legacy tokens stay stable for `manifest_version:1` with an empty spec).

**Entitlements:** optional table **`agent_entitlements`** (`user_id`, `agent_id`, `max_concurrent_jobs`). If no row exists, **`UCDC_DEFAULT_MAX_CONCURRENT_JOBS`** applies (default `10`). Enforced at **enqueue** (HTTP 429) and **re-checked at dequeue** (`job.admission_denied` if failed).

### Postgres migrations (Alembic)

On **Postgres**, services run **`alembic upgrade head`** on startup (see `src/ucdc/db.py`). Tests still use **SQLite** + `create_all()`.

Manual upgrade (local):

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ucdc
export PYTHONPATH=src
alembic upgrade head
```

## Quick smoke test

1. Issue consent:
```bash
curl -s http://localhost:8001/health
curl -s -X POST http://localhost:8001/consents \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user-123",
    "agent_id":"example-agent",
    "resources":["s3://bucket/a"],
    "explanation":"Run a demo job with user consent.",
    "ttl_seconds":3600
  }' | jq -r .consent_token
```

2. Schedule job:
```bash
CONSENT_TOKEN="PASTE_TOKEN_HERE"
curl -s -X POST http://localhost:8002/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "consent_token":"'"$CONSENT_TOKEN"'",
    "job_manifest":{
      "agent_id":"example-agent",
      "resources":["s3://bucket/a"],
      "data":{"example":"value"}
    }
  }'
```

3. Revoke consent and verify scheduling fails:
```bash
# replace CONSENT_ID from the first response
curl -s -X POST http://localhost:8001/consents/$CONSENT_ID/revoke
```

## Tests

```bash
pytest -q
```

Tests use SQLite (`tests/conftest.py`); production path uses Postgres via `DATABASE_URL`.

## API (P0 additions)

- `GET /consents/{id}/events` — audit trail for a consent
- `GET /jobs/{id}` — job detail
- `POST /jobs/{id}/cancel` — cancel a scheduled job
- `GET /jobs/{id}/events` — audit events for a job

Set `UCDC_ENV=production` only with a non-default `JWT_SECRET` (startup will fail otherwise).

