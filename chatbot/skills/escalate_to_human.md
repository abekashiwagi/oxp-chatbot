---
name: escalate_to_human
title: Hand the prospect off to the leasing team
for_intents: [PROPERTY_INFO, POLICIES, SPECIALS, TOUR_BOOKING, UNKNOWN]
capabilities_used: [escalate_to_human]
needs_property_id: false
needs_move_in_date: false
---

## When to use
- The prospect explicitly asks for a person: "transfer me to a
  human", "I want to speak with leasing".
- A required tool failed twice in a row.
- The question is out of agent scope (legal advice, personal
  finance, dispute resolution).
- The prospect needs to share sensitive info (SSN, full DOB, bank
  account) — this agent must not collect those.
- A tour booking hit a hard failure mid-flow.

## Tools, in order
Call ONE tool per turn:
1. Call `escalate_to_human` with a short plain-English reason
   ("tour booking failed", "out of scope question",
   "prospect requested").

## Arguments to fill
- `reason` — one short sentence, no internal ids. Describe what
  happened in human terms.

## What to ask the prospect
If they did not explicitly ask, confirm gently: "Want me to put
you in touch with the leasing team?" Wait for yes. If they
explicitly asked, escalate without re-asking.

## Property identity (best-effort, do NOT block on it)
This skill MUST work even when `<agent-context>/property/property_id`
is missing — that is often *why* the prospect is being escalated.
If a property is known, include its human-friendly name in the
`reason` string (e.g. "tour booking failed at <property name>").
If not, escalate anyway with whatever context you have; do NOT ask
the prospect for a property as a prerequisite to escalation.

## How to reply
After the tool call, emit a `route-handoff` fence with the team's
contact info and one sentence of apology / context. Keep the tone
warm — escalating is success, not failure.

## If the tool fails
Surface the office's public phone number from
`get_property_contact_details` (if available from a prior turn)
as a manual fallback so the prospect is not stranded.

## Do NOT
- Do NOT escalate proactively on the first tool-empty result —
  offer the canonical "I don't have that on file" fallback first
  and only escalate if the prospect insists.
- Do NOT promise a specific person or a specific callback time.
- Do NOT include internal ids in the `reason` string.
- Do NOT escalate to bypass a guardrail (blocked topic, security
  invariant) — those are refusals, not handoffs.
- Do NOT make parallel tool calls — one tool per turn, always.
