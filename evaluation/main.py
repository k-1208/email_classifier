# local_llm_inference_hf.py

from transformers import AutoTokenizer, AutoModelForCausalLM
import json
from pathlib import Path
from typing import Any, Dict, List
import torch
import time

# ============================================
# HUGGING FACE MODEL
# ============================================

# Replace with any HF model you want
MODEL_NAME = "kugu/email_classification"
# ============================================
# LOAD TOKENIZER
# ============================================

print("Loading tokenizer from Hugging Face...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

# ============================================
# LOAD MODEL
# ============================================

print("Loading model from Hugging Face on CPU...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    device_map="cpu",
    trust_remote_code=True,
    low_cpu_mem_usage=True
)

print("Model loaded successfully!")

DATA_PATH = Path("spam_normal_emails.jsonl")
OUTPUT_PATH = Path("evaluation_results.json")

LABEL_MAP = {
    "0": "valid",
    "1": "spam",
    "safe": "valid",
    "valid": "valid",
    "spam": "spam",
    "phishing": "phishing",
}

def build_prompt(email_text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI cybersecurity assistant trained to classify "
                "emails into phishing, spam, or valid categories. "
                "Respond with ONLY a JSON object and nothing else. "
                "Schema: {\"label\": \"phishing|spam|valid\", "
                "\"confidence\": number between 0 and 1}."
            )
        },
        {
            "role": "user",
            "content": f"""
Classify this email.

Email:
{email_text}
"""
        }
    ]

    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

    parts = []
    for message in messages:
        parts.append(f"{message['role']}: {message['content'].strip()}")
    return "\n\n".join(parts)

def normalize_label(raw: str) -> str:
    lowered = raw.strip().lower()
    for label in ("phishing", "spam", "valid", "safe"):
        if label in lowered:
            return "valid" if label == "safe" else label
    return ""

def normalize_eval_label(label: str) -> str:
    lowered = label.strip().lower()
    if lowered == "phishing":
        return "spam"
    return lowered

def extract_json(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

def parse_prediction(text: str) -> Dict[str, Any]:
    payload = extract_json(text)
    label = ""
    confidence = None

    if isinstance(payload, dict):
        raw_label = payload.get("label", "")
        if isinstance(raw_label, str):
            label = normalize_label(raw_label)
        raw_conf = payload.get("confidence", None)
        if isinstance(raw_conf, (int, float)):
            confidence = max(0.0, min(1.0, float(raw_conf)))

    if not label:
        label = normalize_label(text)

    return {"label": label, "confidence": confidence, "raw": text.strip()}

def predict_label(email_text: str) -> Dict[str, Any]:
    prompt = build_prompt(email_text)
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=10,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return parse_prediction(response)

print("\nRunning evaluation...\n")

start = time.time()
total = 0
correct = 0
unknown = 0
labels = ["spam", "valid"]
gold_counts = {label: 0 for label in labels}
correct_counts = {label: 0 for label in labels}
results: List[Dict[str, Any]] = []

with DATA_PATH.open("r", encoding="utf-8") as data_file:
    for line in data_file:
        if not line.strip():
            continue
        record = json.loads(line)
        text = record.get("text", "")
        gold_raw = str(record.get("spam", "")).strip()
        gold = normalize_eval_label(LABEL_MAP.get(gold_raw, ""))

        pred_payload = predict_label(text)
        pred_label_raw = pred_payload.get("label", "")
        pred_label = normalize_eval_label(pred_label_raw)
        if not pred_label:
            unknown += 1
        if pred_label == gold:
            correct += 1
            if gold in correct_counts:
                correct_counts[gold] += 1
        if gold in gold_counts:
            gold_counts[gold] += 1
        results.append(
            {
                "text": text,
                "gold": gold,
                "predicted": pred_label,
                "predicted_raw": pred_label_raw,
                "confidence": pred_payload.get("confidence", None),
                "raw_output": pred_payload.get("raw", ""),
            }
        )
        print(
            f"[{total + 1}] gold={gold or 'unknown'} pred={pred_label or 'unknown'} "
            f"raw={pred_label_raw or 'unknown'} conf={pred_payload.get('confidence', None)}"
        )
        total += 1

end = time.time()

accuracy = (correct / total) if total else 0.0

print("========== EVALUATION RESULT ==========")
print(f"Total: {total}")
print(f"Correct: {correct}")
print(f"Unknown predictions: {unknown}")
print(f"Accuracy: {accuracy:.4f}")
print("Per-class recall:")
for label in labels:
    denom = gold_counts[label]
    recall = (correct_counts[label] / denom) if denom else 0.0
    print(f"  {label}: {recall:.4f} ({correct_counts[label]}/{denom})")
print(f"Elapsed Time: {end - start:.2f} seconds")

summary = {
    "total": total,
    "correct": correct,
    "unknown": unknown,
    "accuracy": accuracy,
    "per_class_recall": {
        label: (
            (correct_counts[label] / gold_counts[label]) if gold_counts[label] else 0.0
        )
        for label in labels
    },
    "elapsed_seconds": end - start,
}

output_payload = {"summary": summary, "results": results}
OUTPUT_PATH.write_text(json.dumps(output_payload, ensure_ascii=True, indent=2))
print(f"Saved results to: {OUTPUT_PATH}")