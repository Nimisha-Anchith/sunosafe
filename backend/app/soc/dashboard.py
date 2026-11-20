"""Numbers for the SIEM dashboard, computed only from what the Mini-SIEM really stored.

Nothing here is invented or estimated. Where SunoSafe deliberately stores nothing
(ordinary callers and ordinary messages are never kept, for privacy), the dashboard
shows no count instead of a guess.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta

from app.soc.redact import redact
from app.soc.severity import LEVELS

CALL_TYPES = {"call_screened": "Caller-ID check", "call_shielded": "Answered by SunoSafe", "call_reported": "Reported by you"}
CHECK_TYPES = {"message_analysed", "url_investigated", *CALL_TYPES}
# What kind of scam an event shows, from the rule codes it carries. First match wins.
THREAT_TYPES = [
    ("OTP / PIN request", {"requests_otp", "requests_upi_pin", "pin_to_receive_money", "requests_credentials"}),
    ("Police / digital arrest", {"authority_threat"}),
    ("KYC / account threat", {"kyc_update_request", "account_threat"}),
    ("Remote-control app", {"asks_remote_access", "asks_to_install_app"}),
    ("Money / prize lure", {"asks_for_payment", "too_good_to_be_true", "contains_upi_payment_link"}),
    ("Fake website", {"link_not_official_for_brand", "known_dangerous_site", "domain_recently_registered"}),
    ("Known scam number", {"known_scam_number", "same_scam_story_by_call"}),
]
LIVE_WINDOW = timedelta(minutes=3)


def _data(ev: dict) -> dict:
    d = ev.get("data")
    if isinstance(d, str):
        try:
            return json.loads(d)
        except ValueError:
            return {}
    return d or {}


def _serious(level: str | None, at_least: str = "medium") -> bool:
    return bool(level) and LEVELS.index(level) >= LEVELS.index(at_least)


def _threat_type(codes: set[str]) -> str:
    return next((name for name, group in THREAT_TYPES if codes & group), "Other warning signs")


def _caller(ev: dict) -> str | None:
    """A masked caller number for display, from the event's own summary (already redacted when stored)."""
    if ev["type"] not in ("call_screened", "call_reported"):
        return None
    summary = ev.get("summary") or ""
    return summary.rsplit(" from ", 1)[1].split(",")[0].strip() if " from " in summary else None


def build(store, now: datetime, days: int = 7) -> dict:
    days = max(1, min(days, 30))
    since = now - timedelta(days=days)
    since_s = since.isoformat(timespec="seconds")
    events = [e for e in store.recent_events(2000) if e["ts"] >= since_s]
    incidents = [i for i in store.list_incidents(500) if i["updated_at"] >= since_s]
    blocked_links = [b for b in store.blocklist() if (b.get("created_at") or b.get("ts") or "") >= since_s]

    suspicious = [e for e in events if e["type"] in CHECK_TYPES and _serious(e["level"])]
    calls = [e for e in events if e["type"] in CALL_TYPES]

    # one bar per day: suspicious events by level
    timeline = []
    for back in range(days - 1, -1, -1):
        day = (now - timedelta(days=back)).date().isoformat()
        todays = [e for e in suspicious if e["ts"][:10] == day]
        timeline.append({"day": day,
                         "high": sum(1 for e in todays if _serious(e["level"], "high")),
                         "medium": sum(1 for e in todays if e["level"] == "medium")})

    types = Counter(_threat_type(set(_data(e).get("codes") or [])) for e in suspicious if e["type"] != "url_investigated")

    recent = []
    for inc in incidents[:8]:
        evs = store.events_for_incident(inc["id"])
        channels = sorted({("call" if e["type"] in CALL_TYPES else "message" if e["type"] == "message_analysed"
                            else "link") for e in evs if e["type"] in CHECK_TYPES})
        codes = set().union(*[set(_data(e).get("codes") or []) for e in evs]) if evs else set()
        done = any(e["type"] == "remediation_completed" for e in evs)
        recent.append({"id": inc["id"], "title": inc["title"], "severity": inc["severity"], "status": inc["status"],
                       "updated_at": inc["updated_at"], "channels": channels, "threat": _threat_type(codes),
                       "action": "Blocked" if done else ("Warned" if _serious(inc["severity"], "high") else "Watching")})

    call_log = []
    for e in calls[:20]:
        d = _data(e)
        call_log.append({"id": e["id"], "ts": e["ts"], "kind": CALL_TYPES[e["type"]], "level": e["level"],
                         "incident_id": e["incident_id"], "caller": _caller(e),
                         "threat": _threat_type(set(d.get("codes") or [])) if _serious(e["level"]) else None,
                         # what the caller said, masked at storage time; shown as plain text only
                         "heard": redact(d.get("text") or d.get("description") or "")[:600] or None,
                         "asked": d.get("asked") or [],
                         "why": [r.get("text") for r in d.get("verdict_reasons") or [] if r.get("text")][:3]})

    last_shield = next((c for c in call_log if c["kind"] == CALL_TYPES["call_shielded"]), None)
    live = None
    if last_shield:
        age = now - datetime.fromisoformat(last_shield["ts"])
        live = {**last_shield, "seconds_ago": int(age.total_seconds()), "active": age <= LIVE_WINDOW}

    return {
        "days": days,
        "generated_at": now.isoformat(timespec="seconds"),
        "stats": {
            "scams_stopped": sum(1 for e in calls if e["type"] == "call_shielded" and _serious(e["level"], "high"))
                             + sum(1 for e in events if e["type"] == "protected_browser_block"),
            "links_blocked": len(blocked_links),
            "suspicious_calls": sum(1 for e in calls if _serious(e["level"])),
            "high_risk_incidents": sum(1 for i in incidents if _serious(i["severity"], "high")),
            "messages_checked": sum(1 for e in events if e["type"] == "message_analysed"),
            "open_incidents": sum(1 for i in incidents if i["status"] in ("open", "contained")),
        },
        "timeline": timeline,
        "threat_types": [{"name": n, "count": c} for n, c in types.most_common()],
        "recent_incidents": recent,
        "calls": call_log,
        "live_call": live,
    }
