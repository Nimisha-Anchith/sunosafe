"""Scam-message rules, redaction and severity. All messages are synthetic."""
import pytest

from app.security.message_rules import analyze_message
from app.soc.redact import redact
from app.soc.severity import assess

FAKE_KYC = ("Dear SBI customer, your account will be BLOCKED today. Update KYC now at "
            "hxxps://sbi-kyc-update[.]in/verify and share the OTP sent to you. Call 9876543210.")
LEGIT_OTP = "OTP for your SBI transaction of Rs 500 is 482913. Valid for 10 mins. Do not share this OTP with anyone. -SBI"
PIN_REFUND = "Congratulations! Refund of Rs 4999 approved. Enter UPI PIN to receive money: upi://pay?pa=refund@ybl"
DIGITAL_ARREST = ("This is CBI cyber cell. A parcel in your name has drugs. You are under digital arrest. "
                  "Install AnyDesk and stay on video call.")
LEGIT_AMAZON = "Your Amazon order has shipped. Track at https://www.amazon.in/gp/your-orders"


def codes(text):
    return analyze_message(text).codes()


def test_fake_kyc_message():
    a = analyze_message(FAKE_KYC)
    assert {"requests_otp", "urgency", "account_threat", "kyc_update_request",
            "asks_to_call_number", "link_not_official_for_brand"} <= a.codes()
    assert a.brands == ["sbi"] and a.web_urls == ["https://sbi-kyc-update.in/verify"]
    assert a.phone_numbers == ["9876543210"]


@pytest.mark.parametrize("text", [
    LEGIT_OTP,
    "Never share your OTP, PIN or password with anyone. SBI never asks for these.",
    "Your OTP expires in 10 minutes.",
])
def test_genuine_safety_messages_are_not_flagged_as_requests(text):
    assert not codes(text) & {"requests_otp", "requests_upi_pin", "requests_credentials", "account_threat"}


@pytest.mark.parametrize("text", [
    "Don't delay, share the OTP now to avoid blocking",   # negation belongs to "delay", not "share"
    "Do not wait. Send OTP immediately.",
    "Never ignore this: share your OTP with our agent",
    "Share the OTP received on your phone",
])
def test_scammer_wording_cannot_hide_behind_a_nearby_negation(text):
    assert "requests_otp" in codes(text)


@pytest.mark.parametrize("text", [
    "SBI never asks you to share your OTP, PIN or password.",
    "We will never ask you to share OTP",
    "kripya OTP kisi ko mat batao",
])
def test_negation_that_governs_the_verb_is_respected(text):
    assert "requests_otp" not in codes(text)


def test_pin_to_receive_money_trick():
    assert {"pin_to_receive_money", "contains_upi_payment_link"} <= codes(PIN_REFUND)


def test_digital_arrest_and_remote_access():
    assert {"authority_threat", "asks_remote_access"} <= codes(DIGITAL_ARREST)


def test_official_brand_link_is_not_flagged():
    assert "link_not_official_for_brand" not in codes(LEGIT_AMAZON)


def test_bank_in_domain_counts_as_official():
    assert "link_not_official_for_brand" not in codes("SBI: view your statement at https://sbi.bank.in/statement")


def test_apk_install_request():
    assert "asks_to_install_app" in codes("Download the SBI Rewards app: http://rewards-sbi.example/sbi.apk")


def test_hindi_words():
    assert {"urgency", "authority_threat"} <= codes("पुलिस आपके घर आएगी, तुरंत कॉल करें")


# ---------- redaction ----------
def test_redaction_masks_personal_numbers():
    out = redact("card 4111 1111 1111 1234, aadhaar 2345 6789 0123, PAN ABCDE1234F, OTP is 482913, call 9876543210")
    assert "4111 1111 1111 1234" not in out and out.count("1234") == 1
    assert "2345 6789" not in out and "ABCDE1234F" not in out
    assert "482913" not in out and "9876543210" not in out and "98XXXXX210" in out


# ---------- severity ----------
def test_legit_message_has_no_known_issues_and_says_so():
    v = assess(codes(LEGIT_OTP))
    assert v.level == "info" and v.label == "no_known_issues"
    assert any("cannot" in u or "may not" in u for u in v.uncertainties)
    assert "safe" not in v.label


def test_fake_kyc_is_high_with_reasons():
    v = assess(codes(FAKE_KYC))
    assert v.level == "high" and v.label == "danger"
    assert "R5_brand_impersonation_with_pressure" in {r.rule for r in v.reasons}


def test_reputation_match_is_confirmed():
    v = assess({"known_dangerous_site"})
    assert (v.level, v.confidence) == ("high", "confirmed")


def test_unknown_call_plus_unknown_message_is_not_critical():
    v = assess({"urgency", "asks_to_call_number"})
    assert v.level == "low"


def test_disclosure_with_evidence_is_critical():
    v = assess({"requests_otp"}, {"otp"})
    assert v.level == "critical"


def test_disclosure_without_evidence_is_high_not_critical():
    assert assess(set(), {"password"}).level == "high"


def test_tool_problems_are_reported_as_uncertainty():
    v = assess({"url_shortener"}, tool_problems=["The rdap check failed, so its evidence is missing."])
    assert "The rdap check failed, so its evidence is missing." in v.uncertainties
