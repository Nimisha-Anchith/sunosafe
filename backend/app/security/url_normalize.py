"""Turn messy or disguised links into one canonical form, plus a list of indicators.

Scam messages hide links in many ways: missing "https://", "defanged" dots like
sbi-kyc[.]co, look-alike Unicode letters, numeric IP addresses, or a fake brand
name placed before an "@". This module undoes those tricks so every later tool
(DNS, RDAP, TLS, reputation) looks at the *real* destination.

Pure functions only: nothing here touches the network.

Indicators are *observations*, not verdicts. "punycode_domain" means "this
domain uses non-English letters", not "this is a scam". Severity is decided
later by explicit rules that combine evidence from several tools.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


class URLNormalizeError(ValueError):
    """The input cannot be understood as a link at all."""


# Plain-language meaning of every indicator. Later milestones feed these to the
# explainer, so the voice can say *why* something looks wrong.
INDICATOR_TEXT: dict[str, str] = {
    "no_scheme": "The link had no http/https prefix; it was written so it looks less like a link.",
    "defanged": "The link was written in a 'defanged' form such as [.] instead of a dot.",
    "hidden_characters": "The link contains invisible characters, a trick to fool filters.",
    "userinfo_in_url": "Text before an '@' in the link is ignored by browsers; the real website is the part after the '@'.",
    "ip_address_host": "The link points to a raw number address instead of a named website.",
    "obfuscated_ip_host": "The link hides a number address in an unusual format.",
    "non_ascii_hostname": "The website name contains non-English letters that can look identical to English ones.",
    "punycode_domain": "The website name is internationalised (xn--); look-alike letters are possible.",
    "non_standard_port": "The link uses an unusual network port.",
    "http_not_https": "The link is not encrypted (http instead of https).",
    "url_shortener": "The link uses a URL shortener, which hides the real destination.",
    "many_subdomains": "The website name has many parts, often used to bury a fake brand name.",
    "many_hyphens": "The website name has many hyphens, common in fake look-alike domains.",
    "very_long_url": "The link is unusually long.",
    "non_web_scheme": "This is not a normal website link.",
    "upi_payment_link": "This is a UPI payment link: opening it can start a money transfer request.",
}

# Well-known shorteners. A shortener is not malicious by itself; it just means
# the redirect investigation (Milestone 2) must reveal the real destination.
URL_SHORTENERS = frozenset({
    "bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "is.gd", "rb.gy", "shorturl.at",
    "goo.gl", "ow.ly", "tiny.cc", "t.co", "rebrand.ly", "s.id", "v.gd",
})

# Schemes that are not web pages. We still report them (a upi:// link in an SMS
# is very relevant), but nothing downstream will ever fetch them.
NON_WEB_SCHEMES = frozenset({
    "javascript", "data", "file", "intent", "tel", "sms", "mailto", "upi",
    "ftp", "vbscript", "blob", "content", "market",
})

_DEFAULT_PORTS = {"http": 80, "https": 443}

_DEFANG_RULES = [
    (re.compile(r"^h(xx|XX|xX|Xx)p", re.ASCII), "http"),
    (re.compile(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]", re.IGNORECASE), "."),
    (re.compile(r"\[:\]"), ":"),
    (re.compile(r"\[/\]"), "/"),
]

# Zero-width and byte-order-mark characters: invisible, but they change the text.
_HIDDEN_CHARS = re.compile("[​‌‍⁠﻿­]")

# Punctuation that often sticks to the end of a link inside a sentence.
_TRAILING_PUNCT = ".,;:!?)]}>'\"’”"

_SCHEME_PREFIX = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

# Links inside free text: explicit scheme / www. / defanged scheme, or a bare
# domain such as "sbi-kyc.co/update". The look-behind avoids e-mail addresses.
_URL_WITH_PREFIX = re.compile(r"(?i)\b(?:h(?:tt|xx)ps?://|www\.|upi://)\S+")
_BARE_DOMAIN = re.compile(
    r"(?i)(?<![@\w.\-/])"
    r"[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?"
    r"(?:(?:\.|\[\.\])[a-z0-9\-]{1,63})*"
    r"(?:\.|\[\.\])[a-z]{2,24}\b"
    r"(?:/\S*)?"
)

_NUMERIC_HOST = re.compile(r"^(0x[0-9a-f]+|\d+)(\.(0x[0-9a-f]+|\d+)){0,3}$", re.IGNORECASE)


@dataclass
class NormalizedURL:
    original: str                 # exactly what the user/message contained
    url: str                      # canonical form used by every later tool
    scheme: str
    host: str                     # ASCII (punycode) host, lowercase; "" for non-web schemes
    host_display: str             # human-readable (Unicode) host for explanations
    port: int | None              # explicit non-default port, else None
    indicators: list[str] = field(default_factory=list)

    def explain(self) -> list[str]:
        return [INDICATOR_TEXT[i] for i in self.indicators]


def extract_urls(text: str) -> list[str]:
    """Find candidate links in a message, in order, without duplicates."""
    cleaned = _HIDDEN_CHARS.sub("", text)
    found: list[tuple[int, str]] = []
    taken: list[tuple[int, int]] = []
    for pattern in (_URL_WITH_PREFIX, _BARE_DOMAIN):
        for m in pattern.finditer(cleaned):
            start, end = m.span()
            if any(s <= start < e for s, e in taken):
                continue  # already covered by a longer, explicit match
            candidate = m.group(0).rstrip(_TRAILING_PUNCT)
            if candidate:
                found.append((start, candidate))
                taken.append((start, end))
    seen: set[str] = set()
    result = []
    for _, url in sorted(found):
        if url.lower() not in seen:
            seen.add(url.lower())
            result.append(url)
    return result


def _parse_numeric_ipv4(host: str) -> ipaddress.IPv4Address | None:
    """Decode classic 'inet_aton' forms: 3232235777, 0x7f.1, 0177.0.0.1 ...

    Browsers and OS resolvers accept these, so attackers use them to hide
    addresses such as 127.0.0.1 (localhost) from naive filters.
    """
    if not _NUMERIC_HOST.match(host):
        return None
    parts = []
    for p in host.split("."):
        if p.lower().startswith("0x"):
            parts.append(int(p, 16))
        elif len(p) > 1 and p.startswith("0"):
            parts.append(int(p, 8))
        else:
            parts.append(int(p))
    # Same layout rules as inet_aton: the last part fills the remaining bytes.
    widths = {1: [32], 2: [8, 24], 3: [8, 8, 16], 4: [8, 8, 8, 8]}[len(parts)]
    value = 0
    for part, bits in zip(parts, widths):
        if part >= 1 << bits:
            return None
        value = (value << bits) | part
    return ipaddress.IPv4Address(value)


def normalize_url(raw: str) -> NormalizedURL:
    """Canonicalise one link and record what was suspicious about how it was written."""
    if not isinstance(raw, str) or not raw.strip():
        raise URLNormalizeError("empty link")
    indicators: list[str] = []

    s = raw.strip()
    if _HIDDEN_CHARS.search(s):
        indicators.append("hidden_characters")
        s = _HIDDEN_CHARS.sub("", s)
    s = s.rstrip(_TRAILING_PUNCT)

    defanged = s
    for pattern, repl in _DEFANG_RULES:
        defanged = pattern.sub(repl, defanged)
    if defanged != s:
        indicators.append("defanged")
        s = defanged

    # Non-web schemes (upi:, javascript:, intent: ...) are reported, never fetched.
    m = _SCHEME_PREFIX.match(s)
    if m and m.group(1).lower() in NON_WEB_SCHEMES:
        scheme = m.group(1).lower()
        indicators.append("non_web_scheme")
        if scheme == "upi":
            indicators.append("upi_payment_link")
        return NormalizedURL(raw, s, scheme, "", "", None, indicators)

    if "://" not in s:
        indicators.append("no_scheme")
        s = "http://" + s.lstrip("/")

    try:
        parts = urlsplit(s)
        port = parts.port  # raises ValueError for junk like :99999
    except ValueError as exc:
        raise URLNormalizeError(f"malformed link: {exc}") from None

    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise URLNormalizeError(f"unsupported scheme: {scheme}")

    if parts.username is not None or parts.password is not None:
        indicators.append("userinfo_in_url")  # credentials are dropped below

    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise URLNormalizeError("link has no website name")

    # Raw IPs, including disguised numeric forms.
    host_display = host
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        ip = ipaddress.ip_address(host)
        indicators.append("ip_address_host")
    except ValueError:
        ip = _parse_numeric_ipv4(host)
        if ip is not None:
            indicators.append("obfuscated_ip_host")
    if ip is not None:
        host = host_display = str(ip)
    else:
        if not host.isascii():
            indicators.append("non_ascii_hostname")
        try:
            host = host.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise URLNormalizeError("website name is not valid") from None
        if any(label.startswith("xn--") for label in host.split(".")):
            indicators.append("punycode_domain")
            try:
                host_display = host.encode("ascii").decode("idna")
            except UnicodeError:
                host_display = host
        if host in URL_SHORTENERS:
            indicators.append("url_shortener")
        if host.count(".") >= 4:
            indicators.append("many_subdomains")
        if host.count("-") >= 3:
            indicators.append("many_hyphens")

    if port == _DEFAULT_PORTS[scheme]:
        port = None
    elif port is not None:
        indicators.append("non_standard_port")
    if scheme == "http":
        indicators.append("http_not_https")

    netloc = f"[{host}]" if ip is not None and ip.version == 6 else host
    if port is not None:
        netloc += f":{port}"
    # The #fragment is never sent to a server, so it is dropped.
    url = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    if len(url) > 200:
        indicators.append("very_long_url")

    return NormalizedURL(raw, url, scheme, host, host_display, port, indicators)
