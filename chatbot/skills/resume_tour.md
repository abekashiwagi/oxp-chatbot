---
name: resume_tour
title: Read-only display of existing tours for the prospect
for_intents: [TOUR_BOOKING, UNKNOWN]
capabilities_used: [list_tours, get_tour, get_lead]
needs_property_id: true
needs_move_in_date: false
---

## When to use
"What tours do I have", "do I have an appointment", "show my
booking", "when's my tour". Read-only — no writes.

## Property identity precondition (always first)
Before calling any tour tool, confirm a property is in scope:
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent (the `<property>` block is missing or empty), ask the
  prospect once: "which property are you asking about?". On their
  reply, call `list_properties` with the named property as your
  ONLY tool call this turn. Carry the resolved id forward for the
  rest of this session.
- If `list_properties` returns zero matches, ask the prospect for a
  full name or lookup code. If it returns multiple, ask them to
  pick one before continuing. Never guess.

Never call `list_tours` / `get_tour` with a placeholder, null, or
empty `property_id` — that loops on validation errors. If you
cannot resolve a property after one ask, route to
`escalate_to_human`.

## Tools, in order
Call ONE tool per turn:
1. Call `list_tours` with `applicant_id` (from working notes) and
   `property_id`.
2. (Optional, NEXT turn only) When `list_tours` returned a single
   booked tour AND the prospect's reply asks anything about their
   own stored preferences ("am I still down for a 2-bed?", "did I
   give you a move-in date?"), call `get_lead` with
   `application_id=<tour.application_id>` and paraphrase the
   non-null `applicant_preferences` fields into the reply ("you
   booked a Self-Guided Tour for June 23rd, and you were
   originally looking for a 2-bed move-in May 15 — still that
   range?"). Never echo numeric ranges verbatim; never expose
   internal ids; skip null fields. Skip this step entirely when
   the prospect's reply is purely tour-state ("when's my tour?",
   "show my booking") — Step 3 covers that.
3. If the prospect asked about ONE specific tour AND `list_tours`
   returned multiple, call `get_tour` for the matching `tour_id`
   on the next turn.

## Arguments to fill
- `applicant_id` — from working notes. If missing, ask for the
  prospect's email or phone and route to `lead_capture_resume`
  first to resolve the applicant.
- `property_id` — from `<agent-context>/property/property_id` once
  resolved (see "Property identity precondition" above). Never
  accept a number from the prospect's text — only resolve via
  `list_properties`.

## What to ask the prospect
Email or phone ONLY if `applicant_id` is missing. Don't ask for
both — one is enough.

## How to reply
For each tour: tour_type, date (human-friendly: "Saturday May 24"),
time slot, location label. If only one tour, one prose sentence.
If multiple, a bullet list. After replying, ask the next adjacent
question: "want to reschedule, cancel, or book another?".

## If the tool returns nothing
"I don't see a tour booked under that email/phone. Want to
schedule one?" (→ `book_tour`).

## Do NOT
- Do NOT book a new tour from this skill — that is `book_tour`.
- Do NOT call `cancel_tour` here — that is the `cancel_tour`
  skill.
- Do NOT call `reschedule_tour` here — that is the
  `reschedule_tour` skill.
- Do NOT call `get_lead` when `list_tours` returned 0 or 2+ tours.
  The rich-profile enrichment in Step 2 only applies after a
  single tour resolves.
- Do NOT echo `applicant_preferences` values verbatim. Paraphrase
  numeric ranges, dates, and ids into conversational prose.
- Do NOT include `tour_id` or `application_id` in the reply.
- Do NOT make parallel tool calls — one tool per turn, always.
