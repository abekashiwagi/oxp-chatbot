# Leasing AI Agent — Skills

A **skill** is a step-by-step recipe that tells the agent how to
handle one specific prospect workflow — for example "book a tour",
"show available units", or "find a prior lead profile".

Each skill lives in its own markdown file in this folder. The
agent loads every skill at boot time and includes the right ones
in the system prompt based on the prospect's intent. This means
the LLM gets a focused playbook for the current conversation
instead of one giant document covering everything.

## How a skill is structured

Every skill file follows the same simple shape:

1. **Metadata** at the top (between `---` lines) — the skill's
   name, a short title, which intents it applies to, which
   tools it uses, and a couple of preflight requirements.
2. **The recipe** — a numbered list of steps the agent should
   walk through, one tool call per turn, plus rules for what
   to ask the prospect, how to reply, and how to recover from
   failure.
3. **A "Do NOT" section** — the hard prohibitions. Things the
   agent should never do (skip a step, fabricate an id, leak an
   internal id into prose, call two tools at once).

Here's an example metadata block:

```yaml
---
name: book_tour
title: Book a new property tour for the prospect
for_intents: [TOUR_BOOKING]
capabilities_used: [get_property_available_tour_types, list_tour_types, ...]
needs_property_id: true
needs_move_in_date: false
---
```

The fields are:

| Field | What it does |
|---|---|
| `name` | The skill's unique handle. |
| `title` | A one-line description for humans. |
| `for_intents` | Which conversation intents this skill is offered on. |
| `capabilities_used` | The tools the skill walks through. |
| `needs_property_id` | Whether the skill needs a resolved property before it can act. |
| `needs_move_in_date` | Whether the skill needs a move-in date before it can act. |

## What skills the agent ships with today

The library currently has twelve skills, grouped by what the
prospect is trying to do.

### Tour-related (the booking funnel)

| Skill | When to use |
|---|---|
| **book_tour** | The prospect says they want to schedule / book / set up a tour, visit, viewing, walkthrough, or appointment. |
| **reschedule_tour** | The prospect already has a tour and wants to move it to a different date or time. |
| **cancel_tour** | The prospect wants to call off an existing tour. |
| **resume_tour** | Read-only "what tours do I have", "when's my tour", "show my booking". No writes. |
| **capture_lead** | The prospect volunteers their contact info outside a tour booking ("add me to your list", "send me more info"). |
| **lead_capture_resume** | The prospect implies a prior interaction ("I called yesterday", "find my profile") — search the system for an existing lead before creating a duplicate. |

### Property information (what is this place?)

| Skill | When to use |
|---|---|
| **property_overview** | Operational basics — address, office hours, phone / email, "where is it", "are you open Saturday". |
| **property_offering** | What the property includes — amenities, addons, utilities, specials. |
| **property_facts** | Neighborhood + policies — nearby schools, parks, transit, pet policy, parking policy, deposit. |

### Inventory + pricing (what's available, what does it cost?)

| Skill | When to use |
|---|---|
| **show_units** | List floor plans and available units for a move-in date. |
| **show_fee_catalog** | Full price-out for ONE specific picked unit — rent, fees, deposits, total move-in cost. |

### Handoff

| Skill | When to use |
|---|---|
| **escalate_to_human** | The prospect needs (or asks for) a human, the agent has run out of options, or the tool calls have failed and the prospect should not be stranded. |

## How a turn flows

When a prospect sends a message, the agent does roughly this:

1. **Classify the intent.** Is this a tour question? An inventory
   question? A policy question? A handoff?
2. **Load the matching skills** for that intent. They become part
   of the system prompt for this turn.
3. **Walk one step of one skill** — usually a single tool call
   plus a reply. Never two tools at once.
4. **Carry context forward.** Identity (`applicant_id`,
   `application_id`, `customer_id`), the property in scope, the
   picked tour date, and similar values are stored in the
   long-term memory and read by the next turn's skill so the
   prospect never has to repeat themselves.

## Why skills look the way they do

A few design choices show up across every skill:

- **One tool per turn.** Two tools in parallel makes the
  conversation hard to recover from when one fails, and it
  doubles the prospect's wait time. Every skill enforces this.
- **Property identity is always confirmed first.** A skill that
  acts on the wrong property is worse than a skill that asks
  one extra question. Each skill's "Property identity
  precondition" reads `<agent-context>/property/property_id`
  and falls back to a `list_properties` lookup on miss.
- **Identity bootstrap before any write.** Tour and lead skills
  short-circuit when the prospect is already on file (via the
  super-agent `customer_id`, or a previously captured
  `applicant_id`) so duplicate guest cards never get written.
- **Internal ids never appear in prose.** `applicant_id`,
  `application_id`, `tour_id`, `property_id` — these live in
  agent-context, not in replies. The prospect sees names and
  human-friendly dates, never integers.
- **Same-day tours are not allowed.** Tour writes must be
  booked for tomorrow or later. The MCP server enforces this
  with a guard; the skills mirror the rule so the agent never
  even attempts a same-day call.

## How to add a new skill

1. Create a new `*.md` file in this folder with the metadata
   block at the top and the recipe below it.
2. Reference any tools the skill uses by their MCP tool name
   (the exact name the LLM sees in its tool list).
3. Make sure every capability listed in `capabilities_used`
   appears in `app/capabilities/aliases.py`.
4. Add a recipe test under `tests/app/skills/` that pins the
   skill's invariants (the step ordering, the must-do bullets,
   the must-not-do bullets) so future edits cannot silently
   regress the contract.
5. If the new skill applies to an intent that doesn't already
   load it, add the intent to `for_intents` in the metadata.

The library is designed so a non-engineer can read any skill
file end to end without needing to understand the runtime —
the markdown IS the source of truth, and the loader just turns
it into a system-prompt fragment for the LLM.

## See also

- `_loader.py` — parses the markdown files into `Skill` objects.
- `_models.py` — the `Skill` dataclass definition.
- `app/capabilities/aliases.py` — the map from skill capability
  names to the MCP tools the LLM actually calls.
- `tests/app/skills/` — the recipe pins for each skill.
