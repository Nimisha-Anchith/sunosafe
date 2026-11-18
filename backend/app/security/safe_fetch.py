"""Make ONE careful HTTP request to a link that the SSRF guard has already vetted.

Safety properties:
  * IP pinning: the TCP connection goes only to the IPs that `vet_url`
    checked. DNS is not asked again, so DNS rebinding cannot swap in an
    internal address between the check and the request.
  * TLS is still verified against the real hostname (SNI + certificate check),
    because pinning only changes *where* we connect, not *who* we expect.
  * We never read the response body: status line and headers are enough to
    follow redirects and inspect security headers. Nothing is downloaded,
    rendered or executed.
  * No cookies, no credentials, short timeouts, redirects NOT followed here
    (the redirect tracer re-vets every hop itself).
"""
from __future__ import annotations

import ssl
from collections.abc import Callable
from dataclasses import dataclass, field

import certifi
import httpcore

from app.security.ssrf_guard import VettedTarget


def trusted_ssl_context() -> ssl.SSLContext:
    """TLS context with certificate + hostname verification.

    Uses the Mozilla CA bundle from `certifi` so verdicts are identical on every
    machine. (The Windows certificate store can be missing roots, which would
    make a safe site look like it has a broken certificate — a false alarm.)
    """
    return ssl.create_default_context(cafile=certifi.where())

USER_AGENT = "SunoSafe-LinkInspector/0.2 (+https://github.com/Nimisha-Anchith/sunosafe)"

# Response headers worth keeping as evidence. Everything else is dropped.
KEPT_HEADERS = (
    "location", "content-type", "server", "strict-transport-security",
    "content-security-policy", "x-frame-options", "x-content-type-options",
    "referrer-policy", "refresh",
)


@dataclass
class FetchResult:
    status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    set_cookie: bool = False
    connected_ip: str | None = None
    error: str | None = None          # machine-readable code, e.g. "tls_error"
    error_detail: str | None = None


Fetcher = Callable[[VettedTarget, float], FetchResult]


class _PinnedBackend(httpcore.NetworkBackend):
    """Network backend that resolves ONE hostname to a fixed list of vetted IPs."""

    def __init__(self, host: str, ips: tuple[str, ...]):
        self._host = host
        self._ips = ips
        self._inner = httpcore.SyncBackend()
        self.connected_ip: str | None = None

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host.strip("[]").lower() != self._host:
            raise httpcore.ConnectError(f"refusing unexpected host {host}")
        last_error: Exception | None = None
        for ip in self._ips:
            try:
                stream = self._inner.connect_tcp(ip, port, timeout, local_address, socket_options)
                self.connected_ip = ip
                return stream
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        raise last_error or httpcore.ConnectError("no vetted address reachable")

    def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("unix sockets are not allowed")

    def sleep(self, seconds: float) -> None:
        self._inner.sleep(seconds)


def _classify(exc: Exception) -> str:
    text = str(exc)
    if isinstance(exc, (httpcore.ConnectTimeout, httpcore.ReadTimeout, httpcore.WriteTimeout, httpcore.PoolTimeout)):
        return "timeout"
    if "CERTIFICATE_VERIFY_FAILED" in text or "SSL" in text or "TLS" in text or isinstance(exc, ssl.SSLError):
        return "tls_error"
    if isinstance(exc, httpcore.ConnectError):
        return "connect_failed"
    if isinstance(exc, (httpcore.RemoteProtocolError, httpcore.LocalProtocolError)):
        return "protocol_error"
    return "fetch_failed"


def pinned_fetch(target: VettedTarget, timeout: float = 5.0) -> FetchResult:
    """GET the vetted URL once, headers only. Never raises: errors are returned."""
    backend = _PinnedBackend(target.host, target.ips)
    ssl_context = trusted_ssl_context()
    result = FetchResult()
    try:
        with httpcore.ConnectionPool(
            ssl_context=ssl_context, network_backend=backend, max_connections=1, retries=0
        ) as pool:
            with pool.stream(
                "GET",
                target.url,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"},
                extensions={"timeout": {"connect": timeout, "read": timeout, "write": timeout, "pool": timeout}},
            ) as response:
                result.status = response.status
                for raw_name, raw_value in response.headers:
                    name = raw_name.decode("latin-1").lower()
                    if name == "set-cookie":
                        result.set_cookie = True
                    elif name in KEPT_HEADERS and name not in result.headers:
                        result.headers[name] = raw_value.decode("latin-1")[:500]
                # Body intentionally not read; leaving the block closes the connection.
    except Exception as exc:  # network errors are data, not crashes
        result.error = _classify(exc)
        result.error_detail = str(exc)[:300]
    result.connected_ip = backend.connected_ip
    return result
