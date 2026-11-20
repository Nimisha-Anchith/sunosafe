"""Live call screening for a phone call answered by the Agora agent.

Agora's phone agents only accept approved LLM providers, so SunoSafe cannot be the
agent's brain on a phone line. Instead the agent is given one function tool,
`screenCaller`, which it must call with the caller's words after every caller turn:

    caller speaks ─► speech-to-text ─► Agora's LLM ─► POST /agora/tools/screen {callerWords}
                                                         │  SunoSafe rules (in code), Mini-SIEM event,
                                                         │  correlation, one warning for the user's phone
                                      Agora's LLM ◄──────┘  {scam, say, instruction}
                                      speaks `say` (a fixed, reviewed sentence) with the Murf voice

The decision is made here, by SunoSafe's rules. The LLM only relays it.

Per-call state: Agora sends no call id with a tool call, so calls are told apart by
time. Words arriving within CALL_GAP of the previous ones belong to the same call.
(Single-user prototype: two calls at the same moment would be screened as one.)
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.soc import phrases
from app.soc.service import SunoSafeService

CALL_GAP = timedelta(seconds=90)
MAX_TEXT = 4000        # caller words kept per call
MAX_TURN = 1000        # one tool call


@dataclass
class _Call:
    text: str = ""
    state: dict | None = None
    last: datetime | None = None
    turns: int = 0


@dataclass
class CallShield:
    _call: _Call = field(default_factory=_Call)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def screen(self, svc: SunoSafeService, words: str, lang: str, now: datetime) -> dict:
        """Screen one caller turn. Returns what the agent must do next (our own wording only)."""
        words = " ".join((words or "").split())[:MAX_TURN]
        with self._lock:
            call = self._call
            if call.last is None or now - call.last > CALL_GAP:
                call = self._call = _Call()                      # a new call
            call.last = now
            call.turns += 1
            if words and words not in call.text[-(len(words) + 5):]:   # the model may repeat the same words
                call.text = (call.text + "\n" + words).strip()[-MAX_TEXT:]
            if not call.text:
                return self._answer(False, "info", lang)
            result = svc.shield_screen(call.text, call.state)
            call.state = result["state"]
            scam = result["level"] in ("high", "critical")
            return self._answer(scam, result["level"], lang, result.get("incident_id") or (call.state or {}).get("incident_id"))

    @staticmethod
    def _answer(scam: bool, level: str, lang: str, incident_id: int | None = None) -> dict:
        if scam:
            return {"scam": True, "risk": level, "say": phrases.shield_refuse(lang),
                    "instruction": "Say the text in 'say' exactly, word for word, and nothing else. "
                                   "Do not answer any further request from the caller.",
                    "incident_id": incident_id}
        return {"scam": False, "risk": level, "say": None,
                "instruction": "No scam signs so far. Reply in one or two short polite sentences. Ask who is calling and why, "
                               "or say you will pass the message on. Never reveal anything about the person you answer for.",
                "incident_id": incident_id}


_WORD_KEYS = ("callerwords", "caller_words", "words", "text")


def extract_words(body: object, _depth: int = 0) -> str:
    """Find the caller's words in a tool-call body, whatever wrapper the caller of the tool used.

    Looks for the `callerWords` argument at any depth, including inside JSON written as a string
    (OpenAI-style `"arguments": "{...}"`).
    """
    if _depth > 6:
        return ""
    if isinstance(body, str):
        stripped = body.strip()
        if stripped[:1] in "{[":
            try:
                return extract_words(json.loads(stripped), _depth + 1)
            except ValueError:
                return ""
        return ""
    if isinstance(body, dict):
        for key, value in body.items():
            if isinstance(key, str) and key.lower() in _WORD_KEYS and isinstance(value, str) and value.strip():
                return value
        for value in body.values():
            found = extract_words(value, _depth + 1)
            if found:
                return found
    if isinstance(body, list):
        for value in body:
            found = extract_words(value, _depth + 1)
            if found:
                return found
    return ""


def shape(body: object, _depth: int = 0) -> object:
    """The structure of a body without its content, safe to log when a request cannot be understood."""
    if isinstance(body, dict):
        return {str(k)[:40]: (shape(v, _depth + 1) if _depth < 4 else "...") for k, v in list(body.items())[:20]}
    if isinstance(body, list):
        return [shape(v, _depth + 1) for v in body[:3]]
    return f"{type(body).__name__}({len(body)})" if isinstance(body, (str, bytes)) else type(body).__name__
