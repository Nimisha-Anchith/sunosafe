"""Spoken warnings: five languages, Murf audio, and the phone can only ask for sentences SunoSafe produced."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import gateway, main
from app.config import Settings
from app.soc import phrases, speech
from app.soc.service import SunoSafeService
from app.soc.store import Store
from tests.test_service import FAKE_KYC, Clock, fake_toolkit

DEVICE = {"Authorization": "Bearer dev-token"}
MP3 = b"ID3" + b"\x00" * 2000


@pytest.mark.parametrize("lang", phrases.SUPPORTED)
def test_every_language_has_every_sentence(lang):
    native = lang != "en"
    assert phrases.message_alert(lang, "high", "English summary").strip()
    assert phrases.message_alert(lang, "medium", "English summary").strip()
    for text in (phrases.call_alert(lang), phrases.voice_greeting(lang, "high", "State Bank of India", True),
                 phrases.voice_greeting(lang, "high", None, False), phrases.drill_greeting(lang),
                 phrases.shield_greeting(lang), phrases.plain_greeting(lang),
                 phrases.shield_alert(lang, "State Bank of India", ["otp", "pin"]),
                 phrases.shield_alert(lang, None, [])):
        assert text.strip() and "{" not in text and "}" not in text
        if native:
            assert any(ord(ch) > 0x0900 for ch in text), f"{lang} sentence has no native script: {text[:40]}"
    if native:
        assert "State Bank of India" in phrases.voice_greeting(lang, "high", "State Bank of India", True)
        assert phrases.message_alert(lang, "high", "x") != phrases.message_alert(lang, "medium", "x")


@pytest.fixture(autouse=True)
def clean():
    speech._ids.clear()
    speech._audio.clear()
    yield


def test_synthesize_calls_murf_once_then_uses_the_cache():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=MP3)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert speech.synthesize("test sentence", "hi", "k", client=client) == MP3
    assert speech.synthesize("test sentence", "hi", "k", client=client) == MP3
    assert len(calls) == 1
    body = calls[0].read().decode()
    assert "hi-IN" in body and "FALCON" in body and calls[0].headers["api-key"] == "k"


def test_unconfigured_or_failing_murf_raises_so_the_phone_can_fall_back():
    with pytest.raises(speech.SpeechUnavailable):
        speech.synthesize("x", "en", None)
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="no")))
    with pytest.raises(speech.SpeechUnavailable):
        speech.synthesize("x", "en", "k", client=bad)
    junk = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"<html>" * 300)))
    with pytest.raises(speech.SpeechUnavailable):
        speech.synthesize("x", "en", "k", client=junk)


def _settings(**extra):
    return Settings(None, ("1.1.1.1",), 5.0, None, ":memory:", gateway_token="gw-token",
                    device_token="dev-token", **extra)


@pytest.fixture
def client(tmp_path, monkeypatch):
    svc = SunoSafeService(Store(tmp_path / "sp.db"), fake_toolkit, Clock())
    monkeypatch.setattr(gateway, "get_settings", lambda: _settings(murf_api_key="murf-test"))

    def fake_synth(text, lang, key, voice="v", client=None):
        if key != "murf-test":
            raise speech.SpeechUnavailable("not configured")
        return MP3
    monkeypatch.setattr(speech, "synthesize", fake_synth)
    gateway.app.dependency_overrides[main.get_service] = lambda: svc
    main._hits.clear()
    gateway._fails.clear()
    gateway._recent.clear()
    yield TestClient(gateway.app)
    gateway.app.dependency_overrides.clear()


@pytest.mark.parametrize("lang", phrases.SUPPORTED)
def test_alert_in_every_language_comes_with_playable_audio(client, lang):
    note = {"app": "com.whatsapp", "title": "x", "text": FAKE_KYC, "device_id": "phone-1234abcd", "lang": lang}
    out = client.post("/device/notifications", json=note, headers=DEVICE).json()
    assert out["alert"] and out["audio_id"]
    assert client.get(f"/device/speech/{out['audio_id']}").status_code == 401
    r = client.get(f"/device/speech/{out['audio_id']}", headers=DEVICE)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and r.content == MP3


def test_only_sentences_we_produced_can_be_spoken(client):
    assert client.get("/device/speech/dnotreal", headers=DEVICE).status_code == 404
    assert client.get("/device/speech/bad%20id", headers=DEVICE).status_code in (404, 422)
    assert client.get("/device/speech/call-watch-ml", headers=DEVICE).status_code == 200   # fixed, named phrase
    assert client.get("/device/speech/call-watch-fr", headers=DEVICE).status_code == 404


def test_expired_ids_stop_working():
    sid = speech.register("hello", "en", now=1000.0)
    assert speech.lookup(sid, now=1001.0) == ("hello", "en")
    assert speech.lookup(sid, now=1000.0 + speech.ID_TTL + 1) is None


def test_murf_down_gives_503_so_phone_uses_its_own_voice(client, monkeypatch):
    monkeypatch.setattr(gateway, "get_settings", lambda: _settings())
    assert client.get("/device/speech/call-watch-hi", headers=DEVICE).status_code == 503
