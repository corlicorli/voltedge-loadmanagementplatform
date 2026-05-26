"""API/integration tests against a running MongoDB (skipped if unreachable).

The TestClient triggers the app lifespan (ensures indexes); the conftest fixture
builds the YN area + 24 chargers + baseline via the API, so these exercise the
real DDD stack through HTTP.
"""
import pytest

pytestmark = pytest.mark.integration


def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_status_returns_camelcase_contract(api_client):
    response = api_client.get("/load-areas/YN/status")
    assert response.status_code == 200
    body = response.json()
    assert body["areaCode"] == "YN"
    assert "currentLoadKw" in body
    assert "maxCapacityKw" in body
    assert body["status"] in ("STABLE", "WARNING", "CRITICAL")


def test_unknown_area_returns_404(api_client):
    assert api_client.get("/load-areas/ZZ/status").status_code == 404


def test_start_session_keeps_load_below_max(api_client):
    response = api_client.post(
        "/load-areas/YN/sessions", json={"chargerId": "YN-23", "powerLevelKw": 11}
    )
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["sessionId"], str)
    area = body["areaStatus"]
    assert area["currentLoadKw"] <= area["maxCapacityKw"] + 0.001


def test_invalid_power_is_rejected(api_client):
    response = api_client.post(
        "/load-areas/YN/sessions", json={"chargerId": "YN-01", "powerLevelKw": 0}
    )
    assert response.status_code == 422


def test_unknown_charger_is_rejected(api_client):
    response = api_client.post(
        "/load-areas/YN/sessions", json={"chargerId": "DOES-NOT-EXIST", "powerLevelKw": 11}
    )
    assert response.status_code == 422


def test_list_areas_includes_yn(api_client):
    response = api_client.get("/load-areas")
    assert response.status_code == 200
    assert "YN" in [a["areaCode"] for a in response.json()]


def test_create_duplicate_area_conflicts(api_client):
    response = api_client.post(
        "/load-areas",
        json={"areaCode": "YN", "areaName": "Ydre Nørrebro", "maxCapacityKw": 240},
    )
    assert response.status_code == 409


def test_onboard_separate_area_and_register_charger(api_client):
    # Onboard a separate area so YN keeps exactly its 24 stations.
    created = api_client.post(
        "/load-areas",
        json={"areaCode": "TST", "areaName": "Test Area", "maxCapacityKw": 100},
    )
    assert created.status_code == 201
    charger = api_client.post(
        "/load-areas/TST/chargers", json={"chargerId": "TST-01", "maxPowerKw": 11}
    )
    assert charger.status_code == 201
    listed = api_client.get("/load-areas/TST/chargers")
    assert listed.status_code == 200
    assert any(c["chargerId"] == "TST-01" for c in listed.json())


def test_adjustments_endpoint(api_client):
    response = api_client.get("/load-areas/YN/adjustments?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_analytics_kpis(api_client):
    response = api_client.get("/analytics/YN/kpis")
    assert response.status_code == 200
    assert "currentUtilisationPct" in response.json()


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/YN/load-timeseries?hours=24",
        "/analytics/YN/hourly-utilisation?hours=48",
        "/analytics/YN/daily-peaks?days=7",
        "/analytics/YN/status-distribution?days=7",
        "/analytics/YN/regulation-events?limit=10",
    ],
)
def test_analytics_list_endpoints(api_client, path):
    response = api_client.get(path)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_charger_by_id_free(api_client):
    response = api_client.get("/load-areas/YN/chargers/YN-24")  # free at baseline
    assert response.status_code == 200
    c = response.json()
    assert c["chargerId"] == "YN-24"
    assert c["name"]
    assert c["occupancyStatus"] == "AVAILABLE"
    assert c["currentOutputKw"] == 0
    assert c["connectivity"] in ("ONLINE", "OFFLINE")


def test_occupied_charger_reports_output(api_client):
    response = api_client.get("/load-areas/YN/chargers/YN-01")  # has a baseline session
    assert response.status_code == 200
    c = response.json()
    assert c["occupancyStatus"] == "OCCUPIED"
    assert c["currentOutputKw"] > 0


def test_charger_heartbeat_marks_online(api_client):
    response = api_client.post("/load-areas/YN/chargers/YN-24/heartbeat")
    assert response.status_code == 200
    assert response.json()["connectivity"] == "ONLINE"


def test_get_unknown_charger_returns_404(api_client):
    assert api_client.get("/load-areas/YN/chargers/NOPE").status_code == 404
