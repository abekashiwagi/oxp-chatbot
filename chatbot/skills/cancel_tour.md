---
name: cancel_tour
title: Cancel an existing tour with explicit prospect confirmation
for_intents: [TOUR_BOOKING]
capabilities_used: [list_tours, cancel_tour, find_applicant, search_leads, list_lead_activities]
needs_property_id: true
needs_move_in_date: false
---

## When to use
"Cancel my tour", "I want to cancel my appointment", "drop the
Saturday tour", "I can't come anymore", "I need to cancel".

If the prospect says "reschedule" or "move my tour", that is the
`reschedule_tour` skill — do NOT cancel-then-rebook.

## Property identity precondition (always first)
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent, ask the prospect once which property the tour is at.
  On their reply call `list_properties` as your ONLY tool call this
  turn. Never call `cancel_tour` with a placeholder, null, or empty
  `property_id`.

## Identity bootstrap (always before `list_tours`)
A cancel needs `applicant_id` to scope `list_tours`. Resolve it in
this order, stopping at the first source that yields it. Note the
origin of each field — `customer_id` is ONLY ever pushed by the
super-agent on the invocation contract; `prospect_email` /
`prospect_phone` are ONLY ever volunteered by the prospect and
captured into LTM by `capture_lead` + the session-state extractor.
The agent NEVER asks the super-agent for email/phone and NEVER reads
email/phone off the invocation contract for identity bootstrap.

1. `<agent-context>/lead_preferences/applicant_id` is set — use
   directly. Skip to Step 1 below.
2. `<agent-context>/lead_preferences/customer_id` is set
   (super-agent handoff path — this is the ONLY identity field the
   super-agent ever pushes) — call `search_leads` with
   `{customer_id, property_id}`. Read the matched row's
   `applicant_id` + `application_id`. On the next turn, call
   `list_lead_activities` with that `application_id` and surface a
   one-line "we last spoke about <topic> on <date>" recap before
   continuing the cancel. NEVER expose `customer_id` /
   `applicant_id` / `application_id` in prose.
3. `<agent-context>/lead_preferences/prospect_email` OR
   `<agent-context>/lead_preferences/prospect_phone` is set
   (prospect-volunteered earlier in this session) — call
   `search_leads` with `{email, property_id}` (or `phone_number`
   for the phone path). Same resolution as step 2.
4. Nothing on file — ask the prospect exactly once:
   > To find your tour I need to look up your profile — what's the
   > email or phone number you used when you scheduled it?
   On the prospect's reply, the session-state extractor stamps
   `prospect_email` / `prospect_phone` into LTM. On the NEXT turn
   bootstrap step 3 fires and `search_leads` resolves the lead.

If `search_leads` (steps 2 or 3) returns ZERO rows, reply "I don't
see a tour scheduled under that profile." End the turn. Do NOT call
`cancel_tour` with a guessed id. Do NOT offer to book — the
prospect asked to cancel, not to start over; let them re-ask.

## Tools, in order — one tool per turn, never in parallel

### Step 1 — Resolve the tour to cancel
The identity-bootstrap preamble (above) yielded `applicant_id`.
Look at `<agent-context>/lead_preferences/`:
- If `tour_id` + `application_id` are both present AND the
  prospect's reference matches the stamped `picked_tour_type` /
  `picked_tour_date` ("cancel my Friday tour" against
  `picked_tour_date=2026-06-12`), skip to Step 2 with the held ids.
- Otherwise call `list_tours` with
  `{applicant_id, property_id, status: "scheduled"}`. Branch by
  result:

  - Empty `data` → reply "I don't see a tour scheduled under that
    profile." End the turn. Do NOT call `cancel_tour` with a
    guessed id. Do NOT offer to book — the prospect asked to
    cancel, not to start over; let them re-ask if they want to
    book.
  - One or more rows → match the prospect's reference (date /
    time / tour type) against a row. If ambiguous, ask once to
    disambiguate, then continue with the matched row. Hold the
    row's `id` (→ `tour_id`), `application_id`, `tour_type`, and
    `scheduling_mode`.

### Step 2 — Confirm in prose (HARD GATE)
**You MUST get an explicit "yes" from the prospect before calling
`cancel_tour`. This is destructive and cannot be undone.** Ask:

> Just to confirm — cancel your **{Tour Type Name}** on
> **{Date}** at **{Time}**?

Wait for the prospect's next message. Accept only an explicit
affirmative ("yes", "confirm", "cancel it", "go ahead", "do it",
"proceed"). On anything else — "hold on", "wait", "actually let me
reschedule instead", silence, or any non-affirmative — do NOT call
`cancel_tour`. If they pivot to "reschedule instead" or "change to
a different day", end this skill and let the next turn route to
`reschedule_tour`.

After the prospect's explicit "yes", generate a `confirmation_token`
for the audit log: the literal string
`"prospect-{YYYY-MM-DD}-{tour_id}"` using today's date and the
resolved `tour_id`. Hold it for Step 3.

### Step 3 — Cancel
Call `cancel_tour` with:
- `tour_id` — from Step 1
- `application_id` — from Step 1
- `property_id` — from agent-context
- `tour_type` — from Step 1 (closed enum: `self_guided_tour` |
  `virtual_tour` | `tour`)
- `scheduling_mode` — from Step 1 (defaults to `"scheduled"` if
  the `list_tours` row didn't carry it)
- `initiated_by` — `{"company_user_id": 11}` ONLY. The cancel
  audit shape is NARROWER than the schedule one — no `product` /
  `product_id` keys.
- `confirmation_token` — the string from Step 2

Do NOT pass `calendar_event_category_id` — the May 2026 spec
migration dropped it (server-derived from `tour_type` now). The
MCP will reject the call with a teaching `ValidationFailure`
envelope if you include it.

On success (response carries `data.status == "cancelled"`), reply
in one prose sentence:

> Cancelled — your **{Tour Type Name}** on **{Date}** at **{Time}**
> is off the books. Let me know if you want to rebook.

The session-state extractor sees the successful `cancel_tour`
ToolMessage and clears `tour_id` / `picked_tour_date` /
`picked_tour_time_slot` from `<agent-context>` for the next turn.
The prospect's identity (name, email, phone, `applicant_id`,
`application_id`) survives — they're still the same lead.

## Arguments to fill
- `property_id` — `<agent-context>/property/property_id`. Never
  accept a number from the prospect's text; resolve via
  `list_properties` if missing.
- `tour_id` / `application_id` / `tour_type` / `scheduling_mode` —
  from `<agent-context>/lead_preferences/` first; fall back to the
  `list_tours` row in Step 1. Never guess.
- `initiated_by` — `{"company_user_id": 11}` (no `product` /
  `product_id` — cancel audit shape is narrower than schedule).
- `confirmation_token` — generated in Step 2 as
  `"prospect-{YYYY-MM-DD}-{tour_id}"` ONLY after the prospect
  explicitly confirmed in prose. Never call `cancel_tour` with a
  placeholder or empty token.

## If a step fails
- `list_tours` returns zero rows → "I don't see a tour scheduled
  under that profile." End the turn. Do NOT call `cancel_tour`.
  Do NOT auto-offer to book — let the prospect re-ask if they
  want to start over.
- `search_leads` empty (identity bootstrap step 2 or 3) → see the
  identity-bootstrap section's terminal branch — same "I don't
  see a tour scheduled" exit.
- `cancel_tour` returns 409 `TourStateConflictException` (tour
  already terminal — cancelled / completed / missed) → "Looks like
  that tour was already cancelled." End the turn.
- 404 `TourNotFoundException` → re-run `list_tours` once to resync.
  If still mismatched, route to `escalate_to_human`.
- Any other error → route to `escalate_to_human`.

## Do NOT
- Do NOT call `cancel_tour` without an explicit prospect "yes" in
  the immediately-prior turn. The Step 2 confirmation gate is the
  only safety belt against an accidental destructive write.
- Do NOT cancel a tour the prospect asked to RESCHEDULE — route
  to `reschedule_tour` instead. Cancel-then-rebook is forbidden.
- Do NOT pass `calendar_event_category_id` — the May 2026 spec
  dropped it. The MCP wrapper will reject the call with a
  teaching `ValidationFailure` envelope and the cancel will fail.
- Do NOT include `tour_id` / `application_id` in the prose. Refer
  to tours by human date + time + type.
- Do NOT emit JSON fences. Plain markdown only.
- Do NOT call `get_property_contact_details` with the prospect's
  own email / phone — those are theirs, not the property's.
- Do NOT make parallel tool calls — one tool per turn, always.
  Even when the first call returns a validation error, do NOT
  retry in the same turn with corrected args — read the error,
  end the turn, and retry on the NEXT turn.
