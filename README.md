# UCDC (User-Consented Distributed Compute Engine) - Skeleton

This repo contains the initial skeleton for:
- Consent Service (issue/revoke consent tokens)
- Orchestrator (validate consent and schedule jobs)
- Example Agent Adapter (capabilities + stub execution)

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

The orchestrator calls the agent adapter **`POST /execute`** after scheduling a job (`AGENT_ADAPTER_BASE_URL`, default in Compose: `http://agent_adapter_service:8003`). Jobs transition **`scheduled` → `running` → `completed`** or **`failed`** (with audit events).

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

