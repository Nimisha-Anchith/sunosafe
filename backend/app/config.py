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


def get_settings() -> Settings:
    load_env_file()
    servers = os.environ.get("DNS_SERVERS", "1.1.1.1,8.8.8.8")
    return Settings(
        safe_browsing_api_key=os.environ.get("SAFE_BROWSING_API_KEY") or None,
        dns_servers=tuple(s.strip() for s in servers.split(",") if s.strip()),
        http_timeout=float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5")),
        api_token=os.environ.get("API_TOKEN") or None,
        db_path=os.environ.get("SUNOSAFE_DB") or str(DEFAULT_DB),
    )
