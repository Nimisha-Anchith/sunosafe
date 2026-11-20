"""Explainable scam-pattern rules for SMS / WhatsApp text.

Each rule produces a *signal*: a named observation with the exact words that
triggered it, so the voice can say "the message asks you to share your OTP"
and the Guardian view can show the evidence.

Design choices:
  * Deterministic regex rules, not an AI guess. The LLM (Milestone 4) may
    rephrase, but it cannot invent or remove signals.
  * Negation-aware for the most common false alarm: real bank SMS say
    "Do NOT share your OTP with anyone" — that must not count as a request.
  * English and romanised Hindi directly; Hindi, Malayalam, Kannada and Tamil script through the
    reviewed word lists in indic.py.
  * Signals are evidence, not verdicts. severity.py combines them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.security.indic import gloss
from app.security.rdap import registrable_domain
from app.security.url_normalize import URLNormalizeError, extract_urls, normalize_url

# ---------------------------------------------------------------------------
# Brands commonly impersonated in India, with the official registrable
# domains we accept as genuine. Banks also use the RBI-mandated *.bank.in
# domains. Keep this list conservative and reviewed: a missing official
# domain would cause a false "not official" signal.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Brand:
    name: str
    pattern: str
    official: frozenset[str]


BRANDS: dict[str, Brand] = {
    "sbi": Brand("State Bank of India", r"\b(sbi|state bank)\b",
                 frozenset({"sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "sbicard.com", "yonosbi.com"})),
    "hdfc": Brand("HDFC Bank", r"\bhdfc\b", frozenset({"hdfcbank.com", "hdfc.bank.in", "hdfc.com"})),
    "icici": Brand("ICICI Bank", r"\bicici\b", frozenset({"icicibank.com", "icici.bank.in"})),
    "axis": Brand("Axis Bank", r"\baxis bank\b", frozenset({"axisbank.com", "axis.bank.in"})),
    "pnb": Brand("Punjab National Bank", r"\b(pnb|punjab national bank)\b", frozenset({"pnbindia.in", "pnb.bank.in"})),
    "kotak": Brand("Kotak Mahindra Bank", r"\bkotak\b", frozenset({"kotak.com", "kotak.bank.in"})),
    "paytm": Brand("Paytm", r"\bpaytm\b", frozenset({"paytm.com", "paytmbank.com"})),
    "phonepe": Brand("PhonePe", r"\bphone\s?pe\b", frozenset({"phonepe.com"})),
    "gpay": Brand("Google Pay", r"\b(gpay|google pay)\b", frozenset({"google.com"})),
    "amazon": Brand("Amazon", r"\bamazon\b", frozenset({"amazon.in", "amazon.com", "amzn.in", "amzn.to"})),
    "flipkart": Brand("Flipkart", r"\bflipkart\b", frozenset({"flipkart.com", "fkrt.it"})),
    "indiapost": Brand("India Post", r"\b(india\s?post|speed\s?post)\b", frozenset({"indiapost.gov.in"})),
    "incometax": Brand("Income Tax Department", r"\bincome\s?tax\b",
                       frozenset({"incometax.gov.in", "incometaxindia.gov.in"})),
    "rbi": Brand("Reserve Bank of India", r"\b(rbi|reserve bank)\b", frozenset({"rbi.org.in"})),
    "trai": Brand("TRAI", r"\btrai\b", frozenset({"trai.gov.in"})),
}

_NEGATION = r"(do\s*not|don'?t|dont|never|not\s+to|mat|nahi|nahin|na\s+karein|मत|ना)"
_SHARE = r"(share|send|tell|forward|provide|give|reply|bata|batao|bhejo|बताएं|भेजें|शेयर)"
_OTP = (r"(otp|one[\s-]?time[\s-]?password|verification\s+code|security\s+code|ओटीपी|"
        r"code\s+(sent|received|that\s+came)|(\d|four|six)[\s-]digit\s+(code|number))")
_PIN = r"(upi\s*pin|m-?pin|atm\s*pin|\bpin\b)"
_CRED = (r"(password|net\s?banking|login\s+details|cvv|card\s+(number|details)|"
         r"debit\s+card|credit\s+card|aadhaa?r|pan\s+card|bank\s+details)")
_ASK = r"(update|verify|share|enter|provide|submit|confirm|send|fill|type|link|tell|give|read\s+out)"

PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")


@dataclass
class Signal:
    code: str
    category: str      # credential_request | payment_trick | pressure | authority | impersonation | lure | contact | link
    detail: str        # plain language, safe to speak
    match: str = ""    # the words that triggered it (evidence)


@dataclass
class MessageAnalysis:
    signals: list[Signal] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)          # every link found, normalised
    web_urls: list[str] = field(default_factory=list)      # http/https links to investigate
    brands: list[str] = field(default_factory=list)        # brand keys the message claims
    phone_numbers: list[str] = field(default_factory=list)

    def codes(self) -> set[str]:
        return {s.code for s in self.signals}


def _search(pattern: str, text: str) -> re.Match | None:
    return re.search(pattern, text, re.IGNORECASE)


# A negation only cancels a request when it directly governs the verb:
# "do not share", "never ask you to share" (up to 4 plain words in between)
# but NOT "Don't delay, share the OTP" — the comma ends the negated phrase.
_GOVERNING_NEGATION = re.compile(rf"{_NEGATION}(\s+[\w']+){{0,4}}\s*$", re.IGNORECASE)


def _verb_is_negated(text: str, verb_start: int) -> bool:
    return bool(_GOVERNING_NEGATION.search(text[max(0, verb_start - 45):verb_start]))


def _non_negated_request(text: str, obj: str, verb: str = _SHARE, window: int = 40) -> re.Match | None:
    """Find 'verb ... obj' or 'obj ... verb' (within `window` chars) whose verb is NOT negated."""
    pattern = rf"({verb}.{{0,{window}}}?{obj}|{obj}.{{0,{window}}}?{verb})"
    for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        for v in re.finditer(verb, m.group(0), re.IGNORECASE):
            if not _verb_is_negated(text, m.start() + v.start()):
                return m
    return None


def analyze_message(text: str) -> MessageAnalysis:
    a = MessageAnalysis()
    t = text or ""
    add = a.signals.append

    # --- links -------------------------------------------------------------
    for raw in extract_urls(t):
        try:
            n = normalize_url(raw)
        except URLNormalizeError:
            continue
        a.urls.append(n.url)
        if n.scheme in ("http", "https"):
            a.web_urls.append(n.url)
        if "upi_payment_link" in n.indicators:
            add(Signal("contains_upi_payment_link", "payment_trick",
                       "The message contains a UPI payment link; opening it can start a payment request.", raw))

    # Hindi, Malayalam, Kannada and Tamil script: swap the scam vocabulary for the English words the
    # rules below understand (see indic.py). Links were taken from the original text above.
    t = gloss(t)

    # --- secrets the sender wants -------------------------------------------
    if m := _non_negated_request(t, _OTP):
        add(Signal("requests_otp", "credential_request",
                   "The message asks you to share an OTP. Banks and companies never ask for your OTP.", m.group(0)))
    if (m := _search(rf"{_PIN}.{{0,60}}(receive|refund|cashback|credited|get\s+money|claim)|"
                     rf"(receive|refund|cashback|credited|get\s+money|claim).{{0,60}}{_PIN}", t)):
        add(Signal("pin_to_receive_money", "payment_trick",
                   "It says you must enter a PIN to receive money. You never need a PIN to receive money.",
                   m.group(0)))
    elif m := _non_negated_request(t, _PIN, rf"({_SHARE}|enter|type)"):
        add(Signal("requests_upi_pin", "credential_request",
                   "The message asks for your PIN. Never share or enter your PIN because someone asked.", m.group(0)))
    if m := _non_negated_request(t, _CRED, _ASK):
        add(Signal("requests_credentials", "credential_request",
                   "The message asks you to share or update bank, card, password or ID details.", m.group(0)))

    # --- risky apps -----------------------------------------------------------
    if m := _search(r"\b(anydesk|any\s+desk|teamviewer|team\s+viewer|quick\s?support|rustdesk|airdroid|screen\s?share)\b", t):
        add(Signal("asks_remote_access", "credential_request",
                   "It mentions a screen-sharing or remote-control app. Scammers use these to control your phone.",
                   m.group(0)))
    if m := _search(r"(\.apk\b|install\s+(this|the|our)\s+app|download\s+(this|the|our)\s+app)", t):
        add(Signal("asks_to_install_app", "credential_request",
                   "It asks you to install an app from a link. Apps from links can steal your messages and money.",
                   m.group(0)))

    # --- pressure, authority, lures -----------------------------------------
    if m := _search(r"\b(urgent|urgently|immediately|today|tonight|within\s+\d+\s*(hours?|hrs?|minutes?|mins?)|"
                    r"last\s+(chance|warning|reminder)|act\s+now|right\s+now|turant|abhi|aaj\s+hi)\b|तुरंत|आज ही", t):
        add(Signal("urgency", "pressure", "It pressures you to act quickly. Real organisations give you time.",
                   m.group(0)))
    # Needs an object (account, card, SIM ...) so "OTP expires in 10 min" is not a threat.
    obj = r"(account|a/c|card|sim|kyc|service|connection|number|wallet|upi|pan|aadhaa?r|khata)"
    threat = (r"(block(ed)?|suspend(ed)?|deactivat(ed|e)|frozen|freeze|closed|disconnect(ed)?|"
              r"expired?|expiring|band\s+ho\s+jayega|बंद|ब्लॉक)")
    if m := _search(rf"\b{obj}\b.{{0,40}}{threat}|{threat}.{{0,40}}\b{obj}\b", t):
        add(Signal("account_threat", "pressure",
                   "It threatens that your account, card, SIM or service will be stopped.", m.group(0)))
    if m := _search(r"\b(police|cbi|customs|narcotics|enforcement\s+directorate|cyber\s+cell|court|arrest(ed)?|"
                    r"fir|digital\s+arrest|warrant)\b|पुलिस|गिरफ्तार", t):
        add(Signal("authority_threat", "authority",
                   "It uses police, court or government threats. Officials never arrest or fine people over phone or chat.",
                   m.group(0)))
    if m := _search(r"\bkyc\b.{0,40}(update|expire|expired|pending|complete|verify|suspend)|"
                    r"(update|complete|verify).{0,40}\bkyc\b", t):
        add(Signal("kyc_update_request", "pressure",
                   "It asks you to update KYC through a message. Banks do KYC at the branch or in their official app.",
                   m.group(0)))
    if m := _search(r"\b(won|winner|lottery|prize|lucky\s+draw|kbc|gift|reward|cashback|refund|"
                    r"work\s+from\s+home|part[\s-]?time\s+job|daily\s+income|double\s+your\s+money|"
                    r"guaranteed\s+returns?)\b", t):
        add(Signal("too_good_to_be_true", "lure",
                   "It offers money, a prize, a refund or an easy job. Unexpected offers like this are common scams.",
                   m.group(0)))
    if m := _search(r"\b(electricity|bijli|power)\b.{0,60}\b(disconnect\w*|cut|band)\b", t):
        add(Signal("electricity_disconnection", "pressure",
                   "It threatens to cut your electricity. Electricity boards send official notices, not urgent SMS with numbers.",
                   m.group(0)))

    # A demand to move money. On its own this is weak (bills are normal); with police or court
    # threats it is the "digital arrest" scam (see severity R13).
    money = r"(money|rupees|\brs\.?|₹|amount|\bfine\b|penalty|\bfee\b|charges)"
    if m := _non_negated_request(t, money, r"(transfer|deposit|\bpay\b|send)", window=30):
        add(Signal("asks_for_payment", "payment_trick",
                   "It asks you to send or transfer money.", m.group(0)))

    # --- contact numbers -------------------------------------------------------
    a.phone_numbers = list(dict.fromkeys(re.sub(r"[\s-]", "", m.group(1)) for m in PHONE_RE.finditer(t)))
    if a.phone_numbers and _search(r"\b(call|contact|whatsapp|dial|ring|phone)\b", t):
        add(Signal("asks_to_call_number", "contact",
                   "It asks you to call or message a number given in the message. Use only numbers from the official website or your card.",
                   a.phone_numbers[0]))

    # --- impersonation: brand named, but the link is not theirs --------------
    for key, brand in BRANDS.items():
        if _search(brand.pattern, t):
            a.brands.append(key)
    for key in a.brands:
        official = BRANDS[key].official
        for url in a.web_urls:
            domain = registrable_domain(normalize_url(url).host)
            if domain and domain not in official:
                add(Signal("link_not_official_for_brand", "impersonation",
                           f"The message claims to be from {BRANDS[key].name}, but the link goes to {domain}, "
                           f"which is not one of their official websites.",
                           f"{BRANDS[key].name} -> {domain}"))
                break
    return a
