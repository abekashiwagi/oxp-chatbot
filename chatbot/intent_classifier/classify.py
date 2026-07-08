"""Runtime intent prediction for the chatbot backend.

Lazily loads the fine-tuned DistilBERT from ./model/ on first call.
If the model directory doesn't exist (not trained yet), predict_intent
returns ("GENERAL", 0.0) so the server falls back to loading all skills.
"""

from __future__ import annotations

import logging
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "model"

log = logging.getLogger("leasing-ai.intent")

_model = None
_tokenizer = None
_device = None


def _load():
    global _model, _tokenizer, _device
    if _model is not None:
        return True
    if not MODEL_DIR.exists():
        return False
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    _device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(_device)
    _model.eval()
    log.info("Intent classifier loaded from %s (device=%s)", MODEL_DIR, _device)
    return True


def predict_intent(text: str) -> tuple[str, float]:
    """Return (intent_label, confidence) for a prospect message."""
    if not _load():
        return "GENERAL", 0.0

    import torch

    inputs = _tokenizer(
        text, truncation=True, max_length=128, return_tensors="pt"
    ).to(_device)
    with torch.no_grad():
        logits = _model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    idx = int(probs.argmax())
    label = _model.config.id2label[idx]
    return label, float(probs[idx])


if __name__ == "__main__":
    import sys

    msg = " ".join(sys.argv[1:]) or "Can I book a tour for Saturday?"
    intent, conf = predict_intent(msg)
    print(f"{msg!r} -> {intent} ({conf:.3f})")
