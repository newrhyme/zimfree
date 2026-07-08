"""API endpoint assertions (Step 3)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schema import DB_PATH

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="app.db not built; run preprocess first"
)

# demo station codes
BUSAN = 113       # 부산역 (std_name 부산)
HAEUNDAE = 203    # 해운대
SEOMYEON1 = 119   # 서면 (line 1)
DADAEPO = 95      # 다대포해수욕장 (ALT_NONE elevators present)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_list_stations():
    r = client.get("/api/stations")
    data = r.json()
    assert r.status_code == 200
    assert len(data) == 114
    assert {"station_code", "line", "name", "std_name", "lat", "lng"} <= set(data[0])


def test_facilities_shape():
    r = client.get(f"/api/stations/{SEOMYEON1}/facilities")
    d = r.json()
    assert r.status_code == 200
    for k in ("lockers", "atms", "chargers", "kiosks"):
        assert isinstance(d[k], list)
    assert isinstance(d["elevators_count"], int)


def test_facilities_404():
    assert client.get("/api/stations/99999/facilities").status_code == 404


def test_congestion_seomyeon_friday_evening():
    # 2026-01-02 is a Friday; 18시 rush at 서면 should be 혼잡 or worse
    r = client.get(
        "/api/congestion",
        params={"station_code": SEOMYEON1, "date": "2026-01-02", "hour": 18, "io_type": "alight"},
    )
    d = r.json()
    assert r.status_code == 200
    assert d["level"] in ("혼잡", "매우혼잡")
    assert isinstance(d["better_hours"], list)


def test_route_plan_busan_to_haeundae():
    r = client.post(
        "/api/route/plan",
        json={
            "origin_code": BUSAN, "dest_code": HAEUNDAE,
            "luggage": {"size": "XL", "count": 2, "stroller": False},
            "battery_pct": 15, "depart_at": "2026-07-08T14:00",
        },
    )
    d = r.json()
    assert r.status_code == 200
    assert d["boarding"]["door_pos"] is not None
    assert d["num_transfers"] >= 1  # 부산(1호선) -> 해운대(2호선)
    assert "charging" in d  # battery < 30
    assert d["luggage_advice"]["recommendation"] in ("carry", "locker", "delivery")


def test_luggage_decision_delivery_prior():
    r = client.post(
        "/api/luggage/decision",
        json={"origin_code": BUSAN, "dest_code": HAEUNDAE,
              "luggage": {"size": "XL", "count": 2}},
    )
    d = r.json()
    assert r.status_code == 200
    assert d["recommendation"] == "delivery"
    assert any("flow_priors" in s for s in d["source_notes"])


def test_scenario_alt_none_impassable():
    # 다대포해수욕장 elevator 3/4 are ALT_NONE in ground truth
    r = client.post(
        "/api/scenario/elevator-outage",
        json={"station_code": DADAEPO, "elevator_id": "3"},
    )
    d = r.json()
    assert r.status_code == 200
    assert d["source"] == "data"
    assert d["passable"] is False


def test_scenario_passable_case():
    r = client.post(
        "/api/scenario/elevator-outage",
        json={"station_code": DADAEPO, "elevator_id": "1"},
    )
    d = r.json()
    assert r.status_code == 200
    assert d["passable"] is True


def test_assistant_status_or_disabled():
    r = client.get("/api/assistant/status")
    assert "enabled" in r.json()
    # without key, chat returns 501
    if not r.json()["enabled"]:
        assert client.post("/api/assistant/chat", json={"message": "hi"}).status_code == 501
