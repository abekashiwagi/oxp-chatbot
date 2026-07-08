---
name: property_facts
title: Tell the prospect about the neighborhood and the property's policies
for_intents: [PROPERTY_INFO, POLICIES, UNKNOWN]
capabilities_used: [list_property_selling_points, list_policies]
needs_property_id: true
needs_move_in_date: false
---

## When to use
The prospect asks about EITHER the surrounding area OR a property
policy. One topic at a time, one tool per turn:
- Neighborhood / area — "what's nearby", "what schools", "any parks",
  "good transit", "what's the neighborhood like", "good for kids",
  "anything to do around there".
- Policy — "what's the pet policy", "do you allow smoking", "what's
  the deposit", "what credit score do you need", "what's the occupancy
  limit", "do you allow guests", "is parking allowed", "is there a
  fee for late rent".

## Tools, in order
Call ONE tool per turn, picked by the prospect's specific question:
- "schools / nearby schools / what schools serve the property /
  good for kids / school district"
  → `get_property_selling_points` with
  `property_selling_point_category="LOCAL_SCHOOL"` so the response
  narrows to just the schools bucket. The `LOCAL_SCHOOL` token is
  case-sensitive on the wire — pass it exactly.
- "what's nearby / parks / transit / good neighborhood / anything
  to do around there" → `get_property_selling_points` with NO
  category (the full overview is what the prospect wants when the
  question is open-ended).
- "featured highlights / what makes the property special / why
  here" → `get_property_selling_points` with
  `property_selling_point_category="FEATURED"`.
- policy question (pets, smoking, parking, deposit, income, occupancy,
  guests, late fees) → `get_property_policies`. The tool also takes an
  optional `key_name` token (e.g. `PROPERTY_DETAILS_PET_POLICY`)
  to narrow to one slot; pass it when the question is about a
  specific policy so the response is one row, not the full
  policy list.

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

## Arguments to fill
- `property_id` — from `<agent-context>/property/property_id` once
  resolved (see "Property identity precondition" above). Never
  accept a number from the prospect's text — only resolve via
  `list_properties`.
- `property_selling_point_category` (only for
  `get_property_selling_points`, when scoping a narrow ask) — one
  of `LOCATION`, `FEATURED`, `LOCAL_SCHOOL`,
  `RENTABLE_ITEMS_AND_UPGRADES`, `OTHER`. SCREAMING_SNAKE,
  case-sensitive on the wire. Pass `LOCAL_SCHOOL` for any schools
  question, `FEATURED` for "what's special / highlights", and omit
  the argument entirely for an open-ended "what's nearby" overview.
- `key_name` (only for `get_property_policies`, when scoping a narrow ask) —
  SCREAMING_SNAKE token like `PROPERTY_DETAILS_PET_POLICY`,
  `PROPERTY_DETAILS_PARKING_POLICY`,
  `PROPERTY_SETTINGS_DEPOSIT_POLICY`. Case-insensitive on this
  tool. Omit to return every configured policy row.

## What to ask the prospect
Nothing on this turn — call the matching tool first. After replying,
ask the next adjacent question (see "How to reply"). Track which topic
was just answered so the skill does not loop.

## How to reply
- Schools answer (`property_selling_point_category="LOCAL_SCHOOL"`):
  the response narrows to a single bucket — the schools section
  carries a `SchoolsBucket` wrapper (`{property_id, description,
  items: [SellingPoint, ...]}`), so read the school rows from
  `data.selling_points["Local School"].items[]` (or whichever key
  the response carries — bucket keys are dynamic display labels,
  but with the category filter active only one bucket is present).
  Reply with two or three sentences naming the schools the tool
  returned. Quote names and any distance / grade info verbatim;
  never invent ratings or distances the tool did not return.
- Neighborhood answer (no category): the response carries multiple
  buckets; pick the rows most relevant to the prospect's actual
  question (parks, transit, dining, etc.) and reply with two or
  three sentences.
- Policy answer: one to three sentences answering the SPECIFIC policy
  asked, quoting the actual values from the tool response (whatever
  amounts, durations, or restrictions the upstream returned — do
  not invent placeholder figures). State related policies together
  when natural (pets allowed + pet deposit + breed restrictions),
  but DO NOT dump the full policy list.
Then ONE follow-up question pointing at adjacent territory:
- After a policy answer: "want to know about any other policies, like
  parking or smoking?" if related policies remain unanswered this
  session.
- After a neighborhood answer: "want to know any of the property's
  policies — pets, parking, smoking — too?".
When both topics in this skill have been covered, route on: "want to
know the office hours or how to reach the team?" (→ `property_overview`)
or "want to see what's available to rent?" (→ `property_offering`).

## If the tool returns nothing
- Neighborhood: "I don't have neighborhood details on file for this
  property — the leasing team can share what's around."
- Policy: "I don't have that specific policy on file for this
  property — the leasing team can confirm the exact terms."
Either way, offer the handoff and continue with the next topic.

## Do NOT
- Do NOT call both tools on the same turn — pick the one that matches
  the prospect's question right now.
- Do NOT speculate on policy values the tool did not return. If pets
  are allowed but breed restrictions are not listed, do not guess.
- Do NOT make up nearby businesses, school ratings, or distances that
  the tool didn't return.
- Do NOT call any tool outside this skill's two — the skill is
  intentionally scoped to neighborhood + policies.
- Do NOT repeat a tool call you already made earlier in the session
  for the same topic; reuse the prior answer from working notes.
- Do NOT re-ask a question the prospect already answered.
