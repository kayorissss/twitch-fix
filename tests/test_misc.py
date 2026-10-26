"""Дополнительные тесты чистых функций диагностики и утилит."""
from __future__ import annotations

from pathlib import Path

from src.core.diagnostics.firewall_check import parse_blocking_rules
from src.core.diagnostics.http_check import looks_like_block_page
from src.core.diagnostics.ping_check import parse_traceroute
from src.core.diagnostics.proxy_check import mask_url
from src.core.diagnostics.ssl_check import detect_av_issuer, issuer_name
from src.utils.admin import is_admin
from src.utils.backup import BackupManager


def test_av_issuer_detection() -> None:
    assert detect_av_issuer("Kaspersky Lab Root CA") == "Kaspersky"
    assert detect_av_issuer("ESET SSL Filter CA") == "ESET"
    assert detect_av_issuer("DigiCert Global Root CA") is None


def test_issuer_name_extracts_organization() -> None:
    cert = {"issuer": ((("organizationName", "DigiCert Inc"),), (("commonName", "Root CA"),))}
    assert issuer_name(cert) == "DigiCert Inc"
    assert issuer_name({}) == "unknown"


def test_block_page_markers() -> None:
    assert looks_like_block_page("Доступ к сайту ограничен", 200) is not None
    assert looks_like_block_page("Access denied by your ISP", 403) is not None
    assert looks_like_block_page("<html>twitch streams</html>" * 1000, 200) is None


def test_mask_url_hides_credentials() -> None:
    masked = mask_url("http://user:secret@proxy.local:8080")
    assert "secret" not in masked
    assert "proxy.local:8080" in masked
    assert mask_url("127.0.0.1:8888").endswith("127.0.0.1:8888")


def test_parse_traceroute_hops() -> None:
    output = " 1  192.168.1.1  1.123 ms  1.001 ms\n 2  10.0.0.1  9.5 ms\n 3  * * *\n"
    hops = parse_traceroute(output)
    assert len(hops) >= 2
    assert hops[0]["address"] == "192.168.1.1"
    assert hops[1]["ms"] == 9.5


def test_parse_blocking_rules_filters_relevant_only() -> None:
    output = (
        "Rule Name: Block Twitch\n"
        "Enabled: Yes\n"
        "Direction: Out\n"
        "Action: Block\n"
        "Program: C:\\chrome.exe\n"
        "---\n"
        "Rule Name: Allow Something\n"
        "Enabled: Yes\n"
        "Action: Allow\n"
        "---\n"
        "Rule Name: Block Other\n"
        "Enabled: Yes\n"
        "Action: Block\n"
        "Program: C:\\other.exe\n"
        "---\n"
    )
    rules = parse_blocking_rules(output)
    assert len(rules) == 1
    assert "Block Twitch" in rules[0]["rule name"]


def test_backup_registry_is_noop_on_posix(tmp_path: Path) -> None:
    import sys  # noqa: PLC0415

    if sys.platform == "win32":
        return
    backup = BackupManager(session="unit")
    assert backup.backup_registry("HKCU", r"Software\Test", ["Value"]) is False
    assert (Path(backup.directory) / "manifest.json").exists()


def test_is_admin_returns_bool() -> None:
    assert isinstance(is_admin(), bool)
