"""End-to-end investigation tests with a fully fake toolkit, plus API tests."""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import main
from app.security.dns_lookup import DNSReport
from app.security.investigate import Toolkit, investigate_url
from app.security.rdap import RDAPReport
from app.security.redirects import Hop, RedirectTrace
from app.security.reputation import ReputationReport, ThreatMatch
from app.security.tls_check import TLSReport

NOW = datetime(2026, 11, 18, tzinfo=UTC)


def scam_toolkit(sent_to_reputation=None):
    def trace(url):
        return RedirectTrace(url, [
            Hop(url=url, host="bit.ly", ips=("67.199.248.10",), status=301, location="https://sbi-kyc-update.example/"),
            Hop(url="https://sbi-kyc-update.example/", host="sbi-kyc-update.example", ips=("93.184.215.14",), status=200),
        ], "https://sbi-kyc-update.example/", "reached")

    def reputation(urls):
        if sent_to_reputation is not None:
            sent_to_reputation.extend(urls)
        return ReputationReport("google_safe_browsing", "flagged",
                                [ThreatMatch("https://sbi-kyc-update.example/", "SOCIAL_ENGINEERING", "ANY_PLATFORM")])

    return Toolkit(
        trace=trace,
        dns=lambda host, reg: DNSReport(host=host, status="ok", a=["93.184.215.14"]),
        rdap=lambda d: RDAPReport(domain=d, status="ok", age_days=3 if d == "sbi-kyc-update.example" else 5000,
                                  registered="2026-11-15T00:00:00Z"),
        tls=lambda url: TLSReport(host="sbi-kyc-update.example", status="valid", cert_age_days=2),
        reputation=reputation,
    )


def codes(inv):
    return {(f.tool, f.code) for f in inv.findings}


def test_scam_link_produces_evidence_from_every_tool():
    sent = []
    inv = investigate_url("bit.ly/abc", scam_toolkit(sent), now=NOW)
    assert {
        ("url_normalize", "url_shortener"),
        ("redirects", "redirect_chain"),
        ("redirects", "destination_differs"),
        ("rdap", "domain_recently_registered"),
        ("tls", "certificate_very_new"),
        ("reputation", "known_dangerous_site"),
    } <= codes(inv)
    assert sent == ["http://bit.ly/abc", "https://sbi-kyc-update.example/"]  # whole chain checked
    assert all(r.status == "ok" for r in inv.tool_runs)


def test_a_crashing_tool_is_recorded_as_failed_not_ignored():
    tk = scam_toolkit()

    def broken_rdap(domain):
        raise TimeoutError("registry slow")
    tk.rdap = broken_rdap
    inv = investigate_url("bit.ly/abc", tk, now=NOW)
    failed = [r for r in inv.tool_runs if r.tool == "rdap"]
    assert failed and all(r.status == "failed" for r in failed)
    assert ("rdap", "domain_recently_registered") not in codes(inv)  # no invented evidence


def test_upi_link_is_never_fetched():
    def must_not_run(*_):
        raise AssertionError("network tool called for a upi: link")
    tk = Toolkit(trace=must_not_run, dns=must_not_run, rdap=must_not_run, tls=must_not_run, reputation=must_not_run)
    inv = investigate_url("upi://pay?pa=refund@ybl&am=1", tk, now=NOW)
    assert ("url_normalize", "upi_payment_link") in codes(inv)
    assert {r.status for r in inv.tool_runs if r.tool != "url_normalize"} == {"skipped"}


def test_internal_link_is_not_sent_to_reputation_provider():
    sent = []
    tk = scam_toolkit(sent)
    tk.trace = lambda url: RedirectTrace(url, [Hop(url=url, error="private_address")], url,
                                         "blocked_unsafe_hop", "private_address")
    inv = investigate_url("http://169.254.169.254/latest", tk, now=NOW)
    assert ("ssrf_guard", "link_to_internal_address") in codes(inv)
    assert sent == []


def test_garbage_input():
    inv = investigate_url("http://", scam_toolkit(), now=NOW)
    assert ("url_normalize", "not_a_link") in codes(inv)


# ---------- API ----------
@pytest.fixture
def client(monkeypatch):
    from app.config import Settings
    # No token configured + request from this computer = allowed (independent of any local .env).
    monkeypatch.setattr(main, "get_settings", lambda: Settings(None, ("1.1.1.1",), 5.0, None, ":memory:"))
    monkeypatch.setattr(main, "default_toolkit", lambda settings: scam_toolkit())
    main._hits.clear()
    return TestClient(main.app, client=("127.0.0.1", 50000))


def test_api_returns_findings(client):
    r = client.post("/api/investigate/url", json={"url": "bit.ly/abc"})
    assert r.status_code == 200
    assert any(f["code"] == "known_dangerous_site" for f in r.json()["findings"])


def test_api_validates_input(client):
    assert client.post("/api/investigate/url", json={"url": ""}).status_code == 422
    assert client.post("/api/investigate/url", json={"url": "x" * 3000}).status_code == 422


def test_rate_limiter_forgets_idle_clients(monkeypatch):
    main._hits.clear()
    monkeypatch.setattr(main, "SWEEP_THRESHOLD", 5)
    clock = [1000.0]
    monkeypatch.setattr(main.time, "monotonic", lambda: clock[0])
    for i in range(5):
        main._check_rate_limit(f"10.0.0.{i}")
    clock[0] += main.RATE_WINDOW + 1          # everyone goes idle
    main._check_rate_limit("10.0.0.99")       # triggers the sweep
    assert list(main._hits) == ["10.0.0.99"]  # memory stays bounded


def test_api_rate_limit(client):
    for _ in range(main.RATE_LIMIT):
        assert client.post("/api/investigate/url", json={"url": "bit.ly/abc"}).status_code == 200
    assert client.post("/api/investigate/url", json={"url": "bit.ly/abc"}).status_code == 429
