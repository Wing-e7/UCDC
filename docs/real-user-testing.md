# Real User Testing Plan (Onboarding MVP)

This plan is for quick validation of the Trust Pact + Staffer onboarding flow with Indian 18-25 users.

## Goal
- Verify users understand and complete onboarding without help.
- Confirm trust and control messaging is clear before activation.
- Detect friction in approval checkpoint and first dashboard experience.

## Test Setup
- Participants: 8 to 12 users from target group (Indian 18-25).
- Session length: 20 minutes each.
- Environment: consent service UI at `/ui`, local or staging APIs connected.
- Moderator: 1 facilitator, 1 note taker.

## Scenarios
1. Activate Trust Pact for Staffer.
2. Launch one mission from Mission Board.
3. Find Proof Ledger evidence of action.
4. Use Kill Switch and explain expected outcome.

## Success Metrics
- Completion rate: >= 80% finish all four scenarios.
- Time to Trust Pact activation: <= 3 minutes median.
- Misunderstanding rate:
  - <= 20% users confuse Kill Switch effect.
  - <= 20% users fail to locate Proof Ledger.
- Confidence score (1-5): >= 4 average on "I understand what I approved."

## Interview Script (Concise)
- "What do you think this screen wants you to do first?"
- "What does Trust Pact mean in your own words?"
- "When does Staffer actually become active?"
- "Where would you check proof of what happened?"
- "If you wanted to stop everything now, what would you click?"

## Notes Template
- Participant ID:
- Scenario completion (Y/N):
- Time per scenario:
- Confusions observed:
- Quotes (verbatim):
- Severity (High/Medium/Low):
- Suggested fix:

## Iteration Rules
- If 2 or more users fail the same step, fix copy or layout before next round.
- Prioritize fixes in this order:
  1. Consent understanding
  2. Approval checkpoint clarity
  3. Kill Switch discoverability
  4. Proof Ledger visibility

## Exit Criteria For MVP Onboarding
- Two consecutive rounds hit all success metrics.
- No high-severity trust misunderstandings remain open.
