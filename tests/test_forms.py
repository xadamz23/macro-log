import pytest

from app.forms import fmt_num, form_values, parse_macro_form, parse_servings, parse_text
from app.services.macros import Macros


def test_fmt_num():
    assert fmt_num(12.0) == "12"
    assert fmt_num(12.46) == "12.5"
    assert fmt_num(None) == "–"
    assert fmt_num(-3.0) == "-3"


def test_form_values():
    assert form_values(Macros(410, 30, 10.5, 50)) == {"calories": "410", "protein": "30", "fat": "10.5", "carbs": "50"}


def test_blank_calories_autofill_and_blank_grams_are_zero():
    form = parse_macro_form({"protein": "30", "fat": "", "carbs": "50", "calories": ""})
    assert form.ok
    assert form.macros == Macros(320, 30, 0, 50)


def test_explicit_calories_override_autofill():
    form = parse_macro_form({"protein": "30", "fat": "10", "carbs": "50", "calories": "450"})
    assert form.macros.calories == 450


def test_comma_decimal_accepted_and_rounded():
    form = parse_macro_form({"protein": "12,46", "fat": "0", "carbs": "0", "calories": ""})
    assert form.macros.protein == 12.5


@pytest.mark.parametrize("raw", ["-1", "abc", "nan", "inf", "5000"])
def test_invalid_grams_rejected(raw):
    form = parse_macro_form({"protein": raw, "fat": "1", "carbs": "1", "calories": ""})
    assert not form.ok
    assert "protein" in form.errors
    assert form.macros is None
    assert form.values["protein"] == raw


def test_invalid_calories_rejected():
    form = parse_macro_form({"protein": "1", "fat": "1", "carbs": "1", "calories": "-5"})
    assert "calories" in form.errors


def test_all_zero_rejected():
    form = parse_macro_form({"protein": "", "fat": "", "carbs": "", "calories": ""})
    assert form.errors == {"form": "Enter at least one value"}


def test_parse_text():
    assert parse_text({"name": "  Eggs "}, "name", max_len=100) == ("Eggs", None)
    assert parse_text({}, "name", max_len=100, required=True) == ("", "Required")
    assert parse_text({"name": "x" * 101}, "name", max_len=100)[1] == "Max 100 characters"


def test_parse_servings():
    assert parse_servings(None) == 1.0
    assert parse_servings("0.5") == 0.5
    for bad in ["0", "-1", "abc", "50"]:
        with pytest.raises(ValueError):
            parse_servings(bad)
