"""Классификация DNS-ответов и TCP-помощники."""
from __future__ import annotations

from src.core.diagnostics.dns_check import DNSCheck, classify_resolution, google_resolve
from src.utils.network import is_suspicious_ip, tcp_connect


def test_suspicious_ip_categories() -> None:
    for address in ("127.0.0.1", "0.0.0.0", "::1", "10.0.0.5", "192.168.1.1",
                    "169.254.10.1", "100.64.1.1", "224.0.0.1", "not-an-ip"):
        assert is_suspicious_ip(address), address
    for address in ("151.101.66.167", "8.8.8.8", "1.1.1.1", "2606:4700::1111"):
        assert not is_suspicious_ip(address), address


def test_classify_resolution_matrix() -> None:
    assert classify_resolution(["127.0.0.1"], ["1.2.3.4"]) == "suspicious"
    assert classify_resolution([], ["1.2.3.4"]) == "failed"
    assert classify_resolution([], []) == "unknown"
    assert classify_resolution(["1.2.3.4"], ["1.2.3.4"]) == "ok"
    assert classify_resolution(["1.2.3.4"], ["5.6.7.8"]) == "mismatch"


def test_google_resolve_returns_list_on_failure(monkeypatch) -> None:
    import dns.resolver  # noqa: PLC0415

    class Broken:
        def __init__(self, *args, **kwargs):
            raise OSError("no network")

    monkeypatch.setattr(dns.resolver, "Resolver", Broken)
    assert google_resolve("example.invalid") == []


def test_tcp_connect_failure_is_graceful() -> None:
    answer = tcp_connect("127.0.0.1", 1, timeout=0.2)
    assert answer.ok is False
    assert answer.error
    assert answer.latency_ms >= 0


def test_dns_check_has_expected_metadata() -> None:
    check = DNSCheck()
    assert check.id == "dns"
    assert check.fix_id == "dns"
