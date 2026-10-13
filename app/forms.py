import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.services.macros import MACRO_KEYS, Macros, calories_from

GRAM_MAX = 2000
CALORIE_MAX = 20000
GRAM_KEYS = ("protein", "fat", "carbs")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "–"
    rounded = round(float(value), 1)
    return str(int(rounded)) if rounded.is_integer() else f"{rounded:.1f}"


def form_values(macros: Macros) -> dict[str, str]:
    return {key: fmt_num(getattr(macros, key)) for key in MACRO_KEYS}


@dataclass
class MacroForm:
    values: dict[str, str]
    errors: dict[str, str]
    macros: Macros | None

    @property
    def ok(self) -> bool:
        return not self.errors


def _number(raw: str, maximum: float) -> float | None:
    """Parse a user-typed number. Blank -> None. Raises ValueError with a message."""
    if raw == "":
        return None
    if "," in raw and not re.fullmatch(r"\d+,\d{1,2}", raw):
        raise ValueError("Must be a number")
    try:
        value = float(raw.replace(",", "."))
    except ValueError:
        raise ValueError("Must be a number") from None
    if not math.isfinite(value):
        raise ValueError("Must be a number")
    if value < 0 or value > maximum:
        raise ValueError(f"Must be between 0 and {maximum}")
    return value


def parse_macro_form(data: Mapping[str, Any]) -> MacroForm:
    values = {key: str(data.get(key) or "").strip() for key in MACRO_KEYS}
    errors: dict[str, str] = {}
    grams: dict[str, float] = {}
    for key in GRAM_KEYS:
        try:
            grams[key] = round(_number(values[key], GRAM_MAX) or 0.0, 1)
        except ValueError as exc:
            errors[key] = str(exc)
    calories: int | None = None
    try:
        raw_calories = _number(values["calories"], CALORIE_MAX)
        calories = None if raw_calories is None else round(raw_calories)
    except ValueError as exc:
        errors["calories"] = str(exc)
    if errors:
        return MacroForm(values, errors, None)

    if calories is None:
        calories = calories_from(grams["protein"], grams["fat"], grams["carbs"])
    macros = Macros(calories, grams["protein"], grams["fat"], grams["carbs"])
    if macros.is_zero():
        return MacroForm(values, {"form": "Enter at least one value"}, None)
    return MacroForm(values, {}, macros)


def parse_text(data: Mapping[str, Any], key: str, *, max_len: int, required: bool = False) -> tuple[str, str | None]:
    value = str(data.get(key) or "").strip()
    if required and not value:
        return value, "Required"
    if len(value) > max_len:
        return value, f"Max {max_len} characters"
    return value, None


def parse_servings(raw: str | None) -> float:
    if raw is None or str(raw).strip() == "":
        return 1.0
    value = float(str(raw).replace(",", "."))
    if not math.isfinite(value) or value <= 0 or value > 20:
        raise ValueError("Servings must be between 0 and 20")
    return value
