---
name: lead_capture_resume
title: Find a prior lead profile when application_id is unknown
for_intents: [TOUR_BOOKING, UNKNOWN]
capabilities_used: [search_leads, get_lead, list_lead_activities]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect implies a prior interaction: "I called yesterday",
"I already gave my info", "find my profile", "I started an
application last week". Or: you are about to book a tour and want
to avoid a duplicate `capture_lead` for someone the system
already has.

## Property identity precondition (always first)
Before calling any lead-lookup tool, confirm a property is in scope:
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent (the `<property>` block is missing or empty), ask the
  prospect once: "which property did you reach out about?". On
  their reply, call `list_properties` with the named property as
  your ONLY tool call this turn. Carry the resolved id forward for
  the rest of this session.
- If `list_properties` returns zero matches, ask the prospect for a
  full name or lookup code. If it returns multiple, ask them to
  pick one before continuing. Never guess.

Never call `search_leads` / `list_lead_activities` with a
placeholder, null, or empty `property_id` — that loops on
validation errors. If you cannot resolve a property after one ask,
route to `escalate_to_human`.

## Tools, in order
Call ONE tool per turn:
1. Call `search_leads` with email OR phone OR `applicant_id`
   (whichever the prospect supplied) AND `property_id`.
2. If exactly one match — pull the rich profile and surface it
   conversationally:
   2a. Call `get_lead` with `application_id=<row.id>` on the NEXT
       turn. The response carries `applicants[]` plus
       `applicant_preferences` (`move_in_date`, `desired_unit_id`,
       `bedrooms`, `bathrooms`, `desired_rent_from`,
       `desired_rent_to`, `desired_lease_terms`). Paraphrase the
       non-null fields into the next reply ("last time you were
       looking for a 2-bed under $2,000 starting June 1 — still
       relevant?"). Never echo numeric ranges verbatim; never
       expose internal ids; skip any preference field that is null.
   2b. Optionally call `list_lead_activities` on the turn after
       that to surface a one-line "last activity" recap. Keep
       Step 2a and 2b on separate turns — one tool per turn.
3. If multiple matches: ask the prospect to confirm by date or
   property to disambiguate, then drill into one on the next turn.
   Do NOT call `get_lead` until the disambiguation collapses to a
   single row.

## Arguments to fill
- `email` / `phone` / `applicant_id` — from the prospect. One is
  enough; do NOT ask for all three.
- `property_id` — from `<agent-context>/property/property_id` once
  resolved (see "Property identity precondition" above). Never
  accept a number from the prospect's text — only resolve via
  `list_properties`.

## What to ask the prospect
Email OR phone if missing. Don't ask for both — one is enough.

## How to reply
Acknowledge with one sentence ("Found your profile — last activity
was a tour scheduled for May 12"), then route to the next workflow:
`book_tour`, `reschedule_tour`, `cancel_tour`, `resume_tour`, or
`show_units`. Ask ONE follow-up question that names the next
workflow explicitly.

## If the tool returns nothing
"I don't see a prior profile under that email/phone — let's start
fresh." Continue as a new prospect (route to `book_tour` or
`show_units` depending on intent).

## Do NOT
- Do NOT display `applicant_id`, `application_id`, or any other
  internal id in the reply prose.
- Do NOT make assumptions about the prior conversation; quote
  only facts from `list_lead_activities` or `get_lead`.
- Do NOT call `get_lead` when `search_leads` returned 0 or 2+ rows.
  Step 3 disambiguation controls that fork — calling `get_lead`
  across multiple candidates speculatively is a guess.
- Do NOT echo `applicant_preferences` values verbatim. Numeric
  ranges, dates, and ids paraphrase into conversational prose;
  raw `{"desired_rent_from": 1500, "desired_rent_to": 2000}` is
  never a reply.
- Do NOT make parallel tool calls — one tool per turn, always.
- Do NOT skip this skill before `capture_lead` when the prospect
  said anything implying a prior interaction; duplicate leads are
  a real cost.
