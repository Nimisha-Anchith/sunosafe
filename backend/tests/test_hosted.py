"""Hosted mode: one public address, private API locked by API_TOKEN, gateway under /gw."""
from fastapi.testclient import TestClient

from app import gateway, hosted, main
from app.config import Settings
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_service import Clock, fake_toolkit


def test_private_api_needs_the_token_and_gateway_lives_under_gw(tmp_path, monkeypatch):
    s = Settings(None, ("1.1.1.1",), 5.0, "api-secret", ":memory:", gateway_token="gw-token", device_token="dev-token")
    monkeypatch.setattr(main, "get_settings", lambda: s)
    monkeypatch.setattr(gateway, "get_settings", lambda: s)
    svc = SunoSafeService(Store(tmp_path / "h.db"), fake_toolkit, Clock())
    main.app.dependency_overrides[main.get_service] = lambda: svc
    gateway.app.dependency_overrides[main.get_service] = lambda: svc
    main._hits.clear()
    gateway._fails.clear()
    try:
        c = TestClient(hosted.app, client=("8.8.8.8", 5000), headers={"x-forwarded-for": "8.8.8.8"})
        assert c.get("/health").status_code == 200
        assert c.get("/api/incidents").status_code == 401
        assert c.get("/api/incidents", headers={"Authorization": "Bearer api-secret"}).status_code == 200
        assert c.get("/gw/health").status_code == 200
        assert c.get("/gw/device/alerts").status_code == 401
        assert c.get("/gw/device/alerts", headers={"Authorization": "Bearer dev-token"}).status_code == 200
        assert c.get("/gw/device/alerts", headers={"Authorization": "Bearer api-secret"}).status_code == 401
    finally:
        main.app.dependency_overrides.clear()
        gateway.app.dependency_overrides.clear()
