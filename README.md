# Email Classification Fine-Tune Repo

This repo contains the end-to-end data pipeline, training notebook, evaluation script, and a minimal API + frontend for email classification (valid/spam/phishing).

## What is inside

- Data sources and raw datasets: [dataset/](dataset/) and [dataset_part2/](dataset_part2/)
- Data analysis + cleaning notebooks:
  - [dataset/merge_dataset.ipynb](dataset/merge_dataset.ipynb)
  - [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb)
  - [dataset/eval_dataset/clean.ipynb](dataset/eval_dataset/clean.ipynb)
  - [dataset_part2/main.ipynb](dataset_part2/main.ipynb)
  - [dataset_part2/cleaned/merge.ipynb](dataset_part2/cleaned/merge.ipynb)
  - [dataset_part2/cleaned/extra_clean/merge.ipynb](dataset_part2/cleaned/extra_clean/merge.ipynb)
  - [dataset_part2/cleaned/extra_clean/final/final.ipynb](dataset_part2/cleaned/extra_clean/final/final.ipynb)
- Training notebook: [trainer_8b_llama_8b_instruct.ipynb](trainer_8b_llama_8b_instruct.ipynb)
- Evaluation script: [evaluation/main.py](evaluation/main.py)
- Backend API: [backend/app/main.py](backend/app/main.py)
- Prompt template for inference: [backend/app/utils/prompts.py](backend/app/utils/prompts.py)
- Frontend UI: [frontend/](frontend/)

## Data analysis and processing (repo-wide)

This section summarizes the data analysis and preparation pipeline across the notebooks and datasets in this repo.

### 1) Source conversions and dataset slicing

From [dataset/merge_dataset.ipynb](dataset/merge_dataset.ipynb):
- CSV to JSONL conversions for raw sources (e.g., `phishing_legit_dataset_KD_10000.csv`, `Nigerian_Fraud.csv`, `Nazario.csv`).
- Split the PhishFuzzer JSON into separate JSONL files by `Type` (spam, valid, phishing).
- Extract a "legitimate" subset from `phishing_legit_dataset_KD_10000.jsonl`.
- Parse "Subject:" prefixes into a dedicated `subject` field for some datasets.
- Remove personal metadata fields (`sender`, `receiver`, `date`) from CEAS and Nigerian Fraud datasets.
- Extract URL lists + URL counts into CEAS records.
- Sample a subset of phishing rows from KD-10000 (label 1) to build a small phishing sample file.

### 2) Balanced class sampling and normalization

From [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb):
- Sample a fixed number of records per class (valid/spam/phishing) across multiple sources.
- Normalize different schemas into a consistent shape with `subject`, `body`, `urls`, and `label`.
- Map numeric labels to string labels (`0 -> valid`, `1 -> spam`, `2 -> phishing`).

### 3) Text cleaning and filtering

From [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb):
- Clean HTML, URLs, repeated characters, control characters, and extra whitespace.
- Drop empty emails, very short emails, and extremely long emails.

From [dataset_part2/main.ipynb](dataset_part2/main.ipynb):
- Clean CSV datasets (normalize whitespace, remove zero-width chars, drop non-ASCII if configured).
- Drop rows missing body/subject, or those matching subject blacklists.
- Deduplicate exact duplicates and remove exact text duplicates.
- Embedding-based near-duplicate removal with sentence-transformers.

### 4) Token length analysis and max-length filtering

From [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb):
- Compute token length stats (global and per-class) using a tokenizer.
- Report % of samples exceeding common context lengths.
- Filter out samples above a configured token limit (e.g., 2048 tokens).

### 5) Metadata feature engineering

From [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb):
- Add metadata features such as keyword counts, URL features, entropy, caps ratio, etc.

From [dataset_part2/cleaned/extra_clean/final/final.ipynb](dataset_part2/cleaned/extra_clean/final/final.ipynb):
- Add a fixed metadata schema with phishing-related features (URL indicators, urgency language, uppercase counts, length, etc.).

### 6) Instruction / SFT dataset generation

From [dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb](dataset/cleaned_dataset/cleaning_Dataset_phase2.ipynb):
- Convert cleaned rows into instruction-style JSONL with `messages` and separate metadata.
- Deduplicate the instruction dataset by hashing user+assistant content.

From [dataset_part2/cleaned/extra_clean/final/final.ipynb](dataset_part2/cleaned/extra_clean/final/final.ipynb):
- Convert final dataset rows into SFT chat format: system prompt + user email + assistant label.
- Validate JSONL for broken lines.

### 7) Label normalization and class balancing (part2)

From [dataset_part2/cleaned/merge.ipynb](dataset_part2/cleaned/merge.ipynb):
- Normalize label mappings for CEAS and Nazario datasets.
- Map `full_dataset` categories to `valid/spam/marketing`.

From [dataset_part2/cleaned/extra_clean/merge.ipynb](dataset_part2/cleaned/extra_clean/merge.ipynb):
- Convert `spam -> phishing` for a specific dataset variant.
- Build a final dataset with target class counts and shuffle.

## Training flow

From [trainer_8b_llama_8b_instruct.ipynb](trainer_8b_llama_8b_instruct.ipynb):
- Install Unsloth + TRL and load `meta-llama/Llama-3.1-8B-Instruct`.
- Apply LoRA (PEFT) for fine-tuning.
- Load a final SFT JSONL dataset (`final_dataset.sft.jsonl`).
- Shuffle and split train/eval.
- Format messages for chat training and run `SFTTrainer`.
- Save merged weights and optionally upload to Hugging Face.

## Evaluation flow

From [evaluation/main.py](evaluation/main.py):
- Load a Hugging Face model (`kugu/email_classification`) on CPU.
- Run inference on [evaluation/spam_normal_emails.jsonl](evaluation/spam_normal_emails.jsonl).
- Normalize labels and report accuracy + per-class recall.
- Save per-row predictions to `evaluation_results.json`.

## API (backend) behavior

From [backend/app/main.py](backend/app/main.py) and [backend/app/service/llm_service.py](backend/app/service/llm_service.py):
- `POST /classify` accepts `{ "email_text": "..." }` and returns a label.
- Uses RunPod async endpoint by default and polls for completion.
- Optional self-hosted endpoint for logprob-based confidence.
- Prompt template is defined in [backend/app/utils/prompts.py](backend/app/utils/prompts.py).

## How to start (local)

### 1) Backend API

1. Create and activate a virtual environment.
2. Install dependencies (minimum imports seen in code):

```bash
pip install fastapi uvicorn requests python-dotenv
```

3. Create a `.env` file in the repo root with placeholders:

```env
RUNPOD_API_KEY=YOUR_RUNPOD_API_KEY
RUNPOD_SELF_HOSTED_CHAT_COMPLETIONS_ENDPOINT=YOUR_SELF_HOSTED_ENDPOINT
RUNPOD_SELF_HOSTED_API_KEY=YOUR_SELF_HOSTED_API_KEY
```

4. Start the API server:

```bash
python backend/app/main.py
```

The API listens on `http://localhost:8001`.

### 2) Frontend UI

From [frontend/README.md](frontend/README.md):

```bash
cd frontend
npm install
npm run dev
```

The UI runs on `http://localhost:3000`.

### 3) Training notebook

Open [trainer_8b_llama_8b_instruct.ipynb](trainer_8b_llama_8b_instruct.ipynb) and run the cells in order. The notebook installs its own training dependencies and expects a final SFT JSONL file (`final_dataset.sft.jsonl`) in the working directory.

### 4) Evaluation

```bash
python evaluation/main.py
```

This reads [evaluation/spam_normal_emails.jsonl](evaluation/spam_normal_emails.jsonl) and writes `evaluation_results.json`.

## Key datasets produced

- `combined.jsonl`, `combined_normalized.jsonl`, `combined_cleaned.jsonl`, `combined_final.jsonl`, `combined_with_metadata.jsonl`
- `instruction_dataset.jsonl`, `instruction_dataset_dedup.jsonl`
- `final_dataset.jsonl`, `final_dataset.no_urls.jsonl`, `final_dataset.with_metadata.jsonl`, `final_dataset.sft.jsonl`
