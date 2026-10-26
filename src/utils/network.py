"""Сетевые помощники, не зависящие от Qt и платформы.

Содержат только чистые функции (классификация IP) и короткие сетевые вызовы
с таймаутами. Все функции безопасны для запуска в worker-потоке.
"""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from dataclasses import dataclass

# Подсети, которые НЕ должны встречаться в ответе DNS для публичного домена.
_NON_PUBLIC_V4 = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
        "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
        "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
        "224.0.0.0/4", "240.0.0.0/4",
    )
)


def is_suspicious_ip(value: str) -> bool:
    """Подозрительный ли IP для публичного домена Twitch.

    True: loopback, 0.0.0.0, private/LAN, CGNAT, link-local, reserved,
    documentation и multicast адреса — типичные признаки подмены DNS,
    записи в hosts или PAC/прокси-заглушки провайдера.
    """
    try:
        ip = ipaddress.ip_address(value.strip())
    except (ValueError, AttributeError):
        return True
    if ip.is_loopback or ip.is_unspecified or ip.is_reserved or ip.is_multicast:
        return True
    if ip.is_private or ip.is_link_local:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv6 ULA / совместимые с IPv4 адреса тоже не ожидаются от CDN.
        return ip.is_site_local or bool(ip.ipv4_mapped and is_suspicious_ip(str(ip.ipv4_mapped)))
    return any(ip in network for network in _NON_PUBLIC_V4)


def is_ipv6(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).version == 6
    except ValueError:
        return False


@dataclass(frozen=True)
class ConnectResult:
    ok: bool
    latency_ms: float
    address: str = ""
    error: str = ""


def tcp_connect(host: str, port: int, timeout: float = 2.5) -> ConnectResult:
    """TCP handshake с замером задержки. Никогда не выбрасывает исключение."""
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            peer = sock.getpeername()
            address = str(peer[0]) if isinstance(peer, tuple) else ""
            return ConnectResult(True, (time.perf_counter() - started) * 1000, address)
    except OSError as exc:
        return ConnectResult(False, (time.perf_counter() - started) * 1000, error=str(exc))


_DEFAULT_TIMEOUT_LOCK = threading.Lock()


def resolve(host: str, family: int = socket.AF_UNSPEC, timeout: float = 3.0) -> tuple[list[str], float]:
    """Системное разрешение домена. Возвращает (список IP, миллисекунды).

    Таймаут реализован через временное значение socket.setdefaulttimeout;
    getaddrinfo не умеет принимать таймаут напрямую. Лок не даёт нескольким
    проверкам одновременно перезаписать глобальное значение.
    """
    started = time.perf_counter()
    with _DEFAULT_TIMEOUT_LOCK:
        previous = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            infos = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
            addresses = list(dict.fromkeys(str(item[4][0]) for item in infos))
            return addresses, (time.perf_counter() - started) * 1000
        except (OSError, ValueError):
            return [], (time.perf_counter() - started) * 1000
        finally:
            socket.setdefaulttimeout(previous)
