---
name: show_specials
title: Communicate active leasing specials relevant to the prospect's context
for_intents: [PROPERTY_INFO, SPECIALS, UNKNOWN]
capabilities_used: [list_properties, list_specials, list_floor_plans, list_available_units]
needs_property_id: true
needs_move_in_date: false
---

## When to use
Any prospect question about promotions, discounts, specials, deals,
incentives, or move-in offers. Trigger phrases:
"any specials", "current promotions", "any deals", "move-in
specials", "any discounts", "free month", "concessions", "what
promos do you have", "any incentives for signing now", "do you
offer anything off rent".

Also fire this skill when:
- The prospect asks about pricing AND the `get_specials` response
  contains active specials relevant to their context — present
  specials alongside pricing as part of the value conversation.
- The prospect is discussing a specific floor plan or unit type
  and eligible specials exist at that scope level.

For fee breakdown and total monthly pricing, use
`show_fee_catalog` / `fee_transparency`. For general floor plan
browsing, use `show_floor_plans`. This skill owns the specials
communication layer.

## Property identity precondition (always first)
Confirm a property is in scope before any tool call:
- Read `<agent-context>/property/property_id`. If present, use it.
- If absent, ask once: "which property are you asking about?". On
  reply, call `list_properties` with the named property as your
  only tool call this turn. Carry the resolved id forward.
- Zero matches → ask for a full name or lookup code. Multiple
  matches → ask the prospect to pick one. Never guess.
- After one failed ask, route to `escalate_to_human`.

## Move-in date handling
Move-in date is NOT required to retrieve the specials list, but IS
required to determine eligibility for date-restricted specials.

- If the prospect has a move-in date on file
  (`<agent-context>/lead_preferences/target_move_in_date`), use it
  to filter eligible specials.
- If no move-in date is on file AND the special has a move-in date
  range restriction, note the restriction conversationally:
  "This special is available for move-in dates between [start] and
  [end]."
- Do NOT block the specials response on a missing move-in date.
  Present what is available and note eligibility constraints.

## Tools, in order (ONE per turn)

### Step 1 — Retrieve specials
Call `get_specials` with `property_id`. The response contains
specials with their scope, eligibility rules, and descriptions.

### Step 2 — Context enrichment (if needed)
If the prospect is asking about specials for a specific floor plan
or unit type and you need to confirm which plans/units qualify:
- Call `get_floor_plans` to resolve floor plan context (next turn).
- Call `list_available_units` to confirm unit-level specials apply
  to available inventory (next turn, only if prospect is at unit
  level).

## Eligibility filtering
Before communicating any special, verify ALL of the following from
the MCP response data:

| Condition | Rule |
|---|---|
| Active | Special must be marked active |
| Web visible | Special must be flagged as web-visible |
| Recipient type | Must include "Prospect" |
| Available inventory | Associated inventory must exist |
| Campaign date range | Today must fall within the special's campaign dates (if defined) |
| Move-in date range | Prospect's move-in date must fall within the special's eligible move-in dates (if defined and prospect date is known) |
| Lease term match | Prospect's lease term must match (if defined and prospect term is known) |
| Scope match | Special must apply to the relevant unit / unit type / floor plan the prospect is discussing |

Only communicate specials that pass ALL applicable conditions.
If a condition cannot be evaluated (e.g., no move-in date on file),
note the restriction rather than excluding the special entirely.

## Special scope hierarchy
Specials are configured at different levels. Apply this logic:

| Scope level | When to surface |
|---|---|
| **Property level** | Mention to any prospect at this property — applies to all units |
| **Floor plan level** | Surface when the prospect is discussing the matching floor plan |
| **Unit type level** | Surface when the prospect is discussing the matching unit type |
| **Unit level** | Since conversations typically operate at the unit-type level, communicate as: "Some units within this floor plan qualify for [special]" |

When a prospect is browsing at the floor plan level, surface:
- Property-level specials (apply to everything)
- Floor-plan-level specials (for the plan being discussed)
- Unit-type-level specials (for types within that plan)
- Unit-level specials (mentioned as partial: "some units qualify")

## Arguments to fill
- `property_id` — from `<agent-context>/property/property_id`.
  Never accept a number from the prospect's text.
- `move_in_date` (optional for filtering) — from
  `<agent-context>/lead_preferences/target_move_in_date` if
  present. Do NOT require it to retrieve specials.
- `floorplan_id` (optional for scope filtering) — from
  `<agent-context>/lead_preferences/picked_floorplan_id` if the
  prospect has narrowed to a plan.

## What to ask the prospect
- Do NOT ask for move-in date just to show specials — present
  what's available and note date restrictions.
- After presenting specials: "Would you like to know the terms and
  conditions for any of these?" or "Want me to show you the floor
  plans these apply to?"
- If >4 specials exist and you showed only the top 4: "There are
  additional specials available — would you like to see more?"

## How to reply

### Standard specials response (≤4 specials)
Shape the response as one cohesive message combining context and
specials:

1. **Context line** — reference the prospect's current interest
   (unit type, floor plan, move-in date) to anchor relevance.
2. **Pricing context** (if available from prior calls) — include
   the price range and a general lease-term statement: "depending
   on lease terms" (do NOT list the lease term range).
3. **Specials list** — up to 4 specials, each with:
   - Special name
   - Marketing description (the benefit in plain language)
   - Relevant lease terms (only if the special is restricted to
     specific terms; if ALL terms qualify, omit this)
4. **Lease-term note** — "Specials may vary depending on the lease
   term."
5. **Overflow note** (if >4 exist) — "There are additional offers
   available as well."
6. **Follow-up** — one adjacent question.

Example shape (fill from tool response, NOT literal):
> "For a 1-bedroom with a move-in date of [date], pricing
> currently ranges between $X and $Y, depending on lease terms.
>
> We currently have a few specials available:
> - **[Special Name]** — [marketing description], available for
>   [lease term] lease terms
> - **[Special Name]** — [marketing description]
> - **[Special Name]** — [marketing description]
>
> Specials may vary depending on the lease term, and there are
> additional offers available as well. Would you like more details
> on any of these?"

### When prospect asks for more detail
On follow-up, provide:
- **Eligible move-in date range** (the special's validity dates)
- **Terms & conditions** (rules and limitations from MCP)
- **Scope clarification** (which units/plans qualify)

### When >4 specials exist
Initial response: show the top 4 most relevant (prioritize by
scope match, then by value to prospect). Note that more exist.
If asked, show the full list with names and descriptions.

### Student housing exception
For student housing, specials are at the **space level** (a
specific room) and linked to lease terms rather than units.
Communicate accordingly: "This special applies to [lease term]
terms" rather than referencing specific units.

## Communication principles
- Keep messaging concise, natural, and conversational.
- Prioritize clarity and value over completeness.
- Present pricing and specials as one cohesive flow — do NOT
  separate them into disjointed responses.
- Use the marketing description to explain the benefit in plain
  language. Do NOT quote internal field names.
- Avoid overwhelming the prospect with every detail upfront.
  Use progressive disclosure: summary first, details on request.

## If the tool returns nothing
- No active specials: "I don't see any active promotions for this
  property right now. Specials change regularly — the leasing team
  can let you know about upcoming offers."
- Specials exist but none match the prospect's context (wrong
  move-in date, wrong floor plan): "The current specials don't
  apply to [context], but let me check if there are other options."
  Offer to broaden the search (different plan, different date).

## Do NOT
- Do NOT present specials that fail any eligibility condition.
  If it's not active, not web-visible, not for prospects, or has
  no associated inventory — do NOT mention it.
- Do NOT list the lease term RANGE (e.g., "6 to 18 months").
  Instead use a general statement: "depending on lease terms."
- Do NOT list more than 4 specials in the initial response. Note
  that more exist and offer to share on request.
- Do NOT communicate terms & conditions unprompted. Only share
  when the prospect asks for details or eligibility requirements.
- Do NOT communicate the special's validity date range unprompted.
  Only share when the prospect asks "when does this expire" or
  "am I eligible".
- Do NOT guarantee a special applies to a specific unit without
  confirming scope. Unit-level specials only apply to specific
  units — say "some units within this floor plan qualify."
- Do NOT present specials that are restricted to a move-in date
  range the prospect clearly falls outside of (when their date is
  known). Silently filter those out.
- Do NOT fabricate special names, descriptions, terms, or
  eligibility rules. Quote from MCP only.
- Do NOT independently calculate the value of a special (e.g.,
  "that saves you $1,800"). Quote the marketing description as
  returned.
- Do NOT conflate specials with base rent or fee transparency
  data. Specials are promotions; fees are charges. Keep them
  conceptually separate even when presenting together.
- Do NOT block the entire response on a missing move-in date.
  Present available specials and note date restrictions where
  applicable.
- Do NOT make parallel tool calls — one per turn, always.
- Do NOT include any internal id in the reply.
- Do NOT emit JSON code fences. Plain markdown only.
