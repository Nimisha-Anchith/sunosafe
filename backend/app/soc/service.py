"""SunoSafe's mini-SOC workflows: analyse, correlate, open incidents, respond.

    Detection ─► Triage ─► Investigation ─► Containment ─► Remediation ─► Follow-up
    analyse_message    assess()       investigate_url   block_link    recovery steps   step tracking

Correlation (explainable, evidence-based):
  C1  events that share a strong indicator (scam domain, exact URL, phone
      number) within 7 days join the same open incident.
  Severity of an incident is recomputed from ALL its evidence and never
  silently drops. Two events with no shared evidence are never merged, and an
  unknown call plus an unknown message does not become "critical" by itself.

Consequential actions (blocking) require explicit confirmation; the voice
policy gate (Milestone 4) supplies it only after the user says yes.
"""
from __future__ import annotations

import re
import threading
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from app.security.investigate import Toolkit, URLInvestigation, investigate_url
from app.security.message_rules import BRANDS, MessageAnalysis, analyze_message
from app.security.rdap import registrable_domain
from app.security.url_normalize import URL_SHORTENERS, URLNormalizeError, normalize_url
from app.soc.redact import redact
from app.soc.severity import LEVELS, Verdict, assess
from app.soc.store import Store

MAX_LINKS_PER_MESSAGE = 3
CORRELATION_WINDOW = timedelta(days=7)
CORRELATE_KINDS = ("domain", "url", "phone")
OFFICIAL_DOMAINS = frozenset(d for b in BRANDS.values() for d in b.official)
# What a caller asked for (user-reported) -> evidence code understood by severity.py
CALL_ASKS = {
    "otp": "requests_otp", "upi_pin": "requests_upi_pin", "password": "requests_credentials",
    "card_details": "requests_credentials", "bank_details": "requests_credentials",
    "remote_app": "asks_remote_access", "money": "asks_for_payment",
}
DOMAIN_BLOCK_EVIDENCE = {"known_dangerous_site", "domain_recently_registered", "link_not_official_for_brand"}

STEP_LIBRARY: dict[str, tuple[str, str, bool]] = {
    "do_not_click": ("Don't open the link or reply",
                     "Do not click the link, call the number in the message, or reply.", False),
    "block_link": ("Block the link in SunoSafe",
                   "SunoSafe's protected browser will refuse to open it. Needs your approval.", True),
    "report_chakshu": ("Report it on Sanchar Saathi (Chakshu)",
                       "Report suspected fraud messages and calls at sancharsaathi.gov.in under Chakshu.", False),
    "call_1930": ("Call 1930 now",
                  "India's National Cyber Crime Helpline. If money was taken, calling quickly gives the best "
                  "chance to stop it.", False),
    "contact_bank": ("Call your bank's official number",
                     "Use the number printed on your card or on the bank's official website to block your card "
                     "or UPI and dispute any transaction.", False),
    "change_passwords": ("Change your passwords",
                         "Change the password you entered, and the same password anywhere else you used it.", False),
    "remove_remote_app": ("Uninstall the remote-control app",
                          "Remove AnyDesk, TeamViewer or any app the caller asked you to install, then restart "
                          "your phone.", False),
    "report_cybercrime_portal": ("File a complaint at cybercrime.gov.in",
                                 "Use the incident summary from SunoSafe to fill in the complaint.", False),
    "inform_guardian": ("Tell a trusted family member",
                        "Only if you choose to. SunoSafe never alerts anyone without your permission.", True),
}


def _steps(codes: list[str]) -> list[dict]:
    return [{"code": c, "title": STEP_LIBRARY[c][0], "detail": STEP_LIBRARY[c][1],
             "needs_approval": STEP_LIBRARY[c][2]} for c in dict.fromkeys(codes)]


def defang(url: str) -> str:
    """Make a link non-clickable for reports: https://evil.in -> hxxps://evil[.]in"""
    return url.replace("http", "hxxp", 1).replace(".", "[.]")


def _compact(inv: URLInvestigation) -> dict:
    """What we keep from an investigation: facts with provenance, no page content."""
    return {
        "url": inv.normalized.url if inv.normalized else inv.input,
        "final_url": inv.redirects.final_url if inv.redirects else None,
        "hops": [h.url for h in inv.redirects.hops] if inv.redirects else [],
        "findings": [asdict(f) for f in inv.findings],
        "tool_runs": [asdict(r) for r in inv.tool_runs],
        "domain_ages": {r.domain: r.age_days for r in inv.rdap if r.domain},
        "tls": inv.tls.status if inv.tls else None,
        "reputation": inv.reputation.status if inv.reputation else None,
    }


def _tool_problems(invs: list[URLInvestigation]) -> list[str]:
    problems = []
    for inv in invs:
        for run in inv.tool_runs:
            if run.status == "failed":
                problems.append(f"The {run.tool} check failed, so its evidence is missing.")
            elif run.status == "not_configured" and run.tool == "reputation":
                problems.append("Google Safe Browsing is not configured, so known-scam lists were not checked.")
    return list(dict.fromkeys(problems))


def _link_indicators(urls: list[str]) -> list[tuple[str, str]]:
    out = []
    for url in urls:
        out.append(("url", url))
        try:
            host = normalize_url(url).host
        except URLNormalizeError:
            continue
        domain = registrable_domain(host)
        # Official brand domains and shorteners are shared by everyone: never correlate on them.
        if domain and domain not in OFFICIAL_DOMAINS and host not in URL_SHORTENERS:
            out.append(("domain", domain))
    return out


BLOCK_LOG_INTERVAL = timedelta(seconds=60)   # log the same blocked link at most once a minute
_PHONE_INPUT = re.compile(r"^\+?[\d\s-]{7,20}$")


def normalize_caller_number(raw: str | None) -> str | None:
    """'+91 98765-43210' -> '9876543210'. Raises ValueError for anything that is not a phone number."""
    if raw is None or not raw.strip():
        return None
    if not _PHONE_INPUT.match(raw.strip()):
        raise ValueError("caller_number must contain only digits, spaces, dashes and an optional leading +")
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if not 7 <= len(digits) <= 13:
        raise ValueError("caller_number has an unusual length")
    return digits


class SunoSafeService:
    def __init__(self, store: Store, toolkit_factory: Callable[[], Toolkit],
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.store = store
        self.toolkit_factory = toolkit_factory
        self.clock = clock
        self._last_block_log: dict[str, datetime] = {}
        self._block_log_lock = threading.Lock()

    def _should_log_block(self, url: str) -> bool:
        """A page that keeps redirecting to a blocked link must not flood the incident log."""
        now = self.clock()
        with self._block_log_lock:
            if len(self._last_block_log) > 1000:      # keep memory bounded
                self._last_block_log = {u: t for u, t in self._last_block_log.items()
                                        if now - t < BLOCK_LOG_INTERVAL}
            last = self._last_block_log.get(url)
            if last is not None and now - last < BLOCK_LOG_INTERVAL:
                return False
            self._last_block_log[url] = now
            return True

    def _ts(self) -> str:
        return self.clock().isoformat(timespec="seconds")

    # ------------------------------------------------------------------ helpers
    def _incident_codes(self, incident_id: int) -> tuple[set[str], set[str]]:
        codes, disclosed = set(), set()
        for ev in self.store.events_for_incident(incident_id):
            codes |= set(ev["data"].get("codes", []))
            disclosed |= set(ev["data"].get("disclosed", []))
        return codes, disclosed

    def _correlate(self, event_ids: list[int], indicators: list[tuple[str, str]], verdict: Verdict,
                   title: str, kind: str, steps: list[str], force_incident: bool = False,
                   incident_id: int | None = None) -> int | None:
        ts = self._ts()
        since = (self.clock() - CORRELATION_WINDOW).isoformat(timespec="seconds")
        strong = [(k, v) for k, v in indicators if k in CORRELATE_KINDS]
        rationale_entry = None
        if incident_id is None:
            matches = self.store.find_open_incidents(strong, since)
            if matches:
                incident_id = matches[0]["id"]
                rationale_entry = {"ts": ts, "rule": "C1_shared_indicator",
                                   "text": f"Linked because it shares {matches[0]['kind']} "
                                           f"{matches[0]['value']} with this incident."}
        if incident_id is None:
            if not force_incident and LEVELS.index(verdict.level) < LEVELS.index("medium"):
                return None
            incident_id = self.store.create_incident(ts, title, kind, verdict.level, [
                {"ts": ts, "rule": r.rule, "text": r.text, "evidence": r.evidence} for r in verdict.reasons])
            self.store.add_event(ts, "incident_created", "correlation", f"Incident opened: {title}",
                                 {"severity": verdict.level}, verdict.level, incident_id)
        for eid in event_ids:
            self.store.attach_event(eid, incident_id)
        self.store.add_incident_indicators(incident_id, strong)
        self.store.add_steps(incident_id, ts, _steps(steps))

        incident = self.store.get_incident(incident_id)
        codes, disclosed = self._incident_codes(incident_id)
        combined = assess(codes, disclosed)
        new_level = max(incident["severity"], combined.level, verdict.level, key=LEVELS.index)
        rationale = incident["rationale"]
        if rationale_entry:
            rationale.append(rationale_entry)
        if new_level != incident["severity"]:
            rationale.append({"ts": ts, "rule": "severity_raised",
                              "text": f"Severity raised from {incident['severity']} to {new_level} "
                                      "based on the combined evidence."})
            self.store.add_event(ts, "incident_updated", "correlation",
                                 f"Severity raised to {new_level}", {"from": incident["severity"], "to": new_level},
                                 new_level, incident_id)
        self.store.update_incident(incident_id, ts, severity=new_level, rationale=rationale)
        return incident_id

    def _investigate_links(self, urls: list[str]) -> tuple[list[URLInvestigation], list[int]]:
        toolkit = self.toolkit_factory()
        invs, event_ids = [], []
        for url in urls[:MAX_LINKS_PER_MESSAGE]:
            inv = investigate_url(url, toolkit, self.clock())
            invs.append(inv)
            codes = sorted({f.code for f in inv.findings})
            event_ids.append(self.store.add_event(
                self._ts(), "url_investigated", "investigator",
                f"Investigated {defang(url)}: {len(inv.findings)} finding(s)",
                {**_compact(inv), "codes": codes}, assess(set(codes)).level,
                indicators=_link_indicators([url] + ([inv.redirects.final_url] if inv.redirects else []))))
        return invs, event_ids

    # ------------------------------------------------------------------ workflows
    def analyze_message(self, text: str, sender: str | None = None, source: str = "paste") -> dict:
        analysis: MessageAnalysis = analyze_message(text)
        invs, link_events = self._investigate_links(analysis.web_urls)
        codes = analysis.codes() | {f.code for inv in invs for f in inv.findings}
        verdict = assess(codes, tool_problems=_tool_problems(invs))

        final_urls = [inv.redirects.final_url for inv in invs if inv.redirects]
        indicators = (_link_indicators(analysis.web_urls + final_urls)
                      + [("phone", p) for p in analysis.phone_numbers]
                      + [("brand", b) for b in analysis.brands])
        brand = BRANDS[analysis.brands[0]].name if analysis.brands else None
        title = f"Suspicious message claiming to be {brand}" if brand else "Suspicious message"
        msg_event = self.store.add_event(
            self._ts(), "message_analysed", f"message_rules/{source}",
            f"Message analysed: {verdict.label} ({verdict.level})",
            {"text": redact(text)[:2000], "sender": redact(sender or "") or None,
             "signals": [asdict(s) for s in analysis.signals], "codes": sorted(codes),
             "verdict_reasons": [asdict(r) for r in verdict.reasons]},
            verdict.level, indicators=indicators)

        steps = ["do_not_click", "block_link", "report_chakshu"] if analysis.web_urls else \
            ["do_not_click", "report_chakshu"]
        incident_id = self._correlate([msg_event, *link_events], indicators, verdict, title,
                                      "suspicious_message", steps)
        return {
            "event_id": msg_event,
            "incident_id": incident_id,
            "verdict": asdict(verdict),
            "signals": [asdict(s) for s in analysis.signals],
            "links": [_compact(i) for i in invs],
            "links_not_checked": analysis.web_urls[MAX_LINKS_PER_MESSAGE:],
        }

    def check_link(self, url: str, source: str = "app") -> dict:
        """Investigate a single link the user asks about and store the result."""
        invs, event_ids = self._investigate_links([url])
        codes = {f.code for f in invs[0].findings}
        verdict = assess(codes, tool_problems=_tool_problems(invs))
        host = invs[0].normalized.host if invs[0].normalized else url
        incident_id = self._correlate(event_ids, _link_indicators([url]), verdict,
                                      f"Dangerous link: {host}", "dangerous_link", ["do_not_click", "block_link"])
        return {"event_id": event_ids[0], "incident_id": incident_id, "verdict": asdict(verdict),
                "link": _compact(invs[0])}

    def report_call(self, description: str, caller_number: str | None, asked_for: list[str]) -> dict:
        """User reports a suspicious phone call (we cannot hear cellular calls; the user tells us)."""
        analysis = analyze_message(description)
        unknown = set(asked_for) - set(CALL_ASKS)
        if unknown:
            raise ValueError(f"unknown asked_for values: {sorted(unknown)}")
        number = normalize_caller_number(caller_number)
        codes = analysis.codes() | {CALL_ASKS[a] for a in asked_for}
        verdict = assess(codes)
        indicators = [("phone", number)] if number else []
        indicators += _link_indicators(analysis.web_urls) + [("phone", p) for p in analysis.phone_numbers]
        ev = self.store.add_event(self._ts(), "call_reported", "user_report",
                                  f"User reported a suspicious call{' from ' + redact(number) if number else ''}",
                                  {"description": redact(description)[:2000], "asked_for": asked_for,
                                   "codes": sorted(codes)}, verdict.level, indicators=indicators)
        incident_id = self._correlate([ev], indicators, verdict, "Suspicious phone call", "suspicious_call",
                                      ["report_chakshu"])
        return {"event_id": ev, "incident_id": incident_id, "verdict": asdict(verdict)}

    def report_scam(self, description: str, disclosed: list[str], amount_lost: float | None = None,
                    incident_id: int | None = None) -> dict:
        """'I think I was scammed' — always opens (or extends) an incident with a recovery plan."""
        analysis = analyze_message(description)
        disclosed_set = set(disclosed)
        if amount_lost:
            disclosed_set.add("money_paid")
        codes = analysis.codes()
        verdict = assess(codes, disclosed_set)
        steps: list[str] = []
        if "money_paid" in disclosed_set:
            steps += ["call_1930", "contact_bank"]
        if disclosed_set & {"otp", "upi_pin", "card_details", "bank_details"}:
            steps += ["contact_bank", "call_1930"]
        if "password" in disclosed_set:
            steps.append("change_passwords")
        if "remote_app_installed" in disclosed_set:
            steps += ["remove_remote_app", "contact_bank"]
        steps += ["report_cybercrime_portal", "report_chakshu", "inform_guardian"]
        indicators = _link_indicators(analysis.web_urls) + [("phone", p) for p in analysis.phone_numbers]
        ev = self.store.add_event(self._ts(), "user_reported_scam", "user_report", "User reported a possible scam",
                                  {"description": redact(description)[:2000], "disclosed": sorted(disclosed_set),
                                   "amount_lost": amount_lost, "codes": sorted(codes)},
                                  verdict.level, indicators=indicators)
        incident_id = self._correlate([ev], indicators, verdict, "Reported scam", "reported_scam", steps,
                                      force_incident=True, incident_id=incident_id)
        return {"event_id": ev, "incident_id": incident_id, "verdict": asdict(verdict),
                "steps": self.store.steps(incident_id)}

    # ------------------------------------------------------------------ containment
    def block_link(self, url: str, confirmed: bool, approved_via: str, incident_id: int | None = None) -> dict:
        """Add a link (and, with strong evidence, its whole scam domain) to SunoSafe's blocklist."""
        if not confirmed:
            raise PermissionError("Blocking needs the user's explicit confirmation.")
        n = normalize_url(url)
        if n.scheme not in ("http", "https"):
            raise ValueError("Only web links can be blocked in the protected browser.")
        ts = self._ts()
        domain = registrable_domain(n.host)
        evidence = set()
        for ev in self.store.recent_events(500):
            if ev["type"] == "url_investigated" and n.url in (ev["data"].get("url"), ev["data"].get("final_url")):
                evidence |= set(ev["data"].get("codes", []))
                incident_id = incident_id or ev["incident_id"]
        blocked = [("url", n.url)]
        # Block the whole domain only with strong evidence and never for shared/official domains.
        if (domain and evidence & DOMAIN_BLOCK_EVIDENCE and domain not in OFFICIAL_DOMAINS
                and n.host not in URL_SHORTENERS):
            blocked.append(("domain", domain))
        reason = "Blocked by user after SunoSafe investigation" + (
            f" ({', '.join(sorted(evidence & DOMAIN_BLOCK_EVIDENCE))})" if evidence & DOMAIN_BLOCK_EVIDENCE else "")
        for kind, value in blocked:
            self.store.add_block(kind, value, reason, incident_id, approved_via, ts)
        ev = self.store.add_event(ts, "remediation_completed", f"blocklist/{approved_via}",
                                  f"Blocked {defang(n.url)}" + (f" and all of {domain}" if len(blocked) > 1 else ""),
                                  {"blocked": [{"kind": k, "value": v} for k, v in blocked],
                                   "approved_via": approved_via}, None, incident_id, _link_indicators([n.url]))
        if incident_id:
            self.store.attach_event(ev, incident_id)
            self.store.add_steps(incident_id, ts, _steps(["block_link"]))
            self.store.set_step_status(incident_id, "block_link", "done", ts)
            inc = self.store.get_incident(incident_id)
            if inc and inc["status"] == "open":
                self.store.update_incident(incident_id, ts, status="contained")
        return {"blocked": [{"kind": k, "value": v} for k, v in blocked], "incident_id": incident_id}

    def protect_check(self, url: str) -> dict:
        """Called by the protected browser before EVERY navigation, including redirects."""
        try:
            n = normalize_url(url)
        except URLNormalizeError:
            return {"action": "block", "reason": "This is not a valid web address.", "indicators": []}
        if n.scheme not in ("http", "https"):
            return {"action": "warn", "reason": "This is not a website link (for example a payment or app link).",
                    "indicators": n.indicators}
        hit = self.store.find_block(n.url, registrable_domain(n.host))
        if hit:
            if self._should_log_block(n.url):
                self.store.add_event(self._ts(), "protected_browser_block", "protected_browser",
                                     f"Protected browser blocked {defang(n.url)}",
                                     {"url": n.url, "rule": hit["kind"], "value": hit["value"]},
                                     "medium", hit["incident_id"], _link_indicators([n.url]))
            return {"action": "block", "reason": "You blocked this site after SunoSafe found it dangerous.",
                    "rule": hit["kind"], "incident_id": hit["incident_id"], "indicators": n.indicators}
        return {"action": "allow", "reason": "Not on your block list. This does not mean it is safe.",
                "indicators": n.indicators}

    # ------------------------------------------------------------------ follow-up
    def update_step(self, incident_id: int, code: str, status: str, actor: str) -> dict:
        if status not in ("pending", "done", "skipped"):
            raise ValueError("status must be pending, done or skipped")
        step = self.store.get_step(incident_id, code)
        if step is None:
            raise KeyError(code)
        if code == "block_link" and status == "done":
            raise PermissionError("Use the block action so the link is really blocked.")
        ts = self._ts()
        self.store.set_step_status(incident_id, code, status, ts)
        self.store.add_event(ts, "step_updated", actor, f"Step '{step['title']}' marked {status}",
                             {"code": code, "status": status}, None, incident_id)
        steps = self.store.steps(incident_id)
        if steps and all(s["status"] in ("done", "skipped") for s in steps):
            self.store.update_incident(incident_id, ts, status="resolved")
        return {"steps": steps, "incident": self.store.get_incident(incident_id)}

    def add_note(self, incident_id: int, author: str, text: str) -> dict:
        if self.store.get_incident(incident_id) is None:
            raise KeyError(incident_id)
        note_id = self.store.add_note(incident_id, self._ts(), author, redact(text)[:2000])
        return {"note_id": note_id}

    def incident_detail(self, incident_id: int) -> dict | None:
        inc = self.store.get_incident(incident_id)
        if inc is None:
            return None
        return {**inc, "events": self.store.events_for_incident(incident_id),
                "steps": self.store.steps(incident_id), "notes": self.store.notes(incident_id),
                "indicators": self.store.incident_indicators(incident_id)}

    def incident_summary(self, incident_id: int) -> str | None:
        """Plain-text report the user can read out to 1930 or paste into cybercrime.gov.in."""
        d = self.incident_detail(incident_id)
        if d is None:
            return None
        lines = [f"SunoSafe incident #{d['id']}: {d['title']}",
                 f"Severity: {d['severity']}   Status: {d['status']}   Opened: {d['created_at']}", "",
                 "What happened:"]
        lines += [f"  {e['ts']}  {e['summary']}" for e in d["events"]]
        disclosed = sorted({x for e in d["events"] for x in e["data"].get("disclosed", [])})
        if disclosed:
            lines += ["", "The user reports sharing: " + ", ".join(x.replace("_", " ") for x in disclosed)]
        amounts = [e["data"]["amount_lost"] for e in d["events"] if e["data"].get("amount_lost")]
        if amounts:
            lines.append(f"Amount reported lost: Rs {sum(amounts):,.2f}")
        if d["indicators"]:
            lines += ["", "Indicators (links are defanged so they cannot be clicked):"]
            for ind in d["indicators"]:
                value = defang(ind["value"]) if ind["kind"] in ("url", "domain") else ind["value"]
                lines.append(f"  {ind['kind']}: {value}")
        lines += ["", "Why SunoSafe flagged it:"] + [f"  - {r['text']}" for r in d["rationale"] if r.get("text")]
        lines += ["", "Recovery steps:"] + [f"  [{s['status']}] {s['title']}" for s in d["steps"]]
        lines += ["", "Personal numbers in this report are masked. Generated by SunoSafe."]
        return "\n".join(lines)
