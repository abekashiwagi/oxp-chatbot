"""LeasingAI chatbot backend — FastAPI + OpenAI function calling.

Receives chat messages from the frontend widget, orchestrates with
OpenAI using all 38 leasing-mcp tool definitions, resolves tool calls
against mock data, and returns the assistant's response.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

from guardrails import GuardrailBlock, apply_input_guardrails, apply_output_guardrails
from intent_classifier.classify import predict_intent
from intent_classifier.labels import ALWAYS_INCLUDE, CONFIDENCE_THRESHOLD, INTENT_TO_SKILLS
from mock_data import resolve_tool
from sales_mode_store import SalesModeConfig, build_sales_mode_skill, load_sales_mode, save_sales_mode
from settings_store import AgentSettings, build_settings_block, load_settings, save_settings
from tools import TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("leasing-ai")

BASE_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "leasing-ai-agent" / "app" / "skills"
SKILLS: dict[str, str] = {}
if SKILLS_DIR.exists():
    for skill_file in sorted(SKILLS_DIR.glob("*.md")):
        if skill_file.name == "SKILLS.md":
            continue
        SKILLS[skill_file.stem] = skill_file.read_text()
log.info("Loaded %d skills from %s", len(SKILLS), SKILLS_DIR)

SKILLS_HEADER = (
    "\n\n# Available Skills\n"
    "Follow the matching skill exactly when the prospect's request aligns with its "
    "triggers. Walk one step per turn — one tool call, one reply.\n"
)


def build_system_prompt(skill_names: list[str], property_id: int | None = None) -> str:
    """Compose the system prompt with settings block + sales mode + property context + selected skills."""
    settings = load_settings()
    settings_block = build_settings_block(settings)
    sales_mode_block = "\n\n---\n" + build_sales_mode_skill()
    property_block = _build_property_context(property_id)
    prompt = BASE_PROMPT + settings_block + sales_mode_block + property_block + SKILLS_HEADER
    for name in skill_names:
        if name == "sales_mode":
            continue
        text = SKILLS.get(name)
        if text:
            prompt += f"\n---\n## Skill: {name}\n\n{text}\n"
    return prompt


def _build_property_context(property_id: int | None) -> str:
    """Generate a dynamic property context block from properties.json."""
    from mock_data import _load
    data = _load("properties.json")
    all_props = data.get("data", [])
    if not all_props:
        return ""

    active = None
    others = []
    for p in all_props:
        if p["id"] == property_id:
            active = p
        else:
            others.append(p)

    if active is None:
        active = all_props[0]
        others = all_props[1:]

    lines = [
        "\n\n# Active property context",
        f"- Property ID: {active['id']}",
        f"- Property Name: {active['property_name']}",
        f"- Rent range: ${active['min_rent']:,.0f} – ${active['max_rent']:,.0f}/mo",
        f"- Bedrooms: {active['min_bedrooms']}–{active['max_bedrooms']} BR",
        f"- Total units: {active['number_of_units']}",
    ]

    if others:
        lines.append("")
        lines.append("# Other portfolio properties (prospect can ask about these)")
        for p in others:
            lines.append(
                f"- {p['property_name']} (ID: {p['id']}) — "
                f"${p['min_rent']:,.0f}–${p['max_rent']:,.0f}/mo, "
                f"{p['min_bedrooms']}–{p['max_bedrooms']} BR, "
                f"{p['number_of_units']} units"
            )

    return "\n".join(lines)


def select_skills(message: str) -> list[str]:
    """Classify the message and return the skill subset to inject."""
    intent, confidence = predict_intent(message)
    if confidence >= CONFIDENCE_THRESHOLD:
        routed = INTENT_TO_SKILLS.get(intent, [])
        skill_names = [s for s in dict.fromkeys(routed + ALWAYS_INCLUDE) if s in SKILLS]
        if skill_names:
            log.info("Intent: %s (%.2f) → skills: %s", intent, confidence, skill_names)
            return skill_names
    log.info("Intent: %s (%.2f) below threshold → all skills", intent, confidence)
    return list(SKILLS.keys())

app = FastAPI(title="LeasingAI Chat Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


conversations: dict[str, list[dict]] = {}

MAX_TOOL_ROUNDS = 5


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    messages: list[dict] | None = None
    property_id: int | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())

    if req.messages and len(req.messages) > 0:
        history = [{"role": m["role"], "content": m["content"]} for m in req.messages]
    elif conversation_id in conversations:
        history = conversations[conversation_id]
    else:
        history = []

    try:
        cleaned_message = apply_input_guardrails(req.message)
    except GuardrailBlock as block:
        log.warning("Input guardrail blocked: %s", block.reason)
        return ChatResponse(response=block.reason, conversation_id=conversation_id)

    history.append({"role": "user", "content": cleaned_message})

    system_prompt = build_system_prompt(select_skills(cleaned_message), req.property_id)
    log.info("System prompt: %d chars (~%d tokens)", len(system_prompt), len(system_prompt) // 4)

    today_context = f"\n\nToday is {__import__('datetime').date.today().strftime('%A, %B %d, %Y')}."
    messages_for_api = [{"role": "system", "content": system_prompt + today_context}] + history

    try:
        assistant_message = await _run_conversation(messages_for_api)
    except Exception as exc:
        log.exception("OpenAI API error")
        raise HTTPException(status_code=502, detail=str(exc))

    assistant_message = apply_output_guardrails(assistant_message)

    history.append({"role": "assistant", "content": assistant_message})
    conversations[conversation_id] = history

    return ChatResponse(response=assistant_message, conversation_id=conversation_id)


async def _run_conversation(messages: list[dict]) -> str:
    """Run the OpenAI conversation loop, handling tool calls."""
    import os
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    for _round in range(MAX_TOOL_ROUNDS):
        response = await get_client().chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]

        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            return choice.message.content or "I'm here to help! What would you like to know about The Residences?"

        messages.append(choice.message.model_dump())

        for tool_call in choice.message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            log.info("Tool call: %s(%s)", tool_name, json.dumps(tool_args, default=str)[:200])

            result = resolve_tool(tool_name, tool_args)

            log.info("Tool result: %s → %s", tool_name, json.dumps(result, default=str)[:300])

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

    return "I gathered quite a bit of information! Let me know if you have any other questions about The Residences."


@app.get("/health")
async def health():
    return {"status": "ok", "service": "leasing-ai-chat"}


@app.get("/settings", response_model=AgentSettings)
async def get_settings():
    return load_settings()


@app.post("/settings", response_model=AgentSettings)
async def update_settings(settings: AgentSettings):
    save_settings(settings)
    log.info("Settings updated")
    return settings


@app.get("/sales-mode", response_model=SalesModeConfig)
async def get_sales_mode():
    return load_sales_mode()


@app.post("/sales-mode", response_model=SalesModeConfig)
async def update_sales_mode(config: SalesModeConfig):
    save_sales_mode(config)
    log.info("Sales mode updated: %s", config.mode_id)
    return config


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
