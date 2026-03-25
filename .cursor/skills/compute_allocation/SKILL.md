# Compute allocation (UCDC)

Use this skill when designing or implementing **job scheduling**, **resource allocation**, **queues/workers**, **entitlements**, or **multi-tenant fairness** for the User-Consented Distributed Compute stack.

## Repo anchors

Paths are from the **repository root** (e.g. `src/ucdc/...`).

- Consent + issuance: `src/ucdc/consent_api.py`, `src/ucdc/consent_hash.py`
- Job lifecycle: `src/ucdc/orchestrator_api.py`, `src/ucdc/models.py` (`Job`)
- Manifest + contracts: `src/ucdc/schemas.py` (`JobManifest`, `JobRequest`)
- Adapter integration: `src/ucdc/adapter_client.py`
- Audit: `src/ucdc/audit.py`
- Tests often set `UCDC_SKIP_ADAPTER_INTEGRATION=1` — preserve this pattern for unit tests.

## Principles

1. **Consent binds scope** — Any field that changes what runs or what capacity is consumed must be included in the **consent hash** (same canonicalization rules for issuance and verification). Do not silently widen scope after consent.
2. **Enforce at enqueue and dequeue** — **Re-check entitlements at dequeue** (user may downgrade while a job waits). Consent validity must still hold.
3. **Explicit resource model** — Move from opaque `resources: List[str]` toward **structured** requests (tier, cpu/memory class, GPU flag, max runtime) as the product matures; version manifests (`manifest_version` or nested spec) when extending.
4. **Async by default for scale** — Prefer **queue + workers** over holding HTTP requests open for adapter execution; keep a **feature flag** for sync fallback during rollout.
5. **Idempotent workers** — At-least-once delivery implies **idempotent completion** (dedupe by `job_id`, lease/visibility timeout, poison-queue handling).
6. **Observability** — Emit metrics for enqueue depth, wait time, admission denials (with reason label), and terminal job states. Correlate with `job_id` in logs.

## Networking / service boundaries

- Orchestrator calls adapter via **HTTP** using `AGENT_ADAPTER_BASE_URL` (see `src/ucdc/config.py`). In Docker Compose, use **service DNS names**, not `127.0.0.1`.
- Timeouts: respect `agent_adapter_timeout_seconds`; queue workers may use longer bounds than the public schedule API.
- Do not assume single-node only: design message payloads so **workers** can run in separate processes/containers.

## Implementation checklist (when changing allocation)

- [ ] Schema/migrations if storing SKUs, entitlements, or queue metadata
- [ ] Orchestrator admission logic + clear HTTP errors or `202 Accepted` + poll contract
- [ ] Worker loop: dequeue → admissions → `call_adapter_execute` (or equivalent) → finalize `Job` status + audit events
- [ ] Tests: entitlement limit exceeded, expired consent while queued, hash mismatch on manifest
- [ ] Env docs and Compose updates for broker + worker service

## Anti-patterns

- Allocating capacity only from free-text tags with no numeric cap or tier mapping.
- Scheduling execution in the request thread without backpressure — starves the API under load.
- Checking entitlements only at enqueue — allows post-run abuse after downgrade.
- Changing hash inputs without versioning — breaks existing consent tokens.
