"""DNS, RDAP and TLS tests using fakes and httpx.MockTransport (no network)."""
from datetime import UTC, datetime

import dns.resolver
import httpx
import pytest

from app.security import rdap
from app.security.dns_lookup import lookup_dns
from app.security.rdap import lookup_rdap, parse_rdap, registrable_domain
from app.security.tls_check import report_from_cert

NOW = datetime(2026, 11, 18, tzinfo=UTC)


# ---------- DNS ----------
class _Rdata:
    def __init__(self, text):
        self._t = text

    def to_text(self):
        return self._t


class FakeResolver:
    def __init__(self, answers=None, raise_for=None):
        self.answers = answers or {}
        self.raise_for = raise_for

    def resolve(self, name, rdtype):
        if self.raise_for:
            raise self.raise_for
        if (name, rdtype) not in self.answers:
            raise dns.resolver.NoAnswer()
        return [_Rdata(t) for t in self.answers[(name, rdtype)]]


def test_dns_collects_records():
    r = FakeResolver({("www.bank.example", "A"): ["93.184.215.14"],
                      ("bank.example", "MX"): ["10 mail.bank.example."],
                      ("bank.example", "NS"): ["ns1.dns.example."]})
    rep = lookup_dns("www.bank.example", "bank.example", r)
    assert rep.status == "ok" and rep.a == ["93.184.215.14"]
    assert rep.mx == ["mail.bank.example"] and rep.ns == ["ns1.dns.example"]


def test_dns_nxdomain():
    rep = lookup_dns("nope.example", "nope.example", FakeResolver(raise_for=dns.resolver.NXDOMAIN()))
    assert rep.status == "nxdomain"


def test_dns_server_failure_is_an_error_not_an_empty_answer():
    rep = lookup_dns("x.example", "x.example", FakeResolver(raise_for=dns.resolver.NoNameservers()))
    assert rep.status == "error"


# ---------- RDAP ----------
@pytest.mark.parametrize("host, expected", [
    ("login.sbi-kyc.co.in", "sbi-kyc.co.in"),
    ("www.example.com", "example.com"),
    ("93.184.215.14", None),
    ("co.in", None),
])
def test_registrable_domain(host, expected):
    assert registrable_domain(host) == expected


BOOTSTRAP = {"services": [[["in"], ["https://rdap.registry.in/"]], [["com"], ["https://rdap.verisign.com/com/v1/"]]]}


def _client(domain_responses):
    def handler(request: httpx.Request):
        if request.url == rdap.BOOTSTRAP_URL:
            return httpx.Response(200, json=BOOTSTRAP)
        for suffix, (status, body) in domain_responses.items():
            if str(request.url).endswith(suffix):
                return httpx.Response(status, json=body)
        return httpx.Response(500)
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _fresh_bootstrap():
    rdap.reset_bootstrap_cache()
    yield
    rdap.reset_bootstrap_cache()


def test_rdap_young_domain_age_and_registrar():
    body = {"events": [{"eventAction": "registration", "eventDate": "2026-11-15T09:00:00Z"},
                       {"eventAction": "expiration", "eventDate": "2027-11-15T09:00:00Z"}],
            "entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "Cheap Names Ltd"]]]}],
            "status": ["client transfer prohibited"]}
    rep = lookup_rdap("sbi-kyc.co.in", _client({"domain/sbi-kyc.co.in": (200, body)}), now=NOW)
    assert rep.status == "ok" and rep.age_days == 2 and rep.registrar == "Cheap Names Ltd"


def test_rdap_not_found_and_unsupported_tld():
    c = _client({"domain/ghost.com": (404, {})})
    assert lookup_rdap("ghost.com", c, now=NOW).status == "not_found"
    assert lookup_rdap("thing.io", c, now=NOW).status == "unsupported_tld"


def test_rdap_error_is_reported():
    assert lookup_rdap("broken.com", _client({}), now=NOW).status == "error"


def test_rdap_refuses_redirect_to_plain_http_before_requesting_it():
    requested = []

    def handler(request: httpx.Request):
        requested.append(str(request.url))
        if request.url == rdap.BOOTSTRAP_URL:
            return httpx.Response(200, json=BOOTSTRAP)
        return httpx.Response(302, headers={"location": "http://downgrade.example/domain/x.com"})

    rep = lookup_rdap("x.com", httpx.Client(transport=httpx.MockTransport(handler)), now=NOW)
    assert rep.status == "error"
    assert not any(u.startswith("http://") for u in requested)  # never contacted


def test_rdap_follows_https_redirect():
    def handler(request: httpx.Request):
        if request.url == rdap.BOOTSTRAP_URL:
            return httpx.Response(200, json=BOOTSTRAP)
        if request.url.host == "rdap.verisign.com":
            return httpx.Response(301, headers={"location": "https://rdap.mirror.example/domain/x.com"})
        return httpx.Response(200, json={"events": [{"eventAction": "registration",
                                                      "eventDate": "2000-01-01T00:00:00Z"}]})

    rep = lookup_rdap("x.com", httpx.Client(transport=httpx.MockTransport(handler)), now=NOW)
    assert rep.status == "ok" and rep.age_days > 9000


def test_rdap_rejects_odd_domain_text():
    assert lookup_rdap("bad/../path.com", now=NOW).status == "error"


def test_parse_rdap_handles_missing_fields():
    rep = parse_rdap("x.com", {}, None, NOW)
    assert rep.status == "ok" and rep.age_days is None


# ---------- TLS ----------
def test_report_from_cert_computes_ages():
    cert = {
        "subject": ((("commonName", "secure-login.example"),),),
        "issuer": ((("organizationName", "Let's Encrypt"),), (("commonName", "R11"),)),
        "notBefore": "Nov 16 00:00:00 2026 GMT",
        "notAfter": "Feb 14 00:00:00 2027 GMT",
        "subjectAltName": (("DNS", "secure-login.example"),),
    }
    rep = report_from_cert("secure-login.example", cert, "TLSv1.3", NOW)
    assert rep.status == "valid" and rep.issuer_org == "Let's Encrypt"
    assert rep.cert_age_days == 2 and rep.days_until_expiry == 88
    assert rep.san == ["secure-login.example"]
