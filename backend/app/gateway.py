"""The public voice gateway: the ONLY part of SunoSafe meant to be reachable from the internet.

Agora's cloud must be able to call our LLM endpoint, so something has to be
public. Instead of exposing the whole backend, this tiny separate app serves
exactly four routes:

    GET  /health                 liveness check, no data
    POST /llm/chat/completions   the voice agent's brain, GATEWAY_TOKEN required
    POST /device/notifications   the Android companion reports a notification, DEVICE_TOKEN required
    POST /device/calls           the Android companion reports an incoming caller, DEVICE_TOKEN required

Everything else (incidents, blocklist, Guardian page, API docs) exists only on
the private app (port 8000) and answers 404 here.

Run:  .venv\\Scripts\\python -m uvicorn app.gateway:app --port 8001

Protections on the public route:
  * GATEWAY_TOKEN is mandatory. If it is not configured the gateway refuses
    every request (503) rather than falling back to "open".
  * The token is separate from the private API's token.
  * Rate limit, checked AFTER the token so strangers cannot use up the allowance.
  * Wrong-token attempts have their own per-address limit (429 after 30 a minute).
  * If the token leaks: generate a new GATEWAY_TOKEN, put it in backend/.env and
    in the voice app's settings, and restart both. The old token stops working at once.
  * Request size limits and validation come from the shared endpoint code.
  * Interactive API docs are switched off.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
import json
import hmac
import logging
import threading
import urllib.parse
import time
from collections import deque

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, Field

from app import main as private_app
from app.agent.call_shield import CallShield, extract_words, shape
from app.config import get_settings
from app.soc import phrases, speech
from app.soc.service import SunoSafeService

app = FastAPI(title="SunoSafe voice gateway", docs_url=None, redoc_url=None, openapi_url=None)


FAIL_LIMIT = 30          # wrong-token attempts allowed per address...
FAIL_WINDOW = 60.0       # ...in this many seconds; after that they get 429 instead of 401
_fails: dict[str, deque[float]] = {}
_fails_lock = threading.Lock()


def _failed_attempt_allowed(client: str) -> bool:
    """Count a wrong-token attempt. False once this address has made too many.

    Kept separate from the main rate limit, and never applied to requests with
    the correct token, so a stranger can neither use up the agent's allowance
    nor lock the real caller out.
    """
    now = time.monotonic()
    with _fails_lock:
        if len(_fails) > 1000:   # bounded memory: forget addresses with no recent failures
            for key in [k for k, q in _fails.items() if not q or now - q[-1] > FAIL_WINDOW]:
                del _fails[key]
        q = _fails.setdefault(client, deque())
        while q and now - q[0] > FAIL_WINDOW:
            q.popleft()
        if len(q) >= FAIL_LIMIT:
            return False
        q.append(now)
        return True


def _check_token(expected: str | None, request: Request, authorization: str | None) -> None:
    if not expected:
        raise HTTPException(status_code=503, detail="Gateway is not configured.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if hmac.compare_digest(supplied.encode(), expected.encode()):
        return
    client = request.client.host if request.client else "unknown"
    if not _failed_attempt_allowed(client):
        raise HTTPException(status_code=429, detail="Too many failed attempts.")
    raise HTTPException(status_code=401, detail="Missing or wrong access token.")


def require_gateway_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Token held by Agora, for the voice brain only."""
    _check_token(get_settings().gateway_token, request, authorization)


def require_device_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Token held by the paired Android companion, for reporting notifications only.

    It is a different secret from the voice token, so a leak of one does not
    open the other route.
    """
    _check_token(get_settings().device_token, request, authorization)


MAX_BODY_BYTES = 256 * 1024   # a conversation history is a few kilobytes; refuse anything huge


def limit_body_size(content_length: int | None = Header(default=None)) -> None:
    if content_length is None:
        raise HTTPException(status_code=411, detail="Content-Length required.")
    if content_length > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Request too large.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.add_api_route(
    "/llm/chat/completions",
    private_app.llm_chat,
    methods=["POST"],
    dependencies=[Depends(require_gateway_token), Depends(limit_body_size), Depends(private_app.rate_limited)],
)


# ---------------------------------------------------------------------------
# Android companion: automatic notification monitoring
# ---------------------------------------------------------------------------
#   phone notification ─► on-phone pre-filter ─► POST /device/notifications ─► message rules
#        (only notifications with a link or scam wording leave the phone)      + link investigation
#                                                                              + correlation / incident
#   phone ◄── verdict + one sentence to speak ◄──────────────────────────────────────┘
#
# The phone only sends what Android itself shows in the notification, and only
# after the user has switched on notification access for SunoSafe.

DEDUPE_SECONDS = 600   # the same text again within 10 minutes reuses the first answer
_recent: dict[str, tuple[float, dict]] = {}
_recent_lock = threading.Lock()


class DeviceNotification(BaseModel):
    app: str = Field(..., min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.]+$",
                     description="Android package that posted it, e.g. com.whatsapp")
    title: str = Field(default="", max_length=200, description="What Android shows as the title (usually the sender)")
    text: str = Field(..., min_length=1, max_length=4000, description="The notification text Android exposes")
    device_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    lang: str = Field(default="en", pattern=r"^(en|hi|ml|kn|ta)$")
    source: str = Field(default="notification", pattern=r"^(notification|screen)$",
                        description="notification = a new notification; screen = a message the user opened or scrolled")


class DeviceCall(BaseModel):
    number: str = Field(default="", max_length=20, pattern=r"^[0-9+\s-]*$",
                        description="Caller number as Android exposes it; empty when hidden")
    device_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    lang: str = Field(default="en", pattern=r"^(en|hi|ml|kn|ta)$")


def _cached(key: str, now: float) -> dict | None:
    with _recent_lock:
        for k in [k for k, (t, _) in _recent.items() if now - t > DEDUPE_SECONDS]:
            del _recent[k]
        hit = _recent.get(key)
        return hit[1] if hit else None


@app.post("/device/notifications",
          dependencies=[Depends(require_device_token), Depends(limit_body_size), Depends(private_app.rate_limited)])
def device_notification(item: DeviceNotification,
                        svc: SunoSafeService = Depends(private_app.get_service)) -> dict:
    """Investigate one notification reported by the Android companion.

    Returns a small answer for the phone: whether to alert, how serious, and one
    calm sentence to show and speak. Evidence stays in the mini-SIEM.
    """
    key = hashlib.sha256(f"{item.device_id}\n{item.app}\n{item.lang}\n{item.text}".encode()).hexdigest()
    now = time.monotonic()
    previous = _cached(key, now)
    if previous is not None:
        return {**previous, "duplicate": True}

    out = svc.analyze_message(item.text, sender=item.title or None, source=item.source)
    verdict = out["verdict"]
    alert = verdict["label"] != "no_known_issues" and verdict["level"] in ("medium", "high", "critical")
    answer = {
        "alert": alert,
        "level": verdict["level"],
        "label": verdict["label"],
        "say": phrases.message_alert(item.lang, verdict["level"], verdict["summary"]),
        # English copy for phones that have no voice for the chosen language.
        "say_en": phrases.message_alert("en", verdict["level"], verdict["summary"]),
        "incident_id": out["incident_id"],
        "duplicate": False,
        # Numbers written in a dangerous message, so the phone can warn instantly,
        # without a network round trip, if one of them calls.
        "watch_numbers": out.get("phone_numbers", [])[:5] if alert else [],
    }
    answer["audio_id"] = speech.register(answer["say"], item.lang)
    with _recent_lock:
        _recent[key] = (now, answer)
    return answer


@app.post("/device/calls",
          dependencies=[Depends(require_device_token), Depends(limit_body_size), Depends(private_app.rate_limited)])
def device_call(item: DeviceCall, svc: SunoSafeService = Depends(private_app.get_service)) -> dict:
    """An incoming call seen by the Android call-screening service.

    Only callers already linked to scam evidence are recorded; other numbers
    are looked up and forgotten.
    """
    out = svc.screen_call(item.number or None)
    say = phrases.call_alert(item.lang) if out["alert"] else ""
    return {"alert": out["alert"], "level": out["level"], "incident_id": out["incident_id"], "say": say,
            "say_en": phrases.call_alert("en") if out["alert"] else "", "reason": out["reason"],
            "audio_id": speech.register(say, item.lang) if say else None}


@app.get("/device/alerts",
         dependencies=[Depends(require_device_token), Depends(private_app.rate_limited)])
def device_alerts(after: int = Query(default=0, ge=0), lang: str = Query(default="en", pattern=r"^(en|hi|ml|kn|ta)$"),
                  svc: SunoSafeService = Depends(private_app.get_service)) -> dict:
    """Warnings the phone has not fetched yet, e.g. after SunoSafe's call assistant answered a
    scam call for the user (call forwarding -> Vobiz number -> Agora agent -> /llm in shield mode).
    The companion asks every few seconds; only our own wording is returned, never caller text."""
    alerts = svc.device_alerts(after, lang)
    for a in alerts:
        a["audio_id"] = speech.register(a["say"], lang)
    return {"alerts": alerts}


_SPEECH_ID = r"^[A-Za-z0-9-]{3,40}$"


@app.get("/device/speech/{speech_id}",
         dependencies=[Depends(require_device_token), Depends(private_app.rate_limited)])
def device_speech(speech_id: str = Path(..., pattern=_SPEECH_ID)) -> Response:
    """MP3 of a sentence SunoSafe produced (Murf Falcon). Only ids handed out with an alert work, so this
    cannot be used to speak arbitrary text. 503 means: use the phone's own voice instead."""
    found = speech.lookup(speech_id)
    if found is None:
        raise HTTPException(status_code=404, detail="unknown or expired")
    s = get_settings()
    try:
        audio = speech.synthesize(found[0], found[1], s.murf_api_key, s.murf_voice)
    except speech.SpeechUnavailable:
        raise HTTPException(status_code=503, detail="voice unavailable")
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


# ---------------------------------------------------------------------------
# Live phone calls: the Agora phone agent asks SunoSafe what to do, every caller turn
# ---------------------------------------------------------------------------
CALL_SHIELD = CallShield()
log = logging.getLogger("uvicorn.error")


@app.post("/agora/tools/screen",
          dependencies=[Depends(require_gateway_token), Depends(limit_body_size), Depends(private_app.rate_limited)])
async def agora_screen_tool(request: Request,
                            lang: str = Query(default="en", pattern=r"^(en|hi|ml|kn|ta)$"),
                            svc: SunoSafeService = Depends(private_app.get_service)) -> dict:
    """Function tool `screenCaller` of the Agora phone agent (see app/agent/call_shield.py).

    The caller's words are untrusted input: they are only ever screened by SunoSafe's
    rules and stored masked. The reply contains our own wording, never the caller's.
    """
    raw = await request.body()
    try:
        body: object = json.loads(raw or b"{}")
    except ValueError:
        body = dict(urllib.parse.parse_qsl(raw.decode("utf-8", "replace")))      # form-encoded
    # The tool's arguments may also arrive in the address (query string).
    words = extract_words(body) or extract_words(dict(request.query_params))
    if "{{" in words:          # an unfilled placeholder is not something a caller said
        words = ""
    if not words.strip():
        # Log the structure only (never the content), so an unexpected format can be supported.
        log.warning("screenCaller: no callerWords found. content-type=%s query=%s body=%s",
                    request.headers.get("content-type"), sorted(request.query_params.keys()), shape(body))
        raise HTTPException(status_code=422, detail="callerWords is required")
    return CALL_SHIELD.screen(svc, words, lang, datetime.now(UTC))
