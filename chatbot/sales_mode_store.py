"""Sales mode configuration storage for the LeasingAI chatbot.

Persists to sales_mode.json in the chatbot directory. All reads go
through load_sales_mode() so changes take effect on the next request
without a server restart.

The build_sales_mode_skill() function renders the saved config into a
markdown skill block that gets injected into every system prompt,
overriding default qualification and routing behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

SALES_MODE_PATH = Path(__file__).parent / "sales_mode.json"

ACTION_LABELS = {
    "allow_tour": "Allow tour",
    "recommend_application": "Recommend application",
    "continue_discovery": "Continue discovery",
    "escalate": "Escalate to team",
    "fallback_message": "Fallback message",
    "mark_unqualified": "Mark unqualified",
}

MODE_DIRECTIVES = {
    "maximize-tour": (
        "Your primary goal is to **maximize tours**. Proactively offer available "
        "tours and invite the prospect to take a tour. Only offer an application "
        "if the prospect explicitly asks for one. Use the Maximize Tour follow-up "
        "cadence."
    ),
    "maximize-application": (
        "Your primary goal is to **maximize applications**. Proactively share the "
        "application link and invite the prospect to apply. Only offer a tour if "
        "the prospect explicitly asks for one. Use the Application Mode follow-up "
        "cadence."
    ),
    "none": (
        "Do **not** proactively offer tours or applications. Answer the prospect's "
        "questions and let them lead the conversation. Only surface a tour or "
        "application if the prospect explicitly asks."
    ),
    # Legacy mode ids
    "tour-first": (
        "Your primary goal is to **schedule tours** with minimal friction. "
        "Keep qualification light — collect only required discovery questions "
        "before offering tour availability."
    ),
    "application-first": (
        "Your primary goal is to **drive prospects toward submitting an application**. "
        "Tour booking is secondary — guide them directly to the application."
    ),
    "qualification-first": (
        "Your primary goal is to **pre-qualify prospects before booking**. "
        "Ask all required discovery questions up front. Apply screening rules strictly."
    ),
}

PREQUAL_OPERATOR_LABELS = {
    "greater_than": "is greater than",
    "less_than": "is less than",
    "at_least": "is at least",
    "at_most": "is at most",
    "equals": "equals",
    "not_equals": "does not equal",
    "less_than_multiplier": "is less than (multiplier of rent)",
    "at_least_multiplier": "is at least (multiplier of rent)",
    "yes": "Yes",
    "no": "No",
    "dont_know": "Don't Know",
}

PREQUAL_RESULT_LABELS = {
    "qualified": "Qualified",
    "over_income": "Over-income",
    "under_income": "Under-income",
    "age_ineligible": "Age-ineligible",
    "unit_ineligible": "Unit-ineligible",
    "potentially_qualified": "Potentially qualified",
    "in_progress": "In progress",
}

TOUR_GOAL_LABELS = {
    "offer": "Proactively offer a tour",
    "if_asked": "Offer a tour only if asked",
    "none": "Do not offer a tour",
}

APP_GOAL_LABELS = {
    "offer": "Proactively share application",
    "if_asked": "Share application only if asked",
    "none": "Do not share application",
}

# Legacy — retained for back-compat rendering if old configs are loaded
PREQUAL_ACTION_LABELS = {
    "offer_tour": "Proactively offer a tour",
    "tour_if_asked": "Offer a tour only if asked",
    "no_tour": "Do not offer a tour",
    "offer_application": "Proactively share application",
    "application_if_asked": "Share application only if asked",
    "no_application": "Do not share application",
    "offer_market_rate": "Offer market-rate units",
    "recommend_larger_unit": "Recommend a larger unit",
    "suppress_cta": "Suppress CTA",
    "handoff": "Escalate to leasing agent",
    "ask_missing": "Ask the missing question",
}


# ── Pydantic models ──────────────────────────────────────────────────────


class DiscoveryQuestion(BaseModel):
    label: str
    status: str = "optional"


class ScreeningCriterion(BaseModel):
    question_label: str
    acceptable_values: str
    resulting_action: str
    priority: int


class PreQualCondition(BaseModel):
    input: str
    operator: str
    value: str


class PreQualRule(BaseModel):
    label: str = ""
    connector: str = "and"
    conditions: list[PreQualCondition] = []
    result: str
    # Legacy single-condition fields
    input: str | None = None
    operator: str | None = None
    value: str | None = None

    def resolved_conditions(self) -> list[PreQualCondition]:
        if self.conditions:
            return self.conditions
        if self.input and self.operator and self.value:
            return [PreQualCondition(input=self.input, operator=self.operator, value=self.value)]
        return []


class PreQualActionPolicy(BaseModel):
    result: str
    action: str


class PreQualGoal(BaseModel):
    result: str
    tour: str = "none"
    application: str = "none"
    offer_market_rate: bool = False


class PreQualQuestion(BaseModel):
    question: str
    data_point: str
    qualified_cta: str = "continue"
    unqualified_cta: str = "deny"
    unknown_cta: str = "escalate"


class SalesModeConfig(BaseModel):
    mode_id: str = "maximize-tour"
    mode_name: str = "Maximize Tour Mode"
    conversion_goal: str = "schedule_tours"
    prequalification_enabled: bool = False
    affordable_flow_enabled: bool = False
    conversation_start: str = "market_first"
    household_income: str = ""
    household_size: str = ""
    vouchers_accepted: bool = False
    # Legacy fields from prior affordable settings
    minimum_income: str = ""
    age_requirement: str = "none"
    prequalification_rules: list[PreQualRule] = []
    prequalification_goals: list[PreQualGoal] = []
    # Legacy fields — retained so older saved configs still parse.
    prequalification_actions: list[PreQualActionPolicy] = []
    prequalification_questions: list[PreQualQuestion] = []
    discovery_questions: list[DiscoveryQuestion] = []
    screening_criteria: list[ScreeningCriterion] = []


def load_sales_mode() -> SalesModeConfig:
    if SALES_MODE_PATH.exists():
        try:
            data = json.loads(SALES_MODE_PATH.read_text())
            return SalesModeConfig(**data)
        except Exception:
            pass
    return SalesModeConfig()


def save_sales_mode(config: SalesModeConfig) -> None:
    SALES_MODE_PATH.write_text(config.model_dump_json(indent=2))


def build_sales_mode_skill(config: SalesModeConfig | None = None) -> str:
    """Render the sales mode config into a markdown skill block."""
    if config is None:
        config = load_sales_mode()

    directive = MODE_DIRECTIVES.get(config.mode_id, MODE_DIRECTIVES["maximize-tour"])

    sections: list[str] = []
    sections.append("## Skill: sales_mode\n")
    sections.append(f"### Active Mode: {config.mode_name}")
    sections.append(directive)

    # ── Conversation flow start (only when affordable flow is enabled) ──
    if config.prequalification_enabled and config.affordable_flow_enabled:
        if config.conversation_start == "affordable_first":
            sections.append(
                "### Conversation Flow: Start with Affordable Units\n"
                "Open the conversation offering affordable units and pre-qualify "
                "all leads against the building's requirements. If the prospect "
                "does NOT qualify for an affordable unit but qualifies for a "
                "market-rate unit, offer market-rate options instead. If no "
                "market-rate units are available, do not suggest them."
            )
        else:
            sections.append(
                "### Conversation Flow: Start with Market Rate Units\n"
                "Open the conversation offering market-rate units. If the prospect "
                "asks about affordable or cheaper units, switch to offering "
                "affordable units and begin the pre-qualification flow. Also "
                "suggest affordable units if no more market-rate units are available."
            )

        aff_lines = ["### Affordable Settings"]
        if config.household_income:
            aff_lines.append(f"- **Household income limit**: {config.household_income}")
        if config.household_size:
            aff_lines.append(f"- **Household size**: {config.household_size}")
        if config.vouchers_accepted:
            aff_lines.append(
                "- **Vouchers accepted**: Yes — voucher holders may bypass "
                "income rejection."
            )
        else:
            aff_lines.append("- **Vouchers accepted**: No")
        sections.append("\n".join(aff_lines))

    # ── Qualification rules ──
    if config.prequalification_enabled and config.prequalification_rules:
        lines = [
            "### Pre-qualification Rules",
            "Collect answers for the inputs referenced below, then apply these "
            "rules deterministically to classify the prospect. The first matching "
            "rule (top to bottom) sets the result. Do NOT improvise the "
            "classification — use the rules.",
            "\n**Qualification rules (first match wins):**",
        ]
        yes_no_ops = {"yes", "no", "dont_know"}
        for i, r in enumerate(config.prequalification_rules, start=1):
            res = PREQUAL_RESULT_LABELS.get(r.result, r.result)
            prefix = f"{r.label}: " if r.label else ""
            join = " AND " if r.connector == "and" else " OR "
            parts = []
            for c in r.resolved_conditions():
                op_label = PREQUAL_OPERATOR_LABELS.get(c.operator, c.operator)
                if c.operator in yes_no_ops:
                    parts.append(f"{c.input} = {op_label}")
                else:
                    parts.append(f"{c.input} {op_label} \"{c.value}\"")
            expr = join.join(parts)
            lines.append(f"{i}. {prefix}If {expr} → {res}")
        sections.append("\n".join(lines))

    # ── Post-qualification goals ──
    if config.prequalification_enabled and config.prequalification_goals:
        lines = [
            "### Post-Qualification Goals",
            "After classification, follow these rules for what to offer the "
            "prospect based on their status:",
            "",
        ]
        for g in config.prequalification_goals:
            res = PREQUAL_RESULT_LABELS.get(g.result, g.result)
            tour = TOUR_GOAL_LABELS.get(g.tour, g.tour)
            app = APP_GOAL_LABELS.get(g.application, g.application)
            mkt = "Yes — offer market-rate units" if g.offer_market_rate else "No"
            lines.append(f"**{res}:**")
            lines.append(f"- Tour: {tour}")
            lines.append(f"- Application: {app}")
            lines.append(f"- Offer market-rate: {mkt}")
            lines.append("")
        sections.append("\n".join(lines))

    # ── Legacy action policy (back-compat) ──
    elif config.prequalification_enabled and config.prequalification_actions:
        lines = ["\n**Action policy (legacy — what to do after classification):**"]
        for a in config.prequalification_actions:
            res = PREQUAL_RESULT_LABELS.get(a.result, a.result)
            act = PREQUAL_ACTION_LABELS.get(a.action, a.action)
            lines.append(f"- {res} → {act}")
        sections.append("\n".join(lines))

    # ── Legacy discovery questions ──
    required = [q for q in config.discovery_questions if q.status == "required"]
    optional = [q for q in config.discovery_questions if q.status == "optional"]
    disabled = [q for q in config.discovery_questions if q.status == "disabled"]

    if required or optional or disabled:
        lines = [
            "### Discovery Questions",
            "Ask these questions naturally during conversation.",
        ]
        if required:
            lines.append("\n**Required (must ask):**")
            lines.extend(f"- {q.label}" for q in required)
        if optional:
            lines.append("\n**Optional (ask if natural):**")
            lines.extend(f"- {q.label}" for q in optional)
        if disabled:
            lines.append("\n**Disabled (do not ask):**")
            lines.extend(f"- {q.label}" for q in disabled)
        sections.append("\n".join(lines))

    # ── Legacy screening criteria ──
    criteria = sorted(config.screening_criteria, key=lambda c: c.priority)
    if criteria:
        lines = [
            "### Screening Rules (apply in priority order)",
            "When a prospect's answer matches a rule, take the resulting action:",
            "",
        ]
        for c in criteria:
            action = ACTION_LABELS.get(c.resulting_action, c.resulting_action)
            lines.append(
                f"{c.priority}. {c.question_label} = \"{c.acceptable_values}\" → {action}"
            )
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
