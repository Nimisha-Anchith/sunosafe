"""Settings from environment variables, optionally loaded from backend/.env.

Secrets live ONLY in the environment or the git-ignored .env file — never in
source code, never in the Android app, never in logs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal KEY=VALUE loader. Real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "sunosafe.db"


@dataclass(frozen=True)
class Settings:
    safe_browsing_api_key: str | None
    dns_servers: tuple[str, ...]
    http_timeout: float
    api_token: str | None
    db_path: str
    llm_api_key: str | None = None
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_models: tuple[str, ...] = ("gemini-3.5-flash-lite", "gemini-flash-lite-latest")


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GROQ_URL = "https://api.groq.com/openai/v1"


def resolve_llm(env) -> tuple[str | None, str, str]:
    """Pick the LLM provider -> (api_key, base_url, default_models).

    Each key is only ever paired with its own provider's address, so a key can
    never be sent to the wrong company.
      1. LLM_BASE_URL set  -> custom provider, uses LLM_API_KEY only
      2. GROQ_API_KEY set  -> Groq
      3. otherwise         -> Gemini with GEMINI_API_KEY
    """
    if env.get("LLM_BASE_URL"):
        return env.get("LLM_API_KEY") or None, env["LLM_BASE_URL"].rstrip("/"), ""
    if env.get("GROQ_API_KEY"):
        return env["GROQ_API_KEY"], GROQ_URL, "openai/gpt-oss-20b,openai/gpt-oss-120b"
    return env.get("GEMINI_API_KEY") or None, GEMINI_URL, "gemini-3.5-flash-lite,gemini-flash-lite-latest"


def get_settings() -> Settings:
    load_env_file()
    servers = os.environ.get("DNS_SERVERS", "1.1.1.1,8.8.8.8")
    llm_key, llm_url, llm_default_models = resolve_llm(os.environ)
    return Settings(
        safe_browsing_api_key=os.environ.get("SAFE_BROWSING_API_KEY") or None,
        dns_servers=tuple(s.strip() for s in servers.split(",") if s.strip()),
        http_timeout=float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5")),
        api_token=os.environ.get("API_TOKEN") or None,
        db_path=os.environ.get("SUNOSAFE_DB") or str(DEFAULT_DB),
        llm_api_key=llm_key,
        llm_base_url=llm_url,
        llm_models=tuple(m.strip() for m in (os.environ.get("LLM_MODELS") or llm_default_models).split(",")
                         if m.strip()),
    )
