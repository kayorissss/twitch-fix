"""Обнаружение конфликтующих процессов (чистые функции)."""
from __future__ import annotations

from src.core.diagnostics.process_check import find_conflicts, match_category, scan_names


def test_match_category() -> None:
    assert match_category("goodbyedpi.exe") == "dpi"
    assert match_category("ekrn.exe") == "antivirus"
    assert match_category("openvpn.exe") == "vpn"
    assert match_category("Fiddler.exe") == "proxy"
    assert match_category("AdGuard.exe") == "blocker"
    assert match_category("explorer.exe") is None


def test_scan_names_groups_unique_values() -> None:
    grouped = scan_names(["wireguard.exe", "wireguard.exe", "zapret.exe", "chrome.exe"])
    assert grouped["vpn"] == ["wireguard.exe"]
    assert grouped["dpi"] == ["zapret.exe"]
    assert "chrome.exe" not in grouped.get("dpi", [])


def test_find_conflicts_detects_dpi_plus_vpn() -> None:
    grouped = {"dpi": ["goodbyedpi.exe"], "vpn": ["wireguard.exe"]}
    conflicts = find_conflicts(grouped)
    assert any("DPI" in item and "VPN" in item for item in conflicts)


def test_find_conflicts_empty_for_single_category() -> None:
    assert find_conflicts({"antivirus": ["avp.exe"]}) == []
