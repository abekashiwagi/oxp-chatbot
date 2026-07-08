"""Input and output guardrails for the LeasingAI chatbot.

Mirrors the leasing-ai-agent guardrail chain (ADR-0004):
- Input: max length, sensitive financial data, blocked topics, prompt injection
- Output: PII redaction, internal ID scrubbing
"""

from __future__ import annotations

import re

MAX_INPUT_LENGTH = 4000

REFUSAL = (
    "I'm sorry, that's outside what I can help with. I can answer "
    "questions about this property — units, pricing, amenities, policies, "
    "hours, address — and walk you through booking a tour. What would "
    "you like to know?"
)

SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
BANK_ACCOUNT_PATTERN = re.compile(r"\b\d{8,17}\b")

SENSITIVE_FINANCIAL_PATTERNS = [SSN_PATTERN, CREDIT_CARD_PATTERN]

BLOCKED_TOPIC_KEYWORDS = [
    "credit score", "credit check", "criminal background", "criminal record",
    "felony", "misdemeanor", "arrest record", "eviction history",
    "bankruptcy", "foreclosure", "disability", "handicap",
    "race", "religion", "national origin", "familial status",
    "sexual orientation", "gender identity", "immigration status",
    "social security number", "ssn", "bank account number",
    "routing number", "credit card number",
]

PROMPT_INJECTION_SENTINELS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard your instructions",
    "forget your instructions",
    "you are now",
    "new instructions:",
    "system prompt:",
    "reveal your prompt",
    "show me your prompt",
    "what are your instructions",
    "print your system message",
]

OUT_OF_SCOPE_PATTERNS = [
    re.compile(r"what is the property.?id", re.IGNORECASE),
    re.compile(r"what.?s your (model|system|prompt)", re.IGNORECASE),
    re.compile(r"are you (chat\s*gpt|claude|gemini|ai|a bot)", re.IGNORECASE),
    re.compile(r"which (llm|model|ai) (are you|do you use)", re.IGNORECASE),
]

PHONE_PATTERN = re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
INTERNAL_ID_PATTERN = re.compile(r"\b(?:id|ID|Id)\s*[:=]?\s*\d{5,}\b")
RAW_NUMERIC_ID_PATTERN = re.compile(r"\b\d{6,}\b")

SAFE_NUMBERS = {"1062921", "50000", "84101"}


class GuardrailBlock(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def apply_input_guardrails(text: str) -> str:
    """Run input guardrails. Raises GuardrailBlock if blocked."""

    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]

    lower = text.lower()

    for pattern in SENSITIVE_FINANCIAL_PATTERNS:
        if pattern.search(text):
            raise GuardrailBlock(
                "For your security, please don't share sensitive financial "
                "information like Social Security or credit card numbers in chat. "
                "Our leasing team can help you securely at (801) 555-0142."
            )

    for keyword in BLOCKED_TOPIC_KEYWORDS:
        if keyword in lower:
            raise GuardrailBlock(
                "I'm not able to discuss that topic in this chat. For questions "
                "about applications and screening, please contact our leasing "
                "office directly at (801) 555-0142 or leasing@theresidences.com."
            )

    for sentinel in PROMPT_INJECTION_SENTINELS:
        if sentinel in lower:
            raise GuardrailBlock(REFUSAL)

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(text):
            raise GuardrailBlock(REFUSAL)

    return text


def apply_output_guardrails(text: str) -> str:
    """Run output guardrails — redact PII and internal IDs."""

    for match in EMAIL_PATTERN.finditer(text):
        email = match.group()
        if "theresidences" in email.lower() or "entrata" in email.lower():
            continue
        parts = email.split("@")
        if len(parts) == 2:
            redacted = parts[0][:2] + "***@" + parts[1]
            text = text.replace(email, redacted)

    text = INTERNAL_ID_PATTERN.sub("[ID redacted]", text)

    return text
