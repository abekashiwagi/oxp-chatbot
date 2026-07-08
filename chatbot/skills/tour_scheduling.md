---
name: tour_scheduling
title: End-to-end tour scheduling — book, reschedule, or cancel with full lifecycle awareness
for_intents: [TOUR_BOOKING, TOUR_RESCHEDULE, TOUR_CANCEL, TOUR_INQUIRY]
capabilities_used: [get_property_available_tour_types, get_tour_schedule_time_slots, schedule_tour, reschedule_tour, cancel_tour, list_tours, search_leads, capture_lead, list_lead_activities, update_applicant]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect wants to schedule, reschedule, cancel, or ask about a tour. Phrases:
"I want to tour", "book a viewing", "schedule a visit", "guided tour", "self-guided
tour", "virtual tour", "move my tour", "reschedule my appointment", "cancel my tour",
"what tours do I have", "can I see the unit".

Also triggers when ELI+ proactively surfaces available tour slots during an
introductory conversation. Proactive suggestions MUST be drawn from real availability
returned by `get_tour_schedule_time_slots` — never fabricated.

## Preconditions & Core Constraints
* **Property ID:** Check `<agent-context>/property/property_id`. If absent, ask once
  for the property name, then call `list_properties`. Never proceed with a null or
  placeholder `property_id`.
* **One tool per turn:** Never execute parallel tool calls. One tool call, then reply,
  then wait for the prospect's next message.
* **Prose restrictions:** Never expose internal IDs (`property_id`, `applicant_id`,
  `application_id`, `tour_id`, `customer_id`) in chat prose. Human-friendly dates,
  times, and tour type names only.
* **Same-day tours:** Only offer same-day availability when the property's Same-Day
  Tour toggle is enabled AND the requested slot falls outside the configured Lead Time
  window. When the toggle is disabled, only present slots starting the next day.

## Identity Bootstrap (always before any write)
Resolve `applicant_id` and `application_id` sequentially. Stop at the first match:

1. **LTM resolved:** `lead_preferences/applicant_id` AND `application_id` both set →
   use directly. Skip to the relevant step in ## Tools.
2. **Super-agent handoff:** `lead_preferences/customer_id` is set → call `search_leads`
   with `{customer_id, property_id}`. Next turn, call `list_lead_activities` with
   the retrieved `application_id` and surface a one-line "we last spoke about…" recap.
   NEVER expose `customer_id` / `applicant_id` / `application_id` in prose.
3. **Session-volunteered contact:** `lead_preferences/prospect_email` OR
   `prospect_phone` is set → call `search_leads` with `{email/phone_number,
   property_id}`. Resolve IDs the same way as step 2.
4. **Fallback:** Context is empty or `search_leads` returns zero rows → proceed
   directly to the ## Booking Flow, Step 1. Identity captures happen downstream in
   Steps 6 and 7.

## Tour History Awareness
Before presenting availability, check whether a prior tour context exists in
`<agent-context>/lead_preferences/`:

- `tour_id`, `picked_tour_date`, `picked_tour_type` are set → the prospect has an
  active or recently-referenced tour. Do NOT proactively offer a new slot — ask
  whether they want to reschedule, cancel, or book an additional tour instead.
- Completed tours (status ≠ `scheduled`) → if a tour results report is available,
  use it to personalize the conversation (interests, unit preferences, prior outcome)
  without surfacing internal data.
- Prospects who have completed a prior tour remain fully eligible for new tour
  scheduling. Do NOT treat them as post-tour nurture only. Support additional tours
  when requested.

## Multiple Tour Handling
When the prospect references "a tour" and `list_tours` returns results:

- **One row:** Present the tour details (type, date, time), then ask whether they want
  to reschedule it.
- **Multiple rows:** List each tour (type + date + time), ask which one they mean.
  After changes, ask whether the other tour(s) should remain as scheduled.

ELI+ must NOT proactively schedule multiple upcoming tours for the same prospect.

---

## Booking Flow — one tool per turn, never in parallel

### Step 1 — Discover available tour types
**Always call `get_property_available_tour_types` first.**

- Non-empty `data`: render each row's `name` field as a markdown bullet list. Ask
  which tour type the prospect wants. NEVER expose the integer `id` or the
  snake_case `value`.
- If the PM has configured a preferred tour type (property setting), recommend it
  first while still listing all eligible options.
- Empty `data`: call `escalate_to_human`. Message: "Prospect at {property name}
  requested a tour — `get_property_available_tour_types` returned empty."
- Do NOT loop the tool.

**Tour type reference:**
| Human label | `value` enum |
|---|---|
| Guided Tour | `tour` |
| Self-Guided Tour | `self_guided_tour` |
| Virtual Tour | `virtual_tour` |

**Virtual Tour path:** If the prospect picks Virtual Tour, provide the property's
configured virtual tour link. Do NOT walk through the availability/slot steps — there
is no calendar slot to book. Confirm the link has been sent and end the flow.

### Step 2 — Capture the prospect's tour type pick
Match their reply (case-insensitive) against the `name` column. Read the `value`
field from that row (e.g. `"self_guided_tour"`). Hold for Step 4.

### Step 3 — Ask for the desired tour date
"What date would you like to tour? I'll pull up available slots for that day."

- Only future dates are acceptable. Same-day is blocked unless the Same-Day Tour
  toggle is enabled (see Step 4 guard below).
- Convert any natural-language input ("next Friday", "June 24") to ISO
  `YYYY-MM-DD` yourself. Do NOT ask the prospect to reformat.

### Step 4 — Fetch available tour slots (HARD GATE)
The moment a date is settled, call `get_tour_schedule_time_slots` with
`{property_id, start_date, end_date (= start_date), tour_type}`.

**Same-Day Guard:**
- If the resolved date == today AND the property's Same-Day Tour toggle is disabled:
  reply "Same-day tours aren't available at this property — the earliest I can book
  is tomorrow. What other date works?" and loop back to Step 3.
- If the toggle IS enabled, pass only the slots that clear the property's configured
  Lead Time (e.g., if Lead Time = 2 hours and it's 10:00 AM, only slots ≥ 12:00 PM).
  The API enforces this; do not fabricate the filtered list yourself.

**Slot presentation:**
- Empty `slots`: "No openings on {date} — want to try another?" → loop to Step 3.
- Non-empty `slots`: render every slot as a markdown bullet (`10:00 AM – 10:30 AM`)
  and ask "Which time works for you?" in the same reply.
- After 3 consecutive empty-slot responses, call `escalate_to_human`.

### Step 5 — Capture the prospect's slot pick
Match the prospect's reply against the rendered list. Read `start_time` and
`end_time` from that row. The prospect may give only a start time; map it to the
matching slot. Hold `{start_time: "HH:MM", end_time: "HH:MM"}`.

### Step 5.5 — Duplicate-tour gate (run when `applicant_id` is already in scope)
Call `list_tours` with `{applicant_id, property_id, status: "scheduled"}`.

- Empty `data` → continue to Step 6.
- Non-empty `data` → STOP. Do NOT call `capture_lead` or `schedule_tour`.

  Emit the `prefs-update` fence (fence first, then prose):

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

  Prose (one sentence — offer reschedule only, never "or cancel"):
  > You already have a **{Tour Type}** booked for **{Existing Date}** at
  > **{Existing Time}**. Want me to move it to **{Step-3 Date}**?

  End the turn. The next reply routes to the ## Reschedule Flow.

### Step 6 — Collect prospect contact info
**Skip what you already have.** Check `<agent-context>/lead_preferences/` for
`prospect_first_name`, `prospect_last_name`, `prospect_email`, AND `prospect_phone`.
If ALL four are set, skip Steps 6, 6.5, and 7. Pull `application_id` and
`applicant_id` from context and jump to Step 8.

Otherwise ask for the missing fields in a single question.

### Step 6.5 — Check for an existing lead
Call `search_leads` with `{property_id, email, phone_number}`.

- **Empty `data`:** continue to Step 7.
- **1+ rows:** Pick the most-recently-updated row. Read `applicant_id` and
  `application_id`. Do NOT call `capture_lead`. Run the duplicate-tour check:

  Call `list_tours` with `{applicant_id, property_id, status: "scheduled"}`.
  - Empty `data` → jump to Step 8.
  - Non-empty `data` → STOP. Emit the fence + reschedule prose from Step 5.5.
    End the turn.

### Step 7 — Create the guest card
**Skip when Step 6.5 already resolved the lead.**

Call `capture_lead` with:
- `property_id` — from agent-context
- `primary_applicant` — `{first_name, last_name, email, phone}` taken verbatim from
  Step 6 (digits-only phone, no spaces / hyphens / leading `+`)
- `company_user_id` — runtime constant `11` (do not ask the prospect)

Read the response:
- `application_id` → `data.guest_card.id`
- `applicant_id` → `data.primary_applicant.id` (preferred) or
  `data.guest_card.primary_applicant_id` (fallback)
- If both are null → call `search_leads` with the prospect's email.

If `data.guest_card.is_existing == true` → proceed to Step 7.5.
Otherwise proceed to Step 8.

### Step 7.5 — Reconcile applicant name (only when `is_existing=true`)
Compare returned `first_name` / `last_name` vs what you sent (case-insensitive,
stripped). If both match → skip to Step 8.

If either differs → call `update_applicant` ONCE with
`{applicant_id, company_user_id: 11, changes: {first_name, last_name}}`.

On any failure (422 or other) → do NOT retry. Proceed to Step 8 with the name on
file and add "booked under the name on file — let me know if that needs updating"
to the confirmation. Never block the booking on a name-reconcile failure.

### Step 8 — Schedule the tour
**Call `schedule_tour` immediately after identity is resolved — never ask "shall
I proceed?" That is the confirmation-loop trap.**

Call `schedule_tour` with:
`{application_id, applicant_id, property_id, tour_type, tour_date,
time_slot: {start_time, end_time},
initiated_by: {product: "prospect_portal", product_id: 2, company_user_id: 11}}`

Sources:
- `application_id` / `applicant_id` → from Step 6.5 (existing lead) or Step 7
  (new lead)
- `property_id` → agent-context
- `tour_type` → `value` from Step 2
- `tour_date` → `YYYY-MM-DD` from Step 3
- `time_slot` → from Step 5
- `initiated_by` → runtime constant — do not ask the prospect

**On success**, reply in plain markdown:

> Your **{Tour Type Name}** is booked for **{Date}** at **{Time}**.
> Confirmation on its way to **{email}**. Anything else I can help with?

**Post-booking communications are handled automatically:**
- Tour instructions (parking, check-in, access) will be sent through the same
  channel the prospect used. Do NOT ask for consent to send these — they are
  operational, not marketing.
- A tour reminder will be sent the next day for tours scheduled 48+ hours out
  (same-day bookings and next-day bookings are excluded from the reminder).

If `schedule_tour` returns `_active_tour_exists` error → read `tour_id=<digits>`
from `error.got`. Emit the ## Step 5.5 fence with that `tour_id`, then offer the
reschedule prose. End the turn.

---

## Reschedule Flow

Triggered by: "move my tour", "reschedule my appointment", "change my tour time",
or by the `book_tour` duplicate-tour handoff.

### Step R1 — Resolve the existing tour
Check `<agent-context>/lead_preferences/`:
- `tour_id`, `application_id`, `applicant_id`, `picked_tour_type` ALL present →
  skip `list_tours`. Go to Step R2.
- Otherwise call `list_tours` with `{applicant_id, property_id, status: "scheduled"}`.

  - Empty `data` → "I don't see a tour on file at this property — want to book one?"
    End turn. Route next reply to Booking Flow.
  - One row → carry `id` (→ `tour_id`), `application_id`, `applicant_id`,
    `tour_type` forward.
  - Multiple rows → ask which tour to move. Match their reply to a row.

### Step R2 — Ask for the new date (or short-circuit)
Check `<agent-context>/lead_preferences/picked_tour_date`. If set AND strictly after
today, carry it forward without re-asking:

> Got it — moving your tour to **{date}**. Let me pull up open slots.

Otherwise ask: "What date would you like to move it to?"

Same-day reschedules are blocked at the MCP layer and here. If the resolved date ≤
today, reply:
> Same-day tours aren't available — the earliest I can move it to is tomorrow.
> What other date works for you?

### Step R3 — Fetch slots for the new date
Call `get_tour_schedule_time_slots` with `{property_id, start_date, end_date,
tour_type}` (single-day window, `tour_type` from Step R1 — do NOT change tour type
during a reschedule).

- Empty `slots` → "No slots open on that date — want to try a different day?" →
  loop to Step R2.
- Non-empty → render as markdown bullets. Ask which slot they want.

### Step R4 — Reschedule atomically
**Call `reschedule_tour` immediately after the prospect picks a slot.** Do NOT
sequence `cancel_tour` + `schedule_tour` — the upstream is atomic; a manual
cancel-then-rebook leaves an orphaned cancellation if the rebook step fails.

Call `reschedule_tour` with:
`{tour_id, application_id, applicant_id, property_id, tour_type, tour_date,
time_slot: {start_time, end_time},
initiated_by: {product: "prospect_portal", product_id: 2, company_user_id: 11}}`

On success, reply:

> Your **{Tour Type Name}** is now on **{New Date}** at **{New Time}**. See you then.

---

## Cancellation Flow

Triggered by: "cancel my tour", "I can't make it", "drop my appointment".
If the prospect says "reschedule" or "move", route to Reschedule Flow instead —
never cancel-then-rebook.

### Step C1 — Resolve the tour to cancel
Same logic as Step R1. Hold `tour_id`, `application_id`, `tour_type`,
`scheduling_mode`.

### Step C2 — Confirmation gate (HARD GATE — destructive action)
**You MUST get an explicit "yes" before calling `cancel_tour`.**

Ask:
> Just to confirm — cancel your **{Tour Type Name}** on **{Date}** at **{Time}**?

Accept only an explicit affirmative: "yes", "confirm", "cancel it", "go ahead",
"proceed". On anything ambiguous or non-affirmative, do NOT call `cancel_tour`.
If the prospect pivots to "reschedule instead", end this flow and route next turn
to Reschedule Flow.

After explicit "yes", generate a `confirmation_token`:
`"prospect-{YYYY-MM-DD}-{tour_id}"` using today's date.

### Step C3 — Cancel
Call `cancel_tour` with:
- `tour_id` — from Step C1
- `application_id` — from Step C1
- `property_id` — from agent-context
- `tour_type` — from Step C1 (closed enum: `self_guided_tour` | `virtual_tour` |
  `tour`)
- `scheduling_mode` — from Step C1 (default `"scheduled"` if not on the row)
- `initiated_by` — `{"company_user_id": 11}` ONLY (narrower than schedule shape —
  no `product` / `product_id`)
- `confirmation_token` — from Step C2

Do NOT pass `calendar_event_category_id` — the field was dropped in May 2026; the
MCP will reject the call with a `ValidationFailure` envelope if present.

On success (`data.status == "cancelled"`):

> Cancelled — your **{Tour Type Name}** on **{Date}** at **{Time}** is off the
> books. Let me know if you want to rebook.

---

## Arguments to fill
The argument values come from the step that produced them; never invent them.

- `property_id` — `<agent-context>/property/property_id`. Never accept a number
  from the prospect's text.
- `tour_id` — `data.id` from `schedule_tour` / `reschedule_tour`, OR
  `data[*].id` from `list_tours`, OR LTM `tourId`. NEVER `application_id`.
- `application_id` — `data.guest_card.id` from `capture_lead`, OR `data[*].id`
  from `search_leads`, OR LTM `applicationId`. NEVER the value after `tour_id=`
  in any error envelope.
- `applicant_id` — `data.primary_applicant.id` from `capture_lead`, OR
  `applicants[0].applicant_id` from `search_leads`, OR LTM `applicantId`.
  NEVER `data.id`.
- `tour_type` — closed enum: `tour` | `self_guided_tour` | `virtual_tour`. From
  Step 2 (new booking) or carried from `list_tours` row (reschedule / cancel).
  Do NOT change tour type during a reschedule.
- `time_slot` — `{"start_time": "HH:MM", "end_time": "HH:MM"}` taken VERBATIM from
  the `get_tour_schedule_time_slots` row. Never round, shift, or invent times.
- `initiated_by` (schedule / reschedule) —
  `{"product": "prospect_portal", "product_id": 2, "company_user_id": 11}`.
- `initiated_by` (cancel) — `{"company_user_id": 11}` ONLY.
- `confirmation_token` (cancel) — `"prospect-{YYYY-MM-DD}-{tour_id}"` generated in
  Step C2. Never call `cancel_tour` without it.

**CRITICAL — three different integers:** `tour_id`, `application_id`, and
`applicant_id` are THREE DIFFERENT integers from three different upstream rows.
They are NOT interchangeable. If all three would be the same number on a call,
STOP — re-derive each from its proper source row before retrying.

## Error Recovery

| Error | Recovery |
|---|---|
| `get_tour_schedule_time_slots` empty | "No slots on {date} — try another?" → loop to date ask |
| After 3 empty-slot attempts | `escalate_to_human` |
| `schedule_tour` → `_active_tour_exists` | Read `tour_id` from `error.got`. Emit prefs-update fence + reschedule prose. End turn. |
| `reschedule_tour` → `ValidationError, field: tour_id` | Read correct `tour_id` from `error.got`. Emit `prefs-update` fence with corrected id. Retry ONCE. Do NOT apologize in prose. |
| `reschedule_tour` → 409 `TourStateConflictException` | "Looks like that tour was already changed — want me to book a fresh one?" Route to Booking Flow. |
| `cancel_tour` → 409 `TourStateConflictException` | "Looks like that tour was already cancelled." End turn. |
| `search_leads` empty | "I don't see a profile on file — want to book a new tour?" End turn. |
| `list_tours` empty (reschedule / cancel) | "I don't see a tour on file at this property — want to book one?" End turn. |
| 404 `TourNotFoundException` | Re-run `list_tours` once to resync. If still mismatched, `escalate_to_human`. |
| Any other error | `escalate_to_human` |

## Do NOT
- Do NOT make parallel tool calls — one tool per turn, always.
- Do NOT expose `tour_id`, `applicant_id`, `application_id`, or `property_id` in
  prose. Refer to tours by human date + time + type only.
- Do NOT emit JSON fences except the `prefs-update` fence (fence first, prose second).
- Do NOT ask "shall I proceed?" or "would you like me to book this?" after identity
  is resolved — that is the confirmation-loop trap.
- Do NOT cancel-then-rebook to reschedule — `reschedule_tour` is atomic.
- Do NOT change `tour_type` during a reschedule. A type change is cancel + new
  booking, not a reschedule.
- Do NOT call `cancel_tour` without an explicit "yes" in the immediately-prior turn.
- Do NOT offer same-day tour slots unless the property's Same-Day Tour toggle is
  enabled and the slot clears the configured Lead Time window.
- Do NOT proactively book multiple upcoming tours for the same prospect.
- Do NOT ask for SMS consent when sending tour instructions — they are operational
  communications, not marketing. Consent is managed separately and out of scope.
- Do NOT pass `calendar_event_category_id` to `cancel_tour` — the field was removed
  in May 2026.
- Do NOT substitute `application_id` (or any other integer) for `tour_id`. Read each
  ID from its canonical source row.
- Do NOT call `get_property_hours` for slot availability — office hours and bookable
  slots are not the same thing.
- Do NOT call `get_property_contact_details` with the prospect's own email / phone.
- Do NOT fabricate tour slot times, dates, or availability without calling
  `get_tour_schedule_time_slots` first.
