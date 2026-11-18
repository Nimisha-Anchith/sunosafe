"""Reputation check with Google Safe Browsing (Lookup API v4, threatMatches:find).

Google maintains lists of web addresses known to host phishing ("social
engineering"), malware and unwanted software. We ask whether ANY link in the
redirect chain is on those lists.

Honesty rules:
  * A match is strong evidence: Google has confirmed the address as dangerous.
  * "no_match" does NOT mean safe. New scam sites appear faster than any list,
    which is why SunoSafe also checks domain age, certificates and redirects.
  * With no API key the status is "not_configured" — we never invent a result.

Privacy: the URLs are sent to Google. Demos use synthetic links only, and the
Safe Browsing APIs are for non-commercial use (Web Risk is the commercial one).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

SAFE_BROWSING_ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
THREAT_TYPES = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"]
MAX_URLS = 50  # Lookup API limit is 500 per request; a redirect chain is far smaller


@dataclass
class ThreatMatch:
    url: str
    threat_type: str
    platform: str


@dataclass
class ReputationReport:
    provider: str
    status: str                      # "flagged" | "no_match" | "not_configured" | "error"
    matches: list[ThreatMatch] = field(default_factory=list)
    checked_urls: list[str] = field(default_factory=list)
    detail: str | None = None


def check_safe_browsing(urls: list[str], api_key: str | None,
                        client: httpx.Client | None = None, timeout: float = 5.0) -> ReputationReport:
    """Look up every URL in one request. Never raises; never logs the key."""
    unique = list(dict.fromkeys(u for u in urls if u))[:MAX_URLS]
    report = ReputationReport(provider="google_safe_browsing", status="no_match", checked_urls=unique)
    if not api_key:
        report.status = "not_configured"
        report.detail = "SAFE_BROWSING_API_KEY is not set; reputation was not checked."
        return report
    if not unique:
        report.detail = "No web links to check."
        return report

    body = {
        "client": {"clientId": "sunosafe", "clientVersion": "0.2"},
        "threatInfo": {
            "threatTypes": THREAT_TYPES,
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in unique],
        },
    }
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        # Key goes in the x-goog-api-key header, so it never appears in URLs or logs.
        r = client.post(SAFE_BROWSING_ENDPOINT, json=body, headers={"x-goog-api-key": api_key})
        if r.status_code != 200:
            report.status = "error"
            report.detail = f"Safe Browsing returned HTTP {r.status_code}"
            return report
        data = r.json()
        for m in data.get("matches", []):
            report.matches.append(ThreatMatch(
                url=m.get("threat", {}).get("url", ""),
                threat_type=m.get("threatType", "UNKNOWN"),
                platform=m.get("platformType", "ANY_PLATFORM"),
            ))
        if report.matches:
            report.status = "flagged"
    except (httpx.HTTPError, ValueError) as exc:
        report.status = "error"
        report.detail = f"{type(exc).__name__}"
    finally:
        if own_client:
            client.close()
    return report
