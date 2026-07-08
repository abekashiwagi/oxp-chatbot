---
name: reschedule_tour
title: Move an existing tour to a new slot atomically
for_intents: [TOUR_BOOKING]
capabilities_used: [list_tours, check_tour_availability, reschedule_tour, find_applicant, search_leads, list_lead_activities]
needs_property_id: true
needs_move_in_date: false
---

## When to use
"Move my tour", "reschedule my appointment", "change my tour time",
"can we push my tour to Friday", "I can't make Saturday".

## Property identity precondition (always first)
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent, ask the prospect once which property the tour is at.
  On their reply call `list_properties` as your ONLY tool call this
  turn. Never call a tour tool with a placeholder, null, or empty
  `property_id` — that loops on validation errors.

## Identity bootstrap (always before `list_tours`)
A reschedule needs `applicant_id` to scope `list_tours`. Resolve it
in this order, stopping at the first source that yields it. Note
the origin of each field — `customer_id` is ONLY ever pushed by the
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
   continuing the reschedule. NEVER expose `customer_id` /
   `applicant_id` / `application_id` in prose.
3. `<agent-context>/lead_preferences/prospect_email` OR
   `<agent-context>/lead_preferences/prospect_phone` is set
   (prospect-volunteered earlier in this session) — call
   `search_leads` with `{email, property_id}` (or `phone_number`
   for the phone path). Same resolution as step 2.
4. Nothing on file — ask the prospect exactly once:
   > To pull up your tour I need to find your profile — what's the
   > email or phone number you used when you scheduled it?
   On the prospect's reply, the session-state extractor stamps
   `prospect_email` / `prospect_phone` into LTM. On the NEXT turn
   bootstrap step 3 fires and `search_leads` resolves the lead.

If `search_leads` (steps 2 or 3) returns ZERO rows, reply "I don't
see a tour on file at this property — want to book one?" and end
the turn. Do NOT call `reschedule_tour` with a guessed id. The
prospect's next message routes into `book_tour`.

## Tools, in order — one tool per turn, never in parallel

### Step 1 — Resolve the existing tour
The identity-bootstrap preamble (above) yielded `applicant_id`.
Look at `<agent-context>/lead_preferences/`:
- `tour_id`, `application_id`, `applicant_id`, `picked_tour_type` —
  if ALL FOUR are present, skip directly to Step 2 (the booking
  from earlier in this session is already in scope).
- Otherwise call `list_tours` with
  `{applicant_id, property_id, status: "scheduled"}`. Branch by
  result:

  - Empty `data` → reply "I don't see a tour on file at this
    property — want to book one?" End the turn. The prospect's
    next message routes into `book_tour`. Do NOT call
    `reschedule_tour` with a guessed id.
  - One row → carry the row's `id` (→ `tour_id`),
    `application_id`, `applicant_id`, `tour_type`, and
    `scheduling_mode` forward to Step 2.
  - Multiple rows → ask the prospect which one ("you have tours
    on May 24 and June 12 — which should I move?"). Match their
    next reply to the row by date/time.

### Step 2 — Ask for the new date (or skip when it's already in scope)
**Short-circuit:** look at
`<agent-context>/lead_preferences/picked_tour_date`. If it is set
AND strictly later than today, the prospect already named the
target date on the previous turn — typically via the
`book_tour` Step 6.5 duplicate-tour handoff, which seeds
`pickedTourDate` into LTM as part of its `prefs-update` fence.
Carry that date forward as the new date; do NOT re-ask the
prospect. Reply with one prose sentence that names the date so
the prospect can correct if needed:

> Got it — moving your tour to **{picked_tour_date in human
> form}**. Let me pull up open slots.

Then proceed straight to Step 3 with `start_date` = `end_date` =
`picked_tour_date`.

**Otherwise** (no `picked_tour_date` in agent-context, or it is
stale / past), ask the prospect for the new date with the
original question:

Ask: "What date would you like to move it to?"
- Accept any date format ("next Friday", "June 24", "10/24").
  Interpret it yourself; do NOT ask the prospect to confirm the
  format.
- **Resolve the date string into an ISO date** the same way
  `book_tour` Step 3 does: bare day-month inputs ("25 Oct",
  "Oct 25", "25/10") resolve to the NEXT FUTURE occurrence —
  current year if the day-month is still ahead, next year if
  it has already passed. Relative phrases resolve from
  ``today_iso``. Full-date-with-year is used as written.
- **The RESOLVED date MUST be strictly later than ``today_iso``
  (today + 1 or later).** Same-day reschedules are blocked at
  three layers (MCP `_same_day_guard`, agent post-processor,
  this skill). "Today" is the date anchored at the top of the
  system prompt. Interpret relative phrases — "today", "right
  now", "this afternoon", "in an hour", "ASAP" — as same-day
  requests and refuse them.
- When the RESOLVED date is same-day or past, do NOT call
  `get_tour_schedule_time_slots` and do NOT call
  `reschedule_tour`. Reply with the canonical line and loop
  back for a future date (wording matches the MCP guard's
  `fix` string so prompt + guardrail speak with one voice):
  > Same-day tours aren't available — the earliest I can move
  > it to is tomorrow. What other date works for you?
- **The same-day refusal fires ONLY on a RESOLVED date that is
  ≤ ``today_iso``.** Future dates — including bare day-month
  inputs that resolve months ahead — are NOT same-day. Refusing
  them with the canonical line is a real-user-visible bug.
  When in doubt about the year, prefer the future
  interpretation and let `get_tour_schedule_time_slots`
  validate.

### Step 3 — Fetch slots for the new date
**You MUST call `get_tour_schedule_time_slots` now, before saying
anything else.** Never claim "that works" or "that's available"
before the slot grid from THIS tool is in the transcript.

Tool disambiguation — the only correct slot-discovery tool is
`get_tour_schedule_time_slots`. Do NOT substitute:

- `get_tour` — retrieves an already-scheduled tour by event id.
- `list_tours` — already used in Step 1 to find the existing tour.
- `get_property_hours` — office hours, not bookable tour slots.

Call `get_tour_schedule_time_slots` with:
- `property_id` — from agent-context
- `start_date` — the prospect's new date in YYYY-MM-DD
- `end_date` — same as `start_date` (single-day window)
- `tour_type` — the existing tour's type from Step 1 (the
  `picked_tour_type` from agent-context or the `tour_type` from
  the `list_tours` row)

If the response's `data.dates` is empty or that date's `slots` list
is empty, reply "No slots open on that date — want to try a
different day?" and loop back to Step 2.

If slots are available, render each slot as a markdown bullet in
human-friendly form (`10:00 AM – 10:30 AM`). Ask which slot they
want.

### Step 4 — Reschedule atomically
**You MUST call `reschedule_tour` immediately after the prospect
picks a slot.** Never sequence `cancel_tour` + `schedule_tour` for a
reschedule — the upstream is atomic and a manual cancel-then-rebook
leaves an orphaned cancellation if the rebook step fails.

Match the prospect's slot reply against the rendered list. Read the
matching row's `start_time` / `end_time` from the
`get_tour_schedule_time_slots` response (NEVER round, shift, or
invent times).

Call `reschedule_tour` with:
- `tour_id` — from Step 1
- `application_id` — from Step 1
- `applicant_id` — from Step 1
- `property_id` — from agent-context
- `tour_type` — from Step 1 (do NOT change the type during a
  reschedule; if the prospect wants a different type, route them
  to cancel-then-book instead)
- `tour_date` — the YYYY-MM-DD from Step 2
- `time_slot` — `{"start_time": "HH:MM", "end_time": "HH:MM"}`
  from Step 3
- `initiated_by` — runtime constant
  `{"product": "prospect_portal", "product_id": 2, "company_user_id": 11}`
  (do not ask the prospect)

On success, reply in plain markdown:

> Your **{Tour Type Name}** is now on **{New Date}** at **{New Time}**.
> See you then.

Use the human-friendly tour type label (from
`picked_tour_type` or from the `list_tours` row's `tour_type`
field — never expose snake_case enum tokens to the prospect), the
human date, and the human time range. The session-state extractor
re-stamps `picked_tour_date` / `picked_tour_time_slot` from the
`reschedule_tour` ToolMessage automatically.

## Arguments to fill
The argument values for each tool come from the step that produced
them; never invent them.

- `property_id` — `<agent-context>/property/property_id` (resolved
  in the precondition above).
- `tour_id` / `application_id` / `applicant_id` — read from
  `<agent-context>/lead_preferences/` first; fall back to the
  `list_tours` row in Step 1. Never guess; never accept a number
  the prospect typed.
  **CRITICAL — three different integers:** `tour_id`,
  `application_id`, and `applicant_id` are THREE DIFFERENT
  integers that live on three different upstream rows. They are
  NOT interchangeable. Source rules, in order of precedence:
  - `tour_id` = `data.id` from `schedule_tour` / `reschedule_tour`,
    OR `data[*].id` from `list_tours`, OR LTM `tourId`. NEVER
    `data.guest_card.id`, NEVER `application_id`.
  - `application_id` = `data.guest_card.id` from `capture_lead`,
    OR `data[*].id` from `search_leads`, OR LTM `applicationId`.
    NEVER the value after `tour_id=` in any envelope.
  - `applicant_id` = `data.primary_applicant.id` from
    `capture_lead`, OR `applicants[0].applicant_id` from
    `search_leads`, OR LTM `applicantId`. NEVER `data.id`.
  If the three ids would all be the same number on this call,
  STOP — that is the live-fire id-confusion bug, not a real
  state. Re-derive each id from its proper source row before
  retrying.
- `tour_type` — the existing tour's type (carried via
  `picked_tour_type` or read off the Step 1 row). Closed enum:
  `self_guided_tour` | `virtual_tour` | `tour`.
- `start_date` / `end_date` — the prospect's new date from Step 2
  in `YYYY-MM-DD`. Single-day window; both fields are the same.
- `time_slot` — `{"start_time": "HH:MM", "end_time": "HH:MM"}`
  taken VERBATIM from the row picked in Step 3 of
  `get_tour_schedule_time_slots`. Never round, shift, or invent
  times.
- `initiated_by` — runtime constant
  `{"product": "prospect_portal", "product_id": 2, "company_user_id": 11}`.

## If a step fails
- `list_tours` empty (AND no `tour_id` in `<agent-context>`) →
  "I don't see a tour on file at this property — want to book
  one?" End the turn; the prospect's next message routes into
  `book_tour`.
- `search_leads` empty (identity bootstrap step 2 or 3) → see the
  identity-bootstrap section's terminal branch — same "want to
  book one?" exit.
- `get_tour_schedule_time_slots` returns an empty `data.dates` /
  empty `slots` list → loop back to Step 2 with "no slots on that
  date — try another?".
- `reschedule_tour` returns 409 `TourStateConflictException` (tour
  already cancelled / completed) → "Looks like that tour was
  already changed — want me to book a fresh one?" Route to
  `book_tour`.
- `reschedule_tour` returns
  `{"error": {"type": "ValidationError", "field": "tour_id",
  "got": "tour_id=<passed_id> (not found; the prospect's only
  active tour is tour_id=<correct_id>)", "fix": "..."}}` → this
  is the server-side tour-id reconcile. It fires when the
  `tour_id` you passed does not match any active tour on file
  for `(applicant_id, property_id)` — almost always because the
  LLM substituted `application_id` (or another in-scope integer)
  for `tour_id`. Read the correct `<correct_id>` from `error.got`
  / `error.fix`, emit a `prefs-update` fence with `{"tourId":
  <correct_id>}`, and retry `reschedule_tour` once with the
  corrected `tour_id` and the same date / slot / type. Do NOT
  apologize in prose — the prospect is unaware of the id
  confusion. When `error.got` lists multiple candidates
  ("active candidates: tour_id=A on ...; tour_id=B on ..."),
  the prospect has more than one active tour at this property;
  pick the candidate matching the conversation context or ask
  the prospect to disambiguate.
- 404 `TourNotFoundException` → re-run `list_tours` once to resync,
  then route to `escalate_to_human` if still mismatched.
- Any other error → route to `escalate_to_human`.

## Do NOT
- NEVER cancel-then-rebook to reschedule — `reschedule_tour` is
  atomic. A manual cancel + schedule_tour leaves an orphaned
  cancellation if the rebook fails.
- Do NOT re-ask for the new date when
  `<agent-context>/lead_preferences/picked_tour_date` is already
  set AND strictly later than today. That field was stamped
  either by an earlier `book_tour` Step 6.5 duplicate-tour
  handoff or by a prior reschedule the session-state extractor
  recorded; re-asking the prospect for a date they already gave
  is a UX regression and a loop trap. Acknowledge the date in
  one prose sentence and proceed straight to Step 3.
- Do NOT change `tour_type` during a reschedule — that's a cancel +
  new booking, not a reschedule.
- Do NOT include `tour_id` / `application_id` / `applicant_id` in
  the reply prose. Refer to tours by human date + time + type.
- Do NOT substitute `application_id` (or `applicant_id`, or any
  other in-scope integer) for `tour_id` on the call args.
  `tour_id` is a separate integer; sourcing it from any field
  other than the three listed in the Arguments section is a bug.
  The MCP rejects mismatches with a teaching envelope naming the
  correct id (see "reschedule_tour returns ... field=tour_id"
  above) — treat that as a hard signal you read the wrong field,
  not as a generic upstream failure.
- Do NOT emit JSON fences. Plain markdown only — the UI no longer
  renders cards.
- Do NOT call `get_property_hours` for "what slots are open" —
  office hours and bookable slots are not the same thing.
- Do NOT call `get_property_contact_details` with the prospect's
  own email / phone — those are theirs, not the property's.
- Do NOT make parallel tool calls — one tool per turn, always.
- Do NOT call `list_tours` with a guessed `applicant_id`.
  `applicant_id` is read ONLY from:
  (a) `<agent-context>/lead_preferences/applicant_id` (stamped
  by an earlier `book_tour` Step 5.5 / Step 6.5 fence, or by
  the session-state extractor from a prior `capture_lead`), OR
  (b) the most-recent `search_leads` row resolved THIS TURN by
  email or phone.
  If neither source has it, run `search_leads` first with the
  prospect's email or digits-only phone — never invent a
  numeric id. Live-fire failure mode: a guessed `applicant_id`
  returns `list_tours` rows for a completely different
  applicant (different `application_id`, different tour type,
  different date), and the LLM then fabricates the matching
  prose ("Virtual Tour on Aug 21 at 12:30") to cover the
  context gap. The downstream `reschedule_tour` either fails
  validation or rewrites the wrong tour.
- Do NOT fabricate the existing tour's date / type / time in
  prose when the underlying `list_tours` row says otherwise.
  If `list_tours` returns a row dated `2026-05-09` at `08:00`,
  the prose MUST say `May 9 at 08:00 AM`, not the date the
  prospect just typed. The fence values and prose values come
  from the SAME row.
- Do NOT call `get_tour_schedule_time_slots` or
  `reschedule_tour` with `tour_date == today` (the date anchored
  at the top of the system prompt). The earliest legal new
  date for a reschedule is tomorrow (today + 1). Calls with
  today's date trip the MCP `_same_day_guard` and waste a
  round-trip; the prospect-facing recovery is the canonical
  line — "Same-day tours aren't available — the earliest I can
  move it to is tomorrow." — followed by a re-ask for a future
  date. Same rule applies when the prospect asks for "today /
  right now / this afternoon / in an hour / ASAP" — interpret
  all of those as same-day and redirect; never silently snap
  them to tomorrow without telling the prospect.
- Do NOT fire the same-day refusal on a date that resolves
  into the FUTURE. Bare day-month inputs like "25 Oct" resolve
  to the NEXT future occurrence — they are NOT same-day.
  Refusing them with the canonical line is a real-user-visible
  bug. The same-day refusal is reserved for resolved dates
  that are `<= today`.
