"""Domain registration facts via RDAP: when was this domain created, by which registrar?

RDAP (Registration Data Access Protocol) is the modern, JSON replacement for
WHOIS. A domain registered a few days ago that claims to be your bank is a
strong warning sign, because real banks have used their domains for years.

How the lookup works:
  1. Find the *registrable* domain: login.sbi-kyc.co.in -> sbi-kyc.co.in
     (uses the Public Suffix List, bundled offline).
  2. Ask IANA's official bootstrap list which RDAP server handles ".in", ".com" ...
  3. Query that registry server over HTTPS.

Only official registry servers from IANA's list are contacted, never a host
taken from user input, so this is not an SSRF path.
"""
from __future__ import annotations

import ipaddress
import json
import re
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import quote, urljoin

import httpx
from publicsuffixlist import PublicSuffixList

BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
MAX_RESPONSE_BYTES = 512 * 1024
_DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")

_psl = PublicSuffixList(only_icann=True)
_bootstrap_lock = threading.Lock()
_bootstrap: dict[str, str] | None = None   # tld -> RDAP base URL


@dataclass
class RDAPReport:
    domain: str | None
    status: str                       # "ok" | "not_found" | "unsupported_tld" | "not_applicable" | "error"
    registered: str | None = None
    age_days: int | None = None
    expires: str | None = None
    last_changed: str | None = None
    registrar: str | None = None
    domain_status: list[str] = field(default_factory=list)
    server: str | None = None
    detail: str | None = None


def registrable_domain(host: str) -> str | None:
    """'login.sbi-kyc.co.in' -> 'sbi-kyc.co.in'; None for IPs and bare suffixes."""
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    return _psl.privatesuffix(host.lower().rstrip("."))


MAX_REDIRECTS = 3
REDIRECT_CODES = {301, 302, 303, 307, 308}


class NotFound(Exception):
    """The RDAP server answered 404."""


def _read_json(response: httpx.Response) -> dict:
    data = b""
    for chunk in response.iter_bytes():
        data += chunk
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("RDAP response too large")
    return json.loads(data)


def _get_json(client: httpx.Client, url: str) -> dict:
    """GET JSON, following at most MAX_REDIRECTS redirects ourselves.

    Each redirect target is checked BEFORE it is requested: anything that is not
    https:// is refused, so a redirect can never downgrade us to plain HTTP.
    """
    for _ in range(MAX_REDIRECTS + 1):
        if not url.startswith("https://"):
            raise ValueError("refusing non-HTTPS RDAP URL")
        with client.stream("GET", url, follow_redirects=False) as r:
            if r.status_code in REDIRECT_CODES and "location" in r.headers:
                url = urljoin(url, r.headers["location"])
                continue
            if r.status_code == 404:
                raise NotFound(url)
            r.raise_for_status()
            return _read_json(r)
    raise ValueError("too many RDAP redirects")


def _load_bootstrap(client: httpx.Client) -> dict[str, str]:
    global _bootstrap
    with _bootstrap_lock:
        if _bootstrap is None:
            doc = _get_json(client, BOOTSTRAP_URL)
            mapping: dict[str, str] = {}
            for tlds, urls in doc.get("services", []):
                https = [u for u in urls if u.startswith("https://")]
                if https:
                    for tld in tlds:
                        mapping[tld.lower()] = https[0] if https[0].endswith("/") else https[0] + "/"
            _bootstrap = mapping
        return _bootstrap


def _registrar(doc: dict) -> str | None:
    for entity in doc.get("entities", []):
        if "registrar" in entity.get("roles", []):
            for item in (entity.get("vcardArray") or [None, []])[1]:
                if item and item[0] == "fn":
                    return str(item[3])[:120]
            return entity.get("handle")
    return None


def parse_rdap(domain: str, doc: dict, server: str | None, now: datetime) -> RDAPReport:
    report = RDAPReport(domain=domain, status="ok", server=server)
    for event in doc.get("events", []):
        action = event.get("eventAction")
        date = event.get("eventDate")
        if not date:
            continue
        if action == "registration":
            report.registered = date
            try:
                created = datetime.fromisoformat(date.replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=UTC)
                report.age_days = (now - created).days
            except ValueError:
                pass
        elif action == "expiration":
            report.expires = date
        elif action == "last changed":
            report.last_changed = date
    report.registrar = _registrar(doc)
    report.domain_status = [str(s) for s in doc.get("status", [])][:10]
    return report


def lookup_rdap(domain: str | None, client: httpx.Client | None = None,
                now: datetime | None = None, timeout: float = 6.0) -> RDAPReport:
    """Look up a registrable domain. Never raises: failures are reported as data."""
    now = now or datetime.now(UTC)
    if not domain:
        return RDAPReport(domain=None, status="not_applicable",
                          detail="No registrable domain (IP address or public suffix).")
    if not _DOMAIN_RE.match(domain):
        return RDAPReport(domain=domain, status="error", detail="domain has unexpected characters")

    own_client = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=False,
                                    headers={"Accept": "application/rdap+json"})
    try:
        tld = domain.rsplit(".", 1)[-1]
        base = _load_bootstrap(client).get(tld)
        if not base:
            return RDAPReport(domain=domain, status="unsupported_tld",
                              detail=f"The .{tld} registry does not publish RDAP data.")
        try:
            doc = _get_json(client, f"{base}domain/{quote(domain)}")
        except NotFound:
            return RDAPReport(domain=domain, status="not_found", server=base,
                              detail="The registry has no record of this domain.")
        return parse_rdap(domain, doc, base, now)
    except Exception as exc:
        return RDAPReport(domain=domain, status="error", detail=f"{type(exc).__name__}: {exc}"[:200])
    finally:
        if own_client:
            client.close()


def reset_bootstrap_cache() -> None:
    """For tests."""
    global _bootstrap
    with _bootstrap_lock:
        _bootstrap = None
