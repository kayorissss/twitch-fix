"""Проверка №9: сетевой адаптер (MTU, IPv6, IP, шлюз, DNS, тип сети).

Для мобильной раздачи типичная проблема — MTU 1500 при туннеле оператора:
рекомендуем 1400. Также проверяем, не «видит» ли система IPv6, который
фактически не работает (тогда браузер долго ждёт AAAA-адрес).
"""
from __future__ import annotations

import socket

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.network import tcp_connect
from src.utils.system_info import _default_gateway, _dns_servers, _local_ip, _mtu, _connection_type

RECOMMENDED_MOBILE_MTU = 1400


class NetworkCheck(BaseCheck):
    id = "network"
    title_ru = "Сетевой адаптер"
    title_en = "Network adapter"
    icon = "network"
    fix_id = "network"
    timeout = 15.0

    def run(self) -> CheckResult:
        details: list[str] = []
        problems: list[str] = []
        ip = _local_ip()
        gateway = _default_gateway()
        dns = _dns_servers()
        mtu = _mtu()
        try:
            connection = _connection_type(gateway)
        except Exception:
            connection = "unknown"

        details.extend(
            [
                f"local IP: {ip or 'n/a'}",
                f"gateway: {gateway or 'n/a'}",
                f"DNS servers: {', '.join(dns) if dns else 'n/a'}",
                f"MTU: {mtu if mtu else 'n/a'}",
                f"connection type: {connection}",
                f"IPv6 supported by OS: {socket.has_ipv6}",
            ]
        )

        # Проверяем работоспособность IPv6: есть ли AAAA и проходит ли handshake.
        ipv6_broken = False
        if socket.has_ipv6:
            try:
                infos = socket.getaddrinfo("www.twitch.tv", 443, socket.AF_INET6, socket.SOCK_STREAM)
                addresses = list(dict.fromkeys(str(item[4][0]) for item in infos))
                details.append(f"AAAA www.twitch.tv: {', '.join(addresses) if addresses else 'none'}")
                if addresses:
                    answer = tcp_connect(addresses[0], 443, timeout=2.0)
                    details.append(f"IPv6 TCP 443: {'OK' if answer.ok else 'FAIL ' + answer.error[:60]}")
                    ipv6_broken = not answer.ok
                    if ipv6_broken:
                        problems.append("IPv6 AAAA resolves but TCP fails")
            except OSError as exc:
                details.append(f"IPv6 lookup: {exc}")

        if connection == "mobile" and mtu and mtu > RECOMMENDED_MOBILE_MTU:
            problems.append(f"MTU {mtu} > {RECOMMENDED_MOBILE_MTU} for mobile tethering")
            details.append(f"recommended MTU for mobile tethering: {RECOMMENDED_MOBILE_MTU}")

        data = {
            "ip": ip,
            "gateway": gateway,
            "dns": dns,
            "mtu": mtu,
            "connection_type": connection,
            "ipv6_broken": ipv6_broken,
        }
        if problems:
            return self.result(
                Status.WARNING,
                f"Параметры сети требуют внимания ({len(problems)})",
                f"Network settings need attention ({len(problems)})",
                details=details + ["issues: " + "; ".join(problems)],
                data=data,
            )
        return self.result(
            Status.OK,
            f"Адаптер настроен корректно ({connection}, MTU {mtu or '?'})",
            f"Adapter looks fine ({connection}, MTU {mtu or '?'})",
            details=details,
            data=data,
            fix_id=None,
        )
