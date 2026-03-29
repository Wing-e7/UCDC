# Deploy UCDC to Render

This guide deploys the **consent service** (which serves **`/ui/`**) as a web service. The Staffer **local bridge** stays off in production (`UCDC_ENV=production` disables it); users run Staffer on their own machine.

## Local smoke (latest UI before cloud)

The Docker image **copies `web/`** into the container; whatever is in your repo at build time is what ships.

**Ordered steps**

1. `docker compose build consent_service`
2. `docker compose up -d postgres consent_service` (wait until Postgres is healthy)
3. **Browser:** `http://127.0.0.1:8001/ui/` — you should see the Staffer cockpit (hero, scoreboard, Staffer-on-device panel, consent flow).
4. **API checks:**
   - `curl -sSf http://127.0.0.1:8001/health`
   - `curl -sSf http://127.0.0.1:8001/public-config | jq .` (or `python -m json.tool`) — confirm `consent_base_url`, `default_agent_id`, `staffer_local_bridge` (false unless you enabled the bridge locally).

**Maya-facing UX:** copy and layout live under `web/index.html`; no separate build step. After you change the file, rebuild the consent image so the latest HTML is included.

**Staffer one-tap buttons:** need `UCDC_ENABLE_STAFFER_LOCAL_BRIDGE` + `STAFFER_LOCAL_REPO` on the **host** (or a mounted path in Compose). They stay **off** on Render production.

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
