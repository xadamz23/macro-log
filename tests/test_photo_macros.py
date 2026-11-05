import json

import pytest

from app.deps import get_macro_estimator
from app.models import Entry
from app.services.macros import Macros
from app.services.photo_macros import EstimateError, PhotoEstimate, build_request_text, parse_estimate
from tests.conftest import TODAY

JPEG = ("meal.jpg", b"fake-jpeg", "image/jpeg")
ESTIMATE = PhotoEstimate(
    name="Burrito bowl", portion="About 500 g", macros=Macros(calories=640, protein=38.0, fat=22.5, carbs=70.0)
)


class FakeEstimator:
    def __init__(self, result=ESTIMATE):
        self.result = result
        self.calls = []

    async def __call__(self, image, media_type, description, has_fork):
        self.calls.append((image, media_type, description, has_fork))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def estimator(app):
    fake = FakeEstimator()
    app.dependency_overrides[get_macro_estimator] = lambda: fake
    return fake


def _entries(db):
    return db.query(Entry).all()


def test_photo_estimate_is_shown_to_check_and_logs_nothing(client, db, estimator):
    r = client.post("/entries/estimate", files={"photo": JPEG}, data={"what": "chicken bowl", "fork": "on"})
    assert r.status_code == 200
    assert "HX-Trigger" not in r.headers
    assert estimator.calls == [(b"fake-jpeg", "image/jpeg", "chicken bowl", True)]
    assert "Burrito bowl" in r.text and "640 kcal" in r.text and "About 500 g" in r.text
    assert 'hx-post="/entries"' in r.text
    for field in ('name="name" value="Burrito bowl"', 'name="calories" value="640"', 'name="protein" value="38"',
                  'name="fat" value="22.5"', 'name="carbs" value="70"', 'name="day" value=""'):
        assert field in r.text
    assert "Estimated from your photo." in r.text
    assert _entries(db) == []


def test_describe_only_estimate_sends_no_photo_or_fork(client, db, estimator):
    r = client.post("/entries/estimate", data={"what": "large coke from mcdonalds", "fork": "on", "day": "2026-10-10"})
    assert r.status_code == 200
    assert estimator.calls == [(None, None, "large coke from mcdonalds", False)]
    assert 'name="day" value="2026-10-10"' in r.text
    assert "with no photo" in r.text
    assert _entries(db) == []


def test_checked_estimate_logs_through_the_entries_route(client, db, estimator):
    r = client.post("/entries", data={"day": "", "name": "Burrito bowl", "calories": "640", "protein": "38", "fat": "22.5",
                                      "carbs": "70"})
    assert r.headers["HX-Trigger"] == "entry-logged"
    [entry] = _entries(db)
    assert (entry.name, entry.calories, entry.protein, entry.fat, entry.carbs, entry.day) == (
        "Burrito bowl", 640, 38.0, 22.5, 70.0, TODAY,
    )


def test_falls_back_to_the_description_when_claude_gives_no_name(client, estimator):
    estimator.result = PhotoEstimate(name="", portion="", macros=Macros(calories=100))
    r = client.post("/entries/estimate", data={"what": "x" * 300})
    assert estimator.calls[0][2] == "x" * 300
    assert f'name="name" value="{"x" * 100}"' in r.text


def test_estimate_failure_reports_why(client, db, estimator):
    estimator.result = EstimateError("Couldn't reach Claude. Try again.")
    r = client.post("/entries/estimate", files={"photo": JPEG})
    assert r.status_code == 502
    assert r.headers["X-Error-Message"] == "Couldn't reach Claude. Try again."
    assert _entries(db) == []


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"files": {"photo": ("a.heic", b"x", "image/heic")}}, 415),
        ({"files": {"photo": ("a.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")}}, 413),
        ({"files": {"photo": ("a.jpg", b"", "image/jpeg")}}, 400),
        ({"data": {"what": "   "}}, 400),
        ({}, 400),
        ({"files": {"photo": JPEG}, "data": {"what": "x" * 501}}, 400),
    ],
)
def test_bad_requests_never_reach_claude(client, db, estimator, kwargs, status):
    r = client.post("/entries/estimate", **kwargs)
    assert r.status_code == status
    assert r.headers["X-Error-Message"]
    assert estimator.calls == []
    assert _entries(db) == []


def test_oversized_body_is_rejected_before_parsing(client, db, estimator):
    r = client.post(
        "/entries/estimate", content=b"x" * 16, headers={"Content-Type": "text/plain", "Content-Length": str(11 * 1024 * 1024)}
    )
    assert r.status_code == 413
    assert r.headers["X-Error-Message"] == "That photo is too large."
    assert estimator.calls == []


def test_extra_files_are_refused(client, db, estimator):
    r = client.post("/entries/estimate", files=[("photo", JPEG), ("other", JPEG)])
    assert r.status_code == 400
    assert estimator.calls == []
    assert _entries(db) == []


def test_estimate_route_is_off_without_a_key(client, db):
    assert client.post("/entries/estimate", data={"what": "toast"}).status_code == 404
    assert _entries(db) == []


def test_log_sheet_hides_the_claude_row_without_a_key(client):
    r = client.get("/")
    assert "Log with Claude" not in r.text
    assert 'id="entry-form"' in r.text


def test_request_text_includes_fork_and_description():
    assert build_request_text("", False) == "Estimate the macros for the food in this photo."
    text = build_request_text("ramen", True)
    assert "fork" in text and "The food is: ramen." in text


def test_request_text_without_a_photo_is_just_the_description():
    text = build_request_text("large coke from mcdonalds", True, has_photo=False)
    assert text == "Estimate the macros for this food: large coke from mcdonalds."


def _reply(**overrides):
    return json.dumps({"name": "Soup", "portion": "1 bowl", "calories": 300.4, "protein": 20.04, "fat": 10, "carbs": 30}
                      | overrides)


def test_parse_estimate_rounds_to_the_apps_precision():
    estimate = parse_estimate(_reply())
    assert estimate.macros == Macros(calories=300, protein=20.0, fat=10.0, carbs=30.0)
    assert (estimate.name, estimate.portion) == ("Soup", "1 bowl")


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        '{"name": "Soup"}',
        _reply(calories=0, protein=0, fat=0, carbs=0),
        _reply(protein=-1),
        _reply(fat=2001),
        _reply(calories=20001),
        _reply(carbs="lots"),
        _reply(carbs=float("nan")),
    ],
)
def test_parse_estimate_rejects_unusable_replies(text):
    with pytest.raises(EstimateError):
        parse_estimate(text)
