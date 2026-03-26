# End-user onboarding (pilot slice)

This document describes the **first vertical slice** for people who are not reading the repo: what they should understand before granting consent, and what the product should make obvious.

## Principles

1. **Plain language** — The user sees *which agent*, *which resources* (data/tools), and *how long* consent lasts (TTL), not JWTs or internal IDs.
2. **Informed consent** — The explanation field is not decorative; surfaced copy should match what the system will enforce (agent + resource list + TTL).
3. **Revocation is real** — After revoke, **new** jobs must not run with the old token; the UI should say that past jobs may already have completed.
4. **Audit trail** — Users (or their org) should be able to answer “what did I approve?” and “what happened next?” without SSH access.

## Happy path (demo UI)

Served by the consent service at **`/ui`** (see `web/index.html`):

1. **Issue consent** — User confirms agent, resources, explanation, TTL; system returns a consent id and token (token is for machines; hide or shorten in a full product).
2. **Schedule job** — Orchestrator validates the token and runs the pipeline (demo: calls the example adapter).
3. **Revoke** — User stops *future* use; verify with a second “schedule job” attempt or adapter call.

## Naming and onboarding language (Indian TG)

Use this naming layer in user-facing onboarding and dashboard copy:

- Consent -> **Trust Pact**
- Job queue and task feed -> **Mission Board**
- Adapter execution layer -> **Engine Link**
- Audit trail -> **Proof Ledger**
- Revocation control -> **Kill Switch**

### MVP onboarding pattern (approved)

1. **Trust Pact setup** — user chooses scope, TTL, and rate limits in plain language.
2. **Human approval checkpoint** — Staffer does not activate without explicit user approval.
3. **Dashboard first state** — show Staffer present with Mission Board and Proof Ledger visible.
4. **Control reminder** — keep Kill Switch visible to emphasize immediate revocation control.

## Copy guidelines (for future product UI)

- **Headline**: What you’re allowing (one line).
- **Body**: Bullet list of resources/URIs; agent name; duration.
- **Risk tone**: Neutral, not alarmist; link to details if needed.
- **Revoke**: “Stop future jobs” (not “delete history”).
- **Trust copy**: Every earning claim should point to the Proof Ledger.
- **Activation copy**: Mention that Staffer activation requires a human approval checkpoint.

## What is not in this slice

- Identity / login for end users (OIDC, etc.).
- Email or push notifications.
- Payment or marketplace for agents.

Those belong in later milestones once the consent + job contract is stable.
