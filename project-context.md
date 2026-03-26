# UCDC Project Context

## Purpose
- This file is the source-of-truth context for all contributors and subagents working on UCDC.
- It combines the target architecture with the currently agreed product direction.
- If a task conflicts with this file, pause and ask for scope confirmation before implementing.

## Product Vision (Target State)
- UCDC is a user-consented distributed compute engine.
- Every compute action must be user-authorized, observable, and revocable.
- The long-term platform includes:
  - consent-aware job orchestration,
  - modular agent adapters,
  - policy and compliance controls,
  - auditable governance and observability.

Reference: `ARCHITECTURE.md`

## Current Product Direction (Business Framing)
- The immediate product framing is a community agent-card economy inspired by collectible communities.
- Initial target demographic (TG): Indian users aged 18-25.
- MVP starts with non-tradable agent licenses ("cards"), with trading deferred.
- MVP card pack is locked to:
  - **Compute Earner**: users consent to compute usage and rate limits to earn economically viable revenue.
  - **Staffer**: an assistant that finds gigs/opportunities with human-in-the-loop approval for sensitive or external actions.

## System Meaning In This Context
- **Issue/Revoke consent**: activate/deactivate a card's right to perform work.
- **Schedule jobs**: queue or run card work units (compute tasks, gig discovery tasks).
- **Execute via adapter**: run card-specific logic in a controlled adapter.
- **Audit lifecycle events**: produce verifiable logs for trust, safety, and payout traceability.

## Spyder Messaging Layer (Indian TG)
- This layer standardizes product language for onboarding and growth communication aimed at Indian 18-25 users.
- It is applied to copy, naming, and UX explainers only. It does not alter backend contracts or architecture.

### Canonical Naming Map
- Consent -> **Trust Pact**
- Job request -> **Mission Board**
- Adapter -> **Engine Link**
- Audit log -> **Proof Ledger**
- Revocation -> **Kill Switch**

### Copy Standards
- Hero message formula: benefit + control + earnings.
  - Example: "Power your Staffer, earn from gigs, keep control over consent."
- Three-value onboarding strip:
  - consent visibility,
  - earning path,
  - trust trail.
- Core step narrative text should align to:
  - "Consent -> Job -> Execution -> Audit"

### Trust and Economics Guardrails (Messaging)
- Every earnings claim must map to an auditable lifecycle event.
- Every control claim must mention revoke, TTL, or rate-limit boundaries.
- If legal/compliance wording differs, legal wording remains primary and Spyder naming is secondary.

## Architecture Alignment (What Exists vs What Is Planned)
- **Implemented baseline**
  - Consent issuance/revocation and consent event logging.
  - Job scheduling/detail/cancel, sync and async execution.
  - Adapter execution path with consent/hash validation.
  - Entitlement-based admission and manifest v2 hashing support.
  - Health/metrics/logging and migration-backed persistence.
- **Planned/partial**
  - Full edge gateway and richer identity/authz.
  - Deep policy/compliance controls and stronger runtime isolation.
  - Advanced observability and governance dashboards.
  - Broader agent ecosystem beyond starter adapters.

## Clear Scope

### In Scope (Now)
- Build a cloud-baseline MVP around Compute Earner + Staffer.
- Keep consent-first controls as hard requirements for all job execution.
- Add economic guardrails:
  - explicit per-user/per-agent rate limits,
  - metered work accounting,
  - auditable payout-related events.
- Keep Staffer actions human-approved at key checkpoints.
- Prioritize hardening-first delivery (security, reliability, policy) before ecosystem expansion.
- Apply Spyder naming and onboarding copy to user-facing language for Compute Earner and Staffer.
- Spyder integration is messaging and UX language only; it does not expand technical MVP scope.

### Out of Scope (Now)
- Tradable card marketplace or on-chain ownership mechanics.
- Broad social/community feature set (events, dating, expansion agents) in MVP.
- Full consumer identity suite and monetization complexity beyond MVP earning flows.
- Large-scale multi-cloud/data residency rollouts before core MVP reliability is proven.

### Deferred Scope (After MVP Alpha)
- Internal trading marketplace for cards.
- Additional cards: Events, social/date, and other community agents.
- Expanded policy engine and richer compliance controls.
- Full operator analytics and customer-facing governance views.

## Sprint Framing (Locked)

### Sprint 1: Compute Earner MVP + Economic Guardrails
- Card activation using existing consent primitives.
- Rate/concurrency controls and clear revoke semantics.
- Baseline earning/payout ledger events.
- Cloud-safe configuration and startup checks.
- Deliver Compute Earner onboarding copy using Spyder language:
  - Trust Pact explainer,
  - rate-limit transparency copy,
  - Proof Ledger earning proof labels.

### Sprint 2: Staffer MVP + Human-In-Loop Reliability
- Staffer pipeline with mandatory approval checkpoints.
- Idempotency, retry/backoff, timeout/cancel semantics across jobs.
- Payout traceability tied to job lifecycle outcomes.
- Scenario tests for revocation mid-flow, duplicates, and worker recovery.
- Deliver Staffer trust and approval copy using Spyder language:
  - Mission Board approval checkpoints,
  - Kill Switch impact messaging,
  - Proof Ledger payout traceability labels.

## Guardrails For Subagents
- Do not propose features outside "In Scope (Now)" unless explicitly requested.
- Treat consent validation and audit logging as non-negotiable acceptance criteria.
- Favor incremental, test-backed changes that preserve the existing consent-job-adapter contract.
- Any new revenue or payout logic must be traceable through auditable events.
- When unclear, ask for scope clarification before implementation.
- For roadmap, UX, and growth language work, reference this file first and use the Spyder naming map consistently.
- Any new naming proposal must include a one-line reason tied to consent trust, monetization clarity, or user control.

## Core References
- `ARCHITECTURE.md`
- `README.md`
- `docs/onboarding-flow.md`
- `src/ucdc/consent_api.py`
- `src/ucdc/orchestrator_api.py`
- `src/ucdc/agent_adapter_api.py`
- `src/ucdc/job_worker.py`
- `src/ucdc/entitlements.py`
- `src/ucdc/schemas.py`
