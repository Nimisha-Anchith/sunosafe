"""Talk to the LLM "brain" through the OpenAI-compatible chat-completions format.

Gemini, Groq, Ollama and many others speak this format, so changing the brain
is a settings change (LLM_BASE_URL, LLM_API_KEY, LLM_MODELS), not a rewrite.

Models are tried in order: if one is overloaded or rate-limited (HTTP 429/5xx)
the next is used, so a busy free tier does not break a live conversation.
"""
from __future__ import annotations

from collections.abc import Callable

import httpx

from app.config import Settings

RETRYABLE = {429, 500, 502, 503, 504}   # busy or rate-limited: try the next model
LLM = Callable[[list[dict], list[dict]], dict]   # (messages, tools) -> assistant message


class LLMError(Exception):
    """The brain could not answer (no key, all models busy, bad response)."""


def make_llm(settings: Settings, client: httpx.Client | None = None) -> LLM:
    def chat(messages: list[dict], tools: list[dict]) -> dict:
        if not settings.llm_api_key:
            raise LLMError("LLM_API_KEY / GEMINI_API_KEY is not set")
        http = client or httpx.Client(timeout=12)
        last = "no models configured"
        try:
            for model in settings.llm_models:
                try:
                    r = http.post(f"{settings.llm_base_url}/chat/completions",
                                  headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                                  json={"model": model, "messages": messages, "tools": tools,
                                        "tool_choice": "auto", "temperature": 0.3})
                except httpx.HTTPError as exc:
                    last = f"{model}: {type(exc).__name__}"
                    continue
                if r.status_code in RETRYABLE:
                    last = f"{model}: HTTP {r.status_code}"
                    continue
                if r.status_code != 200:
                    # e.g. 400 when a model writes a malformed tool call: another model may succeed.
                    last = f"{model}: HTTP {r.status_code}"   # never include the key or body
                    continue
                try:
                    return r.json()["choices"][0]["message"]
                except (ValueError, KeyError, IndexError, TypeError):
                    last = f"{model}: unreadable response"
            raise LLMError(f"all models failed ({last})")
        finally:
            if client is None:
                http.close()
    return chat
