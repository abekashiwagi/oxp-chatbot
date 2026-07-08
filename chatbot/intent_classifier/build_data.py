"""Build labeled training data from production chat exports.

Reads the two xlsx exports, cleans the incoming prospect text, derives
an intent label from the tool call the production agent actually made,
balances classes, and writes data.jsonl next to this script.

Usage:
    python build_data.py "/path/to/Leasing May (1).xlsx" "/path/to/leasing chatbot (1).xlsx"
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import openpyxl

random.seed(42)

OUT_PATH = Path(__file__).parent / "data.jsonl"

# cancel_tour and update_prospect_name fold into TOUR_BOOKING — see labels.py.
TOOL_TO_INTENT = {
    "get_tour_calendar_availability": "TOUR_BOOKING",
    "schedule_tour": "TOUR_BOOKING",
    "schedule_tour_with_confirmation": "TOUR_BOOKING",
    "cancel_tour": "TOUR_BOOKING",
    "update_prospect_name": "TOUR_BOOKING",
    "get_unit_availability": "PROPERTY_INFO",
    "get_property_surroundings": "PROPERTY_INFO",
    "raise_office_escalation": "ESCALATION",
}

# Caps to keep the majority classes from swamping the minority ones.
CLASS_CAPS = {
    "GENERAL": 3000,
    "TOUR_BOOKING": 3000,
    "PROPERTY_INFO": 3000,
}

WRAPPER_RE = re.compile(r"^messages\s*-\s*\((.*)\)\s*$", re.DOTALL)

# Messages that carry no intent signal worth training on.
SKIP_PATTERNS = [
    re.compile(r"^stop$", re.IGNORECASE),
    re.compile(r"^unsubscribe$", re.IGNORECASE),
    re.compile(r'^liked\s+[“"]', re.IGNORECASE),
    re.compile(r'^loved\s+[“"]', re.IGNORECASE),
    re.compile(r'^emphasized\s+[“"]', re.IGNORECASE),
    re.compile(r'^disliked\s+[“"]', re.IGNORECASE),
]


def clean_text(raw: str) -> str | None:
    text = str(raw).strip()
    m = WRAPPER_RE.match(text)
    if m:
        text = m.group(1).strip()
    if not text or len(text) < 2:
        return None
    for pat in SKIP_PATTERNS:
        if pat.match(text):
            return None
    # Collapse whitespace; truncate very long messages (lead-form blobs)
    text = re.sub(r"\s+", " ", text)
    return text[:512]


def load_rows(xlsx_path: str) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["data"]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    incoming_idx = header.index("Incoming Text")
    tool_idx = header.index("Tool_Call 1")

    examples = []
    for row in rows[1:]:
        incoming = row[incoming_idx] if len(row) > incoming_idx else None
        tool_call = row[tool_idx] if len(row) > tool_idx else None
        if not incoming:
            continue
        text = clean_text(incoming)
        if not text:
            continue
        intent = TOOL_TO_INTENT.get(tool_call) if tool_call else "GENERAL"
        if intent is None:
            continue  # unknown tool — skip rather than mislabel
        examples.append({"text": text, "label": intent})
    return examples


def main(paths: list[str]) -> None:
    all_examples = []
    for p in paths:
        examples = load_rows(p)
        print(f"{p}: {len(examples)} usable examples")
        all_examples.extend(examples)

    # The same text often appears with contradictory labels (e.g. "can I
    # book a tour?" labeled GENERAL when the agent replied with a follow-up
    # question instead of calling a tool). Resolve by majority vote per
    # unique text, preferring a specific intent over GENERAL on ties.
    votes: dict[str, Counter] = {}
    text_case: dict[str, str] = {}
    for ex in all_examples:
        key = ex["text"].lower()
        votes.setdefault(key, Counter())[ex["label"]] += 1
        text_case.setdefault(key, ex["text"])

    deduped = []
    for key, counter in votes.items():
        top = counter.most_common()
        best_label, best_count = top[0]
        # Tie or near-tie involving GENERAL → prefer the specific intent
        specific = [(l, c) for l, c in top if l != "GENERAL"]
        if best_label == "GENERAL" and specific and specific[0][1] >= best_count * 0.8:
            best_label = specific[0][0]
        deduped.append({"text": text_case[key], "label": best_label})
    print(f"After majority-vote dedupe: {len(deduped)} examples")

    # Drop very short fragments ("ok", "yes") — their intent is purely
    # contextual and they poison the classifier. At runtime they fall to
    # the low-confidence path, which loads all skills anyway.
    deduped = [ex for ex in deduped if len(ex["text"].split()) >= 3]
    print(f"After short-fragment filter: {len(deduped)} examples")

    # Balance: cap majority classes
    by_label: dict[str, list[dict]] = {}
    for ex in deduped:
        by_label.setdefault(ex["label"], []).append(ex)

    final = []
    for label, items in by_label.items():
        cap = CLASS_CAPS.get(label)
        if cap and len(items) > cap:
            items = random.sample(items, cap)
        final.extend(items)
    random.shuffle(final)

    print("Final distribution:", Counter(ex["label"] for ex in final))

    with OUT_PATH.open("w") as f:
        for ex in final:
            f.write(json.dumps(ex) + "\n")
    print(f"Wrote {len(final)} examples to {OUT_PATH}")


if __name__ == "__main__":
    main(sys.argv[1:])
