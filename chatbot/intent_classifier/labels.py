"""Intent labels and skill routing for the LeasingAI chatbot.

Labels match the for_intents frontmatter taxonomy used across the
skill files. INTENT_TO_SKILLS maps a predicted intent to the skill
files (by stem name) that should be injected into the system prompt.
"""

# TOUR_CANCEL and LEAD_CAPTURE are folded into TOUR_BOOKING: they have
# too few examples to learn reliably, and the TOUR_BOOKING skill set
# already includes the cancel/reschedule/lead-capture skills, so routing
# is unaffected.
LABELS = [
    "TOUR_BOOKING",
    "PROPERTY_INFO",
    "ESCALATION",
    "GENERAL",
]

LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}

# Skill stems per intent. Derived from each skill's for_intents frontmatter.
INTENT_TO_SKILLS = {
    "TOUR_BOOKING": [
        "tour_scheduling",
        "book_tour",
        "reschedule_tour",
        "cancel_tour",
        "resume_tour",
        "capture_lead",
        "lead_capture_resume",
    ],
    "PROPERTY_INFO": [
        "show_floor_plans",
        "show_units",
        "property_overview",
        "property_facts",
        "property_offering",
        "show_specials",
        "show_fee_catalog",
        "fee_transparency",
    ],
    # Includes property basics so an over-eager ESCALATION prediction
    # still lets the model answer simple questions instead of escalating.
    "ESCALATION": [
        "escalate_to_human",
        "property_overview",
        "property_facts",
    ],
    "GENERAL": [
        "property_overview",
        "property_facts",
        "escalate_to_human",
    ],
}

# Below this confidence, fall back to loading all skills.
CONFIDENCE_THRESHOLD = 0.5

# Lightweight skills injected into every routed prompt regardless of
# intent, so a misroute can still answer basic property questions.
ALWAYS_INCLUDE = ["property_overview", "property_facts", "escalate_to_human"]
