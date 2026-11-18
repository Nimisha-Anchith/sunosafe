"""DNS facts about a website: does the name exist, where does it point, who hosts it?

DNS is the internet's phone book. Useful evidence for a suspicious link:
  * NXDOMAIN — the name does not exist (link is dead or was taken down)
  * CNAME — the name is an alias for another host (often a hosting platform)
  * NS — which DNS provider runs the domain
  * MX — whether the domain can receive e-mail (real banks always can)

These are context, not verdicts: plenty of honest small sites have no MX.

We ask well-known public resolvers by default (configurable), so results do
not depend on the laptop's home router or an ISP that rewrites answers. A
resolver *failure* is reported as an error, never as "no records".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import dns.exception
import dns.resolver

DEFAULT_DNS_SERVERS = ("1.1.1.1", "8.8.8.8")


class DNSResolverLike(Protocol):
    def resolve(self, qname: str, rdtype: str): ...


@dataclass
class DNSReport:
    host: str
    status: str                       # "ok" | "nxdomain" | "error"
    a: list[str] = field(default_factory=list)
    aaaa: list[str] = field(default_factory=list)
    cname: list[str] = field(default_factory=list)
    ns: list[str] = field(default_factory=list)
    mx: list[str] = field(default_factory=list)
    detail: str | None = None


def default_dns_resolver(servers: tuple[str, ...] = DEFAULT_DNS_SERVERS,
                         timeout: float = 3.0) -> DNSResolverLike:
    r = dns.resolver.Resolver(configure=not servers)
    if servers:
        r.nameservers = list(servers)
    r.lifetime = timeout
    r.timeout = timeout
    return r


def _records(resolver: DNSResolverLike, name: str, rdtype: str, limit: int = 10) -> list[str]:
    """Records of one type. NoAnswer = none of this type (normal). Other errors propagate."""
    try:
        answer = resolver.resolve(name, rdtype)
    except dns.resolver.NoAnswer:
        return []
    values = []
    for rdata in answer:
        text = rdata.to_text().rstrip(".")
        if rdtype == "MX":  # "10 mail.example.com." -> "mail.example.com"
            text = text.split()[-1].rstrip(".")
        values.append(text.lower())
    return sorted(set(values))[:limit]


def lookup_dns(host: str, registrable: str | None, resolver: DNSResolverLike | None = None) -> DNSReport:
    """Query A/AAAA/CNAME for the host and NS/MX for its registrable domain. Never raises."""
    resolver = resolver or default_dns_resolver()
    report = DNSReport(host=host, status="ok")
    try:
        report.a = _records(resolver, host, "A")          # NXDOMAIN surfaces here first
        report.aaaa = _records(resolver, host, "AAAA")
        report.cname = _records(resolver, host, "CNAME")
        zone = registrable or host
        report.ns = _records(resolver, zone, "NS")
        report.mx = _records(resolver, zone, "MX")
    except dns.resolver.NXDOMAIN:
        report = DNSReport(host=host, status="nxdomain", detail=f"{host} does not exist in DNS")
    except dns.resolver.NoNameservers:
        report.status = "error"
        report.detail = "DNS servers failed to answer (SERVFAIL); existence unknown"
    except dns.exception.DNSException as exc:
        report.status = "error"
        report.detail = f"{type(exc).__name__}: {exc}"[:200]
    return report
