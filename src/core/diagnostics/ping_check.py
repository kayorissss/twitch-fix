"""Проверка №11: ICMP ping и трассировка маршрута.

Показывает задержки до Twitch/CDN и список хопов с цветовой индикацией;
 tracert/traceroute запускается с ограниченным числом прыжков и таймаутом.
"""
from __future__ import annotations

import re
import sys
from statistics import mean

from src.config.constants import PING_HOSTS, TRACEROUTE_HOST
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.network import tcp_connect
from src.utils.system_info import run_command


def ping_host(host: str, count: int = 3) -> dict[str, object]:
    """Пинг через системную утилиту; при недоступности ICMP — TCP fallback."""
    if sys.platform == "win32":
        args = ["ping", "-n", str(count), "-w", "1000", host]
    else:
        args = ["ping", "-c", str(count), "-W", "1", "-n", host]
    code, out, _ = run_command(args, timeout=count + 3)
    latencies = [
        float(value.replace(",", "."))
        for value in re.findall(r"(?:time|время)[=<]\s*([\d.,]+)\s*ms", out, flags=re.I)
    ]
    reply_count = len(latencies)
    if reply_count:
        return {
            "host": host, "ok": True, "sent": count, "received": reply_count,
            "avg_ms": round(mean(latencies), 1), "loss": round((count - reply_count) / count * 100),
            "method": "icmp",
        }
    # ICMP часто закрыт; TCP-handshake всё равно показывает доступность узла.
    answer = tcp_connect(host, 443, timeout=2.0)
    return {
        "host": host, "ok": answer.ok, "sent": count, "received": 0,
        "avg_ms": round(answer.latency_ms, 1) if answer.ok else None,
        "loss": 100 if not answer.ok else None,
        "method": "tcp-fallback" if answer.ok else "icmp",
        "error": answer.error[:100],
    }


def parse_traceroute(output: str) -> list[dict[str, object]]:
    """Разобрать вывод tracert/traceroute в список хопов."""
    hops: list[dict[str, object]] = []
    for line in output.splitlines():
        match = re.match(r"\s*(\d{1,2})\s+(.*)", line)
        if not match:
            continue
        index = int(match.group(1))
        rest = match.group(2).strip()
        if rest.startswith("<1 ms") or rest.startswith("*") and len(rest) < 5:
            continue
        addresses = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", rest)
        times = [float(value.replace(",", ".")) for value in re.findall(r"([\d.,]+)\s*ms", rest)]
        hops.append(
            {
                "hop": index,
                "address": addresses[0] if addresses else "*",
                "ms": round(mean(times), 1) if times else None,
                "ok": bool(addresses),
            }
        )
    return hops


class PingCheck(BaseCheck):
    id = "ping"
    title_ru = "Пинг и трассировка"
    title_en = "Ping and traceroute"
    icon = "pulse"
    fix_id = None
    timeout = 30.0

    def run(self) -> CheckResult:
        pings: list[dict[str, object]] = []
        details: list[str] = []
        for host in PING_HOSTS:
            if self.cancelled():
                break
            result = ping_host(host)
            pings.append(result)
            details.append(
                f"ping {host}: {'OK' if result['ok'] else 'FAIL'} "
                f"avg={result['avg_ms']} ms loss={result['loss']}% ({result['method']})"
            )

        args = (
            ["tracert", "-d", "-h", "12", "-w", "500", TRACEROUTE_HOST]
            if sys.platform == "win32"
            else ["traceroute", "-n", "-m", "12", "-w", "1", TRACEROUTE_HOST]
        )
        code, out, err = run_command(args, timeout=30)
        hops = parse_traceroute(out)
        if hops:
            details.append(f"traceroute {TRACEROUTE_HOST}: {len(hops)} hops")
            for hop in hops:
                marker = f"{hop['ms']} ms" if hop["ms"] is not None else "* * *"
                details.append(f"  {hop['hop']:>2}. {str(hop['address']):<18} {marker}")
        else:
            details.append(f"traceroute unavailable (code={code}): {err[:100] or 'no output'}")

        last_ok = max((int(h["hop"]) for h in hops if h["ok"]), default=0)
        break_at = last_ok if last_ok and last_ok < 12 else None
        if break_at:
            details.append(f"possible route break after hop {break_at}")
        data = {"pings": pings, "hops": hops, "break_at": break_at}

        failed = [p for p in pings if not p["ok"]]
        lossy = [p for p in pings if isinstance(p.get("loss"), int) and int(p["loss"]) > 30]
        if pings and len(failed) == len(pings):
            return self.result(
                Status.ERROR,
                "Twitch и CDN не отвечают на ping/TCP",
                "Twitch and CDN do not answer ping/TCP",
                details=details,
                data=data,
            )
        if failed or lossy or break_at:
            return self.result(
                Status.WARNING,
                f"Есть потери или обрыв маршрута ({len(failed)} хостов недоступно)",
                f"Packet loss or route break ({len(failed)} hosts unreachable)",
                details=details,
                data=data,
            )
        return self.result(
            Status.OK,
            "Маршрут до Twitch стабилен",
            "Route to Twitch is stable",
            details=details,
            data=data,
        )
