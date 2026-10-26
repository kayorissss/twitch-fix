"""Реестр исправлений.

``fixes_for_results`` превращает проблемы, найденные диагностикой, в список
исправлений, готовых к показу на экране «Авто-исправление».
"""
from __future__ import annotations

from src.core.diagnostics.base_check import CheckResult
from src.core.fixes.base_fix import BaseFix, FixResult
from src.core.fixes.hosts_fix import HostsFix
from src.core.fixes.dns_fix import DNSFix
from src.core.fixes.proxy_fix import ProxyFix
from src.core.fixes.cache_fix import CacheFix
from src.core.fixes.network_fix import FirewallFix, NetworkFix, TimeFix
from src.core.fixes.ssl_fix import SSLFix
from src.core.fixes.process_fix import ProcessFix
from src.core.fixes.quick_fix import QuickFix

FIX_CLASSES: tuple[type[BaseFix], ...] = (
    HostsFix,
    DNSFix,
    ProxyFix,
    FirewallFix,
    NetworkFix,
    TimeFix,
    CacheFix,
    SSLFix,
    ProcessFix,
)


def fix_by_id(fix_id: str) -> type[BaseFix] | None:
    return next((cls for cls in FIX_CLASSES if cls.id == fix_id), None)


def all_fixes() -> list[BaseFix]:
    return [cls() for cls in FIX_CLASSES]


def fixes_for_results(results: list[CheckResult]) -> list[BaseFix]:
    """Собрать уникальные исправления для проблемных результатов."""
    ids: list[str] = []
    for result in results:
        if result.is_problem and result.fix_id and result.fix_id not in ids:
            ids.append(result.fix_id)
    return [cls() for fix_id in ids if (cls := fix_by_id(fix_id)) is not None]


__all__ = [
    "BaseFix", "FixResult", "FIX_CLASSES", "all_fixes", "fix_by_id",
    "fixes_for_results", "QuickFix",
]
