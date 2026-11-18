"""SunoSafe backend API.

Run locally:
    .venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8000
Then open http://localhost:8000/docs to try the endpoints in the browser.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security.investigate import default_toolkit, investigate_url

app = FastAPI(title="SunoSafe", version="0.2.0",
              description="Voice-first digital safety companion — security backend")

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


class URLCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048, description="A link exactly as it appeared")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/investigate/url")
def investigate(req: URLCheckRequest, request: Request) -> dict:
    """Investigate one link and return every finding with the tool that produced it.

    Declared with `def` (not `async def`) so FastAPI runs the blocking network
    checks in a worker thread instead of freezing the server.
    """
    _check_rate_limit(request.client.host if request.client else "unknown")
    settings = get_settings()
    return investigate_url(req.url, default_toolkit(settings)).to_dict()
