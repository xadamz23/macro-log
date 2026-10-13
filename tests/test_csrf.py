from app.services.entries import list_entries
from tests.conftest import TODAY


def test_cross_site_post_rejected(client, db):
    r = client.post("/entries", data={"protein": "10"}, headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
    assert list_entries(db, TODAY) == []


def test_foreign_origin_rejected(client, db):
    r = client.post("/entries", data={"protein": "10"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert list_entries(db, TODAY) == []


def test_same_origin_allowed(client, db):
    headers = {"Sec-Fetch-Site": "same-origin", "Origin": "http://testserver"}
    assert client.post("/entries", data={"protein": "10"}, headers=headers).status_code == 200


def test_cross_site_get_still_allowed(client):
    assert client.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 200
