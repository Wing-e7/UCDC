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

## Copy guidelines (for future product UI)

- **Headline**: What you’re allowing (one line).
- **Body**: Bullet list of resources/URIs; agent name; duration.
- **Risk tone**: Neutral, not alarmist; link to details if needed.
- **Revoke**: “Stop future jobs” (not “delete history”).

## What is not in this slice

- Identity / login for end users (OIDC, etc.).
- Email or push notifications.
- Payment or marketplace for agents.

Those belong in later milestones once the consent + job contract is stable.
