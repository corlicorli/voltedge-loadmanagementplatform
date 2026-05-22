"""API/integration tests against a running PostgreSQL (skipped if unreachable).

The TestClient triggers the app lifespan, which runs migrations and seeds the
YN load area, so these exercise the real DDD stack through HTTP.
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


def test_adjustments_endpoint(api_client):
    response = api_client.get("/load-areas/YN/adjustments?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_analytics_kpis(api_client):
    response = api_client.get("/analytics/YN/kpis")
    assert response.status_code == 200
    assert "currentUtilisationPct" in response.json()


def test_forecast_returns_requested_horizon(api_client):
    response = api_client.get("/analytics/YN/forecast?horizon_hours=6")
    assert response.status_code == 200
    assert len(response.json()["points"]) == 6


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
