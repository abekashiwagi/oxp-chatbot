---
name: property_overview
title: Give the prospect the property's operational info (profile + hours + location + contact)
for_intents: [PROPERTY_INFO, UNKNOWN]
capabilities_used: [list_properties, get_property, list_property_hours, get_property_address_by_type, list_property_contact_details]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect asks about the property itself: "tell me about <the
property>", "where is it", "when are you open", "how do I
contact you", "give me a quick overview". This skill covers
profile, hours, address, and contact — ONE topic at a time.

It ALSO owns "is the property open / can I drop by / can I visit
on <day>" — those are office-hours questions answered from
`get_property_hours`, NOT tour-booking questions. Use this skill
whenever the prospect asks whether the property is open on a
specific day; only switch to `book_tour` when the prospect
explicitly says "schedule a tour", "book a tour", "set up a tour",
or otherwise asks for an appointment to be created.

## Property identity precondition (always first)
Before calling any tool in this skill, confirm a property is in scope:
- Look at `<agent-context>/property/property_id`. If present, use it.
- If absent (the `<property>` block is missing or empty), ask the
  prospect once: "which property are you asking about?". On their
  reply, call `list_properties` with the named property as your
  ONLY tool call this turn. Carry the resolved id forward for the
  rest of this session.
- If `list_properties` returns zero matches, ask the prospect for a
  full name or lookup code. If it returns multiple, ask them to
  pick one before continuing. Never guess.

Never call any other tool in this skill with a placeholder, null,
or empty `property_id` — that loops on validation errors. If you
cannot resolve a property after one ask, route to
`escalate_to_human`.

## Tools, in order
Call ONE tool per turn, picked by the prospect's specific question now:
- "tell me about / overview / what kind of place is it" → `get_property`
- "where is it / address / location"                    → `get_property_addresses`
  (pass `address_type="PRIMARY"` for the default postal address — the
  tool's `address_type` argument is mandatory and the 15 valid tokens
  are listed in its description; use `BILLING`, `MAILING`, etc. only
  if the prospect explicitly asked for a non-primary address)
- "office hours / when are you open / pool hours /
  are you open <day> / can I visit <day> / can I drop by"
                                                        → `get_property_hours`
  (read the hours for the named day and answer "open from X to Y"
  or "closed — closure reason". This is NOT a tour question.)
- "phone / email / fax / how do I contact / how can I reach"
                                                        → `get_property_contact_details`

## Arguments to fill
- `property_id` — from `<agent-context>/property/property_id` once
  resolved (see "Property identity precondition" above). Never
  accept a number from the prospect's text — only resolve via
  `list_properties`.
- `address_type` (only for `get_property_addresses`) — pass
  `"PRIMARY"` unless the prospect explicitly asked for a different
  address type (e.g. "what's the billing address?" → `"BILLING"`).
  Tokens are SCREAMING_SNAKE; the 15 valid values live in the tool's
  description.

## What to ask the prospect
Nothing on this turn — call the matching tool first. After replying,
ask the next adjacent question (see "How to reply"). Never re-ask
something the prospect already answered earlier in the session.

## How to reply
One to three sentences quoting actual values from the tool — never
paraphrase numbers, give the exact hours / phone / address.

`get_property_contact_details` has a special reply shape: emit a
```contact-info`` fence wrapping the actual email, phone, and fax
values returned by the tool. The PII redactor scrubs raw
emails / phones from prose but PRESERVES them inside the fence,
so a fence is the only way the prospect actually sees the contact
values. Outside the fence, keep prose generic ("here's how to
reach the leasing team — phone, email, and fax are in the box
below"). Never type the email or phone in prose, even right
before or after the fence — only inside it.

`get_property_hours` ("are you open tomorrow / can I visit on
Saturday") replies with the open/closed status for the named day,
the open and close times if open, and the closure reason if
closed. After the answer, offer the natural next step ("want me
to set up a tour for that time?" → `book_tour`).

`get_property_addresses` replies with the actual street address
(line 1 / line 2 / city / state / zip) for the requested type,
NEVER with the email or phone. If the prospect asked "what is the
address" and got contact info instead, that is a routing error —
call `get_property_addresses(address_type="PRIMARY")` and
answer with the postal address. An empty `data: []` response means
"no address of this type on file" — say so and offer to look up a
different type (e.g. `BILLING`, `MAILING`) before escalating.

`get_property` replies with a short paragraph about the property
(name, type, what makes it distinctive).

Then ONE follow-up question pointing at a tool in this skill the
prospect HAS NOT yet asked about, e.g. after `get_property`:
"want to know the office hours, or how to reach the leasing team?".
When every tool in this skill has been used, route to the next skill:
"want to see what's available?" (→ `property_offering` or
`show_units`) or "anything you want to know about the neighborhood?"
(→ `property_facts`).

## If the tool returns nothing
"I don't have that on file for this property — the leasing team can
confirm." Offer the handoff and continue with the next topic.

## Do NOT
- Do NOT call more than one tool per turn.
- Do NOT call inventory tools (`list_available_units`,
  `list_floor_plans`, `list_fee_catalog`) here — that is
  `property_offering` / `show_units` / `show_fee_catalog` territory.
- Do NOT answer an address question with the email or phone, or a
  contact-info question with the address. `get_property_addresses`
  is for postal address (default `address_type="PRIMARY"`);
  `get_property_contact_details` is for phone / email / fax.
- Do NOT emit email, phone, or fax values OUTSIDE a
  ```contact-info`` fence — the PII redactor will scrub them to
  `[redacted]` and the prospect will see nothing. Inside the
  fence, the values render to the prospect untouched.
- Do NOT call `get_tour_schedule_time_slots` from this skill — "can I
  visit / are you open" is hours, not tour availability. Switch
  to `book_tour` only when the prospect explicitly asks to
  schedule.
- Do NOT ask for information you already have from a previous turn
  (do not re-ask the property, the move-in date, the prospect's name).
- Do NOT include any internal id in the reply.
