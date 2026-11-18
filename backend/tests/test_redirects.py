"""Redirect tracer tests with a fake resolver and fake fetcher (no network)."""
import httpcore
import pytest

from app.security.redirects import trace_redirects
from app.security.safe_fetch import FetchResult, _PinnedBackend

PUBLIC = "93.184.215.14"


def resolver(mapping):
    def fake(host, port):
        return [mapping.get(host, PUBLIC)]
    return fake


def fetcher(responses):
    """responses: url -> (status, location or None) or an error code string."""
    calls = []

    def fake(target, timeout):
        calls.append(target.url)
        r = responses[target.url]
        if isinstance(r, str):
            return FetchResult(error=r, error_detail="simulated")
        status, location = r
        return FetchResult(status=status, headers={"location": location} if location else {})
    fake.calls = calls
    return fake


def test_chain_is_followed_and_recorded():
    f = fetcher({
        "https://short.example/abc": (301, "https://tracker.example/t?id=1"),
        "https://tracker.example/t?id=1": (302, "/login"),          # relative redirect
        "https://tracker.example/login": (200, None),
    })
    t = trace_redirects("https://short.example/abc", resolver=resolver({}), fetcher=f)
    assert t.outcome == "reached"
    assert t.final_url == "https://tracker.example/login"
    assert [h.status for h in t.hops] == [301, 302, 200]
    assert t.changed_host


def test_redirect_into_internal_network_is_blocked_before_any_request():
    f = fetcher({"https://evil.example/": (302, "http://169.254.169.254/latest/meta-data")})
    t = trace_redirects("https://evil.example/", resolver=resolver({}), fetcher=f)
    assert t.outcome == "blocked_unsafe_hop" and t.blocked_code == "private_address"
    assert f.calls == ["https://evil.example/"]  # the metadata address was never contacted


def test_redirect_to_name_resolving_inside_is_blocked():
    f = fetcher({"https://evil.example/": (302, "https://intranet-trick.example/")})
    t = trace_redirects("https://evil.example/",
                        resolver=resolver({"intranet-trick.example": "10.0.0.7"}), fetcher=f)
    assert t.outcome == "blocked_unsafe_hop"


def test_redirect_to_app_link_is_reported():
    f = fetcher({"https://evil.example/": (302, "intent://scan/#Intent;scheme=upi;end")})
    t = trace_redirects("https://evil.example/", resolver=resolver({}), fetcher=f)
    assert t.outcome == "non_web_redirect"


def test_loop_is_detected():
    f = fetcher({"https://a.example/": (302, "https://b.example/"),
                 "https://b.example/": (302, "https://a.example/")})
    assert trace_redirects("https://a.example/", resolver=resolver({}), fetcher=f).outcome == "redirect_loop"


def test_too_many_redirects():
    responses = {f"https://h{i}.example/": (302, f"https://h{i + 1}.example/") for i in range(20)}
    t = trace_redirects("https://h0.example/", resolver=resolver({}), fetcher=fetcher(responses), max_hops=3)
    assert t.outcome == "too_many_redirects" and len(t.hops) == 4


def test_fetch_error_is_reported_not_hidden():
    t = trace_redirects("https://bad-cert.example/", resolver=resolver({}),
                        fetcher=fetcher({"https://bad-cert.example/": "tls_error"}))
    assert t.outcome == "fetch_error" and t.hops[-1].error == "tls_error"


def test_pinned_backend_refuses_any_other_host():
    backend = _PinnedBackend("example.com", ("93.184.215.14",))
    with pytest.raises(httpcore.ConnectError):
        backend.connect_tcp("internal.example", 443)
