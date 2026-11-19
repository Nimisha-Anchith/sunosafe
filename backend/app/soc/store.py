"""SQLite storage for the mini-SIEM: events, indicators, incidents, steps, notes, blocklist.

Why SQLite: zero setup, one file, transactional, and plenty for a prototype.
All SQL uses parameters (?), never string formatting, so stored message text
or URLs can never inject SQL. Only redacted text is ever passed in here.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    status      TEXT NOT NULL,            -- open | contained | resolved | closed
    severity    TEXT NOT NULL,            -- info | low | medium | high | critical
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL,            -- suspicious_message | dangerous_link | reported_scam
    rationale   TEXT NOT NULL DEFAULT '[]'  -- JSON list of correlation / severity notes
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    type        TEXT NOT NULL,            -- message_analysed | url_investigated | protected_browser_block ...
    source      TEXT NOT NULL,            -- which component produced it (provenance)
    level       TEXT,
    summary     TEXT NOT NULL,
    data        TEXT NOT NULL,            -- JSON details (redacted)
    incident_id INTEGER REFERENCES incidents(id)
);
CREATE TABLE IF NOT EXISTS indicators (
    event_id INTEGER NOT NULL REFERENCES events(id),
    kind     TEXT NOT NULL,               -- domain | url | brand | phone | sender
    value    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_indicators ON indicators(kind, value);
CREATE TABLE IF NOT EXISTS incident_indicators (
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    kind TEXT NOT NULL, value TEXT NOT NULL,
    UNIQUE(incident_id, kind, value)
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    code TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
    status TEXT NOT NULL,                 -- pending | done | skipped
    needs_approval INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(incident_id, code)
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incidents(id),
    ts TEXT NOT NULL, author TEXT NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS blocklist (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                   -- url | domain
    value TEXT NOT NULL,
    reason TEXT NOT NULL,
    incident_id INTEGER REFERENCES incidents(id),
    approved_via TEXT NOT NULL,           -- how the user approved: voice | app | guardian
    created_at TEXT NOT NULL,
    UNIQUE(kind, value)
);
CREATE TABLE IF NOT EXISTS inbox (       -- the one message most recently shared from the app
    id   INTEGER PRIMARY KEY CHECK (id = 1),
    text TEXT NOT NULL,
    at   TEXT NOT NULL
);
"""


def _row(r: sqlite3.Row | None) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for key in ("data", "rationale"):
        if key in d and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA foreign_keys=ON")
            if self.path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(SCHEMA)
            self._db.commit()

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, params)
            self._db.commit()
            return cur

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [_row(r) for r in self._db.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            return _row(self._db.execute(sql, params).fetchone())

    # ---- events ------------------------------------------------------------
    def add_event(self, ts: str, type: str, source: str, summary: str, data: dict,
                  level: str | None = None, incident_id: int | None = None,
                  indicators: list[tuple[str, str]] = ()) -> int:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO events(ts, type, source, level, summary, data, incident_id) VALUES (?,?,?,?,?,?,?)",
                (ts, type, source, level, summary, json.dumps(data, default=str), incident_id))
            event_id = cur.lastrowid
            self._db.executemany("INSERT INTO indicators(event_id, kind, value) VALUES (?,?,?)",
                                 [(event_id, k, v) for k, v in dict.fromkeys(indicators)])
            self._db.commit()
            return event_id

    def attach_event(self, event_id: int, incident_id: int) -> None:
        self._exec("UPDATE events SET incident_id=? WHERE id=?", (incident_id, event_id))

    def events_for_incident(self, incident_id: int) -> list[dict]:
        return self._all("SELECT * FROM events WHERE incident_id=? ORDER BY ts, id", (incident_id,))

    def recent_events(self, limit: int = 50) -> list[dict]:
        return self._all("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))

    # ---- incidents ---------------------------------------------------------
    def create_incident(self, ts: str, title: str, kind: str, severity: str, rationale: list) -> int:
        cur = self._exec(
            "INSERT INTO incidents(created_at, updated_at, status, severity, title, kind, rationale) "
            "VALUES (?,?,?,?,?,?,?)", (ts, ts, "open", severity, title, kind, json.dumps(rationale)))
        return cur.lastrowid

    def get_incident(self, incident_id: int) -> dict | None:
        return self._one("SELECT * FROM incidents WHERE id=?", (incident_id,))

    def list_incidents(self, limit: int = 100) -> list[dict]:
        return self._all("SELECT * FROM incidents ORDER BY updated_at DESC, id DESC LIMIT ?", (limit,))

    def update_incident(self, incident_id: int, ts: str, **fields) -> None:
        allowed = {"status", "severity", "title", "rationale"}
        sets, params = ["updated_at=?"], [ts]
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"cannot update {key}")
            sets.append(f"{key}=?")
            params.append(json.dumps(value) if key == "rationale" else value)
        self._exec(f"UPDATE incidents SET {', '.join(sets)} WHERE id=?", (*params, incident_id))

    def add_incident_indicators(self, incident_id: int, indicators: list[tuple[str, str]]) -> None:
        with self._lock:
            self._db.executemany(
                "INSERT OR IGNORE INTO incident_indicators(incident_id, kind, value) VALUES (?,?,?)",
                [(incident_id, k, v) for k, v in indicators])
            self._db.commit()

    def incident_indicators(self, incident_id: int) -> list[dict]:
        return self._all("SELECT kind, value FROM incident_indicators WHERE incident_id=? ORDER BY kind, value",
                         (incident_id,))

    def find_open_incidents(self, indicators: list[tuple[str, str]], since: str) -> list[dict]:
        """Open incidents updated since `since` that share at least one indicator."""
        if not indicators:
            return []
        clause = " OR ".join("(ii.kind=? AND ii.value=?)" for _ in indicators)
        params = [p for pair in indicators for p in pair]
        return self._all(
            "SELECT DISTINCT i.id, ii.kind, ii.value FROM incidents i "
            "JOIN incident_indicators ii ON ii.incident_id=i.id "
            f"WHERE i.status IN ('open','contained') AND i.updated_at >= ? AND ({clause}) "
            "ORDER BY i.updated_at DESC", (since, *params))

    # ---- steps & notes -----------------------------------------------------
    def add_steps(self, incident_id: int, ts: str, steps: list[dict]) -> None:
        with self._lock:
            start = self._db.execute("SELECT COALESCE(MAX(position), 0) FROM steps WHERE incident_id=?",
                                     (incident_id,)).fetchone()[0]
            self._db.executemany(
                "INSERT OR IGNORE INTO steps(incident_id, code, title, detail, status, needs_approval, position, "
                "updated_at) VALUES (?,?,?,?,?,?,?,?)",
                [(incident_id, s["code"], s["title"], s["detail"], "pending", int(s.get("needs_approval", False)),
                  start + i + 1, ts) for i, s in enumerate(steps)])
            self._db.commit()

    def steps(self, incident_id: int) -> list[dict]:
        return self._all("SELECT * FROM steps WHERE incident_id=? ORDER BY position", (incident_id,))

    def get_step(self, incident_id: int, code: str) -> dict | None:
        return self._one("SELECT * FROM steps WHERE incident_id=? AND code=?", (incident_id, code))

    def set_step_status(self, incident_id: int, code: str, status: str, ts: str) -> bool:
        cur = self._exec("UPDATE steps SET status=?, updated_at=? WHERE incident_id=? AND code=?",
                         (status, ts, incident_id, code))
        return cur.rowcount == 1

    def add_note(self, incident_id: int, ts: str, author: str, text: str) -> int:
        return self._exec("INSERT INTO notes(incident_id, ts, author, text) VALUES (?,?,?,?)",
                          (incident_id, ts, author, text)).lastrowid

    def notes(self, incident_id: int) -> list[dict]:
        return self._all("SELECT * FROM notes WHERE incident_id=? ORDER BY ts, id", (incident_id,))

    # ---- shared-message inbox ------------------------------------------------
    # Kept in the database (not in memory) so the private API process and the
    # public voice gateway process both see it. Holds the raw message only until
    # it is analysed or replaced; analysis results are stored redacted elsewhere.
    def set_inbox(self, text: str, at: str) -> None:
        self._exec("INSERT INTO inbox(id, text, at) VALUES (1, ?, ?) "
                   "ON CONFLICT(id) DO UPDATE SET text=excluded.text, at=excluded.at", (text, at))

    def get_inbox(self) -> dict | None:
        return self._one("SELECT text, at FROM inbox WHERE id=1")

    def clear_inbox(self) -> None:
        self._exec("DELETE FROM inbox")

    # ---- blocklist ---------------------------------------------------------
    def add_block(self, kind: str, value: str, reason: str, incident_id: int | None,
                  approved_via: str, ts: str) -> None:
        self._exec("INSERT OR IGNORE INTO blocklist(kind, value, reason, incident_id, approved_via, created_at) "
                   "VALUES (?,?,?,?,?,?)", (kind, value, reason, incident_id, approved_via, ts))

    def find_block(self, url: str, domain: str | None) -> dict | None:
        return self._one(
            "SELECT * FROM blocklist WHERE (kind='url' AND value=?) OR (kind='domain' AND value=?) "
            "ORDER BY kind='url' DESC LIMIT 1", (url, domain or ""))

    def blocklist(self) -> list[dict]:
        return self._all("SELECT * FROM blocklist ORDER BY id DESC")
