"""Mini-SOC workflows end to end: SQLite in a temp folder, fake investigation tools, fixed clock."""
from datetime import UTC, datetime, timedelta

import pytest

from app.security.dns_lookup import DNSReport
from app.security.investigate import Toolkit
from app.security.rdap import RDAPReport
from app.security.redirects import Hop, RedirectTrace
from app.security.reputation import ReputationReport
from app.security.tls_check import TLSReport
from app.soc.service import SunoSafeService
from app.soc.store import Store

FAKE_KYC = ("Dear SBI customer, your account will be BLOCKED today. Update KYC now at "
            "hxxps://sbi-kyc-update[.]in/verify and share the OTP sent to you. Call 9876543210.")


def fake_toolkit():
    def trace(url):
        host = url.split("/")[2]
        return RedirectTrace(url, [Hop(url=url, host=host, ips=("93.184.215.14",), status=200)], url, "reached")
    return Toolkit(
        trace=trace,
        dns=lambda host, reg: DNSReport(host=host, status="ok", a=["93.184.215.14"]),
        rdap=lambda d: RDAPReport(domain=d, status="ok", age_days=3, registered="2026-11-15T00:00:00Z"),
        tls=lambda url: TLSReport(host=url.split("/")[2], status="valid", cert_age_days=2),
        reputation=lambda urls: ReputationReport("google_safe_browsing", "not_configured",
                                                 detail="SAFE_BROWSING_API_KEY is not set"),
    )


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)

    def __call__(self):
        return self.now


@pytest.fixture
def svc(tmp_path):
    return SunoSafeService(Store(tmp_path / "test.db"), fake_toolkit, Clock())


def test_scam_message_opens_incident_with_evidence_and_steps(svc):
    out = svc.analyze_message(FAKE_KYC, sender="VM-SBIKYC")
    assert out["verdict"]["level"] == "high" and out["incident_id"]
    d = svc.incident_detail(out["incident_id"])
    assert d["title"] == "Suspicious message claiming to be State Bank of India"
    assert [s["code"] for s in d["steps"]] == ["do_not_click", "block_link", "report_chakshu"]
    assert ("domain", "sbi-kyc-update.in") in {(i["kind"], i["value"]) for i in d["indicators"]}
    # uncertainty is recorded honestly
    assert any("Safe Browsing is not configured" in u for u in out["verdict"]["uncertainties"])
    # stored text is redacted
    stored = [e for e in d["events"] if e["type"] == "message_analysed"][0]["data"]["text"]
    assert "9876543210" not in stored


def test_genuine_message_creates_no_incident(svc):
    out = svc.analyze_message("OTP for your SBI transaction is 482913. Do not share this OTP with anyone.")
    assert out["incident_id"] is None and out["verdict"]["label"] == "no_known_issues"


def test_call_from_number_in_scam_sms_is_correlated(svc):
    first = svc.analyze_message(FAKE_KYC)
    call = svc.report_call("Caller said he is from SBI and asked for the OTP", "+91 98765 43210", ["otp"])
    assert call["incident_id"] == first["incident_id"]
    d = svc.incident_detail(first["incident_id"])
    assert any(r["rule"] == "C1_shared_indicator" for r in d["rationale"])


def test_unrelated_events_are_not_merged(svc):
    first = svc.analyze_message(FAKE_KYC)
    other = svc.report_call("Caller asked for my UPI PIN", "9123456780", ["upi_pin"])
    assert other["incident_id"] != first["incident_id"]


def test_correlation_window_expires(svc):
    first = svc.analyze_message(FAKE_KYC)
    svc.clock.now += timedelta(days=8)
    later = svc.report_call("asked for otp", "9876543210", ["otp"])
    assert later["incident_id"] != first["incident_id"]


def test_block_requires_confirmation_then_blocks_domain_and_contains_incident(svc):
    out = svc.analyze_message(FAKE_KYC)
    url = "https://sbi-kyc-update.in/verify"
    with pytest.raises(PermissionError):
        svc.block_link(url, confirmed=False, approved_via="voice")
    res = svc.block_link(url, confirmed=True, approved_via="voice")
    assert {"kind": "domain", "value": "sbi-kyc-update.in"} in res["blocked"]
    assert res["incident_id"] == out["incident_id"]
    d = svc.incident_detail(out["incident_id"])
    assert d["status"] == "contained"
    assert {s["code"]: s["status"] for s in d["steps"]}["block_link"] == "done"
    # protected browser now refuses any page on that domain, and logs it to the incident
    check = svc.protect_check("https://login.sbi-kyc-update.in/other-page")
    assert check["action"] == "block" and check["incident_id"] == out["incident_id"]
    assert any(e["type"] == "protected_browser_block" for e in svc.incident_detail(out["incident_id"])["events"])


def test_redirect_loop_to_blocked_link_cannot_flood_the_log(svc):
    out = svc.analyze_message(FAKE_KYC)
    svc.block_link("https://sbi-kyc-update.in/verify", confirmed=True, approved_via="app")
    for _ in range(50):                                   # malicious page bouncing back repeatedly
        assert svc.protect_check("https://sbi-kyc-update.in/verify")["action"] == "block"
    def blocks():
        return [e for e in svc.incident_detail(out["incident_id"])["events"]
                if e["type"] == "protected_browser_block"]
    assert len(blocks()) == 1
    svc.clock.now += timedelta(seconds=61)
    svc.protect_check("https://sbi-kyc-update.in/verify")
    assert len(blocks()) == 2                             # logged again after a minute


@pytest.mark.parametrize("raw, expected", [
    ("+91 98765 43210", "9876543210"), ("98765-43210", "9876543210"), ("919876543210", "9876543210"),
    (None, None), ("", None),
])
def test_caller_number_normalisation(raw, expected):
    from app.soc.service import normalize_caller_number
    assert normalize_caller_number(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "98765abc43", "+91 98765 43210; DROP TABLE", "12"])
def test_invalid_caller_number_is_rejected(svc, raw):
    with pytest.raises(ValueError):
        svc.report_call("asked for otp", raw, ["otp"])


def test_official_domain_is_never_blocked_wholesale(svc):
    res = svc.block_link("https://www.amazon.in/some/page", confirmed=True, approved_via="app")
    assert res["blocked"] == [{"kind": "url", "value": "https://www.amazon.in/some/page"}]
    assert svc.protect_check("https://www.amazon.in/")["action"] == "allow"


def test_protect_check_allow_wording_never_claims_safe(svc):
    assert "does not mean it is safe" in svc.protect_check("https://example.com/")["reason"]


def test_report_scam_builds_recovery_plan(svc):
    out = svc.report_scam("I clicked the SBI KYC link and paid Rs 2000, then shared OTP", ["otp"], amount_lost=2000)
    assert out["verdict"]["level"] in ("high", "critical")
    codes = [s["code"] for s in out["steps"]]
    assert codes[:2] == ["call_1930", "contact_bank"] and "report_cybercrime_portal" in codes
    summary = svc.incident_summary(out["incident_id"])
    assert "Amount reported lost: Rs 2,000.00" in summary and "money paid" in summary


def test_report_scam_attaches_to_existing_incident_and_raises_severity(svc):
    first = svc.analyze_message(FAKE_KYC)
    out = svc.report_scam("I entered my OTP on that page", ["otp"], incident_id=first["incident_id"])
    assert out["incident_id"] == first["incident_id"]
    d = svc.incident_detail(first["incident_id"])
    assert d["severity"] == "critical"
    assert any(r["rule"] == "severity_raised" for r in d["rationale"])


def test_steps_tracking_and_resolution(svc):
    out = svc.analyze_message(FAKE_KYC)
    iid = out["incident_id"]
    with pytest.raises(PermissionError):
        svc.update_step(iid, "block_link", "done", "guardian")   # must use the real block action
    svc.update_step(iid, "do_not_click", "done", "user")
    svc.update_step(iid, "report_chakshu", "skipped", "user")
    svc.block_link("https://sbi-kyc-update.in/verify", confirmed=True, approved_via="app")
    svc.update_step(iid, "report_chakshu", "done", "user")
    assert svc.incident_detail(iid)["status"] == "resolved"


def test_summary_defangs_links(svc):
    out = svc.analyze_message(FAKE_KYC)
    summary = svc.incident_summary(out["incident_id"])
    assert "hxxps://sbi-kyc-update[.]in/verify" in summary and "https://sbi-kyc-update.in" not in summary


def test_notes_are_redacted(svc):
    out = svc.analyze_message(FAKE_KYC)
    svc.add_note(out["incident_id"], "guardian", "Mother's card 4111 1111 1111 1234 blocked at branch")
    assert "4111 1111" not in svc.incident_detail(out["incident_id"])["notes"][0]["text"]
