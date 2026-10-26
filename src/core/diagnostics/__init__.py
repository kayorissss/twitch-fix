"""Реестр всех проверок диагностики.

Порядок важен: быстрые локальные проверки идут первыми, сетевые — дальше.
``all_checks()`` создаёт свежие экземпляры для каждого запуска диагностики.
"""
from __future__ import annotations

from typing import Callable

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status, overall_status
from src.core.diagnostics.hosts_check import HostsCheck
from src.core.diagnostics.dns_check import DNSCheck
from src.core.diagnostics.tcp_check import TCPCheck
from src.core.diagnostics.ssl_check import SSLCheck
from src.core.diagnostics.http_check import HTTPCheck
from src.core.diagnostics.time_check import TimeCheck
from src.core.diagnostics.proxy_check import ProxyCheck
from src.core.diagnostics.firewall_check import FirewallCheck
from src.core.diagnostics.network_check import NetworkCheck
from src.core.diagnostics.process_check import ProcessCheck
from src.core.diagnostics.ping_check import PingCheck
from src.core.diagnostics.browser_check import BrowserCheck
from src.core.diagnostics.twitch_api_check import TwitchAPICheck

CHECK_CLASSES: tuple[type[BaseCheck], ...] = (
    HostsCheck,
    DNSCheck,
    TCPCheck,
    SSLCheck,
    HTTPCheck,
    TwitchAPICheck,
    TimeCheck,
    ProxyCheck,
    FirewallCheck,
    NetworkCheck,
    ProcessCheck,
    PingCheck,
    BrowserCheck,
)


def all_checks(cancelled: Callable[[], bool] | None = None) -> list[BaseCheck]:
    """Создать список из 13 проверок в порядке выполнения."""
    return [cls(cancelled=cancelled) for cls in CHECK_CLASSES]


def check_by_id(check_id: str) -> type[BaseCheck] | None:
    return next((cls for cls in CHECK_CLASSES if cls.id == check_id), None)


__all__ = [
    "BaseCheck", "CheckResult", "Status", "overall_status",
    "CHECK_CLASSES", "all_checks", "check_by_id",
]
