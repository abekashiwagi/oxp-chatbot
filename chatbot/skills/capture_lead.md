---
name: capture_lead
title: Create a guest card when the prospect volunteers contact info
for_intents: [TOUR_BOOKING, UNKNOWN]
capabilities_used: [register_lead, find_applicant, update_applicant, search_leads, list_lead_activities]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect volunteers their name + contact details WITHOUT
asking to book a tour. Phrases: "I'm interested, here's my info",
"let me give you my email", "my name is Jane, jane@x.com,
+1 555 1234", "send me more info", "add me to your list".

If the prospect is in the middle of a tour booking, do NOT switch
to this skill — `book_tour` Step 7 already calls `capture_lead`
inline. This skill is for the standalone "volunteer info outside
a booking" path only.

## Property identity precondition (always first)
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent, ask the prospect once which property they're interested
  in. On their reply call `list_properties` as your ONLY tool call
  this turn. Never call `capture_lead` with a placeholder, null, or
  empty `property_id`.

## Identity bootstrap (always before `capture_lead`)
The goal of this skill is to land the prospect on a guest card. A
duplicate `capture_lead` write for a lead the host already knows
about pollutes the CRM (the upstream is idempotent, but a wasted
round-trip plus an "is_existing=true" reconcile path is noise we
can avoid). Resolve identity in this order, stopping at the first
source that yields an existing lead:

1. `<agent-context>/lead_preferences/applicant_id` AND
   `<agent-context>/lead_preferences/application_id` are both set —
   the prospect already has a guest card in this session. Do NOT
   call `capture_lead`. Reply with a one-line acknowledgement:
   > You're already on file as **{prospect_first_name}** — anything
   > else I can help with?
   End the turn.
2. `<agent-context>/lead_preferences/customer_id` is set
   (super-agent handoff path — this is the ONLY identity field the
   super-agent ever pushes) — call `search_leads` with
   `{customer_id, property_id}`. On a hit, read the row's
   `applicant_id` + `application_id` and reply with the
   acknowledgement above; do NOT call `capture_lead`. On the next
   turn, optionally call `list_lead_activities` for a recap.
3. `<agent-context>/lead_preferences/prospect_email` OR
   `prospect_phone` is set (prospect-volunteered earlier in this
   session) — call `search_leads` with `{email, property_id}` (or
   `phone_number`). Same resolution as step 2.
4. Nothing matched — proceed to Step 1 below and collect missing
   fields, then `capture_lead`.

Note the origin of each field: `customer_id` is ONLY ever pushed by
the super-agent on the invocation contract; `prospect_email` /
`prospect_phone` are ONLY ever volunteered by the prospect. The
agent NEVER asks the super-agent for email/phone and NEVER reads
email/phone off the invocation contract for identity bootstrap.

## Tools, in order — one tool per turn, never in parallel

### Step 1 — Collect what's missing
Look at `<agent-context>/lead_preferences/` for any of
`prospect_first_name` / `prospect_last_name` / `prospect_email` /
`prospect_phone` that may already be stamped from an earlier turn.
Ask only for the fields that are missing — never re-ask for one
already in agent-context. If nothing is stamped, ask in a single
prompt:

> Got it — to get you on file I need your first name, last name,
> phone number, and email.

Wait for the reply. Do NOT proceed without `first_name` +
`last_name` + at least one of (`email`, `phone`). If they give
some but not all, ask once for the rest.

**Contact-info disambiguation — read carefully**
- The first name, last name, email, and phone the prospect gives
  here are THEIR OWN. They belong on the guest card. Pass them to
  `capture_lead` in Step 2.
- Do NOT call any property-contact-details lookup
  (`get_property_contact_details`, etc.) with the prospect's own
  email or phone. Do NOT search the property's contact records
  for the prospect's own contact info.
- If the prospect later asks "what's YOUR phone number?" or "how
  do I reach you?", THAT is a property-contact question — that's
  the `property_overview` skill, not this one. Never quote a
  property phone back when the prospect just told you their own.

**Name vs tour-type disambiguation — critical**
- Never pass a tour-type label (`Guided Tour`, `Virtual Tour`,
  `Self-Guided Tour`, `Tour`, `Guided`, `Virtual`, `Self-Guided`)
  as `first_name` or `last_name`. Those are tour TYPES, not
  names. The tool-validation guardrail will reject any
  `capture_lead` call where the name fields match a tour-type
  label.
- If the prospect's reply is ambiguous (e.g. they typed
  "John Tour" or "Guided Tour" and you cannot tell whether it's
  a name or a leftover from earlier conversation), ask once:
  "Just to confirm — what name should I put on file?"

### Step 2 — Create the guest card
**You MUST call `capture_lead` now.** Calling the tool IS the
action that creates the guest card; writing "I'll register you" or
"got it, I've added you" without invoking `capture_lead` is not
progress — it is a stall.

Call `capture_lead` with:
- `property_id` — from agent-context
- `first_name` — from Step 1
- `last_name` — from Step 1
- `email` — from Step 1 if the prospect provided one
- `phone` — from Step 1 if the prospect provided one (digits only,
  no spaces / hyphens / leading `+`)
- `company_user_id` — runtime constant `11` (do not ask the
  prospect)

Read the response:
- `application_id` — from `data.guest_card.id`
- `applicant_id` — from `data.primary_applicant.id` (preferred) or
  `data.guest_card.primary_applicant_id` (fallback)
- `is_existing` — from `data.guest_card.is_existing` (the upstream
  is idempotent; a duplicate POST for the same
  `(property_id, email_or_phone)` returns the existing card with
  `is_existing: true`)

If `data.primary_applicant` is null AND
`data.guest_card.primary_applicant_id` is also null, call
`search_applicant` ONCE with the prospect's email as the locator
and read `data.applicant_id` from that. Use it once and only once
— never re-call `search_applicant` in the same turn.

### Step 2.5 — Reconcile the applicant name (only when `is_existing=true`)
**Skip this step when `data.guest_card.is_existing` is `false`.**
A freshly-created guest card already carries the correct name.

When `is_existing` is `true`, compare (case-insensitive, stripped):
- `data.primary_applicant.first_name` vs the `first_name` you
  sent in Step 2
- `data.primary_applicant.last_name` vs the `last_name` you sent
  in Step 2

If BOTH match, skip to the reply below. The existing record is
already correct.

If EITHER differs, call `update_applicant` ONCE with:
- `applicant_id` — `data.primary_applicant.id` from Step 2
- `company_user_id` — runtime constant `11`
- `changes` — `{"first_name": "<sent first>", "last_name": "<sent last>"}`

The upstream `createGuestCard` endpoint matches existing rows by
email/phone and does NOT update name fields on its own when a
match is found. This step is the agent's compensating write so
the prospect's actual name lands on the record.

If `update_applicant` fails, do NOT retry — proceed to the reply
below using the prospect's actual name in prose (even though the
upstream record still carries the stale one). Never loop on a
name-reconcile failure.

Reply with one prose sentence:

> Thanks **{First Name}** — you're on file. Want to schedule a
> tour or hear about pricing?

The session-state extractor stamps `prospect_first_name`,
`prospect_last_name`, `prospect_email`, `prospect_phone`,
`application_id`, and `applicant_id` into `<agent-context>` from
the `capture_lead` ToolMessage automatically. The next turn's
`book_tour` skill can skip Steps 6–7 because the guest card is
already in scope.

## Arguments to fill
- `property_id` — `<agent-context>/property/property_id` (resolved
  in the precondition above).
- `first_name` / `last_name` / `email` / `phone` — from Step 1,
  taken VERBATIM from the prospect. Phone is digits-only, no
  spaces / hyphens / leading `+`. Never search property contact
  records for these.
- `company_user_id` — runtime constant `11`.

## If a step fails
- `capture_lead` returns 422 (unknown property / disabled
  property) → re-resolve via `list_properties`, retry once with
  the resolved id. If still 422, route to `escalate_to_human`.
- `find_applicant` returns no match AND `capture_lead` returned a
  null applicant → route to `escalate_to_human` (legacy row that
  needs human reconciliation).
- Any other error → route to `escalate_to_human`.

## Do NOT
- Do NOT call `capture_lead` if
  `<agent-context>/lead_preferences/applicant_id` OR
  `<agent-context>/lead_preferences/customer_id` is already set in
  this session — the identity-bootstrap preamble above resolves
  the lead instead. A duplicate write the upstream idempotently
  echoes is still a wasted round-trip + a misleading
  "is_existing=true" reconcile path; the bootstrap step's
  acknowledgement prose ("you're already on file") is correct.
- Do NOT call `get_property_contact_details` with the prospect's
  OWN email / phone — those are theirs, not the property's.
- Do NOT call `update_guest_card` from this skill (or from any
  prospect-facing path). It patches lead-attribution slots
  (`leasing_agent_id`, `lead_source_id`, listing-service id) plus a
  nested primary-applicant slice — that is an OPERATOR tool for
  leasing-agent reassignment, not a prospect flow. Contact-info
  corrections after Step 2 go through `update_applicant` in Step
  2.5; attribution edits belong to a human operator and are
  outside this skill's surface.
- Do NOT include `application_id` / `applicant_id` in the reply
  prose.
- Do NOT pass a tour-type label as `first_name` / `last_name`
  (`Guided Tour`, `Virtual Tour`, `Self-Guided Tour`, `Tour`,
  `Guided`, `Virtual`, `Self-Guided`). Those are tour TYPES, not
  names. The tool-validation guardrail will reject the call.
- Do NOT skip Step 2.5 when `is_existing=true`. The upstream
  silently returned a pre-existing record whose name may not
  match what the prospect just gave you; the
  `update_applicant` reconcile is what corrects it.
- Do NOT make parallel tool calls — one tool per turn, always.
