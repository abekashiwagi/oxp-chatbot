---
name: show_fee_catalog
title: Show the full fee catalog / move-in price-out for one picked unit
for_intents: [PROPERTY_INFO, UNKNOWN]
capabilities_used: [list_fee_catalog, list_addons]
needs_property_id: true
needs_move_in_date: true
---

## When to use
Any fee-transparency ask: "what fees", "what's the deposit", "total
move-in cost", "break it down", "what does parking cost on top",
"application fee", "pet deposit", full price-out. The fee catalog
is per-unit and per-move-in-date — both inputs must be settled
before any tool call. If either is missing, this skill's job is
elicitation, NOT a tool call. Never answer a fee-transparency
question at property-, floor-plan-, or unit-type-level: deposits,
application fees, parking, pet rent, and total move-in cost ALL
vary by unit, so a generic answer would be misleading.

## Hard-gate elicitation (always, before any tool call)
Three inputs are required: `property_id`, `move_in_date`,
`unit_space_id`. Walk them in this order — one elicitation per
turn, no tool call until all three are settled:

1. **Property.** From `<agent-context>/property/property_id`. If
   absent, ask which property and resolve via `list_properties`
   (only tool call that turn). If `list_properties` returns zero
   matches, ask for a full name or lookup code; if multiple, ask
   the prospect to pick. Never guess. After one failed
   resolution, route to `escalate_to_human` — do NOT loop.
2. **Move-in date.** From
   `<agent-context>/lead_preferences/target_move_in_date` if
   populated (any non-`MISSING` value). Otherwise ask FIRST,
   before any unit-picker step:
   > "To get you accurate pricing I need a target move-in
   > date — even an approximate month works. When are you
   > hoping to move in?"

   No tool call this turn. Wait for the reply, normalise to
   `YYYY-MM-DD`, carry it forward. **NEVER substitute today's
   date for a missing move-in date.** The system-prompt "today
   is …" anchor is for parsing relative phrases the prospect
   typed ("next Saturday", "the 5th"). It is NOT a default for
   `move_in_date` — passing today returns fees scoped to a date
   the prospect did not pick, and the prospect sees a
   confident-looking number that does not apply to them. If the
   prospect later asks "what is my move-in date?", quote it from
   `<agent-context>/lead_preferences/target_move_in_date` — do
   NOT say "I don't have one on file" when the field is
   populated.
3. **Unit.** From `<agent-context>/lead_preferences/picked_unit_space_id`,
   else from a prior `list_available_units` row whose
   `unit_number` matches the prospect's label (case-insensitive
   exact match) — read `unit_space_id` (the integer) from THAT
   row. If the matching row is missing or has no
   `unit_space_id`, treat it as "unit not in catalog" and offer
   the leasing-team handoff (→ `escalate_to_human`); never
   fabricate a numeric id. If neither source has a unit, route
   to `show_units`:
   > "Pricing varies by unit, so let me show you what's
   > available for [move_in_date] — pick one and I'll pull the
   > full price-out."

   `show_units` is the unit picker. `show_fee_catalog` re-enters
   once the prospect names a unit. Do NOT call
   `list_available_units` from this skill.

Never call `get_fee_catalog` until ALL THREE are settled. If you
get this far in one turn (all three already on file from prior
turns or context), the call is allowed THIS turn — see "Tools, in
order".

## Tools, in order
One tool per turn:
1. With all three hard-gate inputs settled, call
   `get_fee_catalog` with `property_id`, `unit_space_id`,
   `move_in_date`. Reply with the breakdown (see "How to reply").
2. If the prospect then asks about parking / storage, call
   `get_addons` on the NEXT turn.

## Calculation policy
Every dollar amount is sourced from the deterministic markdown the
post-processor renders between `<!-- fees-catalog-md -->` anchors —
the headline (`**You'll pay $X/mo. $Y is due at move-in.**`), each
required-monthly bullet, each opt-in bullet, each deposit bullet.
Those numbers are byte-identical with the upstream cascade total;
quote them verbatim and they will always reconcile with what the
prospect was told the unit costs.

NEVER invent a new total by summing items. Specifically:
- A combined "what if I add parking AND storage AND a pet?" total is
  out of bounds — the prospect can opt into different combinations
  with different deposit + proration math the agent does not see.
  Reply: "I can't quote a combined hypothetical total. Here are the
  individual amounts — pick the ones you want and the leasing team
  can confirm the final figure." Then list each requested line item
  VERBATIM from the deterministic markdown (e.g. `Reserved Parking
  — $150.00/mo`, `Storage Unit — $35.00/mo`). Do NOT write
  `$150 + $35 = $185` or any other derived figure.
- The deterministic headline IS the authoritative monthly total
  ("You'll pay $1,408.00/mo" reconciles with the cascade
  `total_monthly_leasing_price.min` and the unit-list rent — quote
  it as-is). It is NOT a hypothetical; it is what the prospect pays
  at the lease the agent just priced.
- If the prospect keeps pushing for a combined hypothetical, treat
  it as unanswerable and offer the leasing-team handoff (→
  `escalate_to_human`).

## Arguments to fill
- **`property_id`** — see Hard-gate elicitation step 1.
- **`move_in_date`** — see Hard-gate elicitation step 2. Never
  fabricate a date. Never re-ask once it is on file.
- **`unit_space_id`** — see Hard-gate elicitation step 3. The
  integer id from a `list_available_units` row OR from
  `<agent-context>/lead_preferences/picked_unit_space_id`. Never
  any character substring of a `unit_number` label. Never an
  integer the prospect typed — they don't know internal ids.

## How to reply
Three parts, in this exact shape — every number, every line item,
every total is filled deterministically by the post-processor from
the `get_fee_catalog` result, so YOU only write the intro and the
close-out:

1. **One-line intro** naming the picked unit and the move-in date
   (e.g. `Here's the move-in price-out for unit Floor21 on May 22,
   2026:`). No numbers in the intro — the breakdown carries them.
2. **Anchor pair** with an empty body — the post-processor swaps
   in the deterministic markdown breakdown (headline + required-
   monthly + at-move-in + deposits + opt-in add-ons + cascade
   range). The anchors are HTML comments; they live INSIDE the
   pipeline (the rewriter fills the body between them, and the
   internal-id redactor + grounding check skip the auto-generated
   region by matching them) and are then stripped by the final
   `strip_fees_catalog_anchors` pass before the reply leaves the
   process. The prospect never sees the anchor lines themselves —
   only the rendered breakdown between them. Emit them exactly
   as shown:

   ```
   <!-- fees-catalog-md -->
   <!-- /fees-catalog-md -->
   ```
3. **Empty `fees-catalog` JSON fence** for the UI's
   `FeeTransparency` cards — the post-processor fills the JSON
   from the same tool result:

   ```
   ```fees-catalog
   {}
   ```
   ```

After the fence, ask the next adjacent question: "want me to add
parking or storage to the total?" (→ `get_addons` next turn) or
"ready to book a tour?" (→ `book_tour`).

Do NOT write any dollar amounts, bullet rows, totals, or section
headings yourself — those are the post-processor's job. If you
do, the prospect sees a doubled / inconsistent breakdown.

## If the tool returns nothing
First sanity-check the call:
- Did you pass an integer `unit_space_id` you READ from a prior
  `list_available_units` row (or `picked_unit_space_id`)? If NO,
  you likely parsed a number out of the prospect's unit label —
  that is the documented cause of an empty fee catalog. Re-run
  Hard-gate elicitation step 3 and retry ONCE with the correct
  id. Do NOT tell the prospect there is no pricing — the call
  was misformed.
- Did you pass a real `move_in_date` (not `None`, not an empty
  string)? If NO, get it and retry.

If both ids are right and `data: null` still came back, reply: "I
don't have pricing for that unit on that date — the
leasing team can confirm." Offer the handoff (→
`escalate_to_human`).

## On error
The hard-gated fields (`property_id`, `unit_space_id`,
`move_in_date`) return `{"error": {field, expected, got, fix}}`
when missing. Lift `fix` directly into the prospect-facing
elicitation question — do NOT loop on the same call.

## Do NOT
- Do NOT call `get_fee_catalog` without BOTH `unit_space_id` AND
  `move_in_date` settled. The wire rejects the call (HTTP 422)
  and the prospect sees a flaky-pricing experience.
- Do NOT call `get_fee_catalog` or `get_addons` with today's
  date when the prospect has not given a move-in date. Ask
  first, call on the NEXT turn. Today's date is a system anchor
  for parsing relative phrases, not a default for `move_in_date`.
  The runtime guardrail
  `reject_today_as_move_in_date_when_prospect_unknown` blocks
  the call at dispatch and surfaces a teaching message — the
  prose contract above is the primary rule, this is the
  belt-and-braces. Confirmed live-fire on 2026-05-23: a
  prospect asked "show pricing of Unit AFP-Unit-122", the LLM
  silently passed `move_in_date=2026-05-23` (today), Data
  Family returned HTTP 404, the prospect saw a flaky-pricing
  message. Ask first, every time.
- Do NOT skip the move-in-date ask. Even when the prospect
  opens with "what fees do you charge?" or "what's the deposit",
  the answer is unit + date scoped — ask for the date first.
- Do NOT answer fee transparency at property-level, floor-plan-
  level, or unit-type-level. Pricing structures (rent +
  application fee + admin fee + deposit + pet fees + parking)
  vary by unit; a property-wide "rough range" is misleading.
  Always elicit a specific unit via `show_units` first.
- Do NOT call `get_fee_catalog` for a monthly-rent-only ask
  when rent already came back in a `list_available_units` fence
  this session — quote from session memory. The fee catalog is
  a 15-45s upstream call; the per-unit market rent + effective
  rent on the units-list row IS the answer to "what's the rent
  for unit X?". Reach for `get_fee_catalog` only when the
  prospect wants the FULL price-out (every fee row, deposits,
  totals).
- Do NOT pass any character substring of a `unit_number` label as
  `unit_space_id` — see Hard-gate elicitation step 3.
- Do NOT call `list_available_units` from this skill — route to
  `show_units` if the prospect needs to re-browse.
- Do NOT call `get_unit_matrix`.
- Do NOT make parallel tool calls.
- Do NOT include any internal id in the reply prose.
- Do NOT write the dollar-amount breakdown yourself — emit the
  empty `<!-- fees-catalog-md -->` anchor pair and let the
  post-processor render it. Sampled / paraphrased rows are why
  the move-in math used to drift from the upstream cascade total.
