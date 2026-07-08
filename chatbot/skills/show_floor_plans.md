---
name: show_floor_plans
title: Answer prospect questions about floor plans and units using the most precise context available
for_intents: [PROPERTY_INFO, UNKNOWN]
capabilities_used: [list_properties, list_floor_plans, list_available_units, list_property_lease_terms, list_specials]
needs_property_id: true
needs_move_in_date: false
---

## When to use
Any prospect question about floor plans, layouts, availability, or
pricing that has NOT yet narrowed to a single unit. Trigger phrases:
"what floor plans do you have", "any 2-bedrooms", "how much is a
1-bed", "what's available", "tell me about your layouts", "starting
price for a studio", "show me floor plans", "what are your prices",
"do you have 3-bedrooms", "what sizes do you offer", "any specials
on a 1-bed".

The default communication level is FLOOR PLAN. Prospects explore at
the floor-plan level first and only dive into specific units when
they want exact pricing, exact availability, or are ready to act
(tour, apply). This skill owns the floor-plan-level conversation;
route to `show_fee_catalog` only after a specific unit is picked.

For amenities / utilities / addons / specials at the property level
(not tied to a floor plan ask), use `property_offering` instead.

## Context resolution hierarchy
When answering any prospect question about inventory, pricing,
availability, or features, resolve context in this priority order:

1. **Unit level** — exact values for one specific unit (unit name,
   exact sq ft, exact rent, exact availability date, unit-specific
   amenities). Use ONLY when the prospect has named or picked a
   specific unit AND unit-level data is available from MCP.
2. **Unit type** — values shared across units of the same type
   within a floor plan. Use when unit type grouping is present in
   tool responses but no specific unit is selected.
3. **Floor plan level** — aggregated or ranged values across all
   units in a plan (sq ft range, rent band, bed/bath count, plan
   amenities, plan description). The DEFAULT communication level.
4. **Property level** — values that apply property-wide (property
   amenities, pet policy, general lease terms). Lowest specificity;
   use only when no plan-level or unit-level data is available.

Always communicate at the MOST SPECIFIC level available. When
answering from an aggregated level, explicitly tell the prospect
the data is aggregated (see "Aggregation transparency" below).

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
`property_id`.

## Move-in date handling
Move-in date is NOT required for static floor plan discovery (step
1 below). It IS required before any pricing or availability call.

**Static questions (no date needed):** "what floor plans do you
have", "how many bedrooms", "describe the Alpine plan", "what's
the square footage range" → answer from `get_floor_plans` without
asking for a date.

**Dynamic questions (date required):** "what's available", "how
much is a 1-bed", "any units for August", "starting price" → check
`<agent-context>/lead_preferences/target_move_in_date` first. If
present, use it. If absent, ask ONCE before calling any pricing or
availability tool:
> "To show you accurate pricing and availability, when are you
> hoping to move in? Even an approximate month works."

No tool call this turn. Wait for the reply, carry the date forward.
**NEVER substitute today's date for a missing move-in date.**

## Tools, in order (ONE per turn)

### Step 1 — Floor plan discovery (static context)
Call `get_floor_plans` with `property_id`. No `move_in_date`
required for this call when the prospect is asking a pure discovery
question. The response contains:
- Floor plan name, bedroom count, bathroom count
- Square footage (may be a range across units in the plan)
- Description, plan-level amenities
- Rent band (min–max across units and lease terms)

Present this as the floor plan menu. This is the DEFAULT first
response for any inventory question. Group by bedroom count.
Communicate pricing as "starting at $X" or "$X – $Y/mo" when the
data represents a range.

### Step 2 — Floor plan availability + pricing (dynamic context)
When the prospect asks about pricing or availability for a plan
AND `move_in_date` is resolved, call `get_floor_plans` with
`property_id` and `move_in_date`. The response includes
availability count, pricing ranges, and applicable lease terms
scoped to that date.

Present aggregated floor-plan-level pricing as a range:
"The [Plan Name] starts at $X/mo depending on unit and lease
term." Always include the aggregation disclaimer (see below).

### Step 3 — Lease terms (when prospect asks about term options)
Call `get_property_lease_terms` if the prospect asks "what lease
lengths", "can I do a 6-month", "what terms are available". Present
available terms. Note that pricing varies by term.

### Step 4 — Specials (when prospect asks about promotions)
Call `get_specials` if the prospect asks about discounts, promos,
or move-in specials. Present at the floor-plan level when plan-
specific; note that applicability may vary by unit and lease term.

### Step 5 — Unit-level deep dive (prospect requests specifics)
ONLY when the prospect explicitly asks for specific units within a
plan they have already discussed, call `list_available_units` with
`property_id` + `move_in_date` + `floorplan_id`. This requires:
- `floorplan_id` resolved per the extractor or prior tool row
  (same procedure as `show_units` step 2)
- `move_in_date` resolved

Present exact unit-level detail: unit name, exact sq ft, exact
rent for the prospect's move-in date, availability date, unit-
specific amenities. At this level, values are exact — no
aggregation disclaimer needed.

## Arguments to fill
- `property_id` — from `<agent-context>/property/property_id`.
  Never accept a number from the prospect's text.
- `move_in_date` — from
  `<agent-context>/lead_preferences/target_move_in_date` if
  present, else from a single ask. Required for pricing and
  availability calls only, NOT for static discovery. Never assume
  today's date.
- `floorplan_id` (for `list_available_units` only) — from
  `<agent-context>/lead_preferences/picked_floorplan_id` if set,
  else from the prior `get_floor_plans` row whose `floorplan_name`
  matches the prospect's label (case-insensitive exact match).
  Never derive from label characters. Never guess.

## What to ask the prospect
- `move_in_date` — ONLY when the prospect asks a pricing or
  availability question AND the date is not on file. Do NOT ask
  for pure discovery questions.
- After presenting floor plans: "Would you like to know more about
  any of these, or shall I show you what's available for a
  specific plan?"
- After presenting plan-level pricing: "Want me to show you the
  specific units available in [Plan Name] so you can see exact
  pricing?"
- After presenting units: "Want me to break down the full pricing
  on one of these?" (→ `show_fee_catalog`) or "Ready to set up a
  tour?" (→ `book_tour`).

## How to reply

### Floor-plan-level responses (the default)
One prose sentence introducing the list, then grouped plan
summary. Communicate:
- Plan name (quoted verbatim from tool response)
- Bed/bath count
- Square footage as a range when data spans multiple units
- Pricing as "starting at $X/mo" or "$X – $Y/mo"
- Available unit count (if dynamic context is loaded)

Example shape (NOT literal — fill from tool response):
> "Here are the floor plans at [Property]. The 1-bedrooms start at
> $1,350/mo and the 2-bedrooms from $1,650/mo:"
> - **[Plan A]** — 1 bed / 1 bath, 650–720 sq ft, from $1,350/mo
> - **[Plan B]** — 2 bed / 2 bath, 980–1,050 sq ft, from $1,650/mo

### Unit-level responses (prospect dove deeper)
One prose sentence naming the picked plan, then one markdown bullet
per unit with exact values: unit number, bed/bath, exact sq ft,
exact rent for the move-in date, availability date. No aggregation
disclaimer — these are exact.

### Aggregation transparency (MANDATORY for floor-plan-level)
Whenever communicating floor-plan-level pricing, availability, or
lease-term data, append ONE of these conversational disclaimers
(choose the one that fits the response):
- "Pricing varies by specific unit and lease term — I can show you
  exact numbers once we narrow to a unit."
- "These are starting prices across the plan. The exact rent
  depends on which unit and lease length you choose."
- "Availability and pricing can change — want me to pull the
  specific units so you can see what's open right now?"

The disclaimer MUST appear. It is NOT optional. Floor-plan-level
data is aggregated; the prospect must understand that exact
combinations of price + sq ft + lease term + amenities cannot be
guaranteed without unit-level context.

## MCP as source of truth
Availability, pricing, lease terms, fees, and specials are DYNAMIC
data owned by the source systems exposed through MCP. Rules:

1. Only communicate values returned through MCP-supported context.
2. Do NOT independently calculate pricing (no summing, no
   averaging, no interpolating between values).
3. Do NOT infer lease-term-to-price combinations the tool did not
   explicitly return.
4. Do NOT predict future inventory or availability.
5. Do NOT determine fee applicability without unit-level context
   from `get_fee_catalog`.
6. Do NOT promise availability — always note that availability and
   pricing may change.
7. If MCP returns no data for a requested context level, say so
   and offer to try a different angle (different date, different
   plan, escalate to leasing team).

## If the tool returns nothing
First sanity-check the call:
- `move_in_date` missing on a pricing/availability call? That is
  the silent-zero failure mode. Get the date, retry. Do NOT tell
  the prospect there are no plans.
- `floorplan_id` wrong? If `list_available_units` rows don't match
  the expected plan, re-resolve per step 5 above.
- For a real call with correct inputs that returns zero rows:
  say "I don't see availability in [Plan Name] for [date]" and
  offer adjacent plans from the prior `get_floor_plans` response,
  or offer to try a different move-in date.

## Graceful fallback handling
When the prospect's question cannot be fully answered at the
requested precision:

- **Unknown floor plan:** "I don't see a plan by that name. Here
  are the plans I have on file: [list from prior tool response].
  Which one were you asking about?"
- **Unknown unit:** "I don't have a unit by that name in [Plan].
  Here are the available units: [list]. Did you mean one of these?"
- **Missing move-in date (for pricing ask):** Ask for the date.
  Do NOT guess. Do NOT answer with undated ranges if the tool
  requires a date.
- **No availability for requested plan/date:** Acknowledge, offer
  adjacent plans or alternative dates.
- **Precision request exceeds available data:** "I can show you
  the starting prices for [Plan], but exact pricing depends on
  which unit and lease term you choose. Want me to pull the
  specific units?"
- **Stale or incomplete data:** "Pricing and availability can
  change — the leasing team can confirm the latest for you."
  Offer handoff if the prospect needs a guarantee.

## Do NOT
- Do NOT skip the floor-plan level. Even when the prospect asks
  "show me units" or "what's available", present floor plans FIRST
  (step 1) so the prospect can orient before diving into unit
  detail.
- Do NOT guarantee specific combinations of price + sq ft + lease
  term + amenities + fees at the floor-plan level. Those are only
  knowable at the unit level with MCP-provided pricing context.
- Do NOT independently calculate pricing. No summing rent + fees,
  no averaging across units, no interpolating between lease terms.
  Quote what MCP returned.
- Do NOT infer that a specific lease term produces a specific
  price unless the tool response explicitly pairs them for a
  specific unit.
- Do NOT predict future availability. "We'll have units opening
  up in September" is a fabrication unless the tool returned
  future-dated availability.
- Do NOT promise availability. Always communicate that inventory
  is subject to change.
- Do NOT omit the aggregation disclaimer when answering at floor-
  plan level. The prospect must know the data is ranged/aggregated.
- Do NOT answer pricing or availability questions without a move-in
  date when the tool requires one. Ask first, then call.
- Do NOT substitute today's date for a missing move-in date.
- Do NOT call `list_available_units` without a `floorplan_id`.
  The flow is plans-first, always.
- Do NOT call `get_fee_catalog` from this skill. Fee transparency
  requires a picked unit → route to `show_fee_catalog`.
- Do NOT make parallel tool calls — one tool per turn, always.
- Do NOT include any internal id (`property_id`, `unit_space_id`,
  `floorplan_id`) in the reply.
- Do NOT emit JSON code fences. Plain markdown only.
- Do NOT fabricate floor plan names, unit names, prices, sq ft,
  or any value the tool did not return.
- Do NOT communicate specials as guaranteed without confirming
  applicability at the unit/lease-term level. Say "there may be
  specials available" and confirm details once context narrows.
