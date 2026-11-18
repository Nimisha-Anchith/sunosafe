"""Tests for the SSRF guard. A fake resolver is used, so tests never touch real DNS."""
import socket

import pytest

from app.security.ssrf_guard import UnsafeTargetError, is_public_ip, vet_url

PUBLIC_IP = "93.184.215.14"  # a public internet address


def resolver_returning(*ips):
    def fake(host, port):
        return list(ips)
    return fake


def failing_resolver(host, port):
    raise socket.gaierror("Name or service not known")


def test_public_site_is_allowed_and_ips_are_pinned():
    t = vet_url("https://example.com/login", resolver_returning(PUBLIC_IP))
    assert (t.host, t.port, t.ips) == ("example.com", 443, (PUBLIC_IP,))


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",                   # loopback
        "http://169.254.169.254/latest/meta-data",  # cloud metadata service
        "http://10.0.0.5/",                         # private network
        "http://192.168.1.1/",                      # home router
        "http://100.64.1.1/",                       # carrier-grade NAT
        "http://[::1]/",                            # IPv6 loopback
        "http://[::ffff:127.0.0.1]/",               # IPv4 hidden inside IPv6
        "http://[64:ff9b::a00:1]/",                 # NAT64 form of 10.0.0.1
        "http://2130706433/",                       # 127.0.0.1 as one decimal number
        "http://0x7f.1/",                           # 127.0.0.1 in hex short form
    ],
)
def test_internal_addresses_are_blocked(url):
    with pytest.raises(UnsafeTargetError) as err:
        vet_url(url, resolver_returning(PUBLIC_IP))
    assert err.value.code == "private_address"


@pytest.mark.parametrize(
    "url", ["http://localhost:80/", "http://metadata.google.internal/", "http://printer.local/"]
)
def test_internal_hostnames_are_blocked_before_dns(url):
    with pytest.raises(UnsafeTargetError) as err:
        vet_url(url, resolver_returning(PUBLIC_IP))
    assert err.value.code == "blocked_hostname"


def test_dns_answer_pointing_inside_is_blocked():
    # Attacker-controlled domain whose DNS answers with an internal address.
    with pytest.raises(UnsafeTargetError) as err:
        vet_url("https://evil.example/", resolver_returning("10.1.2.3"))
    assert err.value.code == "private_address"


def test_one_bad_address_among_good_ones_blocks_everything():
    with pytest.raises(UnsafeTargetError) as err:
        vet_url("https://evil.example/", resolver_returning(PUBLIC_IP, "127.0.0.1"))
    assert err.value.code == "private_address"


@pytest.mark.parametrize(
    "url, code",
    [
        ("ftp://example.com/file", "scheme_not_allowed"),
        ("gopher://example.com/", "invalid_url"),      # unknown scheme: refuse to parse
        ("file:///etc/passwd", "scheme_not_allowed"),
        ("javascript:alert(1)", "scheme_not_allowed"),
        ("upi://pay?pa=x@ybl", "scheme_not_allowed"),
        ("http://example.com:22/", "port_not_allowed"),
        ("https://example.com:8443/", "port_not_allowed"),
    ],
)
def test_schemes_and_ports_are_restricted(url, code):
    with pytest.raises(UnsafeTargetError) as err:
        vet_url(url, resolver_returning(PUBLIC_IP))
    assert err.value.code == code


def test_credentials_are_stripped_not_sent():
    t = vet_url("http://user:secret@example.com/", resolver_returning(PUBLIC_IP))
    assert "secret" not in t.url and t.host == "example.com"


def test_unresolvable_domain_is_reported_honestly():
    with pytest.raises(UnsafeTargetError) as err:
        vet_url("https://does-not-exist.example/", failing_resolver)
    assert err.value.code == "dns_resolution_failed"


@pytest.mark.parametrize(
    "ip, public",
    [("8.8.8.8", True), ("2606:4700:4700::1111", True), ("0.0.0.0", False),
     ("224.0.0.1", False), ("192.0.2.10", False), ("fe80::1", False)],
)
def test_is_public_ip(ip, public):
    assert is_public_ip(ip) is public
