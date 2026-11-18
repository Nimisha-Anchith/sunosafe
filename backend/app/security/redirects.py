"""Follow a link's redirect chain hop by hop, re-checking every hop for safety.

Scam links rarely go straight to the fake page. They bounce through
shorteners and trackers so filters only see the harmless first hop. We follow
each redirect ourselves (never automatically) so that EVERY hop passes the
SSRF guard, and we record the full chain as evidence.

Limits: at most MAX_HOPS redirects, a timeout per hop, headers only. Redirects
done with JavaScript inside a page cannot be seen without running the page,
which we deliberately never do; that gap is reported, not hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from app.security.safe_fetch import Fetcher, FetchResult, pinned_fetch
from app.security.ssrf_guard import Resolver, UnsafeTargetError, system_resolver, vet_url
from app.security.url_normalize import normalize_url

MAX_HOPS = 6
REDIRECT_CODES = {301, 302, 303, 307, 308}


@dataclass
class Hop:
    url: str
    host: str = ""
    ips: tuple[str, ...] = ()
    status: int | None = None
    location: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    set_cookie: bool = False
    error: str | None = None
    error_detail: str | None = None


@dataclass
class RedirectTrace:
    start_url: str
    hops: list[Hop]
    final_url: str
    outcome: str   # "reached" | "blocked_unsafe_hop" | "fetch_error" | "too_many_redirects" | "non_web_redirect" | "redirect_loop"
    blocked_code: str | None = None   # SSRF guard code when outcome is blocked_unsafe_hop

    @property
    def hosts(self) -> list[str]:
        return [h.host for h in self.hops if h.host]

    @property
    def changed_host(self) -> bool:
        hosts = self.hosts
        return len(hosts) > 1 and hosts[0] != hosts[-1]


def trace_redirects(
    url: str,
    *,
    resolver: Resolver = system_resolver,
    fetcher: Fetcher = pinned_fetch,
    timeout: float = 5.0,
    max_hops: int = MAX_HOPS,
) -> RedirectTrace:
    hops: list[Hop] = []
    seen: set[str] = set()
    current = url

    for _ in range(max_hops + 1):
        try:
            target = vet_url(current, resolver)
        except UnsafeTargetError as exc:
            hops.append(Hop(url=current, error=exc.code, error_detail=exc.detail))
            outcome = "blocked_unsafe_hop" if exc.code != "dns_resolution_failed" else "fetch_error"
            if exc.code == "scheme_not_allowed":
                outcome = "non_web_redirect"
            return RedirectTrace(url, hops, current, outcome, exc.code)

        if target.url in seen:
            hops.append(Hop(url=target.url, host=target.host, ips=target.ips, error="redirect_loop"))
            return RedirectTrace(url, hops, target.url, "redirect_loop")
        seen.add(target.url)

        res: FetchResult = fetcher(target, timeout)
        hop = Hop(
            url=target.url, host=target.host, ips=target.ips, status=res.status,
            headers=res.headers, set_cookie=res.set_cookie,
            error=res.error, error_detail=res.error_detail,
        )
        hops.append(hop)
        if res.error:
            return RedirectTrace(url, hops, target.url, "fetch_error")

        location = res.headers.get("location")
        if res.status in REDIRECT_CODES and location:
            hop.location = location
            # Relative redirects ("/login") are resolved against the current URL.
            current = urljoin(target.url, location.strip())
            continue
        return RedirectTrace(url, hops, target.url, "reached")

    return RedirectTrace(url, hops, current, "too_many_redirects")


def start_url_for(raw: str) -> str:
    """Normalised starting URL (raises URLNormalizeError for garbage)."""
    return normalize_url(raw).url
