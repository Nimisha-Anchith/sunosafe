"""Investigate one link end to end and return evidence with provenance.

Pipeline:
    normalise ─► trace redirects (every hop SSRF-checked)
                     │
                     ├─► DNS of final host          ┐
                     ├─► RDAP age of each domain    │  run in parallel
                     ├─► TLS certificate of final   │  (voice users should
                     └─► Safe Browsing, all hops    ┘   not wait long)
                     ▼
               findings[]  — each says WHICH tool observed WHAT

This module reports facts. It does NOT decide "safe" or "dangerous"; the
severity rules (Milestone 3) combine findings into an evidence-based verdict.
Every tool's run is recorded (ok / failed / skipped / not_configured) so a
failure is visible instead of silently becoming "looks fine".
"""
from __future__ import annotations

import ipaddress
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.config import Settings
from app.security.dns_lookup import DNSReport, default_dns_resolver, lookup_dns
from app.security.rdap import RDAPReport, lookup_rdap, registrable_domain
from app.security.redirects import RedirectTrace, trace_redirects
from app.security.reputation import ReputationReport, check_safe_browsing
from app.security.ssrf_guard import vet_url
from app.security.tls_check import TLSReport, check_tls
from app.security.url_normalize import INDICATOR_TEXT, NormalizedURL, normalize_url

RECENT_DOMAIN_DAYS = 30        # registered within a month
YOUNG_DOMAIN_DAYS = 180        # registered within six months
NEW_CERT_DAYS = 7              # certificate issued within a week


@dataclass
class Finding:
    tool: str                  # provenance: which tool observed this
    code: str                  # machine-readable fact, e.g. "domain_recently_registered"
    detail: str                # plain-language explanation
    evidence: dict = field(default_factory=dict)


@dataclass
class ToolRun:
    tool: str
    status: str                # "ok" | "failed" | "skipped" | "not_configured"
    duration_ms: int = 0
    detail: str | None = None


@dataclass
class URLInvestigation:
    input: str
    investigated_at: str
    normalized: NormalizedURL | None
    redirects: RedirectTrace | None = None
    dns: DNSReport | None = None
    rdap: list[RDAPReport] = field(default_factory=list)
    tls: TLSReport | None = None
    reputation: ReputationReport | None = None
    findings: list[Finding] = field(default_factory=list)
    tool_runs: list[ToolRun] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Toolkit:
    """The tools, injectable so tests never touch the network."""
    trace: Callable[[str], RedirectTrace]
    dns: Callable[[str, str | None], DNSReport]
    rdap: Callable[[str | None], RDAPReport]
    tls: Callable[[str], TLSReport]
    reputation: Callable[[list[str]], ReputationReport]


def default_toolkit(settings: Settings) -> Toolkit:
    dns_resolver = default_dns_resolver(settings.dns_servers)
    timeout = settings.http_timeout
    return Toolkit(
        trace=lambda url: trace_redirects(url, timeout=timeout),
        dns=lambda host, reg: lookup_dns(host, reg, dns_resolver),
        rdap=lambda domain: lookup_rdap(domain, timeout=timeout),
        tls=lambda url: check_tls(vet_url(url), timeout=timeout),
        reputation=lambda urls: check_safe_browsing(urls, settings.safe_browsing_api_key, timeout=timeout),
    )


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _timed(runs: list[ToolRun], tool: str, fn, *args):
    start = time.perf_counter()
    try:
        result = fn(*args)
        runs.append(ToolRun(tool, "ok", int((time.perf_counter() - start) * 1000)))
        return result
    except Exception as exc:  # a tool crash is recorded, never hidden
        runs.append(ToolRun(tool, "failed", int((time.perf_counter() - start) * 1000),
                            f"{type(exc).__name__}: {exc}"[:200]))
        return None


def _redirect_findings(trace: RedirectTrace) -> list[Finding]:
    out: list[Finding] = []
    hops = [h.url for h in trace.hops]
    # A plain http -> https upgrade on the same site is normal, not evidence.
    simple_upgrade = (len(trace.hops) == 2 and not trace.changed_host
                      and hops[0].startswith("http://") and hops[1].startswith("https://"))
    if len(trace.hops) > 1 and not simple_upgrade:
        out.append(Finding("redirects", "redirect_chain",
                           f"The link forwards {len(trace.hops) - 1} time(s) before reaching its destination.",
                           {"hops": hops}))
    if trace.changed_host:
        out.append(Finding("redirects", "destination_differs",
                           f"The link starts at {trace.hosts[0]} but ends at {trace.hosts[-1]}.",
                           {"from": trace.hosts[0], "to": trace.hosts[-1]}))
    last = trace.hops[-1] if trace.hops else None
    if trace.outcome == "blocked_unsafe_hop":
        if len(trace.hops) == 1:
            code, text = "link_to_internal_address", "The link points to a private or internal network address."
        else:
            code, text = ("redirect_to_internal_address",
                          "The link forwards you to a private or internal network address.")
        out.append(Finding("ssrf_guard", code, text, {"url": trace.final_url, "code": trace.blocked_code}))
    elif trace.outcome == "non_web_redirect":
        out.append(Finding("redirects", "redirect_to_app_or_payment_link",
                           "The link forwards to a non-website link (for example an app or payment link).",
                           {"url": trace.final_url}))
    elif trace.outcome == "too_many_redirects":
        out.append(Finding("redirects", "too_many_redirects",
                           "The link forwards too many times; this is used to hide the destination.",
                           {"hops": hops}))
    elif trace.outcome == "redirect_loop":
        out.append(Finding("redirects", "redirect_loop", "The link forwards in a loop.", {"hops": hops}))
    elif trace.outcome == "fetch_error" and last is not None:
        if last.error == "dns_resolution_failed":
            out.append(Finding("redirects", "site_unreachable",
                               "The website name could not be found; the site may be down or removed.",
                               {"url": last.url}))
        elif last.error != "tls_error":  # TLS problems are explained by the TLS tool
            out.append(Finding("redirects", "site_unreachable",
                               "The website did not respond to our safe check.",
                               {"url": last.url, "error": last.error}))
    if last is not None and "refresh" in last.headers:
        out.append(Finding("redirects", "refresh_header_redirect",
                           "The page uses a delayed automatic redirect.", {"refresh": last.headers["refresh"]}))
    return out


def investigate_url(raw: str, toolkit: Toolkit, now: datetime | None = None) -> URLInvestigation:
    now = now or datetime.now(UTC)
    runs: list[ToolRun] = []
    inv = URLInvestigation(input=raw, investigated_at=now.isoformat(), normalized=None, tool_runs=runs)

    # 1. Normalise (pure, never touches the network).
    try:
        n = normalize_url(raw)
    except ValueError as exc:
        runs.append(ToolRun("url_normalize", "failed", 0, str(exc)))
        inv.findings.append(Finding("url_normalize", "not_a_link", "This does not look like a valid link."))
        return inv
    inv.normalized = n
    runs.append(ToolRun("url_normalize", "ok"))
    for code in n.indicators:
        inv.findings.append(Finding("url_normalize", code, INDICATOR_TEXT[code], {"url": n.url}))
    if n.scheme not in ("http", "https"):
        for tool in ("redirects", "dns", "rdap", "tls", "reputation"):
            runs.append(ToolRun(tool, "skipped", 0, f"{n.scheme}: links are never fetched"))
        return inv

    # 2. Redirect chain (sequential by nature).
    trace = _timed(runs, "redirects", toolkit.trace, n.url)
    inv.redirects = trace
    if trace is not None:
        inv.findings.extend(_redirect_findings(trace))

    # The final reachable host is what the user would actually land on.
    web_hops = [h for h in (trace.hops if trace else []) if h.host]
    final_host = web_hops[-1].host if web_hops else n.host
    final_url = web_hops[-1].url if web_hops else n.url
    domains = list(dict.fromkeys(d for d in (registrable_domain(n.host), registrable_domain(final_host)) if d))
    # Only hops that passed the SSRF guard (they have a host) go to the reputation
    # provider: internal addresses are never sent to a third party.
    chain_urls = [h.url for h in web_hops if h.host]
    final_is_ip = _is_ip(final_host)

    # 3. Independent checks in parallel.
    def run_tls():
        # Only contact a hop the redirect tracer already vetted with the SSRF guard.
        if not web_hops:
            runs.append(ToolRun("tls", "skipped", 0, "no hop was safe and reachable to inspect"))
            return None
        return _timed(runs, "tls", toolkit.tls, final_url)

    def run_dns():
        if final_is_ip:
            runs.append(ToolRun("dns", "skipped", 0, "the link uses an IP address, not a name"))
            return None
        return _timed(runs, "dns", toolkit.dns, final_host, registrable_domain(final_host))

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_dns = pool.submit(run_dns)
        f_rdap = [pool.submit(_timed, runs, "rdap", toolkit.rdap, d) for d in domains]
        f_tls = pool.submit(run_tls)
        f_rep = pool.submit(_timed, runs, "reputation", toolkit.reputation, chain_urls)
        inv.dns = f_dns.result()
        inv.rdap = [r for r in (f.result() for f in f_rdap) if r is not None]
        inv.tls = f_tls.result()
        inv.reputation = f_rep.result()

    # 4. Turn tool outputs into findings (facts with provenance).
    if inv.dns and inv.dns.status == "nxdomain":
        inv.findings.append(Finding("dns", "domain_does_not_exist", "This website name does not exist.",
                                    {"host": final_host}))
    for r in inv.rdap:
        if r.status == "ok" and r.age_days is not None:
            if r.age_days < RECENT_DOMAIN_DAYS:
                inv.findings.append(Finding("rdap", "domain_recently_registered",
                                            f"The website {r.domain} was created only {r.age_days} day(s) ago.",
                                            {"domain": r.domain, "registered": r.registered, "age_days": r.age_days}))
            elif r.age_days < YOUNG_DOMAIN_DAYS:
                inv.findings.append(Finding("rdap", "domain_young",
                                            f"The website {r.domain} is less than six months old ({r.age_days} days).",
                                            {"domain": r.domain, "registered": r.registered, "age_days": r.age_days}))
        elif r.status == "not_found":
            inv.findings.append(Finding("rdap", "domain_not_registered",
                                        f"The registry has no record of {r.domain}.", {"domain": r.domain}))
    if inv.tls:
        if inv.tls.status == "invalid":
            inv.findings.append(Finding("tls", f"tls_{inv.tls.problem}",
                                        "The website's security certificate is not valid "
                                        f"({inv.tls.problem.replace('_', ' ')}).",
                                        {"host": inv.tls.host, "detail": inv.tls.detail}))
        elif inv.tls.status == "not_https":
            inv.findings.append(Finding("tls", "final_page_not_encrypted",
                                        "The page you would land on is not encrypted (no HTTPS).",
                                        {"host": inv.tls.host}))
        elif (inv.tls.status == "valid" and inv.tls.cert_age_days is not None
              and inv.tls.cert_age_days < NEW_CERT_DAYS):
            inv.findings.append(Finding("tls", "certificate_very_new",
                                        f"The website's certificate was issued {inv.tls.cert_age_days} day(s) ago.",
                                        {"host": inv.tls.host, "issuer": inv.tls.issuer_org,
                                         "not_before": inv.tls.not_before}))
    if inv.reputation and inv.reputation.status == "flagged":
        for m in inv.reputation.matches:
            inv.findings.append(Finding("reputation", "known_dangerous_site",
                                        f"Google Safe Browsing lists this address as {m.threat_type.replace('_', ' ').lower()}.",
                                        {"url": m.url, "threat_type": m.threat_type,
                                         "provider": inv.reputation.provider}))
    if inv.reputation and inv.reputation.status == "not_configured":
        for run in runs:
            if run.tool == "reputation":
                run.status, run.detail = "not_configured", inv.reputation.detail
    return inv
