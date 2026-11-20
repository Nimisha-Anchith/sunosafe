"""Spoken warnings as audio, in the user's language, using Murf Falcon.

Why not the phone's own voice? Phones often lack a voice for Hindi, Malayalam,
Kannada or Tamil (a Samsung S24 stayed silent in Hindi). Murf Falcon speaks all
five languages with the same voice the SunoSafe voice agent uses.

Safety: the phone can only ask for audio of a sentence SunoSafe itself produced
(an id handed out with the alert), never for arbitrary text. That keeps a leaked
device token from being used as a free text-to-speech service.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict

import httpx

from app.soc import phrases

MURF_URL = "https://global.api.murf.ai/v1/speech/stream"
LOCALES = {"en": "en-IN", "hi": "hi-IN", "ml": "ml-IN", "kn": "kn-IN", "ta": "ta-IN"}
ID_TTL = 30 * 60          # an alert's audio can be fetched for 30 minutes
MAX_IDS = 300
MAX_AUDIO = 64            # audio files kept in memory
MAX_TEXT = 600


class SpeechUnavailable(Exception):
    """Murf is not configured or did not answer; the phone falls back to its own voice."""


_lock = threading.Lock()
_ids: OrderedDict[str, tuple[str, str, float]] = OrderedDict()   # id -> (text, lang, expires)
_audio: OrderedDict[str, bytes] = OrderedDict()


def fixed_id(kind: str, lang: str) -> str:
    return f"{kind}-{lang}"


def _fixed_phrases() -> dict[str, tuple[str, str]]:
    """Sentences that never change, so the phone can ask for them by name (and keep the audio)."""
    out = {fixed_id("call-watch", lang): (phrases.call_alert(lang), lang) for lang in phrases.SUPPORTED}
    out.update({fixed_id("voice-sample", lang): (phrases.plain_greeting(lang), lang) for lang in phrases.SUPPORTED})
    return out


def register(text: str, lang: str, now: float | None = None) -> str:
    """Remember a sentence SunoSafe is about to show the user; return the id for its audio."""
    now = time.monotonic() if now is None else now
    text = text[:MAX_TEXT]
    sid = "d" + hashlib.sha256(f"{lang}\n{text}".encode()).hexdigest()[:20]
    with _lock:
        _ids[sid] = (text, lang, now + ID_TTL)
        _ids.move_to_end(sid)
        while len(_ids) > MAX_IDS:
            _ids.popitem(last=False)
    return sid


def lookup(sid: str, now: float | None = None) -> tuple[str, str] | None:
    now = time.monotonic() if now is None else now
    fixed = _fixed_phrases().get(sid)
    if fixed:
        return fixed
    with _lock:
        item = _ids.get(sid)
        if item is None or item[2] < now:
            _ids.pop(sid, None)
            return None
        return item[0], item[1]


def synthesize(text: str, lang: str, api_key: str | None, voice: str = "hi-IN-jaya",
               client: httpx.Client | None = None) -> bytes:
    """MP3 bytes for the sentence, from the cache or from Murf."""
    if not api_key:
        raise SpeechUnavailable("Murf is not configured")
    key = hashlib.sha256(f"{lang}\n{voice}\n{text}".encode()).hexdigest()
    with _lock:
        if key in _audio:
            _audio.move_to_end(key)
            return _audio[key]
    try:
        post = (client or httpx).post
        r = post(MURF_URL, headers={"api-key": api_key, "Content-Type": "application/json"},
                 json={"text": text, "voiceId": voice, "model": "FALCON", "locale": LOCALES.get(lang, "en-IN"),
                       "format": "MP3", "sampleRate": 24000}, timeout=15)
    except httpx.HTTPError as e:
        raise SpeechUnavailable("Murf did not answer") from e
    if r.status_code != 200 or len(r.content) < 1000 or not r.content.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3")):
        raise SpeechUnavailable(f"Murf returned {r.status_code}")
    with _lock:
        _audio[key] = r.content
        while len(_audio) > MAX_AUDIO:
            _audio.popitem(last=False)
    return r.content
