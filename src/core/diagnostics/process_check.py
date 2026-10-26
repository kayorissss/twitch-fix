"""Проверка №10: конфликтующие программы.

Сканирует процессы по категориям (антивирусы, VPN, DPI-обход, прокси/MITM,
блокировщики) и находит типичные конфликтующие комбинации.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from src.config.constants import PROCESS_SIGNATURES
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status


def match_category(process_name: str) -> str | None:
    """Определить категорию по имени процесса (без учёта регистра)."""
    name = process_name.lower().removesuffix(".exe")
    for category, (_, patterns) in PROCESS_SIGNATURES.items():
        if any(pattern in name for pattern in patterns):
            return category
    return None


def scan_names(names: Iterable[str]) -> dict[str, list[str]]:
    """Сгруппировать имена процессов по категориям (чистая функция для тестов)."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for name in names:
        category = match_category(name)
        if category and name not in grouped[category]:
            grouped[category].append(name)
    return dict(grouped)


def find_conflicts(grouped: dict[str, list[str]]) -> list[str]:
    """Вернуть список потенциальных конфликтов в виде готовых строк."""
    conflicts: list[str] = []
    av = grouped.get("antivirus", [])
    if len(av) >= 2:
        conflicts.append(
            f"2+ antivirus engines active ({', '.join(av[:3])}) → double traffic filtering"
        )
    if grouped.get("dpi") and grouped.get("vpn"):
        conflicts.append("DPI bypass + VPN: packet mangling conflicts with the VPN tunnel")
    if grouped.get("proxy") and grouped.get("vpn"):
        conflicts.append("Local proxy + VPN: chained proxies often break gql.twitch.tv")
    if grouped.get("proxy") and grouped.get("blocker"):
        conflicts.append("MITM proxy + DNS blocker: duplicate traffic interception")
    if grouped.get("dpi") and grouped.get("proxy"):
        conflicts.append("DPI bypass + local proxy: TLS handshake can be corrupted")
    if len(grouped.get("vpn", [])) >= 2:
        conflicts.append("Multiple VPN clients running simultaneously")
    return conflicts


class ProcessCheck(BaseCheck):
    id = "process"
    title_ru = "Конфликтующие программы"
    title_en = "Conflicting software"
    icon = "apps"
    fix_id = "process"
    timeout = 12.0

    def run(self) -> CheckResult:
        import psutil  # noqa: PLC0415

        names: list[str] = []
        try:
            for proc in psutil.process_iter(["name"], ad_value=""):
                name = proc.info.get("name") or ""
                if name:
                    names.append(name)
        except Exception as exc:
            return self.result(
                Status.WARNING,
                f"Не удалось перечислить процессы: {exc}",
                f"Could not enumerate processes: {exc}",
                fix_id=None,
            )

        grouped = scan_names(names)
        details = [f"processes scanned: {len(names)}"]
        for category, found in grouped.items():
            label = PROCESS_SIGNATURES[category][0]
            details.append(f"{label}: {', '.join(found[:12])}")
        conflicts = find_conflicts(grouped)
        details.extend(f"CONFLICT: {item}" for item in conflicts)
        data = {"groups": grouped, "conflicts": conflicts, "process_count": len(names)}

        if conflicts:
            return self.result(
                Status.WARNING,
                f"Найдено конфликтующих комбинаций: {len(conflicts)}",
                f"Conflicting combinations found: {len(conflicts)}",
                details=details,
                data=data,
            )
        if grouped:
            return self.result(
                Status.INFO,
                "Программы найдены, явных конфликтов нет",
                "Programs found, no obvious conflicts",
                details=details,
                data=data,
                fix_id=None,
            )
        return self.result(
            Status.OK,
            "Конфликтующих программ не найдено",
            "No conflicting software found",
            details=details,
            data=data,
            fix_id=None,
        )
