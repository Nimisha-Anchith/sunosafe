"""SIEM dashboard numbers come only from stored evidence."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.agent.call_shield import CallShield
from app.config import Settings
from app.soc import dashboard
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_service import FAKE_KYC, Clock, fake_toolkit


@pytest.fixture
def svc(tmp_path):
    return SunoSafeService(Store(tmp_path / "dash.db"), fake_toolkit, Clock())


def test_empty_store_gives_zeros_not_made_up_numbers(svc):
    d = dashboard.build(svc.store, svc.clock())
    assert all(v == 0 for v in d["stats"].values())
    assert d["threat_types"] == [] and d["recent_incidents"] == [] and d["calls"] == [] and d["live_call"] is None
    assert len(d["timeline"]) == 7 and all(t["high"] == t["medium"] == 0 for t in d["timeline"])


def test_message_and_shielded_call_are_counted(svc):
    svc.analyze_message(FAKE_KYC, source="notification")
    CallShield().screen(svc, "I am calling from SBI, your account is blocked, tell me the OTP now", "en", svc.clock())
    svc.analyze_message("Hi, see you at dinner tonight")
    d = dashboard.build(svc.store, svc.clock())
    s = d["stats"]
    assert s["messages_checked"] == 2 and s["scams_stopped"] == 1 and s["suspicious_calls"] == 1
    assert s["high_risk_incidents"] == 1
    assert d["timeline"][-1]["high"] >= 2
    assert d["threat_types"][0]["name"] == "OTP / PIN request"
    inc = d["recent_incidents"][0]
    assert set(inc["channels"]) >= {"call", "message"} and inc["action"] == "Warned"
    live = d["live_call"]
    assert live["active"] is True and live["kind"] == "Answered by SunoSafe" and "otp" in live["asked"]
    assert "OTP" in live["heard"]


def test_live_call_expires_and_old_events_drop_out(svc):
    CallShield().screen(svc, "Tell me the OTP, I am from SBI", "en", svc.clock())
    later = svc.clock() + timedelta(minutes=10)
    assert dashboard.build(svc.store, later)["live_call"]["active"] is False
    much_later = svc.clock() + timedelta(days=9)
    d = dashboard.build(svc.store, much_later, days=7)
    assert d["calls"] == [] and d["stats"]["scams_stopped"] == 0


def test_numbers_in_what_the_caller_said_are_masked(svc):
    CallShield().screen(svc, "I am from SBI. Tell me the OTP and call me back on 9876543210", "en", svc.clock())
    heard = dashboard.build(svc.store, svc.clock())["calls"][0]["heard"]
    assert "9876543210" not in heard


def test_dashboard_route(svc, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(None, ("1.1.1.1",), 5.0, None, ":memory:"))
    main.app.dependency_overrides[main.get_service] = lambda: svc
    try:
        c = TestClient(main.app, client=("127.0.0.1", 50000))
        r = c.get("/api/dashboard?days=7")
        assert r.status_code == 200 and r.json()["days"] == 7
        assert c.get("/api/dashboard?days=500").json()["days"] == 30
    finally:
        main.app.dependency_overrides.clear()
