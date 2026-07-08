---
name: sales_mode
title: Dynamic sales mode — controls qualification depth, discovery questions, and screening behavior
for_intents: [TOUR_BOOKING, PROPERTY_INFO, GENERAL]
capabilities_used: []
needs_property_id: false
needs_move_in_date: false
---

## When to use
This skill is ALWAYS active. It defines the agent's current sales mode,
which discovery questions to ask, and how to screen prospects before
booking or routing. The dynamic version of this skill is injected by the
backend from sales_mode.json — this static file is a fallback only.

## Default Mode: Tour-first / Sales Mode
Your primary goal is to schedule tours with minimal friction. Keep
qualification light — collect only required discovery questions before
offering tour availability. Do not gate the tour on screening unless a
rule explicitly triggers.

## Discovery Questions
Ask these questions naturally during conversation. Required questions
MUST be asked before booking a tour or recommending an application.

**Required (must ask):**
- Desired move-in date
- Tour preference

**Optional (ask if natural):**
- Budget
- Bedroom count
- Bathroom count
- Unit preferences
- Pet ownership
- Lease term

**Disabled (do not ask):**
- Application readiness

## Screening Rules
No screening rules are active in the default tour-first mode.
Prospects are not pre-qualified before tour booking.
