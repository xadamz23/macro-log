"""Estimate a meal's macros from a photo with the Claude API."""

import base64
import json
import logging
from dataclasses import dataclass
from typing import Protocol

import anthropic

from app.forms import CALORIE_MAX, GRAM_MAX
from app.services.macros import Macros

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You estimate the macros of a meal from a photo for a food log.

Estimate the combined totals for everything edible in the photo. Treat the user's description as more reliable than \
what you can see, and allow for ingredients a photo can't show, such as cooking oil and butter.

Give your best single estimate, not a range. Calories are in kcal; protein, fat and carbs are in grams. "name" is a \
short name for the meal, at most six words. "portion" is one short line stating the portion size you assumed.

If the photo shows no food, return zero for all four numbers."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "portion": {"type": "string"},
        "calories": {"type": "number"},
        "protein": {"type": "number"},
        "fat": {"type": "number"},
        "carbs": {"type": "number"},
    },
    "required": ["name", "portion", "calories", "protein", "fat", "carbs"],
    "additionalProperties": False,
}


class EstimateError(Exception):
    """An estimate couldn't be made. The message is safe to show the user."""


@dataclass(frozen=True)
class PhotoEstimate:
    name: str
    portion: str
    macros: Macros


class MacroEstimator(Protocol):
    async def __call__(self, image: bytes, media_type: str, description: str, has_fork: bool) -> PhotoEstimate: ...


def build_request_text(description: str, has_fork: bool) -> str:
    parts = ["Estimate the macros for the food in this photo."]
    if has_fork:
        parts.append("There's a regular dinner fork in the shot for scale.")
    if description:
        parts.append(f"The food is: {description}.")
    return " ".join(parts)


def parse_estimate(text: str) -> PhotoEstimate:
    try:
        data = json.loads(text)
        name, portion = str(data["name"]).strip(), str(data["portion"]).strip()
        calories, protein, fat, carbs = (float(data[key]) for key in ("calories", "protein", "fat", "carbs"))
    except (ValueError, KeyError, TypeError) as err:
        raise EstimateError("Couldn't read the estimate. Try again.") from err

    # float() accepts NaN and inf, which every comparison below rejects or catches.
    in_range = 0 <= calories <= CALORIE_MAX and all(0 <= grams <= GRAM_MAX for grams in (protein, fat, carbs))
    if not in_range:
        raise EstimateError("The estimate looked wrong. Try again or log it manually.")
    macros = Macros(calories=round(calories), protein=round(protein, 1), fat=round(fat, 1), carbs=round(carbs, 1))
    if macros.is_zero():
        raise EstimateError("Couldn't find any food in that photo.")
    return PhotoEstimate(name=name, portion=portion, macros=macros)


class ClaudeMacroEstimator:
    def __init__(self, api_key: str, model: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=60.0, max_retries=1)
        self._model = model

    async def __call__(self, image: bytes, media_type: str, description: str, has_fork: bool) -> PhotoEstimate:
        try:
            response = await self._client.beta.messages.create(
                model=self._model,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64.standard_b64encode(image).decode("ascii"),
                                },
                            },
                            {"type": "text", "text": build_request_text(description, has_fork)},
                        ],
                    }
                ],
            )
        except anthropic.AuthenticationError as err:
            log.error("Claude API rejected the key: %s", err.message)
            raise EstimateError("The Claude API key was rejected.") from err
        except anthropic.RateLimitError as err:
            raise EstimateError("Claude is rate limited right now. Try again in a minute.") from err
        except anthropic.APIConnectionError as err:  # includes timeouts
            log.warning("Claude API unreachable: %s", err)
            raise EstimateError("Couldn't reach Claude. Try again.") from err
        except anthropic.APIStatusError as err:
            log.error("Claude API error %s: %s", err.status_code, err.message)
            raise EstimateError("Claude couldn't estimate that photo. Try again or log it manually.") from err

        if response.stop_reason == "refusal":
            raise EstimateError("Claude declined to estimate that photo. Log it manually.")
        if response.stop_reason == "max_tokens":
            raise EstimateError("The estimate was cut off. Try again.")
        text = next((block.text for block in response.content if block.type == "text"), "")
        return parse_estimate(text)
