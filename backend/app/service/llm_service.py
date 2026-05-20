import asyncio
import math
import requests

from utils.prompts import build_messages

import os
from dotenv import load_dotenv

load_dotenv()


RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")

RUNPOD_ENDPOINT = (
    "https://api.runpod.ai/v2/"
    "gadpyoq0vav6tg/run"
)

RUNPOD_STATUS_ENDPOINT = (
    "https://api.runpod.ai/v2/"
    "gadpyoq0vav6tg/status"
)

RUNPOD_SELF_HOSTED_CHAT_COMPLETIONS_ENDPOINT = os.getenv(
    "RUNPOD_SELF_HOSTED_CHAT_COMPLETIONS_ENDPOINT"
)

RUNPOD_SELF_HOSTED_API_KEY = os.getenv(
    "RUNPOD_SELF_HOSTED_API_KEY"
)


HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}


LABELS = [
    "valid",
    "spam",
    "phishing"
]


def _build_self_hosted_headers():

    headers = {
        "Content-Type": "application/json"
    }

    if RUNPOD_SELF_HOSTED_API_KEY:
        headers["Authorization"] = (
            f"Bearer {RUNPOD_SELF_HOSTED_API_KEY}"
        )

    return headers


def _extract_prediction_and_logprobs(choice):

    if "message" in choice:
        prediction = (
            choice["message"]["content"]
            .strip()
            .lower()
        )
    else:
        tokens = choice.get("tokens", [])
        prediction = (
            "".join(tokens)
            .strip()
            .lower()
        )

    top_logprobs = []
    logprobs_data = choice.get("logprobs")

    try:
        if (
            isinstance(logprobs_data, dict)
            and "content" in logprobs_data
        ):

            content = logprobs_data["content"]

            if (
                isinstance(content, list)
                and len(content) > 0
            ):
                top_logprobs = (
                    content[0]
                    .get("top_logprobs", [])
                )

        elif (
            isinstance(logprobs_data, list)
            and len(logprobs_data) > 0
        ):

            top_logprobs = (
                logprobs_data[0]
                .get("top_logprobs", [])
            )

    except Exception as e:

        print(
            "Error parsing logprobs:",
            e
        )

    return prediction, top_logprobs


def _extract_prediction(choice):

    if "message" in choice:
        return (
            choice["message"]["content"]
            .strip()
            .lower()
        )

    tokens = choice.get("tokens", [])

    return (
        "".join(tokens)
        .strip()
        .lower()
    )


async def classify_email(email_text: str):

    if not RUNPOD_API_KEY:
        raise RuntimeError(
            "RUNPOD_API_KEY is not set"
        )

    messages = build_messages(email_text)

    payload = {
        "input": {
            "messages": messages,
            "sampling_params": {
                "temperature": 0.0,
                "max_tokens": 5,
            }
        }
    }


    response = requests.post(
        RUNPOD_ENDPOINT,
        headers=HEADERS,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()


    if data.get("status") in {
        "IN_QUEUE",
        "IN_PROGRESS"
    }:

        job_id = data.get("id")

        if not job_id:
            raise RuntimeError(
                f"Unexpected response from RunPod: {data}"
            )

        status_url = (
            f"{RUNPOD_STATUS_ENDPOINT}/{job_id}"
        )

        max_wait_seconds = 120
        poll_interval_seconds = 2

        waited = 0

        while waited < max_wait_seconds:

            await asyncio.sleep(
                poll_interval_seconds
            )

            waited += poll_interval_seconds

            status_resp = requests.get(
                status_url,
                headers=HEADERS,
                timeout=60
            )

            status_resp.raise_for_status()

            data = status_resp.json()

            if data.get("status") in {
                "COMPLETED",
                "FAILED"
            }:
                break

    if data.get("status") == "FAILED":

        raise RuntimeError(
            f"RunPod job failed: {data}"
        )

    raw_output = data

    if "output" in data:

        output = data["output"]

        if (
            isinstance(output, list)
            and len(output) > 0
        ):
            data = output[0]

        elif isinstance(output, dict):
            data = output

    if "choices" not in data:

        raise RuntimeError(
            f"Unexpected response from RunPod: {data}"
        )

    choice = data["choices"][0]


    prediction = _extract_prediction(choice)

    probabilities = {}
    confidence = 0.0
    needs_review = True

    print("\n========== RAW OUTPUT ==========")
    print(raw_output)

    return {
        "label": prediction,
        "confidence": round(
            confidence,
            4
        ),
        "needs_review": needs_review,
        "probabilities": probabilities,
        "raw_response": raw_output
    }


async def classify_email_self_hosted(
    email_text: str,
    endpoint: str | None = None
):

    target_endpoint = (
        endpoint
        or RUNPOD_SELF_HOSTED_CHAT_COMPLETIONS_ENDPOINT
    )

    if not target_endpoint:
        raise RuntimeError(
            "Self-hosted chat completions endpoint is not set"
        )

    messages = build_messages(email_text)

    payload = {
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 5,
        "logprobs": True,
        "top_logprobs": 5
    }

    response = requests.post(
        target_endpoint,
        headers=_build_self_hosted_headers(),
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    if "choices" not in data:
        raise RuntimeError(
            f"Unexpected response from self-hosted API: {data}"
        )

    choice = data["choices"][0]

    prediction, top_logprobs = (
        _extract_prediction_and_logprobs(
            choice
        )
    )

    scores = {}

    for token_data in top_logprobs:

        token = (
            token_data.get("token", "")
            .strip()
            .lower()
        )

        if token in LABELS:
            scores[token] = math.exp(
                token_data.get(
                    "logprob",
                    -100
                )
            )

    total = sum(scores.values())

    if total > 0:

        probabilities = {
            k: v / total
            for k, v in scores.items()
        }

        confidence = max(
            probabilities.values()
        )

        needs_review = (
            confidence < 0.85
        )

    else:

        probabilities = {}

        confidence = 0.0

        needs_review = True

    print("\n========== SELF-HOSTED RAW OUTPUT ==========")
    print(data)

    print("\n========== SELF-HOSTED TOP LOGPROBS ==========")
    print(top_logprobs)

    print("\n========== SELF-HOSTED PROBABILITIES ==========")
    print(probabilities)

    return {
        "label": prediction,
        "confidence": round(
            confidence,
            4
        ),
        "needs_review": needs_review,
        "probabilities": probabilities,
        "raw_response": data
    }