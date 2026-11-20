"""The policy gate: deterministic rules that decide whether a risky action may run.

The LLM only SUGGESTS actions. It can be confused or tricked (prompt
injection), so it is never trusted to decide. Blocking a link runs only when
ALL of these hold, checked in plain code:

  1. the link was investigated by SunoSafe's own tools in this conversation
     (the LLM cannot invent a target), and
  2. the USER's own latest words approve it — either an explicit "block it",
     or a "yes" while a block request is pending (and not older than 2 minutes).

Our server receives the user's transcribed words directly from Agora, so the
approval is read from what the user said, not from what the LLM claims.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta

PENDING_TTL = timedelta(minutes=2)
MAX_SESSIONS = 200

_YES = re.compile(r"\b(yes|yeah|yep|ya|ok|okay|sure|please do|go ahead|do it|confirm|correct|"
                  r"haan|han|ha|ji|theek hai|thik hai|kar do|kardo|sari|athe|houdu|aam|aama)\b|हाँ|हां|जी", re.I)
_NO = re.compile(r"\b(no|nope|don'?t|do not|not now|wait|stop|cancel|never|nahi|nahin|mat|"
                 r"venda|vendam|beda|illa)\b|नहीं|मत", re.I)
# "block" must point at the link ("block it", "block that link"), so a question such as
# "did the bank block my card?" is not mistaken for an instruction.
_BLOCK_IT = re.compile(r"\b(block|ban|blacklist)\s+(it|this|that|the|these|those)\b|"
                       r"\b(link|site|website|isko|ise|usko|use)\b.{0,20}\b(block|ban|band|rok)\b|"
                       r"\bblock\s+(kar|karo|kardo|cheyyu|maadi|pannu)\b|ब्लॉक\s*(कर|करो|कर दो)", re.I)
_QUESTION = re.compile(r"\?|\b(what|why|how|who|when|which|kya|kyu|kyun|kaise|kaun|enthu|yaake|enna)\b", re.I)
MAX_YES_WORDS = 6


def _is_question(text: str) -> bool:
    return bool(_QUESTION.search(text))


def says_yes(text: str) -> bool:
    """A clear, short yes. 'OK, but what is KYC?' is a question, not consent."""
    text = text or ""
    return (bool(_YES.search(text)) and not _NO.search(text) and not _is_question(text)
            and len(text.split()) <= MAX_YES_WORDS)


def says_block(text: str) -> bool:
    text = text or ""
    return bool(_BLOCK_IT.search(text)) and not _NO.search(text) and not _is_question(text)


@dataclass
class Pending:
    action: str
    url: str
    created: datetime


@dataclass
class Session:
    investigated: set[str] = field(default_factory=set)   # URLs our tools really checked
    links: dict[str, str] = field(default_factory=dict)   # "link 1" -> URL; the LLM only sees the label
    lang: str = "en"                                       # preferred reply language
    mode: str = "guard"                                    # "guard" (normal), "drill" (practice), "shield" (answers calls)
    shield: dict | None = None                             # call-shield state for the current call
    seeded: bool = False                                   # incident context already loaded
    pending: Pending | None = None
    incident_id: int | None = None
    case_notes: dict = field(default_factory=dict)         # facts from tools, for follow-up questions
    last_seen: datetime | None = None


class Sessions:
    def __init__(self):
        self._data: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str, now: datetime) -> Session:
        with self._lock:
            if session_id not in self._data and len(self._data) >= MAX_SESSIONS:
                oldest = min(self._data, key=lambda k: self._data[k].last_seen or now)
                del self._data[oldest]
            s = self._data.setdefault(session_id, Session())
            s.last_seen = now
            return s


@dataclass
class Decision:
    allowed: bool
    reason: str      # machine-readable: approved | not_investigated | needs_confirmation | nothing_pending | expired | declined


def decide_block(session: Session, url: str | None, user_text: str, now: datetime) -> Decision:
    """May we block `url` right now? Pure function of session state + the user's own words."""
    if session.pending and now - session.pending.created > PENDING_TTL:
        session.pending = None
        if url is None:
            return Decision(False, "expired")
    target = url or (session.pending.url if session.pending else None)
    if target is None:
        return Decision(False, "nothing_pending")
    if target not in session.investigated:
        return Decision(False, "not_investigated")
    if _NO.search(user_text or ""):
        session.pending = None
        return Decision(False, "declined")
    if says_block(user_text):
        return Decision(True, "approved")
    if session.pending and session.pending.url == target and says_yes(user_text):
        return Decision(True, "approved")
    session.pending = Pending("block_link", target, now)
    return Decision(False, "needs_confirmation")
