"""Evidence-based severity: combine signals and findings into an explainable verdict.

Rules, not percentages. Each rule that fires is recorded with the evidence
codes behind it, so every verdict can answer "why?". The level only rises
with stronger evidence:

  info      no known issues found (NOT "safe" — we say what we could not check)
  low       weak signs only (shortener, urgency words, plain http ...)
  medium    a serious sign: secret requested, invalid certificate, brand link mismatch ...
  high      confirmed by a reputation list, OR a secret request combined with a bad link
  critical  the user reports they already gave away secrets or money AND there is evidence

Uncertainty is reported explicitly: failed or unconfigured tools are listed,
and an "info" verdict always reminds that new scam sites may not be known yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field

LEVELS = ["info", "low", "medium", "high", "critical"]

SECRET_REQUESTS = {"requests_otp", "requests_upi_pin", "requests_credentials", "pin_to_receive_money",
                   "asks_remote_access", "asks_to_install_app"}
PRESSURE = {"urgency", "account_threat", "authority_threat", "kyc_update_request", "too_good_to_be_true",
            "electricity_disconnection", "asks_to_call_number", "asks_for_payment"}
CONFIRMED = {"known_dangerous_site"}
# Evidence that links a phone call to an earlier scam message (cross-channel).
CROSS_CHANNEL = {"known_scam_number", "same_scam_story_by_call"}
STRONG_LINK = {"domain_recently_registered", "link_to_internal_address", "redirect_to_internal_address",
               "punycode_domain", "userinfo_in_url", "obfuscated_ip_host", "redirect_to_app_or_payment_link",
               "contains_upi_payment_link", "link_not_official_for_brand"}
STRONG_LINK_PREFIX = ("tls_",)  # tls_expired, tls_hostname_mismatch, tls_self_signed ...
WEAK = {"url_shortener", "http_not_https", "many_hyphens", "many_subdomains", "domain_young",
        "certificate_very_new", "redirect_chain", "destination_differs", "ip_address_host",
        "non_standard_port", "very_long_url", "hidden_characters", "final_page_not_encrypted",
        "too_many_redirects", "redirect_loop", "refresh_header_redirect", "domain_not_registered",
        "domain_does_not_exist"}
DISCLOSURES = {"otp", "upi_pin", "password", "card_details", "bank_details", "aadhaar", "money_paid",
               "remote_app_installed"}


@dataclass
class Reason:
    rule: str
    level: str
    text: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    level: str
    label: str            # "danger" | "caution" | "no_known_issues"  (never "safe")
    confidence: str       # "confirmed" | "likely" | "possible" | "none"
    reasons: list[Reason] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    summary: str = ""


def _is_strong_link(code: str) -> bool:
    return code in STRONG_LINK or code.startswith(STRONG_LINK_PREFIX)


def assess(codes: set[str], disclosures: set[str] | None = None,
           tool_problems: list[str] | None = None) -> Verdict:
    """codes: every signal/finding code observed. disclosures: what the user says they gave away."""
    disclosures = (disclosures or set()) & DISCLOSURES
    reasons: list[Reason] = []
    secrets = sorted(codes & SECRET_REQUESTS)
    pressure = sorted(codes & PRESSURE)
    strong = sorted(c for c in codes if _is_strong_link(c))
    confirmed = sorted(codes & CONFIRMED)
    weak = sorted(codes & WEAK)

    def fire(rule, level, text, evidence):
        reasons.append(Reason(rule, level, text, list(evidence)))

    if confirmed:
        fire("R1_confirmed_by_reputation", "high",
             "A link is on Google Safe Browsing's list of dangerous sites.", confirmed)
    if disclosures and (confirmed or secrets or strong):
        fire("R2_user_disclosed_after_scam", "critical",
             "You may have shared " + ", ".join(sorted(d.replace("_", " ") for d in disclosures))
             + " with a source that shows scam evidence. Act quickly.", sorted(disclosures) + confirmed + secrets + strong)
    elif disclosures:
        fire("R2b_user_disclosed", "high",
             "You may have shared sensitive details. Even without other evidence, protect your accounts now.",
             sorted(disclosures))
    if secrets and strong:
        fire("R3_secret_request_with_bad_link", "high",
             "The message asks for secret details AND its link shows warning signs.", secrets + strong)
    if "pin_to_receive_money" in codes or ("asks_remote_access" in codes and pressure):
        fire("R4_classic_payment_or_remote_trick", "high",
             "This matches a well-known scam pattern (PIN to receive money, or remote-control app under pressure).",
             sorted(codes & {"pin_to_receive_money", "asks_remote_access"}) + pressure)
    if "link_not_official_for_brand" in codes and (pressure or secrets):
        fire("R5_brand_impersonation_with_pressure", "high",
             "It claims to be a known company, uses a link that is not theirs, and pressures you.",
             ["link_not_official_for_brand"] + pressure + secrets)
    if secrets:
        fire("R6_secret_requested", "medium",
             "It asks for an OTP, PIN, password or remote access. Genuine organisations never do this.", secrets)
    if strong:
        fire("R7_strong_link_warning", "medium", "The link shows serious warning signs.", strong)
    if "known_scam_number" in codes:
        fire("R10_caller_from_scam_message", "high",
             "This caller's number appeared in a scam message you received earlier.", ["known_scam_number"])
    if "same_scam_story_by_call" in codes:
        fire("R11_same_scam_by_message_and_call", "high",
             "The same scam reached you by message and by a phone call, a common two-step trick.",
             ["same_scam_story_by_call"])
    if "electricity_disconnection" in codes and "asks_to_call_number" in codes:
        fire("R16_electricity_bill_scam", "high",
             "It threatens to cut your electricity and asks you to call a number: the electricity bill scam. "
             "Electricity boards never ask you to call a private number; check your bill in the official app.",
             ["electricity_disconnection", "asks_to_call_number"])
    if "authority_threat" in codes and "asks_for_payment" in codes:
        fire("R13_authority_demands_payment", "high",
             "It uses police, court or government threats and demands money, the 'digital arrest' scam. "
             "No official collects money over a phone call or chat.", ["authority_threat", "asks_for_payment"])
    if "too_good_to_be_true" in codes and "asks_for_payment" in codes:
        live = "live_caller" in codes
        fire("R14_pay_to_receive_a_prize", "high" if live else "medium",
             "It promises a prize, refund or job and asks you to pay first. Genuine prizes never need a fee.",
             ["too_good_to_be_true", "asks_for_payment"] + (["live_caller"] if live else []))
    elif "live_caller" in codes and "asks_for_payment" in codes:
        fire("R15_caller_asked_for_money", "medium",
             "A caller asked you to send money. Check first by calling the person or office on a number you already know.",
             ["live_caller", "asks_for_payment"])
    if "live_caller" in codes and secrets:
        fire("R12_caller_asked_for_secret", "high",
             "A caller asked for an OTP, PIN, password or remote access on a live call, the most common phone scam.",
             ["live_caller"] + secrets)
    if len(pressure) >= 2:
        fire("R8_multiple_pressure_tactics", "low", "It uses several pressure tactics.", pressure)
    elif pressure or weak:
        fire("R9_weak_signs", "low", "There are minor warning signs.", pressure + weak)

    level = max((r.level for r in reasons), key=LEVELS.index, default="info")
    if confirmed or disclosures:
        confidence = "confirmed" if confirmed else "likely"
    elif level in ("high", "critical"):
        confidence = "likely"
    elif level in ("medium", "low"):
        confidence = "possible"
    else:
        confidence = "none"
    label = "danger" if level in ("high", "critical") else "caution" if level in ("medium", "low") else "no_known_issues"

    uncertainties = list(tool_problems or [])
    if level == "info":
        uncertainties.append("No known problems were found, but brand-new scam sites may not be detected yet.")

    verdict = Verdict(level, label, confidence, reasons, uncertainties)
    verdict.summary = spoken_summary(verdict)
    return verdict


def spoken_summary(v: Verdict) -> str:
    """One calm, plain sentence for voice. The LLM may rephrase it but not change its meaning."""
    top = max(v.reasons, key=lambda r: LEVELS.index(r.level)).text if v.reasons else ""
    if v.level == "critical":
        return f"This is serious. {top}"
    if v.level == "high":
        return f"This looks dangerous. {top} Please do not open it or reply."
    if v.level == "medium":
        return f"Please be careful. {top}"
    if v.level == "low":
        return f"I found a few minor warning signs. {top}"
    return "I did not find known problems, but I cannot promise it is safe. Only continue if you were expecting it."
