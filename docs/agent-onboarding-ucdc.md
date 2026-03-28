# Agent onboarding — integrating with UCDC

This document is the **contract and practice guide** for third-party agents (e.g. **The Staffer**) that run work through the User-Consented Distributed Compute stack. Keep it next to `project-context.md` and `ARCHITECTURE.md`.

## What UCDC guarantees

1. **Trust Pact (consent)** — Every job is tied to a consent record and JWT (`consent_token`). Users can revoke; expired or revoked consents must fail closed.
2. **Mission Board (jobs)** — The orchestrator schedules work; the **Engine Link (adapter)** executes it. Hashing binds `job_manifest` to the consent scope.
3. **Proof Ledger (audit)** — Consent and job lifecycle events are auditable server-side.

Spyder naming above is **UX-only**; HTTP paths and JSON fields use technical names (`/consents`, `job_manifest`, etc.).

## Non-negotiable integration rules

| Rule | Why |
|------|-----|
| **Same `JWT_SECRET` and `CONSENT_ISSUER`** across Consent, Orchestrator, and Agent Adapter services | JWTs must verify everywhere. |
| **Same `agent_id` in** `POST /consents`, inside the JWT, and in `job_manifest.agent_id` | Enforced with 403 on mismatch. |
| **`job_manifest` must match consent hash** | Includes `resources`, and (if used) `manifest_version` + `resource_spec`. Do not send fields that were not part of consent unless you re-issue consent. |
| **Handle `202` from `POST /jobs`** when `UCDC_ASYNC_JOBS=true` | Poll `GET /jobs/{job_id}` until terminal status (`completed`, `failed`, `cancelled`). |
| **Handle `429` on `POST /jobs`** | Entitlements / concurrency limits; back off or surface to the user. |
| **Adapter URL** | Orchestrator calls **`AGENT_ADAPTER_BASE_URL`**; your Staffer deployment must expose the adapter the orchestrator can reach (Compose service DNS vs `localhost`). |

## Manifest versions

- **`manifest_version: 1`** (default) with **no structured `resource_spec`** keeps the **legacy consent hash** (backward compatible).
- To request structured capacity (`compute_class`, `max_runtime_seconds`, `capability_tags`), set **`manifest_version` ≥ 2** or supply a non-empty `resource_spec` at consent time and use the **same** shape on every job.

See `src/ucdc/consent_hash.py` and `src/ucdc/schemas.py`.

## Repository hygiene for agent projects

1. **Pin environment** — Document `CONSENT_BASE_URL`, `ORCHESTRATOR_BASE_URL`, `AGENT_ADAPTER_BASE_URL` (or derive from one host).
2. **Single client module** — Centralize HTTP calls (see `docs/staffer-ucdc-bundle/integrations/ucdc_client.py`).
3. **CI smoke** — Against Docker Compose or pytest: issue consent → schedule job → assert `completed` or expected failure.
4. **Never embed** the user’s long-lived consent token in logs or analytics payloads.
5. **Version your agent** separately from UCDC (`User-Agent`, `X-Agent-Version` headers optional but recommended).

## Compatibility review checklist (before shipping)

- [ ] Consent + job JSON matches `src/ucdc/schemas.py` (`ConsentRequest`, `JobManifest`, `JobRequest`).
- [ ] Client handles **200** and **202** from `POST /jobs`.
- [ ] Client handles **403** (hash / agent mismatch), **429** (admission), **401** (JWT).
- [ ] Adapter implements `POST /execute` with the same manifest validation as the orchestrator path.
- [ ] If async mode is used, a **job worker** is deployed (`python -m ucdc.job_worker` or Compose profile `async`).

## Reference bundle for The Staffer

A drop-in **Python client** and **Staffer-specific README** live under:

- `docs/staffer-ucdc-bundle/`

Copy that folder into the Staffer repository (or depend on it as a submodule) and follow `docs/staffer-ucdc-bundle/README.md`.

## When anonymous GitHub access fails

If automation cannot clone `The_Staffer_UCDC` (private repo, LFS, or network), maintainers should:

1. Clone with credentials locally.
2. Copy `docs/staffer-ucdc-bundle/` into the Staffer tree.
3. Run the checklist in `COMPATIBILITY.md` and add CI.
