from datetime import timedelta

from app.services.entries import create_entry
from app.services.macros import Macros
from app.services.weight import get_weigh_in, recent_weigh_ins, save_weigh_in
from tests.conftest import TODAY


def test_weight_page_empty_shows_input_and_hint(client):
    r = client.get("/weight")
    assert r.status_code == 200
    assert 'id="weigh-card"' in r.text
    assert 'name="weight"' in r.text
    assert "Weigh yourself each morning" in r.text
    assert "weightChart" not in r.text


def test_weight_page_with_data(client, db):
    for n in range(20, 0, -1):
        day = TODAY - timedelta(days=n)
        save_weigh_in(db, day, 190 - 0.1 * (20 - n))
        create_entry(db, day=day, macros=Macros(2200, 150, 70, 200))
    r = client.get("/weight")
    assert "Yesterday 188.1" in r.text
    assert 'x-data="weightChart(90)"' in r.text
    assert "your est.<br>maintenance" in r.text
    assert "By week" in r.text
    assert 'id="weigh-in-' in r.text


def test_weight_page_not_ready_shows_progress(client, db):
    save_weigh_in(db, TODAY - timedelta(days=1), 180)
    create_entry(db, day=TODAY - timedelta(days=1), macros=Macros(2000))
    r = client.get("/weight")
    assert "1 of 14 days" in r.text


def test_post_weight_saves_and_returns_body(client, db):
    save_weigh_in(db, TODAY - timedelta(days=1), 181.0)
    r = client.post("/weight", data={"weight": "180,4"})
    assert r.status_code == 200
    assert 'id="weight-body"' in r.text
    assert get_weigh_in(db, TODAY).weight == 180.4
    assert "180.4 <small>lb</small>" in r.text
    assert "−0.6 from yesterday" in r.text


def test_post_weight_twice_overwrites(client, db):
    client.post("/weight", data={"weight": "180"})
    client.post("/weight", data={"weight": "179.6"})
    assert [w.weight for w in recent_weigh_ins(db)] == [179.6]


def test_post_weight_invalid(client, db):
    for raw in ("", "abc", "20", "900"):
        r = client.post("/weight", data={"weight": raw})
        assert r.status_code == 422
        assert r.headers["HX-Retarget"] == "#weigh-card"
        assert 'class="error"' in r.text
    assert get_weigh_in(db, TODAY) is None


def test_card_edit_mode_prefills(client, db):
    save_weigh_in(db, TODAY, 180.2)
    r = client.get("/weight/card?edit=1")
    assert 'value="180.2"' in r.text and "Cancel" in r.text
    r = client.get("/weight/card")
    assert "Edit" in r.text and 'name="weight"' not in r.text


def test_edit_update_delete_weigh_in(client, db):
    day = TODAY - timedelta(days=2)
    row = save_weigh_in(db, day, 181.0)
    r = client.get(f"/weigh-ins/{row.id}/edit")
    assert 'value="181"' in r.text
    assert client.get(f"/weigh-ins/{row.id}/row").status_code == 200

    r = client.put(f"/weigh-ins/{row.id}", data={"weight": "x"})
    assert r.status_code == 422 and r.headers["HX-Retarget"] == f"#weigh-in-{row.id}"

    r = client.put(f"/weigh-ins/{row.id}", data={"weight": "182.5"})
    assert r.status_code == 200 and 'id="weight-body"' in r.text
    db.expire_all()
    assert get_weigh_in(db, day).weight == 182.5

    assert client.delete(f"/weigh-ins/{row.id}").status_code == 200
    db.expire_all()
    assert get_weigh_in(db, day) is None
    assert client.get("/weigh-ins/9999/edit").status_code == 404


def test_weight_data(client, db):
    save_weigh_in(db, TODAY, 180)
    data = client.get("/weight/data?days=30").json()
    assert len(data["labels"]) == 30 and data["weights"][-1] == 180.0
    assert client.get("/weight/data?days=3").status_code == 422
    assert client.get("/weight/data?days=400").status_code == 422
