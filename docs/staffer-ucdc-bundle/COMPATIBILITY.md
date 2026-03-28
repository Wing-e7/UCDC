# Staffer — UCDC compatibility checklist

Use this when reviewing **`The_Staffer_UCDC`** against a running UCDC stack (Docker Compose or hosted).

## Environment

| Variable | Example (local Compose) | Notes |
|----------|---------------------------|--------|
| `UCDC_CONSENT_BASE_URL` | `http://localhost:8001` | Consent service |
| `UCDC_ORCHESTRATOR_BASE_URL` | `http://localhost:8002` | Job orchestrator |
| `UCDC_AGENT_ID` | `staffer` or `the-staffer` | Must match adapter `agent_id` and consent |
| `JWT_SECRET` / issuer | *(inherited by services)* | Client does not set this; services must match |

## HTTP contract

1. **`POST /consents`** — Body matches `ConsentRequest` in UCDC `schemas.py` (`user_id`, `agent_id`, `resources`, `explanation`, `ttl_seconds`, optional `manifest_version`, `resource_spec`).
2. **`POST /jobs`** — Body: `{ "consent_token", "job_manifest" }`. Accept **`200`** (sync) or **`202`** (async). Response body always includes `job_id` and `status`.
3. **`GET /jobs/{id}`** — Poll until `status` is terminal: `completed`, `failed`, `cancelled` (or `scheduled` / `queued` while processing).
4. **`POST /consents/{id}/revoke`** — Kill-switch path for Trust Pact UX.

## Common mismatches

| Symptom | Likely cause |
|---------|----------------|
| 403 `Resources/manifest mismatch` | `job_manifest` differs from what was hashed at consent (extra fields, wrong `resources`, changed `resource_spec`). |
| 403 `Agent ID mismatch` | `agent_id` in manifest ≠ token / consent. |
| 403 after revoke | Expected; refresh consent. |
| 429 on `/jobs` | Concurrency / entitlements; reduce parallel jobs or raise limits in `agent_entitlements` / `UCDC_DEFAULT_MAX_CONCURRENT_JOBS`. |
| Job stuck `queued` | Async mode on without **job worker** (`python -m ucdc.job_worker` or Compose `--profile async`). |
| Adapter unreachable | Orchestrator `AGENT_ADAPTER_BASE_URL` must resolve **inside** Docker network (`http://agent_adapter_service:8003`), not only `localhost` on the host. |

## Verification commands (from UCDC repo)

```bash
docker compose up --build -d
curl -s http://localhost:8001/health
curl -s http://localhost:8002/health
curl -s http://localhost:8003/health
```

Then run Staffer’s own E2E or the Python client smoke test (see `ucdc_client.py` docstring).
