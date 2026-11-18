"""API tests: access control, validation, and the main SOC endpoints."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_service import FAKE_KYC, Clock, fake_toolkit

TOKEN = "test-token-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("API_TOKEN", TOKEN)
    svc = SunoSafeService(Store(tmp_path / "api.db"), fake_toolkit, Clock())
    main.app.dependency_overrides[main.get_service] = lambda: svc
    main._hits.clear()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def test_requests_without_token_are_rejected(client):
    assert client.get("/api/incidents").status_code == 401
    assert client.get("/api/incidents", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/incidents", headers=AUTH).status_code == 200


def test_without_api_token_only_localhost_is_allowed(client, monkeypatch):
    from app.config import Settings
    monkeypatch.setattr(main, "get_settings", lambda: Settings(None, ("1.1.1.1",), 5.0, None, ":memory:"))
    remote = TestClient(main.app)                                   # appears as host "testclient"
    assert remote.get("/api/incidents").status_code == 401
    local = TestClient(main.app, client=("127.0.0.1", 50000))       # appears as this computer
    assert local.get("/api/incidents").status_code == 200


def test_full_flow_over_http(client):
    r = client.post("/api/messages/analyze", json={"text": FAKE_KYC, "source": "share"}, headers=AUTH)
    assert r.status_code == 200
    iid = r.json()["incident_id"]
    assert r.json()["verdict"]["label"] == "danger"

    # blocking without confirmation is refused
    no = client.post("/api/blocklist", json={"url": "https://sbi-kyc-update.in/verify", "confirm": False,
                                             "approved_via": "voice"}, headers=AUTH)
    assert no.status_code == 403
    yes = client.post("/api/blocklist", json={"url": "https://sbi-kyc-update.in/verify", "confirm": True,
                                              "approved_via": "voice"}, headers=AUTH)
    assert yes.status_code == 200

    check = client.post("/api/protect/check", json={"url": "https://sbi-kyc-update.in/verify"}, headers=AUTH)
    assert check.json()["action"] == "block"

    detail = client.get(f"/api/incidents/{iid}", headers=AUTH).json()
    assert detail["status"] == "contained"
    summary = client.get(f"/api/incidents/{iid}/summary", headers=AUTH)
    assert summary.status_code == 200 and "SunoSafe incident" in summary.text


def test_validation(client):
    assert client.post("/api/messages/analyze", json={"text": ""}, headers=AUTH).status_code == 422
    assert client.post("/api/calls/report", json={"asked_for": ["nuclear_codes"]}, headers=AUTH).status_code == 422
    assert client.post("/api/calls/report", json={"caller_number": "not-a-number"}, headers=AUTH).status_code == 422
    assert client.post("/api/incidents/report-scam", json={"description": "x", "incident_id": 999},
                       headers=AUTH).status_code == 404
    assert client.get("/api/incidents/999", headers=AUTH).status_code == 404


def test_guardian_page_is_served_with_csp(client):
    r = client.get("/guardian")
    assert r.status_code == 200 and "Content-Security-Policy" in r.text
    assert ".innerHTML" not in r.text   # data is only ever inserted as text
