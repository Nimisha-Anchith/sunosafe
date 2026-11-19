"""The tools the voice agent may use, and the code that actually runs them.

Each tool wraps a SunoSafe service call and returns a SHORT summary written by
our code. The LLM never receives the raw scam message or page content — only
our findings — which removes most prompt-injection risk.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from app.agent.policy_gate import Session, decide_block
from app.soc.service import SunoSafeService


def _fn(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or []}}}


_DISCLOSED = ["otp", "upi_pin", "password", "card_details", "bank_details", "aadhaar", "money_paid",
              "remote_app_installed"]
_ASKED = ["otp", "upi_pin", "password", "card_details", "bank_details", "remote_app", "money"]

TOOLS: list[dict] = [
    _fn("analyze_message",
        "Check a suspicious SMS/WhatsApp message and investigate any links in it. Call with no text to check "
        "the message the user most recently shared or pasted in the app.",
        {"text": {"type": "string", "description": "Only if the user dictated the message aloud."}}),
    _fn("check_link", "Investigate one web link (redirects, domain age, certificate, reputation).",
        {"url": {"type": "string"}}, ["url"]),
    _fn("block_link",
        "Ask SunoSafe to block a link that was already investigated. SunoSafe decides whether the user has "
        "approved; if it answers needs_confirmation, ask the user and call this again after they reply.",
        {"link": {"type": "string", "description": "The label from a previous result, e.g. 'link 1'. Omit to "
                                                 "use the link currently awaiting confirmation."}}),
    _fn("report_scam",
        "The user thinks they were scammed or shared something. Opens an incident with a recovery plan.",
        {"description": {"type": "string"},
         "disclosed": {"type": "array", "items": {"type": "string", "enum": _DISCLOSED}},
         "amount_lost": {"type": "number", "description": "Rupees lost, if any."}}, ["description"]),
    _fn("report_call", "The user describes a suspicious phone call.",
        {"description": {"type": "string"}, "caller_number": {"type": "string"},
         "asked_for": {"type": "array", "items": {"type": "string", "enum": _ASKED}}}, ["description"]),
    _fn("recovery_steps", "List the recovery steps for the current incident and their status."),
    _fn("mark_step", "Record that the user completed or skipped a recovery step.",
        {"code": {"type": "string"}, "status": {"type": "string", "enum": ["done", "skipped"]}},
        ["code", "status"]),
]

SLOW_TOOLS = {"analyze_message", "check_link"}   # network checks: speak a short filler first
INBOX_TTL = timedelta(minutes=10)                # a shared message is only "the latest" for this long


def _host(url: str | None) -> str:
    return urlsplit(url or "").hostname or ""


def _verdict_view(verdict: dict) -> dict:
    return {"level": verdict["level"], "label": verdict["label"], "say": verdict["summary"],
            "reasons": [r["text"] for r in verdict["reasons"]][:5],
            "could_not_check": verdict["uncertainties"][:3]}


def _link_view(label: str, link: dict) -> dict:
    """What the LLM learns about a link: a label and website names, never the full address.

    The path of a scam link is written by the attacker and could carry
    instructions aimed at the model, so it stays on our side.
    """
    view = {"link": label, "website": _host(link["url"]),
            "facts": [f["detail"] for f in link["findings"]][:6]}
    final = _host(link.get("final_url"))
    if final and final != view["website"]:
        view["ends_at_website"] = final
    return view


class ToolRunner:
    def __init__(self, service: SunoSafeService, session: Session, user_text: str, now: datetime,
                 inbox: dict | None = None):
        self.svc, self.session, self.user_text, self.now = service, session, user_text, now
        self.inbox = inbox if inbox is not None else {}

    def run(self, name: str, raw_args: str | dict | None) -> dict:
        """Execute one tool call. Never raises: errors are returned so the agent can say so honestly."""
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) and raw_args.strip() else (raw_args or {})
            if not isinstance(args, dict):
                return {"error": "bad_arguments"}
            handler = getattr(self, f"_t_{name}", None)
            if handler is None:
                return {"error": "unknown_tool"}
            return handler(args)
        except (ValueError, KeyError, PermissionError) as exc:
            return {"error": "tool_failed", "detail": str(exc)[:200]}
        except Exception as exc:   # a crashed tool is reported, never hidden
            return {"error": "tool_crashed", "detail": type(exc).__name__}

    # ------------------------------------------------------------------ tools
    def _remember(self, out: dict, links: list[dict]) -> dict:
        views = []
        for link in links:
            self.session.investigated.update(u for u in (link["url"], link.get("final_url")) if u)
            label = next((k for k, v in self.session.links.items() if v == link["url"]), None)
            if label is None:
                label = f"link {len(self.session.links) + 1}"
                self.session.links[label] = link["url"]
            views.append(_link_view(label, link))
        if out.get("incident_id"):
            self.session.incident_id = out["incident_id"]
        view = {"verdict": _verdict_view(out["verdict"]), "links": views,
                "incident_id": out.get("incident_id")}
        self.session.case_notes = view
        return view

    def _t_analyze_message(self, args: dict) -> dict:
        text = (args.get("text") or "").strip()
        if not text:
            shared_at = self.inbox.get("at")
            if self.inbox.get("text") and shared_at and self.now - shared_at > INBOX_TTL:
                self.svc.store.clear_inbox()   # do not keep an unmasked message past its time
                return {"error": "message_expired",
                        "hint": "The shared message is old. Ask the user to share it again in the app."}
            text = self.inbox.get("text")
        if not text:
            return {"error": "no_message",
                    "hint": "Ask the user to paste or share the message in the SunoSafe app first."}
        from_inbox = not args.get("text")
        out = self.svc.analyze_message(text[:5000], source="share" if from_inbox else "voice")
        if from_inbox:
            # The raw message has done its job: only the masked copy in the event log remains.
            self.svc.store.clear_inbox()
        view = self._remember(out, out["links"])
        view["warning_signs"] = [s["detail"] for s in out["signals"]][:6]
        self.session.case_notes = view
        return view

    def _t_check_link(self, args: dict) -> dict:
        out = self.svc.check_link(str(args["url"])[:2048])
        return self._remember(out, [out["link"]])

    def _t_block_link(self, args: dict) -> dict:
        label = " ".join(str(args.get("link") or "").lower().split())
        url = None
        if label:
            url = self.session.links.get(label)
            if url is None:
                return {"blocked": False, "status": "not_investigated"}   # not a link our tools checked
        elif not self.session.pending and len(self.session.links) == 1:
            url = next(iter(self.session.links.values()))
        decision = decide_block(self.session, url, self.user_text, self.now)
        if not decision.allowed:
            return {"blocked": False, "status": decision.reason}
        target = url or self.session.pending.url
        res = self.svc.block_link(target, confirmed=True, approved_via="voice",
                                  incident_id=self.session.incident_id)
        self.session.pending = None
        return {"blocked": True, "website": _host(target),
                "whole_website_blocked": any(b["kind"] == "domain" for b in res["blocked"])}

    def _t_report_scam(self, args: dict) -> dict:
        out = self.svc.report_scam(str(args["description"])[:3000],
                                   [d for d in args.get("disclosed", []) if d in _DISCLOSED],
                                   args.get("amount_lost"), self.session.incident_id)
        self.session.incident_id = out["incident_id"]
        view = {"verdict": _verdict_view(out["verdict"]), "incident_id": out["incident_id"],
                "steps": [{"code": s["code"], "title": s["title"], "status": s["status"]} for s in out["steps"]]}
        self.session.case_notes = view
        return view

    def _t_report_call(self, args: dict) -> dict:
        out = self.svc.report_call(str(args["description"])[:2000], args.get("caller_number"),
                                   [a for a in args.get("asked_for", []) if a in _ASKED])
        if out["incident_id"]:
            self.session.incident_id = out["incident_id"]
        return {"verdict": _verdict_view(out["verdict"]), "incident_id": out["incident_id"]}

    def _t_recovery_steps(self, args: dict) -> dict:
        if not self.session.incident_id:
            return {"error": "no_incident"}
        return {"steps": [{"code": s["code"], "title": s["title"], "detail": s["detail"], "status": s["status"]}
                          for s in self.svc.store.steps(self.session.incident_id)]}

    def _t_mark_step(self, args: dict) -> dict:
        if not self.session.incident_id:
            return {"error": "no_incident"}
        out = self.svc.update_step(self.session.incident_id, str(args["code"]), str(args["status"]), "voice")
        return {"ok": True, "incident_status": out["incident"]["status"]}
