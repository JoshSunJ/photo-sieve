"""Transport validation kept independent of ML and HTTP for inexpensive testing."""

import base64
import binascii
import math
from dataclasses import dataclass

MAX_BODY_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_PROMPTS = 12
MAX_PROMPT_LENGTH = 240


@dataclass(frozen=True)
class ScoreRequest:
    image: bytes
    prompts: tuple[str, ...]
    exclude_prompts: tuple[str, ...]
    threshold: float
    margin: float


def prompts_from(value: object, *, required: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > MAX_PROMPTS:
        raise ValueError(f"Prompts must be a list of at most {MAX_PROMPTS} strings")
    if any(not isinstance(item, str) for item in value):
        raise ValueError("Every prompt must be text")
    result = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
    if required and not result:
        raise ValueError("Enter at least one description")
    if any(len(item) > MAX_PROMPT_LENGTH for item in result):
        raise ValueError(f"Descriptions must be at most {MAX_PROMPT_LENGTH} characters")
    return result


def finite_number(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def parse_request(payload: object) -> ScoreRequest:
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    if payload.get("api_version") != 1:
        raise ValueError("api_version must be 1")
    encoded = payload.get("image_base64")
    if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES * 4 // 3 + 4):
        raise ValueError("Image is missing or too large")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Image is not valid base64") from exc
    if not image or len(image) > MAX_IMAGE_BYTES:
        raise ValueError("Image must contain 1 byte to 2 MiB")
    return ScoreRequest(
        image=image,
        prompts=prompts_from(payload.get("prompts"), required=True),
        exclude_prompts=prompts_from(payload.get("exclude_prompts", []), required=False),
        threshold=finite_number(payload.get("threshold", 0.25), "threshold", -1, 1),
        margin=finite_number(payload.get("margin", 0.02), "margin", 0, 2),
    )


def rank_scores(
    prompts: tuple[str, ...],
    include: list[float],
    exclude: list[float],
    threshold: float,
    margin: float,
) -> dict:
    """An OR across include prompts; optional contrast against keep descriptions."""
    if not prompts or len(prompts) != len(include):
        raise ValueError("Expected one score per include description")
    if any(
        not math.isfinite(score) or not -1.0001 <= score <= 1.0001 for score in include + exclude
    ):
        raise ValueError("Model returned an invalid cosine similarity")
    index = max(range(len(include)), key=include.__getitem__)
    score = max(-1.0, min(1.0, include[index]))
    keep_score = max(exclude) if exclude else None
    candidate = score >= threshold and (keep_score is None or score - keep_score >= margin)
    return {
        "api_version": 1,
        "score": score,
        "best_prompt": prompts[index],
        "keep_score": keep_score,
        "candidate": candidate,
        "scores": dict(zip(prompts, include, strict=True)),
    }
