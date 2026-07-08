---
name: book_tour
title: Book a new property tour for the prospect
for_intents: [TOUR_BOOKING]
capabilities_used: [get_property_available_tour_types, check_tour_availability, register_lead, book_tour, update_applicant, search_leads, list_lead_activities, list_tours]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect asks to schedule / book / set up a tour, visit, viewing,
walkthrough, or appointment. Phrases: "I want to tour", "schedule a
tour", "book a viewing", "can I see the property", "guided tour",
"virtual tour", "self-guided tour".

## Preconditions & Core Constraints
* **Property ID:** Check `<agent-context>/property/property_id`. If absent, ask prospect once for the property name, then call `list_properties` with that name as your ONLY tool call. Never proceed with a placeholder or null `property_id`.
* **Execution Limit:** Make exactly **one tool call per turn**. Never execute parallel tool calls (e.g., never mix `search_leads`/`list_tours` with `schedule_tour` in a single turn).
* **Prose Restrictions:** Never expose internal IDs (`property_id`, `applicant_id`, `application_id`, `tour_id`, `customer_id`) or JSON fences (`tour-slots`, etc.) in chat prose. Use plain markdown.

## Identity Bootstrap (Pre-Write Flow)
Before executing any booking writes, resolve `applicant_id` and `application_id`. Evaluate sequentially and stop at the first matching condition:
1. **LTM Resolved:** If `lead_preferences/applicant_id` AND `application_id` are set, use directly. Advance directly to the ## Tools section, Skip to Step 1.
2. **Super-Agent Handoff:** If `lead_preferences/customer_id` is set, call `search_leads` with `{customer_id, property_id}`. On the subsequent turn, call `list_lead_activities` with the retrieved `application_id` and surface a one-line context recap ("we last spoke about...") before proceeding.
3. **Session-Volunteered Contact:** If `lead_preferences/prospect_email` OR `prospect_phone` is set, call `search_leads` with `{email/phone_number, property_id}`. Re-verify IDs similarly to condition 2.
4. **Fallback:** If context is completely empty or `search_leads` returns zero rows, proceed directly to the ## Tools section Step 1. Identity captures execute downstream in ## Tools section step 6 and ## Tools section step 7.

## Date resolution rules

Whatever date prospect provides convert it into ISO format future date. 
Past date or current date is not acceptable.

## Duplicate-tour gate (shared protocol)
When `list_tours {applicant_id, property_id, status: "scheduled"}`
returns non-empty `data`, STOP. Pick the soonest row. Emit BOTH the
fence and the prose in the SAME reply (fence first, prose second).
The fence carries ids into next turn's `reschedule_tour`; dropping it
is a confirmed failure mode.

Fence:
```prefs-update
{
  "fieldsToUpdate": ["pickedTourDate", "tourId", "applicantId",
                     "applicationId", "pickedTourType"],
  "leadPreferences": {
    "pickedTourDate": "<YYYY-MM-DD from Step 3>",
    "tourId": <existing tour id from list_tours row>,
    "applicantId": <resolved applicant_id>,
    "applicationId": <resolved application_id>,
    "pickedTourType": "<value from existing list_tours row>"
  }
}
```

Prose (one sentence, reschedule-only — never offer "or cancel"):
> You already have a **{Tour Type}** booked for **{Existing Date}**
> at **{Existing Time}**. Want me to move it to **{Step-3 Date}**?

End the turn. Next reply routes to `reschedule_tour`.

## Tools, in order — one tool per turn, never in parallel

### Step 1 — Discover the tour types this property offers
**You MUST call `get_property_available_tour_types` first.**

- If the tool returned rows (`data` is a non-empty array): render
  each row's `name` field as a markdown bullet list and ask which
  one the prospect wants. Quote only the human-readable `name`
  field — never expose the integer `id` or the snake_case `value`
  to the prospect.
- If the tool returned an empty `data` array call `escalate_to_human`.
  Prospect at {property name} requested a {tour type} — both 
  get_property_available_tour_types returned empty
- Do NOT loop either tool.

### Step 2 — Capture the prospect's pick
The prospect names a tour type from your bullet list. Match their
text against the row whose `name` matches (case-insensitive). Read
the `value` field from THAT row (e.g. `"self_guided_tour"`,
`"virtual_tour"`, `"tour"`).

### Step 3 — Ask for the desired tour date
Ask: "What date would you like to tour? So I can fetch slot for that date."
- Ask for the desired tour date. The date should be only future date.
  Current date is not acceptable. 

### Step 4 — Fetch available tour slots (HARD GATE)
**After capturing desired tour date always show time slots**
The moment a date is settled, call `get_tour_schedule_time_slots`
with `{property_id, start_date, end_date (= start_date), tour_type}`.
Never ask "what time" before this call — the slots list is the only
source of truth for which times exist; any time you name without it
is fabricated.

- Empty `slots` → "No openings on {date} — try another?" and go to Step 3.
- Non-empty `slots` → render every slot as a bullet list AND ask
  "Which time works for you?" in the same reply.
- After 3 consecutive empty-slot responses from get_tour_schedule_time_slots, 
  use `escalate_to_human` to escalatation.

### Step 5 — Capture the prospect's slot pick
Match the prospect's reply with tour slots and map `start_time` and
`end_time`. User may give only start time, map that with with tour slots
Hold `{start_time: "HH:MM, end_time: "HH:MM}`.

### Step 5.5 — Check for an existing scheduled tour at this property
Only run this step when `<agent-context>/lead_preferences/applicant_id`
is set (i.e., the identity-bootstrap preamble or a prior turn already
resolved the lead). Skip when `applicant_id` is missing — first-time
prospects cannot have a duplicate tour to collide with, and Step 6.5
will run the same gate after `search_leads` resolves the lead.

Call `list_tours` with `{applicant_id, property_id, status: "scheduled"}`.

- Empty `data` → continue to Step 6.
- Non-empty `data` → STOP. Do NOT call `capture_lead` /
  `schedule_tour`.

  Then the prose offer, in one sentence (identical wording to
  Step 6.5 — never split into "reschedule it OR cancel it"
  options; the prospect just told you they want a tour, so the
  helpful default is to MOVE the existing one to the date /
  time they just picked):
  > You already have a **{Tour Type}** booked for **{Existing
  > Date}** at **{Existing Time}**. Want me to move it to
  > **{Step-3 Date}**?

  End the turn. The next prospect reply ("yes please") routes
  into `reschedule_tour` with `picked_tour_date`, `tour_id`,
  `picked_tour_type`, `applicant_id`, and `application_id` all
  in agent-context — `reschedule_tour` Step 2 short-circuits
  because `picked_tour_date` is set, and Step 3 reads the
  identifiers directly (never re-resolved from email/phone,
  never hallucinated).

### Step 6 — Ask for first name, last name, phone, AND email for lead creation
**Skip what you already have.** Before asking for any field, check
`<agent-context>/lead_preferences/`:

- If `prospect_first_name`, `prospect_last_name`, `prospect_email`,
  AND `prospect_phone` are ALL set, skip Step 6, 6.5, 7. 
  The session-state extractor already stamped them from
  an earlier `capture_lead` ToolMessage — the guest card is in
  scope. Pull `application_id` and `applicant_id` from the same
  context block and jump straight to Step 8.

### Step 6.5 — Confirm whether this prospect already has a lead at this property
Call `search_leads` with:
- `property_id` — `<agent-context>/lead_preferences/property_id`
- `email` — `<agent-context>/lead_preferences/prospect_email`
- `phone_number` — `<agent-context>/lead_preferences/prospect_phone`

Branch by result:

**Empty `data` → no lead on file.** Continue to Step 7
(`capture_lead`) as written today.

**1+ rows → lead exists.** Pick the most-recently-updated row.
Read its `applicant_id` and `application_id`. Do NOT call
`capture_lead` — the row already exists, the prospect did not
change identifying fields, and a re-POST would just echo back the
same row with `is_existing=true` and waste a round-trip. Run the
duplicate-tour check now:

Call `list_tours` with `{applicant_id, property_id, status: "scheduled"}`.

- Empty `data` → jump to Step 8.
- Non-empty `data` → STOP. Do NOT call `schedule_tour`.

  Then the prose offer, in one sentence (never split into "reschedule it 
  OR cancel it"
  options; the prospect just told you they want a tour, so the
  helpful default is to MOVE the existing one to the date /
  time they just picked):
  > You already have a **{Tour Type}** booked for **{Existing
  > Date}** at **{Existing Time}**. Want me to move it to
  > **{Step-3 Date}**?

  End the turn. The next prospect reply ("yes please") routes
  into `reschedule_tour` with `picked_tour_date`, `tour_id`,
  `picked_tour_type`, `applicant_id`, and `application_id` all
  in agent-context — `reschedule_tour` Step 2 short-circuits
  because `picked_tour_date` is set, and Step 3 reads the
  identifiers directly (never re-resolved from email/phone,
  never hallucinated).

### Step 7 — Create the guest card
**Skip this step when Step 6.5 already resolved the lead.**

Call `capture_lead` with:
- `property_id` — from agent-context
- `primary_applicant` — `{first_name, last_name, email, phone}`
  taken VERBATIM from Step 6 (digits-only phone, no spaces /
  hyphens / leading `+`)
- `company_user_id` — runtime constant `11` (do not ask the
  prospect)

Read the response:
- `application_id` — from `data.guest_card.id`
- `applicant_id` — from `data.primary_applicant.id` (preferred) or
  `data.guest_card.primary_applicant_id` (fallback)
- If both are null then call `search_lead` with `email` 
  provided by prospect.

`data.guest_card.is_existing` == `true`, proceed to step 7.5
else proceed to step 8

### Step 7.5 — Reconcile the applicant name (only when `is_existing=true`)

**Skip this step if `data.guest_card.is_existing` is `false`** — a fresh guest card already has the right name from Step 7.

Otherwise, compare returned `first_name` / `last_name` vs what you sent (**case-insensitive, stripped**). If both match → skip to Step 8.

If either differs → call `update_applicant` **ONCE** with `{applicant_id, company_user_id: 11, changes: {first_name, last_name}}` — `applicant_id` = **`data.primary_applicant.id` from Step 7**. (Why: `createGuestCard` doesn't overwrite name on existing rows.)

On any failure (422 ApplicantContactConflict or other) → **do NOT retry**; proceed to Step 8 with the stale name and add "booked under the name on file — let me know if that needs to change" to the confirmation. **Never block the booking on a name-reconcile failure.**


### Step 8 — Schedule the tour

**Call `schedule_tour` immediately after `capture_lead` succeeds — never re-ask the prospect** ("shall I proceed?" / "please confirm" is the loop trap). If every arg is in transcript → call now; if one is missing → ask **only** for that field.

Call `schedule_tour` with: `{application_id, applicant_id, property_id, tour_type, tour_date, time_slot: {start_time, end_time}, initiated_by: {product: "prospect_portal", product_id: 2, company_user_id: 11}}`.

Sources: `application_id` / `applicant_id` from Step 6.5 `search_leads` row (**existing lead, no active tour**) OR Step 7 `capture_lead` response (**new lead**). `property_id` from agent-context. `tour_type` = **`value`** from Step 2. `tour_date` = **YYYY-MM-DD** from Step 3. `time_slot` from Step 5. `initiated_by` is a runtime constant — **do not ask the prospect**.

On success → reply with plain markdown using **`name` from Step 1** as the tour type label, plus human date / time range:

> Your **{Tour Type Name}** is booked for **{Date}** at **{Time}**.
> Confirmation on its way to **{email}**. Anything else I can help
> with?

**No JSON fences. No internal ids in prose.** The session-state extractor auto-stamps `tour_id`, `picked_tour_type`, `picked_tour_date`, and `picked_tour_time_slot` from the `schedule_tour` ToolMessage — next turn's `reschedule_tour` / `cancel_tour` will see all four in `<agent-context>/lead_preferences/`.

If `schedule_tour` returns `_active_tour_exists` error → read `tour_id=<digits>` from `error.got`. Emit **§Duplicate-tour gate** fence with that `tour_id`, then offer the reschedule prose. **End turn.**