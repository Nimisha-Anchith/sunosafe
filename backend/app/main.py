"""SunoSafe backend API.

Run locally:
    .venv\\Scripts\\python -m uvicorn app.main:app --port 8000
Then open http://localhost:8000/docs (API) or http://localhost:8000/guardian (Guardian Web View).

Access control:
    * If API_TOKEN is set, every /api request needs "Authorization: Bearer <token>".
    * If it is not set, only requests from this computer (localhost) are accepted.
"""
from __future__ import annotations

import hmac
import json
import re
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agent.core import run_turn
from app.agent.llm_client import make_llm
from app.agent.policy_gate import Sessions
from app.config import get_settings
from app.security.investigate import default_toolkit, investigate_url
from app.soc.service import SunoSafeService
from app.soc.store import Store

app = FastAPI(title="SunoSafe", version="0.3.0",
              description="Voice-first digital safety companion — security backend and mini-SOC")

WEB_DIR = Path(__file__).resolve().parent / "web"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

# ---------------------------------------------------------------- rate limiting
RATE_LIMIT = 20          # requests
RATE_WINDOW = 60.0       # per this many seconds, per client address
SWEEP_THRESHOLD = 1000   # when this many addresses are tracked, forget idle ones
_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _sweep_idle_clients(now: float) -> None:
    """Drop addresses with no request inside the window, so memory stays bounded
    even if requests arrive from very many different addresses."""
    stale = [c for c, q in _hits.items() if not q or now - q[-1] > RATE_WINDOW]
    for c in stale:
        del _hits[c]


def _check_rate_limit(client: str) -> None:
    now = time.monotonic()
    with _hits_lock:
        if len(_hits) >= SWEEP_THRESHOLD:
            _sweep_idle_clients(now)
        q = _hits[client]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Too many checks. Please wait a minute.")
        q.append(now)


def rate_limited(request: Request) -> None:
    _check_rate_limit(request.client.host if request.client else "unknown")


# ---------------------------------------------------------------- access control
def require_access(request: Request, authorization: str | None = Header(default=None)) -> None:
    token = get_settings().api_token
    if token:
        supplied = (authorization or "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="Missing or wrong access token.")
        return
    if not is_local_request(request):
        raise HTTPException(status_code=401, detail="Remote access needs API_TOKEN to be configured.")


# A tunnel or reverse proxy runs ON this computer, so traffic from the internet
# arrives looking like 127.0.0.1. Proxies add these headers; if any is present
# the request did not really start on this machine.
FORWARDED_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "forwarded", "x-real-ip",
                     "cf-connecting-ip", "cf-ray", "cdn-loop")


def is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in LOCAL_HOSTS and not any(h in request.headers for h in FORWARDED_HEADERS)


@lru_cache(maxsize=1)
def _default_service() -> SunoSafeService:
    settings = get_settings()
    return SunoSafeService(Store(settings.db_path), lambda: default_toolkit(get_settings()))


def get_service() -> SunoSafeService:
    return _default_service()


Guarded = [Depends(require_access)]


def _errors(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


# ---------------------------------------------------------------- request models
class URLCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048, description="A link exactly as it appeared")


class MessageIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    sender: str | None = Field(default=None, max_length=100)
    source: Literal["paste", "share", "notification", "voice"] = "paste"


class CallReportIn(BaseModel):
    description: str = Field(default="", max_length=2000)
    caller_number: str | None = Field(default=None, max_length=20, pattern=r"^\+?[\d\s-]{7,20}$")
    asked_for: list[Literal["otp", "upi_pin", "password", "card_details", "bank_details",
                            "remote_app", "money"]] = Field(default_factory=list, max_length=10)


class ScamReportIn(BaseModel):
    description: str = Field(..., min_length=1, max_length=3000)
    disclosed: list[Literal["otp", "upi_pin", "password", "card_details", "bank_details", "aadhaar",
                            "money_paid", "remote_app_installed"]] = Field(default_factory=list, max_length=10)
    amount_lost: float | None = Field(default=None, ge=0, le=1e9)
    incident_id: int | None = None


class BlockIn(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    confirm: bool = Field(..., description="Must be true: the user explicitly approved blocking")
    approved_via: Literal["voice", "app", "guardian"]
    incident_id: int | None = None


class StepIn(BaseModel):
    status: Literal["pending", "done", "skipped"]
    actor: Literal["user", "guardian", "voice"] = "user"


class NoteIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    author: Literal["user", "guardian", "analyst"] = "guardian"


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/guardian", include_in_schema=False)
def guardian_page() -> FileResponse:
    return FileResponse(WEB_DIR / "guardian.html")


@app.post("/api/investigate/url", dependencies=[*Guarded, Depends(rate_limited)])
def investigate(req: URLCheckRequest) -> dict:
    """Raw investigation of one link (all evidence, nothing stored).

    Declared with `def` (not `async def`) so FastAPI runs the blocking network
    checks in a worker thread instead of freezing the server.
    """
    return investigate_url(req.url, default_toolkit(get_settings())).to_dict()


@app.post("/api/messages/analyze", dependencies=[*Guarded, Depends(rate_limited)])
def analyze_message(req: MessageIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    """Detect → investigate links → assess → store → correlate into an incident."""
    return svc.analyze_message(req.text, req.sender, req.source)


@app.post("/api/links/check", dependencies=[*Guarded, Depends(rate_limited)])
def check_link(req: URLCheckRequest, svc: SunoSafeService = Depends(get_service)) -> dict:
    return svc.check_link(req.url)


@app.post("/api/calls/report", dependencies=[*Guarded, Depends(rate_limited)])
def report_call(req: CallReportIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    return _errors(svc.report_call, req.description, req.caller_number, list(req.asked_for))


@app.post("/api/incidents/report-scam", dependencies=Guarded)
def report_scam(req: ScamReportIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    if req.incident_id is not None and svc.store.get_incident(req.incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return svc.report_scam(req.description, list(req.disclosed), req.amount_lost, req.incident_id)


@app.post("/api/blocklist", dependencies=Guarded)
def block(req: BlockIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    return _errors(svc.block_link, req.url, req.confirm, req.approved_via, req.incident_id)


@app.get("/api/blocklist", dependencies=Guarded)
def blocklist(svc: SunoSafeService = Depends(get_service)) -> list[dict]:
    return svc.store.blocklist()


@app.post("/api/protect/check", dependencies=Guarded)
def protect_check(req: URLCheckRequest, svc: SunoSafeService = Depends(get_service)) -> dict:
    """Protected browser asks before every navigation (fast: no network checks)."""
    return svc.protect_check(req.url)


@app.get("/api/incidents", dependencies=Guarded)
def incidents(svc: SunoSafeService = Depends(get_service)) -> list[dict]:
    return svc.store.list_incidents()


@app.get("/api/incidents/{incident_id}", dependencies=Guarded)
def incident(incident_id: int, svc: SunoSafeService = Depends(get_service)) -> dict:
    detail = svc.incident_detail(incident_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return detail


@app.get("/api/incidents/{incident_id}/summary", dependencies=Guarded, response_class=PlainTextResponse)
def incident_summary(incident_id: int, svc: SunoSafeService = Depends(get_service)) -> str:
    text = svc.incident_summary(incident_id)
    if text is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return text


@app.patch("/api/incidents/{incident_id}/steps/{code}", dependencies=Guarded)
def update_step(incident_id: int, code: str, req: StepIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    return _errors(svc.update_step, incident_id, code, req.status, req.actor)


@app.post("/api/incidents/{incident_id}/notes", dependencies=Guarded)
def add_note(incident_id: int, req: NoteIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    return _errors(svc.add_note, incident_id, req.author, req.text)


@app.get("/api/events", dependencies=Guarded)
def events(svc: SunoSafeService = Depends(get_service)) -> list[dict]:
    return svc.store.recent_events(100)


# ---------------------------------------------------------------- voice agent
SESSIONS = Sessions()
_SESSION_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class InboxIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class ChatIn(BaseModel):
    """OpenAI-style chat request as sent by Agora Conversational AI. Unknown fields are ignored."""
    messages: list = Field(..., max_length=200)
    stream: bool = True


def get_llm():
    return make_llm(get_settings())


@app.post("/api/inbox", dependencies=Guarded)
def share_message(req: InboxIn, svc: SunoSafeService = Depends(get_service)) -> dict:
    """The app stores a pasted/shared message here; the user then asks about it by voice."""
    svc.store.set_inbox(req.text, datetime.now(UTC).isoformat())
    return {"stored": True}


def _load_inbox(svc: SunoSafeService) -> dict:
    row = svc.store.get_inbox()
    return {"text": row["text"], "at": datetime.fromisoformat(row["at"])} if row else {}


def _chunk(text: str | None, finish: str | None = None) -> str:
    delta = {"role": "assistant", "content": text} if text is not None else {}
    body = {"id": "chatcmpl-sunosafe", "object": "chat.completion.chunk", "created": int(time.time()),
            "model": "sunosafe-agent", "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
    return f"data: {json.dumps(body, ensure_ascii=False)}\n\n"


@app.post("/llm/chat/completions", dependencies=[*Guarded, Depends(rate_limited)])
def llm_chat(req: ChatIn, session: str = "default", svc: SunoSafeService = Depends(get_service),
             llm=Depends(get_llm)):
    """Custom-LLM endpoint for Agora Conversational AI.

    Agora sends the conversation here; we run SunoSafe's tools ourselves and
    stream back ONLY the words to speak (Server-Sent Events, OpenAI format).
    """
    if not _SESSION_ID.match(session):
        raise HTTPException(status_code=422, detail="bad session id")
    now = datetime.now(UTC)
    pieces = run_turn(req.messages, llm, svc, SESSIONS.get(session, now), now, _load_inbox(svc))
    if not req.stream:
        return {"id": "chatcmpl-sunosafe", "object": "chat.completion", "created": int(time.time()),
                "model": "sunosafe-agent",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "".join(pieces)}}]}

    def events():
        for piece in pieces:
            yield _chunk(piece)
        yield _chunk(None, "stop")
        yield "data: [DONE]\n\n"
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
