"""The public voice gateway: the ONLY part of SunoSafe meant to be reachable from the internet.

Agora's cloud must be able to call our LLM endpoint, so something has to be
public. Instead of exposing the whole backend, this tiny separate app serves
exactly two routes:

    GET  /health                 liveness check, no data
    POST /llm/chat/completions   the voice agent's brain, token required

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

import hmac
import threading
import time
from collections import deque

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from app import main as private_app
from app.config import get_settings

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


def require_gateway_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    token = get_settings().gateway_token
    if not token:
        raise HTTPException(status_code=503, detail="Gateway is not configured.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if hmac.compare_digest(supplied.encode(), token.encode()):
        return
    client = request.client.host if request.client else "unknown"
    if not _failed_attempt_allowed(client):
        raise HTTPException(status_code=429, detail="Too many failed attempts.")
    raise HTTPException(status_code=401, detail="Missing or wrong access token.")


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
