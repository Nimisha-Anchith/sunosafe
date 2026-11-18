"""Tests for the URL normaliser. All examples are synthetic; no network is used."""
import pytest

from app.security.url_normalize import URLNormalizeError, extract_urls, normalize_url


def test_defanged_link_is_restored():
    n = normalize_url("hxxps://sbi-kyc[.]co/login")
    assert n.url == "https://sbi-kyc.co/login"
    assert "defanged" in n.indicators


def test_missing_scheme_is_added_and_flagged():
    n = normalize_url("sbi-kyc.co/update")
    assert n.url == "http://sbi-kyc.co/update"
    assert {"no_scheme", "http_not_https"} <= set(n.indicators)


def test_case_and_default_port_are_canonicalised_but_path_case_kept():
    n = normalize_url("HTTPS://WWW.Example.COM:443/Account?id=7#top")
    assert n.url == "https://www.example.com/Account?id=7"  # fragment dropped
    assert n.port is None


def test_brand_before_at_sign_is_not_the_real_host():
    n = normalize_url("http://www.onlinesbi.sbi@login-verify.example/kyc")
    assert n.host == "login-verify.example"
    assert "userinfo_in_url" in n.indicators
    assert "@" not in n.url  # credentials never kept


@pytest.mark.parametrize(
    "raw, expected_ip",
    [
        ("http://3232235777/", "192.168.1.1"),   # one big decimal number
        ("http://0x7f.1/", "127.0.0.1"),          # hex + short form
        ("http://0177.0.0.1/", "127.0.0.1"),      # octal
    ],
)
def test_disguised_ip_addresses_are_decoded(raw, expected_ip):
    n = normalize_url(raw)
    assert n.host == expected_ip
    assert "obfuscated_ip_host" in n.indicators


def test_lookalike_unicode_letters_become_punycode():
    n = normalize_url("https://аpple.com/")  # Cyrillic 'а', not Latin 'a'
    assert n.host.startswith("xn--")
    assert {"non_ascii_hostname", "punycode_domain"} <= set(n.indicators)
    assert n.host_display == "аpple.com"


def test_shortener_is_flagged():
    assert "url_shortener" in normalize_url("bit.ly/3xYz").indicators


def test_upi_payment_link_is_reported_not_parsed_as_website():
    n = normalize_url("upi://pay?pa=refund-desk@ybl&am=4999")
    assert n.scheme == "upi" and n.host == ""
    assert {"non_web_scheme", "upi_payment_link"} <= set(n.indicators)


def test_invisible_characters_are_removed_and_flagged():
    n = normalize_url("https://exa​mple.com/")
    assert n.host == "example.com"
    assert "hidden_characters" in n.indicators


def test_ipv6_literal_keeps_brackets():
    n = normalize_url("http://[2606:4700:4700::1111]:8080/x")
    assert n.url == "http://[2606:4700:4700::1111]:8080/x"
    assert "non_standard_port" in n.indicators


@pytest.mark.parametrize("bad", ["", "   ", "http://", "http://example.com:99999/"])
def test_garbage_is_rejected(bad):
    with pytest.raises(URLNormalizeError):
        normalize_url(bad)


def test_every_indicator_has_a_plain_language_explanation():
    n = normalize_url("hxxp://www.sbi.co.in@3232235777:8080/kyc")
    assert len(n.explain()) == len(n.indicators) > 0


def test_extract_urls_from_a_scam_sms():
    sms = (
        "Dear Customer, your SBI KYC expires TODAY. Update now at "
        "hxxps://sbi-kyc[.]co/upd or your account will be blocked. "
        "Pay fee: upi://pay?pa=kyc-desk@ybl&am=10. Help: www.example.com."
    )
    assert extract_urls(sms) == [
        "hxxps://sbi-kyc[.]co/upd",
        "upi://pay?pa=kyc-desk@ybl&am=10",
        "www.example.com",
    ]


def test_extract_urls_ignores_email_addresses_and_amounts():
    assert extract_urls("Mail support@bank.example or pay Rs.500 now") == []
