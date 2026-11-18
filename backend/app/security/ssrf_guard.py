"""SSRF guard: decide whether SunoSafe's *server* may connect to a link.

SSRF (Server-Side Request Forgery) is when an attacker tricks a server into
making requests on their behalf. SunoSafe investigates links that strangers
send, so an attacker could submit http://169.254.169.254/ (the cloud metadata
service that holds server credentials) or http://localhost:8000/admin and use
our investigator to reach things that are only reachable from inside.

Rules enforced here:
  * only http/https, only ports 80/443
  * no internal-only hostnames (localhost, *.internal, *.local ...)
  * resolve the name with DNS and require EVERY address to be public internet
  * return the vetted IPs, so the fetcher (Milestone 2) connects to exactly
    those addresses. Re-resolving later would allow "DNS rebinding": the name
    answers with a public IP during the check and a private one at fetch time.

This module performs DNS lookups only. It never downloads anything.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass

from app.security.url_normalize import URLNormalizeError, normalize_url

ALLOWED_SCHEMES = frozenset({"http", "https"})
ALLOWED_PORTS = frozenset({80, 443})

BLOCKED_HOSTNAMES = frozenset({"localhost", "metadata", "metadata.google.internal"})
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa", ".lan", ".intranet", ".corp")

# NAT64 prefix: IPv6 addresses that embed an IPv4 address in their last 32 bits.
_NAT64 = ipaddress.ip_network("64:ff9b::/96")

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[[str, int], list[str]]


class UnsafeTargetError(Exception):
    """The server must not connect to this link. `code` is machine-readable."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class VettedTarget:
    url: str              # normalised URL
    scheme: str
    host: str
    port: int
    ips: tuple[str, ...]  # connect ONLY to these addresses


def is_public_ip(ip: str | IPAddress) -> bool:
    """True only for addresses on the public internet."""
    addr = ipaddress.ip_address(ip) if isinstance(ip, str) else ip
    if isinstance(addr, ipaddress.IPv6Address):
        # IPv6 forms that smuggle an IPv4 address inside them: check the IPv4.
        if addr.ipv4_mapped is not None:
            return is_public_ip(addr.ipv4_mapped)
        if addr in _NAT64:
            return is_public_ip(ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF))
        if addr.sixtofour is not None:
            return is_public_ip(addr.sixtofour)
        if addr.teredo is not None:
            return False  # tunnelled address; no legitimate reason to allow
    # is_global is False for private, loopback, link-local (169.254.x.x incl.
    # cloud metadata), carrier-grade NAT (100.64/10), documentation ranges, etc.
    return addr.is_global and not addr.is_multicast and not addr.is_reserved


def system_resolver(host: str, port: int) -> list[str]:
    """Resolve a hostname to all its IPv4/IPv6 addresses using the OS."""
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    # Strip IPv6 zone ids such as fe80::1%12.
    return sorted({info[4][0].split("%", 1)[0] for info in infos})


def vet_url(raw_url: str, resolver: Resolver = system_resolver) -> VettedTarget:
    """Return a VettedTarget if the server may fetch this link, else raise UnsafeTargetError."""
    try:
        n = normalize_url(raw_url)
    except URLNormalizeError as exc:
        raise UnsafeTargetError("invalid_url", str(exc)) from None

    if n.scheme not in ALLOWED_SCHEMES:
        raise UnsafeTargetError("scheme_not_allowed", f"'{n.scheme}' links are never fetched")

    port = n.port or (443 if n.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise UnsafeTargetError("port_not_allowed", f"port {port} is not 80 or 443")

    host = n.host
    if host in BLOCKED_HOSTNAMES or host.endswith(BLOCKED_SUFFIXES):
        raise UnsafeTargetError("blocked_hostname", f"{host} is an internal-only name")

    try:
        literal: IPAddress | None = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        ips = [str(literal)]
    else:
        try:
            ips = resolver(host, port)
        except (socket.gaierror, UnicodeError, OSError) as exc:
            raise UnsafeTargetError("dns_resolution_failed", f"{host}: {exc}") from None
        if not ips:
            raise UnsafeTargetError("dns_resolution_failed", f"{host} has no addresses")

    bad = [ip for ip in ips if not is_public_ip(ip)]
    if bad:
        # Even one private answer blocks the whole target (defeats mixed answers).
        raise UnsafeTargetError("private_address", f"{host} resolves to non-public {', '.join(bad)}")

    return VettedTarget(n.url, n.scheme, host, port, tuple(ips))
