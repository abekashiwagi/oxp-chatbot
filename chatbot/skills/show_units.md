---
name: show_units
title: Show available floor plans then available units (plans-first deep flow)
for_intents: [PROPERTY_INFO, UNKNOWN]
capabilities_used: [list_properties, list_floor_plans, list_available_units, list_property_lease_terms]
needs_property_id: true
needs_move_in_date: true
---

## When to use
Any ask about floor plans OR units OR availability. Trigger phrases:
"what floor plans", "show me the floor plans", "what layouts",
"any 1-bedrooms", "what units", "what's available", "show me units",
"any 2-beds under $2000", "any units for August".

Plans and units share ONE recipe here: plans first, units second.
For amenities / utilities / addons / specials, use
`property_offering` instead.

## Property identity precondition (always first)
Confirm a property is in scope before any tool call:
- Read `<agent-context>/property/property_id`. If present, use it.
- If absent, ask once: "which property are you asking about?". On
  reply, call `list_properties` with the named property as your
  only tool call this turn. Carry the resolved id forward.
- Zero matches → ask for a full name or lookup code. Multiple
  matches → ask the prospect to pick one. Never guess.
- After one failed ask, route to `escalate_to_human`.

Never call any other tool with a placeholder, null, or empty
`property_id` — that loops on validation errors.

## Move-in date precondition (ALWAYS before any inventory read)
`get_floor_plans` and `list_available_units` both silently return
zero rows without a move-in date — that is the documented silent-
zero failure mode. So:
1. Check `<agent-context>/lead_preferences/target_move_in_date`. If
   present (any non-`MISSING` value), use it — do NOT ask again.
2. If absent / `MISSING`, ask once: "when are you hoping to move
   in?" and wait for the prospect's reply on the NEXT turn. Do
   NOT call any inventory tool on the same turn as the ask. A
   plan-specific ask ("what units for AFP?") still needs a date
   before the call — the plan name does NOT substitute for a date.
3. Carry the resolved date forward. Never re-ask within a session.

**NEVER substitute today's date for a missing move-in date.** The
system-prompt date anchor is for relative-date math ("next
Saturday") only — it is NOT a default for the inventory tools.
Calling `get_floor_plans` / `list_available_units` with today's
date when the prospect has not stated one filters out plans whose
first available unit is later in the season, and the prospect sees
a wrong-and-confident layout summary. If
`target_move_in_date` is `MISSING`, the ONLY correct action is to
ask the prospect — no tool call this turn.

## Tools, in order (plans-first, ONE per turn)
**Hard gate:** the agent-side validator blocks any
`list_available_units` call that has no `floorplan_id`. The
bypass — "I have property_id and move_in_date, just call units" —
returns a `VALIDATION_FAILED` envelope, not data. Do not attempt
it. The two-turn picker below is the ONLY path.

1. **Floor plans always come first.** Once `property_id` and
   `move_in_date` are resolved, call `get_floor_plans` as your only
   tool call this turn. Render the response (group by bedroom count:
   name + bed/bath + sq ft + rent band) and ask which plan the
   prospect wants. This step is mandatory even when the prospect's
   first message was "show me any units" or named a specific plan —
   the floor-plan response is the picker, and the `floorplan_id` you
   read from it scopes the next call.
2. **Resolve `floorplan_id` in this exact order — do NOT skip step
   2a.** The deterministic session-state extractor resolves the
   prospect's named plan into the integer id on every turn before
   you run, so the id is on file the moment the prospect types
   "AFP" — even when the prior `get_floor_plans` ToolMessage has
   been rehydrated out of the message list. Reading from the
   extractor's output is the ONLY reliable path; reading from the
   prior tool result is the fallback for the same-turn case.
   1. **2a — Trust the extractor.** If
      `<agent-context>/lead_preferences/picked_floorplan_id` is
      set (any non-`MISSING` integer string) AND
      `<agent-context>/lead_preferences/picked_floorplan_name`
      matches the plan label the prospect named (case-insensitive
      exact match), use that `picked_floorplan_id` as-is. Do NOT
      re-derive it from anywhere else.
   2. **2b — Fall back to the prior tool result.** Only when
      `picked_floorplan_id` is `MISSING` AND a `get_floor_plans`
      ToolMessage is still in this turn's loop, find the row
      whose `floorplan_name` matches the label the prospect named
      (case-insensitive exact match on the whole name, not a
      substring) and read the integer `floorplan_id` field from
      THAT row.
   3. **2c — Re-list, never invent.** If neither 2a nor 2b yields
      a match, list the plans the prior `get_floor_plans`
      response DID return (read `floorplan_name` verbatim) and
      ask the prospect to pick from that list. Small integers
      like `1`, `2`, `3` and any digit run not read from a tool
      response or `picked_floorplan_id` are NEVER the real id —
      they look like a guess and the upstream returns units from
      the wrong plan (or zero rows). Never derive `floorplan_id`
      from the label characters, the row position, or your own
      memory of a previous session.
3. **Call `list_available_units` filtered by `floorplan_id`.** Pass
   `property_id` + `move_in_date` + `floorplan_id`. Pass
   `number_of_bedrooms` / `number_of_bathrooms` only if the prospect
   named those (rarely needed once a plan is scoped). Render the
   result as plain markdown (one bulleted row per unit — see
   "How to reply" below). Do NOT emit a `units-list` JSON fence.
4. (Optional, NEXT turn only) Call `get_property_lease_terms` if
   the prospect named a lease length.

## Arguments to fill
- `property_id` — from `<agent-context>/property/property_id`. Never
  accept a number from the prospect's text.
- `move_in_date` — from
  `<agent-context>/lead_preferences/target_move_in_date` if present,
  else from a single ask. Never assume today's date. Never call
  any inventory tool with a `None` / empty date.
- `floorplan_id` (for `list_available_units` only) — resolved per
  step 2 above. Prefer
  `<agent-context>/lead_preferences/picked_floorplan_id` (the
  extractor's deterministic pick); fall back to the prior
  `get_floor_plans` row only when that field is `MISSING`. Never
  any other source.

## What to ask the prospect
- After step 1: ONE follow-up — "which plan would you like to see
  units for?".
- Ask `move_in_date` only if missing AND
  `<agent-context>/lead_preferences/target_move_in_date` is not set.

## How to reply
- **Plans turn (step 1):** one prose sentence introducing the list,
  then the grouped plan summary (name + bed/bath + sq ft + rent
  band). Close with "which plan would you like to see units for?".
  Quote names exactly as the tool returned them — never invent or
  paraphrase a plan name.
- **Units turn (step 3):** one prose sentence above the list
  naming the picked plan ("here are the open units in <plan name>"),
  then ONE markdown bullet per unit. Each bullet quotes the
  prospect-facing fields verbatim from the tool result: unit
  number, bed/bath, square feet, the rent (or rent band) for the
  prospect's move-in date, and the availability date. Skip
  internal ids in the bullet text. After the list, ONE follow-up:
  "want me to break down the full pricing on one of these?"
  (→ `show_fee_catalog`) or "ready to set up a tour?" (→ `book_tour`).

## If the tool returns nothing
First sanity-check the call:
- `move_in_date` missing? That is the silent-zero failure mode. Get
  the date, retry. Do NOT tell the prospect there are no plans / no
  units.
- For `list_available_units`: sanity-check the response — if the
  rows' `property_floorplan_name` does NOT match the plan the
  prospect picked, the `floorplan_id` was wrong (likely a guess).
  STOP, re-run step 2 starting from `picked_floorplan_id`, and
  retry. Never present wrong-plan units to the prospect as if
  they were the right ones.
- For `list_available_units` only: drop `number_of_bedrooms` /
  `number_of_bathrooms` once if you passed them, in case the filter
  was too tight.

If a real `floorplan_id` and a real `move_in_date` still return
zero rows, say "I don't see any open units in <plan name> for your
dates" (using the plan label the prospect typed, not a made-up one)
and offer the adjacent plans the prior `get_floor_plans` response
DID return. For an empty `get_floor_plans` response, offer to
widen the move-in date or route to `escalate_to_human`. Never
invent a unit or guess a rent.

## Do NOT
- Do NOT call `list_available_units` without a `floorplan_id` — the
  flow is plans-first, always.
- Do NOT call `get_property_hours` to check availability — that is
  office hours, not unit vacancy.
- Do NOT call `get_unit` for the whole list; that is the single-
  record fallback for one already-picked unit.
- Do NOT call `get_fee_catalog` until the prospect has picked
  one specific unit (then route to `show_fee_catalog`).
- Do NOT make parallel tool calls — one tool per turn, always.
- Do NOT include any internal id (`property_id`, `unit_space_id`,
  `floor_plan_id`) in the reply — the prospect never needs them.
- Do NOT emit a `units-list` JSON fence (or any other JSON code
  fence). The UI no longer renders cards; the fence shows up as
  raw JSON in the chat. Plain markdown only.
- Do NOT call `get_floor_plans` or `list_available_units` with
  today's date when the prospect has not given a move-in date.
  Ask first, then call on the NEXT turn.
- Do NOT parse a number out of a `unit_number` label and treat it
  as the `unit_space_id` on a follow-up pricing call. Look up the
  row by `unit_number` and read its `unit_space_id` (see
  `show_fee_catalog`).
