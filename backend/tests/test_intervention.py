"""SunoSafe Intervention Intelligence: cross-channel correlation, call screening,
incident-aware voice sessions, language and the scam drill."""
import json

import pytest
from fastapi.testclient import TestClient

from app import gateway, main
from app.agent.core import run_turn
from app.agent.policy_gate import Session
from app.agent.tools import seed_session_from_incident
from app.config import Settings
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_agent import ScriptedLLM, call, say
from tests.test_service import FAKE_KYC, Clock, fake_toolkit

DEVICE = {"Authorization": "Bearer dev-token"}


@pytest.fixture
def svc(tmp_path):
    return SunoSafeService(Store(tmp_path / "iv.db"), fake_toolkit, Clock())


# ---------------------------------------------------------------- C2 + C3 correlation
def test_bank_notification_and_bank_call_become_one_incident(svc):
    msg = svc.analyze_message(FAKE_KYC, source="notification")
    # a different number calls, claiming the same bank and asking for the OTP
    call_out = svc.report_call("Caller said he is from SBI KYC team and asked for my OTP", "9123456780", ["otp"])
    assert call_out["incident_id"] == msg["incident_id"]
    d = svc.incident_detail(msg["incident_id"])
    rules = [r.get("rule") for r in d["rationale"]]
    assert "C2_same_impersonation_story" in rules
    assert any(e["type"] == "correlation_cross_channel" for e in d["events"])
    assert d["severity"] in ("high", "critical")


def test_genuine_bank_message_never_joins_a_scam_incident(svc):
    scam = svc.analyze_message(FAKE_KYC, source="notification")
    legit = svc.analyze_message("OTP for your SBI transaction is 482913. Do not share this OTP with anyone.")
    assert legit["incident_id"] is None
    assert len(svc.incident_detail(scam["incident_id"])["events"]) == len(
        [e for e in svc.store.events_for_incident(scam["incident_id"])])


def test_harmless_call_mentioning_a_bank_does_not_join(svc):
    scam = svc.analyze_message(FAKE_KYC)
    calm = svc.report_call("SBI branch called to confirm my locker appointment", "9123456780", [])
    assert calm["incident_id"] != scam["incident_id"]


# ---------------------------------------------------------------- call screening
def test_number_from_scam_message_calling_is_flagged_and_correlated(svc):
    msg = svc.analyze_message(FAKE_KYC, source="notification")         # contains 9876543210
    out = svc.screen_call("+91 98765 43210")
    assert out["alert"] is True and out["incident_id"] == msg["incident_id"]
    d = svc.incident_detail(msg["incident_id"])
    assert any(e["type"] == "call_screened" for e in d["events"])
    assert any(r.get("rule") == "R10_caller_from_scam_message" or "caller" in (r.get("text") or "").lower()
               for r in d["rationale"]) or d["severity"] == "high"


def test_ordinary_caller_is_not_stored(svc):
    before = len(svc.store.recent_events(500))
    out = svc.screen_call("9000000001")
    assert out["alert"] is False and len(svc.store.recent_events(500)) == before


def test_hidden_or_international_numbers(svc):
    assert svc.caller_risk(None)["risk"] == "unknown"
    assert svc.caller_risk("+92 300 1234567")["risk"] == "caution"


# ---------------------------------------------------------------- gateway device routes
@pytest.fixture
def client(svc, monkeypatch):
    monkeypatch.setattr(gateway, "get_settings",
                        lambda: Settings(None, ("1.1.1.1",), 5.0, None, ":memory:", gateway_token="gw-token",
                                         device_token="dev-token"))
    gateway.app.dependency_overrides[main.get_service] = lambda: svc
    main._hits.clear()
    gateway._fails.clear()
    gateway._recent.clear()
    yield TestClient(gateway.app)
    gateway.app.dependency_overrides.clear()


def test_device_call_route(client):
    note = {"app": "com.google.android.apps.messaging", "title": "VM-SBIKYC", "text": FAKE_KYC,
            "device_id": "phone-1234abcd"}
    assert client.post("/device/notifications", json=note, headers=DEVICE).json()["alert"] is True
    body = {"number": "+919876543210", "device_id": "phone-1234abcd", "lang": "hi"}
    assert client.post("/device/calls", json=body).status_code == 401
    out = client.post("/device/calls", json=body, headers=DEVICE).json()
    assert out["alert"] is True and "सावधान" in out["say"] and out["say_en"].startswith("Careful")
    quiet = client.post("/device/calls", json={**body, "number": ""}, headers=DEVICE).json()
    assert quiet["alert"] is False and quiet["say"] == ""
    assert client.post("/device/calls", json={**body, "number": "1; DROP TABLE"}, headers=DEVICE).status_code == 422


def test_hindi_spoken_warning_for_notifications(client):
    note = {"app": "com.whatsapp", "title": "x", "text": FAKE_KYC, "device_id": "phone-1234abcd", "lang": "hi"}
    out = client.post("/device/notifications", json=note, headers=DEVICE).json()
    assert out["alert"] is True and "OTP" in out["say"] and "सावधान" in out["say"]
    # English copy for phones with no Hindi voice installed
    assert out["say_en"] and not any("ऀ" <= ch <= "ॿ" for ch in out["say_en"])


# ---------------------------------------------------------------- voice context
def test_voice_brief_mentions_brand_and_both_channels(svc):
    msg = svc.analyze_message(FAKE_KYC)
    svc.screen_call("9876543210")
    text = svc.voice_brief(msg["incident_id"], "en")
    assert "State Bank of India" in text and "message and a phone call" in text
    assert "OTP" in svc.voice_brief(msg["incident_id"], "hi")


def test_seeded_voice_session_can_block_by_voice_with_user_approval(svc):
    msg = svc.analyze_message(FAKE_KYC)
    session = Session()
    assert seed_session_from_incident(svc, session, msg["incident_id"])
    assert session.links == {"link 1": "https://sbi-kyc-update.in/verify"}
    notes = json.dumps(session.case_notes)
    assert "9876543210" not in notes and "/verify" not in notes and "share the OTP" not in notes
    llm = ScriptedLLM(call("block_link", link="link 1"), say("Done, it is blocked."))
    list(run_turn([{"role": "user", "content": "Yes, block it"}], llm, svc, session,
                  svc.clock(), None))
    assert svc.protect_check("https://sbi-kyc-update.in/verify")["action"] == "block"


def test_reinvestigating_a_known_website_reuses_the_seeded_link(svc):
    """Regression: the model re-checked the bare website name and then blocked the wrong address."""
    msg = svc.analyze_message(FAKE_KYC)
    session = Session()
    seed_session_from_incident(svc, session, msg["incident_id"])
    events_before = len(svc.store.recent_events(500))
    llm = ScriptedLLM(call("investigate_url", url="sbi-kyc-update.in"), call("block_link"), say("Blocked."))
    list(run_turn([{"role": "user", "content": "Yes, block it"}], llm, svc, session, svc.clock(), None))
    reused = json.loads(llm.seen[1][-1]["content"])
    assert reused["already_investigated"] is True and reused["link"] == "link 1"
    assert session.links == {"link 1": "https://sbi-kyc-update.in/verify"}
    assert svc.protect_check("https://sbi-kyc-update.in/verify")["action"] == "block"
    assert not any(e["type"] == "url_investigated" for e in svc.store.recent_events(500)[: len(svc.store.recent_events(500)) - events_before])


def test_unreachable_website_is_reported_as_unchecked(tmp_path):
    from app.security.tls_check import TLSReport
    from tests.test_service import Clock, fake_toolkit

    def toolkit():
        tk = fake_toolkit()
        tk.tls = lambda url: TLSReport(host="x", status="unreachable", detail="timed out")
        return tk
    s = SunoSafeService(Store(tmp_path / "u.db"), toolkit, Clock())
    out = s.check_link("https://slow-site.example.in/x")
    assert any("could not be checked" in u for u in out["verdict"]["uncertainties"])


def test_new_agent_tools(svc):
    msg = svc.analyze_message(FAKE_KYC)
    session = Session()
    seed_session_from_incident(svc, session, msg["incident_id"])
    llm = ScriptedLLM(call("get_incident_details"), call("check_caller_risk", number="9876543210"),
                      call("get_security_timeline"), say("ok"))
    list(run_turn([{"role": "user", "content": "what happened?"}], llm, svc, session, svc.clock(), None))
    details = json.loads(llm.seen[1][-1]["content"])
    caller = json.loads(llm.seen[2][-1]["content"])
    timeline = json.loads(llm.seen[3][-1]["content"])
    assert details["incident"].startswith("Suspicious message") and details["why"]
    assert caller["risk"] == "high"
    assert timeline["events"] and all("hxxp" not in e for e in timeline["events"])


def test_drill_mode_uses_no_tools_and_language(svc):
    session = Session(mode="drill", lang="hi")
    seen = {}

    def llm(messages, tools):
        seen["tools"], seen["system"] = tools, messages[0]["content"]
        return {"role": "assistant", "content": "नमस्ते, मैं बैंक से बोल रहा हूँ।"}
    out = list(run_turn([{"role": "user", "content": "hello"}], llm, svc, session, svc.clock(), None))
    assert seen["tools"] == [] and "PRACTICE DRILL" in seen["system"] and "Hindi" in seen["system"]
    assert out == ["नमस्ते, मैं बैंक से बोल रहा हूँ।"]


def test_llm_endpoint_parameters_are_validated(svc, monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings(None, ("1.1.1.1",), 5.0, None, ":memory:"))
    main.app.dependency_overrides[main.get_service] = lambda: svc
    main.app.dependency_overrides[main.get_llm] = lambda: ScriptedLLM(say("hi"))
    main._hits.clear()
    try:
        c = TestClient(main.app, client=("127.0.0.1", 50000))
        body = {"messages": [{"role": "user", "content": "hi"}], "stream": False}
        assert c.post("/llm/chat/completions?mode=evil", json=body).status_code == 422
        assert c.post("/llm/chat/completions?lang=fr", json=body).status_code == 422
        assert c.post("/llm/chat/completions?incident=0", json=body).status_code == 422
        assert c.post("/llm/chat/completions?mode=drill&lang=hi", json=body).status_code == 200
        msg = svc.analyze_message(FAKE_KYC)
        r = c.get(f"/api/incidents/{msg['incident_id']}/voice-brief?lang=en")
        assert r.status_code == 200 and "SunoSafe" in r.json()["greeting"]
        assert "practice drill" in c.get("/api/voice/drill-greeting").json()["greeting"]
    finally:
        main.app.dependency_overrides.clear()


def test_voice_brief_describes_the_latest_story_not_the_first(svc):
    first = svc.analyze_message(FAKE_KYC)                      # SBI story, contains 9876543210
    courier = ("FedEx: your parcel is held by customs, a police case will be filed. Call our officer on "
               "9876543210 and pay the fine to avoid arrest.")
    second = svc.analyze_message(courier)                      # same number -> same incident
    assert second["incident_id"] == first["incident_id"]
    text = svc.voice_brief(first["incident_id"], "en")
    assert "police or customs" in text and "State Bank" not in text
    assert "पुलिस" in svc.voice_brief(first["incident_id"], "hi")
