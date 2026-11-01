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


def test_logs_entry_from_photo_using_the_description_as_name(client, db, estimator):
    r = client.post("/entries/photo", files={"photo": JPEG}, data={"what": "chicken bowl", "fork": "on"})
    assert r.status_code == 200
    assert r.headers["HX-Trigger"] == "entry-logged"
    assert "640 kcal" in r.text and "About 500 g" in r.text
    assert estimator.calls == [(b"fake-jpeg", "image/jpeg", "chicken bowl", True)]
    [entry] = _entries(db)
    assert (entry.name, entry.calories, entry.protein, entry.fat, entry.carbs, entry.day) == (
        "chicken bowl", 640, 38.0, 22.5, 70.0, TODAY,
    )


def test_uses_claudes_name_without_a_description_and_honours_day(client, db, estimator):
    r = client.post("/entries/photo", files={"photo": JPEG}, data={"day": "2026-10-10"})
    assert r.status_code == 200
    assert estimator.calls[0][3] is False
    [entry] = _entries(db)
    assert entry.name == "Burrito bowl"
    assert entry.day.isoformat() == "2026-10-10"


def test_long_description_is_capped_to_the_name_column(client, db, estimator):
    client.post("/entries/photo", files={"photo": JPEG}, data={"what": "x" * 300})
    assert estimator.calls[0][2] == "x" * 300
    assert len(_entries(db)[0].name) == 100


def test_estimate_failure_logs_nothing_and_reports_why(client, db, estimator):
    estimator.result = EstimateError("Couldn't reach Claude. Try again.")
    r = client.post("/entries/photo", files={"photo": JPEG})
    assert r.status_code == 502
    assert r.headers["X-Error-Message"] == "Couldn't reach Claude. Try again."
    assert "HX-Trigger" not in r.headers
    assert _entries(db) == []


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"files": {"photo": ("a.heic", b"x", "image/heic")}}, 415),
        ({"files": {"photo": ("a.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")}}, 413),
        ({"files": {"photo": ("a.jpg", b"", "image/jpeg")}}, 400),
        ({"data": {"what": "no photo"}}, 400),
        ({"files": {"photo": JPEG}, "data": {"what": "x" * 501}}, 400),
    ],
)
def test_bad_uploads_never_reach_claude(client, db, estimator, kwargs, status):
    r = client.post("/entries/photo", **kwargs)
    assert r.status_code == status
    assert r.headers["X-Error-Message"]
    assert estimator.calls == []
    assert _entries(db) == []


def test_oversized_body_is_rejected_before_parsing(client, db, estimator):
    r = client.post(
        "/entries/photo", content=b"x" * 16, headers={"Content-Type": "text/plain", "Content-Length": str(11 * 1024 * 1024)}
    )
    assert r.status_code == 413
    assert r.headers["X-Error-Message"] == "That photo is too large."
    assert estimator.calls == []


def test_extra_files_are_refused(client, db, estimator):
    r = client.post("/entries/photo", files=[("photo", JPEG), ("other", JPEG)])
    assert r.status_code == 400
    assert estimator.calls == []
    assert _entries(db) == []


def test_photo_route_is_off_without_a_key(client, db):
    assert client.post("/entries/photo", files={"photo": JPEG}).status_code == 404
    assert _entries(db) == []


def test_log_sheet_hides_the_photo_row_without_a_key(client):
    r = client.get(f"/log-sheet?day={TODAY.isoformat()}")
    assert "Log from a photo" not in r.text
    assert 'id="entry-form"' in r.text


def test_request_text_includes_fork_and_description():
    assert build_request_text("", False) == "Estimate the macros for the food in this photo."
    text = build_request_text("ramen", True)
    assert "fork" in text and "The food is: ramen." in text


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
