"""Inspect a website's HTTPS certificate: is it valid, who issued it, how new is it?

The browser padlock only means "this connection is encrypted". Phishing
sites get free, valid certificates too, so a padlock is NOT proof of safety.
What is useful as evidence:
  * an INVALID certificate (expired, wrong name, self-signed, unknown issuer)
  * a certificate issued only days ago (common for freshly built scam sites)
  * the certificate's subject not matching the brand the message claims

We connect only to IPs already vetted by the SSRF guard, with full
verification (Mozilla CA bundle via certifi).
"""
from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.security.safe_fetch import trusted_ssl_context
from app.security.ssrf_guard import VettedTarget

# OpenSSL verification error codes -> plain problem names.
_VERIFY_PROBLEMS = {
    9: "not_yet_valid",
    10: "expired",
    18: "self_signed",
    19: "self_signed_chain",
    20: "untrusted_issuer",
    21: "untrusted_issuer",
    23: "revoked",
    62: "hostname_mismatch",
}


@dataclass
class TLSReport:
    host: str
    status: str                      # "valid" | "invalid" | "not_https" | "unreachable"
    problem: str | None = None       # e.g. "expired", "hostname_mismatch", "self_signed"
    detail: str | None = None
    issuer_org: str | None = None
    issuer_cn: str | None = None
    subject_cn: str | None = None
    san: list[str] = field(default_factory=list)
    not_before: str | None = None
    not_after: str | None = None
    cert_age_days: int | None = None
    days_until_expiry: int | None = None
    tls_version: str | None = None


def _name_field(name_tuple, key: str) -> str | None:
    for rdn in name_tuple or ():
        for k, v in rdn:
            if k == key:
                return v
    return None


def report_from_cert(host: str, cert: dict, tls_version: str | None, now: datetime) -> TLSReport:
    """Build a 'valid' report from Python's parsed certificate dict."""
    not_before = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notBefore"]), UTC)
    not_after = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), UTC)
    return TLSReport(
        host=host,
        status="valid",
        issuer_org=_name_field(cert.get("issuer"), "organizationName"),
        issuer_cn=_name_field(cert.get("issuer"), "commonName"),
        subject_cn=_name_field(cert.get("subject"), "commonName"),
        san=[v for k, v in cert.get("subjectAltName", ()) if k == "DNS"][:20],
        not_before=not_before.isoformat(),
        not_after=not_after.isoformat(),
        cert_age_days=(now - not_before).days,
        days_until_expiry=(not_after - now).days,
        tls_version=tls_version,
    )


def check_tls(target: VettedTarget, timeout: float = 5.0, now: datetime | None = None) -> TLSReport:
    """Handshake with full verification. Never raises: problems are returned as data."""
    now = now or datetime.now(UTC)
    if target.scheme != "https":
        return TLSReport(host=target.host, status="not_https",
                         detail="The site does not use HTTPS, so the connection is not encrypted.")

    context = trusted_ssl_context()
    last_error = "no vetted address reachable"
    for ip in target.ips:
        try:
            with socket.create_connection((ip, target.port), timeout=timeout) as raw:
                with context.wrap_socket(raw, server_hostname=target.host) as tls:
                    return report_from_cert(target.host, tls.getpeercert(), tls.version(), now)
        except ssl.SSLCertVerificationError as exc:
            problem = _VERIFY_PROBLEMS.get(exc.verify_code, "verification_failed")
            return TLSReport(host=target.host, status="invalid", problem=problem,
                             detail=str(exc.verify_message or exc)[:200])
        except ssl.SSLError as exc:
            return TLSReport(host=target.host, status="invalid", problem="handshake_failed",
                             detail=str(exc)[:200])
        except OSError as exc:  # timeout, refused, unreachable: try the next vetted IP
            last_error = str(exc)[:200]
    return TLSReport(host=target.host, status="unreachable", detail=last_error)
