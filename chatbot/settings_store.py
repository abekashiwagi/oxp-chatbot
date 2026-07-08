"""Settings storage for the LeasingAI chatbot.

Persists to settings.json in the chatbot directory. All reads go
through load_settings() so changes take effect on the next request
without a server restart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

SETTINGS_PATH = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "persona": "Enthusiastic leasing assistant",
    "tone_instructions": (
        "Excited about helping people find their new home. "
        "Always mention current specials. Proactively offer tour scheduling. "
        "Stay warm and conversational without pressuring prospects."
    ),
    "custom_knowledge": "",
    "do_list": [],
    "dont_list": [],
}


class AgentSettings(BaseModel):
    persona: str = _DEFAULTS["persona"]
    tone_instructions: str = _DEFAULTS["tone_instructions"]
    custom_knowledge: str = ""
    do_list: list[str] = []
    dont_list: list[str] = []


def load_settings() -> AgentSettings:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            return AgentSettings(**data)
        except Exception:
            pass
    return AgentSettings()


def save_settings(settings: AgentSettings) -> None:
    SETTINGS_PATH.write_text(settings.model_dump_json(indent=2))


def build_settings_block(settings: AgentSettings) -> str:
    """Return a system prompt block from the current settings.

    This block is injected into EVERY request regardless of intent routing.
    It is placed before the skills so it takes precedence.
    """
    parts: list[str] = []

    if settings.persona:
        parts.append(f"**Persona:** {settings.persona}")

    if settings.tone_instructions:
        parts.append(f"**Tone & instructions:** {settings.tone_instructions}")

    if settings.do_list:
        items = "\n".join(f"- {item}" for item in settings.do_list)
        parts.append(f"**Always do:**\n{items}")

    if settings.dont_list:
        items = "\n".join(f"- {item}" for item in settings.dont_list)
        parts.append(f"**Never do:**\n{items}")

    if settings.custom_knowledge:
        parts.append(
            f"**Custom knowledge (MANDATORY — review every response before replying):**\n"
            f"{settings.custom_knowledge}"
        )

    if not parts:
        return ""

    block = "\n\n".join(parts)
    return (
        "\n\n# Agent Configuration\n"
        "The following instructions are ALWAYS active. "
        "You MUST follow them on every response — they are never skipped.\n\n"
        + block
    )
