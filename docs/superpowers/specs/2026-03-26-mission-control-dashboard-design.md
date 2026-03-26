# Mission Control Dashboard Design (Founder/Operator)

## Objective
- Build a single dual-horizon Mission Control dashboard for the founder/operator.
- Combine daily execution and weekly strategy in one surface.
- Keep terminology aligned to project context: Trust Pact, Mission Board, Engine Link, Proof Ledger, Kill Switch.

## Scope

### In scope
- One dashboard with:
  - daily command signals,
  - weekly strategy analytics,
  - reliability and trust visibility.
- Founder/operator-focused decisions:
  - channel scaling decisions,
  - onboarding quality checks,
  - agent-level reliability actions.

### Out of scope
- External partner/investor dashboards.
- Separate role-based dashboards.
- On-chain or marketplace analytics.

## KPI Set

### Daily command KPIs
- New installs (by channel).
- Trust Pact activations and activation rate.
- Human approval checkpoint completion.
- Missions launched (agent-centric).
- Mission success rate by `agent_id`.
- Kill Switch events and spike detection.
- Proof Ledger coverage.
- System health score.

### Weekly strategy KPIs
- Install -> Trust Pact funnel.
- Trust Pact -> first mission funnel.
- First mission -> repeat mission.
- Channel quality by conversion and reliability.
- Cohort performance.
- Economic signals tied to mission outcomes.
- Trust signal rates (Kill Switch trend).

## Information Architecture

### Layout
1. Header controls (time range, env, source filter, last sync).
2. Critical pulse cards (always visible).
3. Daily Command block (funnel, anomalies, action queue).
4. Weekly Strategy block (channel matrix, cohorts, economics/trust).
5. Reliability and audit block.
6. Drilldown drawer per KPI.

### Hierarchy rules
- Daily execution above the fold.
- Weekly strategy in next viewport.
- Red status creates sticky action banner.
- Keep first-view metrics concise; push depth to drilldown.

## Data and Event Model

### Business keys
- Primary business dimension: `agent_id` (not `job_id`).
- Correlation fields: `consent_id`, `agent_id`, `request_id`.
- Internal execution IDs can exist for diagnostics, but not as primary KPI axis.

### Canonical events
- Acquisition/onboarding:
  - `install.started`
  - `install.completed`
  - `trust_pact.viewed`
  - `trust_pact.approval_checkpoint_seen`
  - `trust_pact.activated`
  - `trust_pact.activation_failed`
- Mission lifecycle:
  - `mission.launch_requested`
  - `mission.launch_accepted`
  - `mission.completed`
  - `mission.failed`
- Trust/control:
  - `kill_switch.triggered`
  - `proof_ledger.event_recorded`
  - `proof_ledger.gap_detected`
- Reliability:
  - `service.health_snapshot`
  - `engine_link.execute_failed`

### Metric definitions
- Activation rate = `trust_pact.activated / install.completed`
- Approval completion = `trust_pact.activated / trust_pact.approval_checkpoint_seen`
- Mission success = `mission.completed / mission.launch_accepted` by `agent_id`
- Kill Switch rate = `kill_switch.triggered / active_users_7d * 100`
- Proof Ledger coverage = missions with all required lifecycle events / missions launched

### Measurement contract (v1)
| Metric | Numerator | Denominator | Window | Grain | Source | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| Activation rate | `trust_pact.activated` | `install.completed` | rolling 24h and 7d | channel, `agent_id` | onboarding + consent events | founder/operator |
| Approval completion | `trust_pact.activated` | `trust_pact.approval_checkpoint_seen` | rolling 24h and 7d | channel, `agent_id` | onboarding events | founder/operator |
| Mission success | `mission.completed` | `mission.launch_accepted` | rolling 24h and 7d | `agent_id` | orchestrator events | founder/operator |
| Kill Switch rate | `kill_switch.triggered` | active users in prior 7d | rolling 24h and 7d | `agent_id` | consent events + active user view | founder/operator |
| Proof Ledger coverage | missions with required events (`launch_requested`, `launch_accepted`, `completed/failed`, ledger-write event) | missions launched | rolling 24h and 7d | `agent_id` | normalized audit/event store | founder/operator |
| Weekly economics (gross) | sum of payout-eligible mission value (INR) | n/a | trailing 7d | `agent_id` | mission outcomes + payout metadata | founder/operator |
| Weekly economics (per active user) | sum of payout-eligible mission value (INR) | active users in prior 7d | trailing 7d | `agent_id` | mission outcomes + active user view | founder/operator |

### Canonical definitions
- `active_users_7d`: distinct users with at least one of (`trust_pact.activated`, `mission.launch_accepted`, `mission.completed`) in trailing 7 days, excluding internal/test accounts.
- Time boundary standard: UTC day boundaries for daily metrics and trailing windows.
- Payout metadata source-of-truth: payout ledger table owned by platform/backend team (founder/operator as interim owner in v1).

## Alert Rules and Runbook

### Red alerts (ack <= 15 min)
- Activation drop > 25% vs trailing 7d baseline.
- Kill Switch spike > 2x trailing 7d baseline in 2h.
- Mission failure > 15% for any `agent_id` in 1h (sample >= 30 launches).
- Proof Ledger coverage < 98% for last 100 launched missions.

#### Red alert execution template
- Owner: founder/operator (primary), designated backup operator (secondary).
- First action: identify impacted `agent_id` and channel scope in drilldown.
- Escalation path: if unresolved in 30 minutes, escalate to engineering owner for affected service.
- Resolution verification: metric returns below threshold for one full evaluation window.

### Amber alerts (same day)
- Channel activation down 10-25% vs trailing 7d baseline.
- Approval completion down 10%+ vs trailing 7d baseline.
- Repeat mission rate down 15% WoW.
- Service p95 latency up 30% over trailing 7d baseline.

### Founder/operator cadence
- Daily: 15-minute command loop for pulse + anomalies + action queue.
- Weekly: 60-minute strategy review for channel, agent quality, and experiment locks.

## Data Ownership and Dependencies
- Consent service owns Trust Pact lifecycle events.
- Orchestrator owns mission lifecycle and reliability events.
- Adapter layer (Engine Link) owns execution-failure classification events.
- UI layer owns onboarding interaction events (views/checkpoint/activation intents).
- Shared analytics schema ownership: platform team (or founder-operator in v1).

## Non-Functional Targets
- Dashboard freshness SLA: <= 5 minutes for daily command metrics.
- Weekly aggregates refresh: hourly.
- KPI query response target: p95 <= 800 ms for headline cards.
- Alert evaluation frequency: every 5 minutes.

## Metric Edge-Case Rules
- Late events: include up to 24 hours of late arrivals in recomputation.
- Deduplication: idempotency key = (`event_type`, `consent_id`, `agent_id`, `request_id`, `timestamp_bucket`).
- Out-of-order events: lifecycle validation allows reorder within a 10-minute grace window.
- Retries: count as one logical mission entity via shared `request_id`.
- Division-by-zero behavior: render `N/A` and suppress alert for that metric window.

## Explicit Non-Goals (v1)
- Role-based access controls and multi-role dashboard views.
- Data masking policies beyond founder-only local/staging usage.

## Implementation Phasing (Design-Level)
1. Define event schema and normalized analytics model.
2. Instrument onboarding + mission + trust events in UI and APIs.
3. Build aggregate queries/views for daily and weekly blocks.
4. Build dashboard UI sections in one page with drilldown drawer.
5. Add alert evaluation and operator action queue.

## Acceptance Criteria
- Single screen includes all six designed sections (header controls, pulse row, daily block, weekly block, reliability block, drilldown drawer).
- All headline metrics are queryable and segmented by `agent_id`.
- Naming and copy align with project-context terms in all user-visible labels.
- Every red alert has owner, first action, escalation condition, and resolution verification step.
- Alert acknowledgment and mitigation timestamps are captured for SLA checks.

## Risks and Mitigations
- Risk: metric ambiguity from mixed IDs.
  - Mitigation: enforce `agent_id` as business primary dimension.
- Risk: noisy alerts.
  - Mitigation: baseline windows and threshold tuning.
- Risk: trust metric gaps.
  - Mitigation: Proof Ledger completeness checks before payout assertions.

## Decisions Traceability
- Chosen: Approach A, single dual-horizon dashboard (daily + weekly in one surface).
- Not chosen: separate daily/weekly dashboards and report-only weekly view.
- Reason: lower context switching and faster founder/operator decision cycles in v1.

## Assumptions and Open Questions
- Assumption: one founder/operator can handle red-alert loop initially.
- Assumption: existing audit/event pathways can be normalized without major schema rewrite.
- Locked decision: weekly economics panel uses hybrid view (gross payout-eligible INR + per-active-user INR).
