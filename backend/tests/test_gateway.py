"""The public voice gateway exposes exactly two routes and always requires its token."""
import pytest
from fastapi.testclient import TestClient

from app import gateway, main
from app.config import Settings
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_agent import ScriptedLLM, say
from tests.test_service import FAKE_KYC, Clock, fake_toolkit

AUTH = {"Authorization": "Bearer gw-token"}
BODY = {"messages": [{"role": "user", "content": "hello"}], "stream": False}


def settings(gateway_token="gw-token", api_token=None):
    return Settings(None, ("1.1.1.1",), 5.0, api_token, ":memory:", gateway_token=gateway_token)


@pytest.fixture
def svc(tmp_path):
    return SunoSafeService(Store(tmp_path / "gw.db"), fake_toolkit, Clock())


@pytest.fixture
def client(svc, monkeypatch):
    monkeypatch.setattr(gateway, "get_settings", lambda: settings())
    gateway.app.dependency_overrides[main.get_service] = lambda: svc
    gateway.app.dependency_overrides[main.get_llm] = lambda: ScriptedLLM(say("Hello from SunoSafe."))
    main._hits.clear()
    gateway._fails.clear()
    yield TestClient(gateway.app, client=("127.0.0.1", 50000))   # even "local" callers need the token
    gateway.app.dependency_overrides.clear()


def test_only_two_routes_exist():
    paths = sorted(r.path for r in gateway.app.routes)
    assert paths == ["/health", "/llm/chat/completions"]


def test_health_is_open_and_reveals_nothing(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/api/incidents", "/api/incidents/1", "/api/blocklist", "/api/events",
                                  "/api/inbox", "/guardian", "/docs", "/openapi.json", "/redoc"])
def test_private_routes_do_not_exist_on_the_gateway(client, path):
    assert client.get(path, headers=AUTH).status_code == 404
    assert client.post(path, headers=AUTH, json={}).status_code in (404, 405)


def test_llm_requires_the_gateway_token(client):
    assert client.post("/llm/chat/completions", json=BODY).status_code == 401
    assert client.post("/llm/chat/completions", json=BODY, headers={"Authorization": "Bearer nope"}).status_code == 401
    ok = client.post("/llm/chat/completions", json=BODY, headers=AUTH)
    assert ok.status_code == 200 and ok.json()["choices"][0]["message"]["content"] == "Hello from SunoSafe."


def test_private_api_token_does_not_open_the_gateway(client, monkeypatch):
    monkeypatch.setattr(gateway, "get_settings", lambda: settings(api_token="private-token"))
    r = client.post("/llm/chat/completions", json=BODY, headers={"Authorization": "Bearer private-token"})
    assert r.status_code == 401


def test_unconfigured_gateway_refuses_everything(client, monkeypatch):
    monkeypatch.setattr(gateway, "get_settings", lambda: settings(gateway_token=None))
    assert client.post("/llm/chat/completions", json=BODY, headers=AUTH).status_code == 503
    assert client.post("/llm/chat/completions", json=BODY).status_code == 503


def test_validation_and_size_limit(client):
    assert client.post("/llm/chat/completions", json={"stream": True}, headers=AUTH).status_code == 422
    assert client.post("/llm/chat/completions?session=../../x", json=BODY, headers=AUTH).status_code == 422
    huge = {"messages": [{"role": "user", "content": "x" * 300_000}]}
    assert client.post("/llm/chat/completions", json=huge, headers=AUTH).status_code == 413


def test_strangers_cannot_use_up_the_rate_limit(client):
    for _ in range(main.RATE_LIMIT + 5):                       # unauthenticated flood
        assert client.post("/llm/chat/completions", json=BODY).status_code == 401
    assert client.post("/llm/chat/completions", json=BODY, headers=AUTH).status_code == 200
    for _ in range(main.RATE_LIMIT - 1):
        client.post("/llm/chat/completions", json=BODY, headers=AUTH)
    assert client.post("/llm/chat/completions", json=BODY, headers=AUTH).status_code == 429


def test_wrong_token_attempts_are_limited_without_locking_out_the_real_caller(client):
    wrong = {"Authorization": "Bearer guess"}
    for _ in range(gateway.FAIL_LIMIT):
        assert client.post("/llm/chat/completions", json=BODY, headers=wrong).status_code == 401
    assert client.post("/llm/chat/completions", json=BODY, headers=wrong).status_code == 429
    assert client.post("/llm/chat/completions", json=BODY).status_code == 429          # no token at all
    assert client.post("/llm/chat/completions", json=BODY, headers=AUTH).status_code == 200   # real caller fine


def test_shared_message_is_deleted_once_analysed(svc):
    from datetime import UTC, datetime
    from app.agent.core import run_turn
    from app.agent.policy_gate import Session
    from tests.test_agent import call
    now = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
    svc.store.set_inbox(FAKE_KYC, now.isoformat())
    llm = ScriptedLLM(call("analyze_message"), say("It looks dangerous."))
    list(run_turn([{"role": "user", "content": "check my message"}], llm, svc, Session(), now, main._load_inbox(svc)))
    assert svc.store.get_inbox() is None                       # raw text gone
    stored = [e for e in svc.store.recent_events() if e["type"] == "message_analysed"][0]["data"]["text"]
    assert "9876543210" not in stored                          # only the masked copy remains


def test_expired_shared_message_is_deleted_not_kept(svc):
    from datetime import UTC, datetime, timedelta
    from app.agent.core import run_turn
    from app.agent.policy_gate import Session
    from tests.test_agent import call
    now = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
    svc.store.set_inbox(FAKE_KYC, (now - timedelta(minutes=11)).isoformat())
    llm = ScriptedLLM(call("analyze_message"), say("Please share it again."))
    list(run_turn([{"role": "user", "content": "check my message"}], llm, svc, Session(), now, main._load_inbox(svc)))
    assert svc.store.get_inbox() is None


def test_inbox_written_by_private_app_is_visible_to_gateway(svc, client):
    svc.store.set_inbox(FAKE_KYC, svc.clock().isoformat())
    assert main._load_inbox(svc)["text"] == FAKE_KYC
    svc.store.clear_inbox()
    assert main._load_inbox(svc) == {}
