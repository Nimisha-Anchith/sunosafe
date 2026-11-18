"""Safe Browsing tests with httpx.MockTransport (no network, no real key)."""
import json

import httpx

from app.security.reputation import SAFE_BROWSING_ENDPOINT, check_safe_browsing


def client_returning(status, body, seen=None):
    def handler(request: httpx.Request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_not_configured_without_key_and_nothing_is_sent():
    seen = []
    rep = check_safe_browsing(["https://a.example/"], None, client_returning(200, {}, seen))
    assert rep.status == "not_configured" and seen == []


def test_no_match_is_not_called_safe():
    rep = check_safe_browsing(["https://a.example/"], "test-key", client_returning(200, {}))
    assert rep.status == "no_match"


def test_flagged_match_is_reported_with_threat_type():
    body = {"matches": [{"threatType": "SOCIAL_ENGINEERING", "platformType": "ANY_PLATFORM",
                         "threat": {"url": "https://fake-bank.example/"}}]}
    rep = check_safe_browsing(["https://fake-bank.example/"], "test-key", client_returning(200, body))
    assert rep.status == "flagged"
    assert rep.matches[0].threat_type == "SOCIAL_ENGINEERING"


def test_request_shape_and_key_stays_out_of_url():
    seen = []
    check_safe_browsing(["https://a.example/", "https://a.example/", "https://b.example/"],
                        "test-key", client_returning(200, {}, seen))
    req = seen[0]
    assert str(req.url) == SAFE_BROWSING_ENDPOINT          # no ?key= in the URL
    assert req.headers["x-goog-api-key"] == "test-key"
    entries = json.loads(req.content)["threatInfo"]["threatEntries"]
    assert entries == [{"url": "https://a.example/"}, {"url": "https://b.example/"}]  # de-duplicated


def test_api_error_is_reported():
    assert check_safe_browsing(["https://a.example/"], "k", client_returning(403, {})).status == "error"
