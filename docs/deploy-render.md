# Deploy UCDC to Render

This guide deploys the **consent service** (which serves **`/ui/`**) as a web service. The Staffer **local bridge** stays off in production (`UCDC_ENV=production` disables it); users run Staffer on their own machine.

## Prerequisites

- Render account, GitHub repo connected.
- Generate a strong `JWT_SECRET` (never commit it).

## Blueprint

The repo includes `render.yaml`. In the Render dashboard: **New → Blueprint**, connect the repo, and apply the file.

Or create a **Web Service** manually:

| Setting | Value |
|--------|--------|
| **Runtime** | Docker |
| **Dockerfile** | `Dockerfile` |
| **Docker command** | `uvicorn ucdc.consent_api:app --host 0.0.0.0 --port $PORT` |
| **Port** | `PORT` (Render injects this) |

**Environment variables** (minimum):

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | Render Postgres URL rewritten for SQLAlchemy + psycopg3, e.g. `postgresql+psycopg://user:pass@host:5432/dbname` |
| `JWT_SECRET` | Strong random string |
| `UCDC_ENV` | `production` |
| `UCDC_PUBLIC_CONSENT_BASE_URL` | `https://your-service.onrender.com` (no trailing path) |
| `UCDC_PUBLIC_ORCHESTRATOR_BASE_URL` | Public URL of your orchestrator (deploy separately or same host with path routing) |
| `UCDC_PUBLIC_AGENT_ADAPTER_BASE_URL` | Public adapter URL |
| `RUN_DB_MIGRATIONS` | `true` on this service only |

After deploy, open `https://your-service.onrender.com/ui/` for the cockpit.

## Notes

- **Ephemeral disk**: do not rely on the container filesystem for persistence; Postgres holds consent data.
- **CORS**: set `CORS_ORIGINS` to your real browser origins in production (avoid `*`).
- **Orchestrator + adapter**: deploy as additional Render services or other hosts; point `UCDC_PUBLIC_*` at URLs users and browsers can reach.
