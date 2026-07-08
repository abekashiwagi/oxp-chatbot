---
name: fee_transparency
title: Communicate pricing, fees, deposits, and concessions using Fee Transparency MCP rules
for_intents: [PROPERTY_INFO, UNKNOWN]
capabilities_used: [list_properties, list_fee_catalog, list_available_units, list_specials]
needs_property_id: true
needs_move_in_date: true
---

## When to use
Any prospect question specifically about fee breakdown, fee details,
what's included in rent, what fees apply, deposit requirements,
concessions, or how pricing is structured. Trigger phrases:
"what fees do I pay", "what's included in rent", "break down the
fees", "are there extra charges", "what's not included", "any
hidden fees", "what about deposits", "is parking extra", "what's
the total monthly cost", "how is rent calculated", "any discounts
applied to my rent".

This skill owns the COMMUNICATION RULES for fee data presentation.
It fires when the prospect wants to understand fee structure,
not just see a price-out. For the mechanical tool-calling flow to
fetch fee data, see `show_fee_catalog`. For general pricing
browsing at the floor-plan level, see `show_floor_plans`.

## Property identity precondition (always first)
Confirm a property is in scope before any tool call:
- Read `<agent-context>/property/property_id`. If present, use it.
- If absent, ask once: "which property are you asking about?". On
  reply, call `list_properties` with the named property as your
  only tool call this turn. Carry the resolved id forward.
- Zero matches → ask for a full name or lookup code. Multiple
  matches → ask the prospect to pick one. Never guess.
- After one failed ask, route to `escalate_to_human`.

## Move-in date precondition
Fee transparency data requires a move-in date:
1. Check `<agent-context>/lead_preferences/target_move_in_date`.
   If present, use it.
2. If absent, ask ONCE:
   > "To get you accurate pricing and fee details, when are you
   > hoping to move in?"
   No tool call this turn. Wait for reply, carry forward.
3. **NEVER substitute today's date for a missing move-in date.**
   Exception: student housing (see section 8 below).

## Unit precondition
Fee transparency is per-unit. A `unit_space_id` must be resolved
before calling `get_fee_catalog`:
- From `<agent-context>/lead_preferences/picked_unit_space_id`, or
- From a prior `list_available_units` row whose `unit_number`
  matches the prospect's label (case-insensitive exact match) —
  read the integer `unit_space_id` from THAT row.
- If no unit is picked, route to `show_units` / `show_floor_plans`
  first:
  > "Fees vary by unit, so let me show you what's available —
  > pick one and I'll pull the full fee breakdown."

## Tools, in order (ONE per turn)
1. Resolve `property_id`, `move_in_date`, `unit_space_id` per
   preconditions above (may take multiple turns of elicitation).
2. Call `get_fee_catalog` with all three resolved inputs.
3. (Optional) Call `get_specials` if concession detail is needed.

## Section 1 — Pricing and fees included in base rent

### Total monthly amount presentation
When communicating pricing from the fee catalog response, present:
- **Total Monthly Leasing Price** — the headline number
- **Base Rent** — the base rent component
- **Included fees** — fees the property bundles INTO base rent

For each fee NOT included in base rent but part of the Total
Monthly Leasing Price, communicate:
- Fee name
- Fee description (when available from MCP)
- Whether the fee is recurring or one-time
- The amount: fixed, minimum, maximum, or average — based on the
  logic the MCP returned (see Section 2 below)

### Fees included in base rent
Do NOT separately break down fees the property already includes in
base rent. If the MCP indicates a fee is part of base rent, it is
already reflected in the Base Rent line — listing it again double-
counts it for the prospect.

### Progressive disclosure for many fees
If there are many fees included in the Total Monthly Leasing Price
but NOT in base rent:
1. **Initial response:** communicate only the KEY fees (the largest
   by amount, or the ones most prospects ask about — rent, admin
   fee, trash/valet, pest control). State: "These are part of the
   full fee set — I can share the complete list if you'd like."
2. **If prospect asks for the full list:** share the full list of
   fee NAMES without prices.
3. **If prospect asks for prices:** share the prices as returned
   by the MCP for each named fee.

### Legal note on large fee sets
If a property has a very large number of fees (e.g. 50+), the
initial response does NOT need to list all of them. Follow the same
progressive disclosure logic above. Match the calculator's
presentation — key fees upfront, full detail on request.

## Section 2 — Minimum, maximum, and range amounts

Communicate fee ranges based on the amount fields returned by the
Fee Transparency MCP:

| MCP returns | How to communicate |
|---|---|
| Both `min` and `max` (or explicit range) | "The [fee] costs between $[min] and $[max] [per unit, per month]." |
| Only `min` | "The [fee] starts at $[min] [per unit, per month]." |
| Only `max` | "The [fee] is up to $[max] [per unit, per month]." |
| Single fixed `amount` | "The [fee] is $[amount] [per month]." |

Always quote the amounts VERBATIM from the MCP response. Never
average, interpolate, or derive a range the MCP did not return.

## Section 3 — One-time fee payment month

### Default behavior
Always clarify that one-time fees are one-time charges. In general
pricing or fee summary responses, describe the fee as a one-time
charge WITHOUT mentioning the payment month:
> "There's a one-time admin fee of $250."

### When prospect asks about payment timing
Communicate the payment month ONLY if the prospect explicitly asks
when the fee is paid:
> Prospect: "When do I pay this fee?"
> AI: "This is a one-time fee and is paid during the move-in
> process."

### Future: payment-month logic
When the MCP returns a payment month value (e.g. `1` for first
month of move-in period), communicate accordingly. Until that
field is available, default to "paid during the move-in process"
for timing questions.

## Section 4 — Fee transparency enabled but data unavailable

### When pricing data is missing
If fee transparency is enabled but no pricing data is available:
- Share available unit or rent term information WITHOUT pricing.
- If the prospect asks for pricing:
  1. Escalate using the existing Pricing issue tag.
  2. Provide the leasing office phone number.
  3. Do NOT estimate, infer, or calculate pricing.

### Data freshness rule
Pricing data is valid for ONE day. If the latest successful pricing
sync is older than one day:
- Treat the data as INVALID.
- Do NOT communicate that pricing to the prospect.
- Respond:
  > "I don't have current pricing for this unit type at the
  > moment. Please contact the leasing office for the most
  > accurate information. Their phone number is [number from
  > agent-context]."

The backend sends the date of the last successful pricing sync to
CAIA. If CAIA does not receive pricing data from the same day, the
AI must refer the prospect to the office.

## Section 5 — Deposits

### Default: do NOT surface unprompted
Deposit details should NOT be added automatically to general
pricing responses. Only surface deposits when the prospect
initiates the topic:
- "What's the deposit?"
- "How much do I need upfront?"
- "Is there a security deposit?"
- "What deposits are required?"

### When asked
Call `get_fee_catalog` (if not already called this session for the
same unit) and communicate deposit information as returned by the
MCP. Quote amounts verbatim. Apply the same min/max/range logic
from Section 2.

## Section 6 — Concessions

### Inclusion rules
Concessions may be part of the Total Monthly Leasing Price. Apply
this logic:

| Concession type | Include in Total Monthly? | Communicate separately? |
|---|---|---|
| Recurring AND not prospect-selectable | YES | YES — it is part of the total but the prospect should know it exists |
| One-time | NO | Only if prospect asks |
| Part of base rent | N/A (already in base rent) | NO — do not mention separately |
| Not part of base rent but in Total Monthly | YES | YES — communicate it |

### What the MCP returns
The AI will only receive concessions that are:
- NOT selectable by the prospect (the prospect cannot opt in/out)
- Itemized in the MCP response because the property included the
  special charge code in Setup > Properties > Pricing >
  Transparency > Fees Include

Do NOT expect to receive information about currently selectable
specials through the fee catalog. Those come through `get_specials`
when present.

### Communication shape
When a concession is included in the Total Monthly Leasing Price
and is not part of base rent:
> "Your total monthly amount of $[total] includes a $[amount]
> [concession name] discount."

Do NOT communicate concessions separately from the Total Monthly
Leasing Price when they are already reflected in it — just
acknowledge their existence within the total.

## Section 7 — Fee frequency normalization

### Source of truth for fee price
For each fee, the MCP may return both `amount` and
`advertisedFrequencyAmount`. Rules:
- **Always use `amount`** as the source for the communicated price.
- **Default assumption: monthly frequency** unless the MCP provides
  `chargeTiming` that indicates otherwise.

### What NOT to do
- Do NOT independently determine whether a fee is weekly, daily,
  or another frequency.
- Do NOT infer frequency from fee name, description, or amount.
- Do NOT use `advertisedFrequencyAmount` as the price — use
  `amount`.

### When frequency differs from monthly
When the MCP provides frequency context (`advertisedFrequency`,
`chargeTiming`, or `arTriggerName`) AND the frequency is NOT
monthly:
1. State the fee's native frequency using the MCP-provided label.
2. Still communicate the monthly amount using `amount`.

Example:
> "This fee is charged weekly, and the monthly amount is $X."

### Technical note
`amount` and `advertisedFrequencyAmount` are normalized to monthly
values ONLY if `advertisedFrequencyAmount` is set to monthly. The
`arTriggerId` or `chargeTiming` indicates the charge timing on the
rate, which is then converted to the property's advertised
frequency if the charge timing and advertised frequency differ.

## Section 8 — Max future move-in date vs default window

### Move-in date for MCP pricing requests
When retrieving pricing through the MCP, use the prospect's stated
move-in date. If the prospect's date exceeds the property's
maximum future move-in date and the MCP fails:
- Retry with the property's maximum allowed date.
- If that is unknown, use the default window (see below).

### Default window logic
If the property's maximum future move-in date is unknown:
- Use a 90-day window from today as the default.
- If the 90-day request fails, retry with a 60-day window.

### Student housing exception
Student pricing does NOT require a move-in date:
- Communicate based on lease terms, consistent with the student
  flow.
- When the MCP request requires a date field, send "today" as the
  move-in date.
- Do NOT ask the student prospect for a move-in date when they are
  asking about pricing in a student housing context.

### Phase 1 behavior
- Use a hardcoded maximum move-in date for GIG and Student
  properties.
- Default to 90 days when property-specific max is unknown.
- Assume HQ validation blocks MCP responses if a property's max
  future move-in date is less than 90 days.

## How to reply

### Initial pricing response (progressive disclosure)
Shape for a standard fee breakdown:
1. **Headline:** Total Monthly Leasing Price
2. **Base Rent:** the base rent component
3. **Key fees:** 3–5 most significant non-base-rent fees with
   amounts (recurring fees first, then one-time)
4. **Disclosure line:** "These are the key fees — I can share the
   full breakdown if you'd like."
5. **Follow-up:** "Want to see the full fee list, or are you ready
   to take the next step?"

### Full fee list (when requested)
List ALL fee names without prices. Group by:
- Recurring monthly fees
- One-time fees

### Full fee list with prices (when requested)
List ALL fees with amounts from MCP. Apply Section 2 range logic.
Group by recurring vs one-time.

### Deposit response (only when asked)
List deposit requirements with amounts from MCP.

## If the tool returns nothing
- Pricing sync stale (>1 day old): refer to office, provide phone.
- `unit_space_id` wrong: re-resolve per unit precondition.
- `move_in_date` exceeds property max: retry with 90-day, then
  60-day window.
- Genuinely no data: "I don't have pricing details for this unit
  right now. The leasing team can provide the most current
  information." Offer handoff.

## Do NOT
- Do NOT separately list fees the property already includes in
  base rent — they are already reflected in the Base Rent line.
- Do NOT list all 50+ fees in the initial response — use
  progressive disclosure (key fees first, full list on request).
- Do NOT estimate, infer, or calculate pricing when data is
  unavailable. Escalate to office.
- Do NOT communicate pricing from a sync older than one day.
- Do NOT surface deposits unprompted — only when the prospect
  asks about deposits.
- Do NOT communicate the payment month for one-time fees unless
  the prospect explicitly asks when it is paid.
- Do NOT infer fee frequency from fee name, description, or
  amount — use `chargeTiming` from MCP only.
- Do NOT use `advertisedFrequencyAmount` as the display price —
  always use `amount`.
- Do NOT include one-time concessions in the Total Monthly Leasing
  Price.
- Do NOT communicate concessions that are part of base rent as
  separate line items.
- Do NOT independently determine whether a fee is weekly, daily,
  or another frequency.
- Do NOT ask student housing prospects for a move-in date when
  they ask about pricing — student pricing is term-based.
- Do NOT guess the property's max future move-in date. Use 90-day
  default, retry with 60 on failure.
- Do NOT make parallel tool calls — one per turn, always.
- Do NOT include any internal id in the reply.
- Do NOT emit JSON code fences. Plain markdown only.
- Do NOT fabricate any fee name, amount, or frequency the MCP did
  not return.
- Do NOT promise that fees or pricing will remain the same —
  always note that pricing is subject to change.
