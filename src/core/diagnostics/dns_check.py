"""Проверка №2: DNS.

- системный резолвер для всех ключевых доменов Twitch;
- поиск подмены: loopback/private/CGNAT/reserved IP;
- сравнение с Google DNS (8.8.8.8) через dnspython;
- замер времени отклика.
"""
from __future__ import annotations

from typing import Any

from src.config.constants import DNS_DOMAINS, DNS_KEY_DOMAINS, GOOGLE_DNS
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.network import is_suspicious_ip, resolve

_RESOLVER_TIMEOUT = 2.0
_RESOLVER_LIFETIME = 3.0


def google_resolve(host: str, nameservers: tuple[str, ...] = GOOGLE_DNS) -> list[str]:
    """Разрешить домен через публичный DNS. Ошибки -> пустой список."""
    try:
        import dns.resolver  # noqa: PLC0415 - dnspython может отсутствовать

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = list(nameservers)
        resolver.timeout = _RESOLVER_TIMEOUT
        resolver.lifetime = _RESOLVER_LIFETIME
        return sorted(
            {str(record.address) for record in resolver.resolve(host, "A", raise_on_no_answer=False)}
        )
    except Exception:
        return []


def classify_resolution(system: list[str], google: list[str]) -> str:
    """Классифицировать ответ: ok / suspicious / mismatch / failed / unknown.

    Вынесено в чистую функцию для модульных тестов.
    """
    if system and any(is_suspicious_ip(ip) for ip in system):
        return "suspicious"
    if not system and google:
        return "failed"
    if not system and not google:
        return "unknown"
    if google and not set(system) & set(google):
        # CDN часто отдаёт разные IP — это повод предупредить, но не ошибка.
        return "mismatch"
    return "ok"


class DNSCheck(BaseCheck):
    id = "dns"
    title_ru = "DNS"
    title_en = "DNS"
    icon = "globe"
    fix_id = "dns"
    timeout = 25.0

    def run(self) -> CheckResult:
        resolutions: dict[str, dict[str, Any]] = {}
        details: list[str] = []
        problems = 0
        slow_count = 0
        total_ms = 0.0
        compared = 0
        google_unavailable = 0

        domains = list(dict.fromkeys(DNS_DOMAINS))
        for host in domains:
            if self.cancelled():
                break
            addresses, elapsed = resolve(host, timeout=2.5)
            resolutions[host] = {"system": addresses, "ms": round(elapsed, 1), "google": []}
            total_ms += elapsed
            if elapsed > 400:
                slow_count += 1
            details.append(
                f"{host}: {', '.join(addresses) if addresses else 'NXDOMAIN/timeout'} "
                f"({elapsed:.0f} ms)"
            )

        # Публичный DNS сравниваем только для ключевых доменов (чтобы не тратить время).
        for host in DNS_KEY_DOMAINS:
            if self.cancelled():
                break
            google = google_resolve(host)
            resolutions.setdefault(host, {"system": [], "ms": 0, "google": []})["google"] = google
            if not google:
                google_unavailable += 1
                continue
            compared += 1
            system = resolutions[host].get("system", [])
            verdict = classify_resolution(system, google)
            details.append(
                f"compare {host}: system={','.join(system) or '-'} google={','.join(google)} -> {verdict}"
            )
            if verdict in ("suspicious", "failed", "mismatch"):
                problems += 1

        failed_key = [h for h in DNS_KEY_DOMAINS if not resolutions.get(h, {}).get("system")]
        suspicious = [
            (host, ip)
            for host, item in resolutions.items()
            for ip in item.get("system", [])
            if is_suspicious_ip(ip)
        ]
        for host, ip in suspicious[:10]:
            details.append(f"SUSPICIOUS {host} -> {ip}")
        if slow_count:
            details.append(f"slow responses (>400 ms): {slow_count}")
        if google_unavailable:
            details.append(f"Google DNS unavailable for {google_unavailable} domains (network/UDP blocked)")
        details.append(f"average system lookup: {total_ms / max(1, len(domains)):.0f} ms")
        details.append(f"public DNS comparisons: {compared}")

        data = {"resolutions": resolutions, "suspicious": suspicious, "slow": slow_count}
        if failed_key and len(failed_key) == len(DNS_KEY_DOMAINS):
            return self.result(
                Status.ERROR,
                "Все ключевые домены Twitch не разрешаются",
                "All key Twitch domains fail to resolve",
                details=details,
                data=data,
            )
        if suspicious:
            return self.result(
                Status.ERROR,
                f"Обнаружена подмена DNS ({len(suspicious)} подозрительных IP)",
                f"DNS spoofing detected ({len(suspicious)} suspicious IPs)",
                details=details,
                data=data,
            )
        if failed_key or problems:
            return self.result(
                Status.WARNING,
                f"Есть проблемы с DNS ({len(failed_key)} доменов не отвечают)",
                f"DNS issues found ({len(failed_key)} domains not resolving)",
                details=details,
                data=data,
            )
        if slow_count >= 3:
            return self.result(
                Status.WARNING,
                "DNS работает, но отвечает медленно",
                "DNS works but responds slowly",
                details=details,
                data=data,
            )
        return self.result(
            Status.OK,
            "DNS разрешает домены Twitch корректно",
            "DNS resolves Twitch domains correctly",
            details=details,
            data=data,
            fix_id=None,
        )
