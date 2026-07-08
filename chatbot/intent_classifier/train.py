"""Fine-tune DistilBERT on the labeled intent data.

Reads data.jsonl (produced by build_data.py), trains a sequence
classifier, prints per-class F1 on a held-out validation split, and
saves the model + tokenizer to ./model/.

Usage:
    python train.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from labels import ID2LABEL, LABEL2ID, LABELS

DATA_PATH = Path(__file__).parent / "data.jsonl"
MODEL_DIR = Path(__file__).parent / "model"
BASE_MODEL = "distilbert-base-uncased"
EPOCHS = 3
BATCH_SIZE = 32
LR = 2e-5
MAX_LENGTH = 128
SEED = 42

torch.manual_seed(SEED)


class IntentDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer):
        self.encodings = tokenizer(
            texts, truncation=True, padding=True, max_length=MAX_LENGTH, return_tensors="pt"
        )
        self.labels = torch.tensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": self.labels[idx],
        }


def main() -> None:
    examples = [json.loads(line) for line in DATA_PATH.read_text().splitlines()]
    texts = [ex["text"] for ex in examples]
    labels = [LABEL2ID[ex["label"]] for ex in examples]

    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=SEED, stratify=labels
    )
    print(f"Train: {len(train_texts)}, Val: {len(val_texts)}")

    device = torch.device(
        "mps" if torch.backends.mps.is_available() else "cpu"
    )
    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    ).to(device)

    train_ds = IntentDataset(train_texts, train_labels, tokenizer)
    val_ds = IntentDataset(val_texts, val_labels, tokenizer)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)

    # Square-root inverse-frequency class weights: boosts minority classes
    # (ESCALATION) without collapsing their precision the way full
    # inverse-frequency weighting does.
    counts = np.bincount(train_labels, minlength=len(LABELS)).astype(np.float64)
    weights = np.sqrt(counts.sum() / (len(LABELS) * np.maximum(counts, 1)))
    class_weights = torch.tensor(weights, dtype=torch.float32).to(device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)
    print("Class weights:", {LABELS[i]: round(float(w), 2) for i, w in enumerate(weights)})

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader):
            batch = {k: v.to(device) for k, v in batch.items()}
            labels_batch = batch.pop("labels")
            optimizer.zero_grad()
            logits = model(**batch).logits
            loss = loss_fn(logits, labels_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            if step % 50 == 0:
                print(f"epoch {epoch + 1} step {step}/{len(train_loader)} loss {loss.item():.4f}", flush=True)
        print(f"epoch {epoch + 1} mean loss {total_loss / len(train_loader):.4f}", flush=True)

    # Validation report
    model.eval()
    preds, golds = [], []
    with torch.no_grad():
        for batch in val_loader:
            labels_batch = batch.pop("labels")
            batch = {k: v.to(device) for k, v in batch.items()}
            logits = model(**batch).logits
            preds.extend(logits.argmax(dim=-1).cpu().numpy())
            golds.extend(labels_batch.numpy())

    print("\nValidation report:")
    print(classification_report(
        golds, preds,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        zero_division=0,
    ))

    MODEL_DIR.mkdir(exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    print(f"Saved model to {MODEL_DIR}")


if __name__ == "__main__":
    main()
