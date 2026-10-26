"""Проверка №3: TCP-соединения к портам 443 и 80.

Замеряет latency handshake для ключевых доменов. Массовые отказы обычно
означают файрвол, провайдерский DPI или неработающий прокси.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config.constants import TCP_DOMAINS, TCP_PORTS
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.network import tcp_connect


class TCPCheck(BaseCheck):
    id = "tcp"
    title_ru = "TCP-соединение"
    title_en = "TCP connection"
    icon = "plug"
    fix_id = "firewall"
    timeout = 20.0

    def run(self) -> CheckResult:
        targets = [(host, port) for host in TCP_DOMAINS for port in TCP_PORTS]
        details: list[str] = []
        results: dict[str, dict[str, object]] = {}
        successes = 0
        latencies: list[float] = []
        failed_443: list[str] = []

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(tcp_connect, host, port, 2.5): (host, port)
                for host, port in targets
            }
            for future in as_completed(futures):
                if self.cancelled():
                    break
                host, port = futures[future]
                try:
                    answer = future.result(timeout=0.2)
                except Exception as exc:  # защита от редких ошибок пула потоков
                    answer = None
                    details.append(f"{host}:{port} -> worker error: {exc}")
                if answer is None:
                    continue
                key = f"{host}:{port}"
                results[key] = {
                    "ok": answer.ok,
                    "ms": round(answer.latency_ms, 1),
                    "address": answer.address,
                    "error": answer.error,
                }
                if answer.ok:
                    successes += 1
                    latencies.append(answer.latency_ms)
                    details.append(
                        f"OK   {key:38s} {answer.address:18s} {answer.latency_ms:6.0f} ms"
                    )
                else:
                    details.append(f"FAIL {key:38s} {answer.error[:70]}")
                    if port == 443:
                        failed_443.append(host)

        total = len(results) or 1
        avg = sum(latencies) / len(latencies) if latencies else 0.0
        details.append(f"successful: {successes}/{total}, average latency: {avg:.0f} ms")
        data = {"results": results, "success_rate": round(successes / total, 2), "avg_ms": avg}

        if successes == 0:
            return self.result(
                Status.ERROR,
                "Ни одно TCP-соединение с Twitch не установлено",
                "No TCP connection to Twitch succeeded",
                details=details,
                data=data,
            )
        if failed_443 or successes / total < 0.7:
            return self.result(
                Status.WARNING,
                f"Не все соединения доступны ({successes}/{total})",
                f"Some connections failed ({successes}/{total})",
                details=details,
                data=data,
            )
        return self.result(
            Status.OK,
            f"TCP 443/80 доступны, средняя задержка {avg:.0f} ms",
            f"TCP 443/80 reachable, average latency {avg:.0f} ms",
            details=details,
            data=data,
            fix_id=None,
        )
