"""Исправление №2: смена DNS адаптеров на 1.1.1.1 / 8.8.8.8.

Перед изменением сохраняем текущую конфигурацию DNS в manifest бэкапа и
сбрасываем кэш DNS. Требуются права администратора.
"""
from __future__ import annotations

import re

from src.config.constants import CLOUDFLARE_DNS, GOOGLE_DNS
from src.core.fixes.base_fix import BaseFix, FixResult
from src.utils.system_info import _dns_servers, run_command


def active_adapters() -> list[str]:
    """Имена активных сетевых адаптеров из `netsh interface show interface`."""
    code, out, _ = run_command(["netsh", "interface", "show", "interface"], timeout=8)
    if code != 0:
        return []
    adapters: list[str] = []
    for line in out.splitlines():
        if "Connected" not in line and "подключен" not in line.lower():
            continue
        # Формат: "Enabled  Connected  Dedicated  Wi-Fi"
        match = re.search(r"\s{2,}([^\s][^\\/:*?\"<>|]+?)\s*$", line)
        if match:
            name = match.group(1).strip()
            if name and name not in adapters and name.lower() not in ("connected", "dedicated"):
                adapters.append(name)
    return adapters


class DNSFix(BaseFix):
    id = "dns"
    title_ru = "Сменить DNS на публичный"
    title_en = "Switch to public DNS"
    description_ru = "Назначить активным адаптерам 1.1.1.1 и 8.8.8.8 (вместо DNS провайдера), затем очистить кэш DNS."
    description_en = "Set active adapters to 1.1.1.1 and 8.8.8.8 (replacing ISP DNS), then flush the DNS cache."
    requires_admin = True
    windows_only = True

    def apply(self, dry_run: bool = False) -> FixResult:
        adapters = active_adapters()
        _, dns_raw, _ = run_command(["netsh", "interface", "ipv4", "show", "dnsservers"], timeout=8)
        if self.backup:
            self.backup.manifest["dns_before"] = {
                "servers": _dns_servers(),
                "adapters": adapters,
                "raw_netsh_output": dns_raw[:8000],
            }
            self.backup._flush()
        details = [
            "current DNS configuration is recorded in the backup manifest",
            f"previous DNS: {', '.join(_dns_servers()) or 'n/a'}",
            f"new DNS: {', '.join(CLOUDFLARE_DNS + GOOGLE_DNS[:1])}",
            f"active adapters: {', '.join(adapters) if adapters else 'none detected'}",
        ]
        if not adapters:
            return self.result(
                False,
                "Не найдено активных сетевых адаптеров",
                "No active network adapters found",
                details=details,
            )
        if dry_run:
            return self.result(
                True,
                f"Будет перенастроено адаптеров: {len(adapters)}",
                f"Would reconfigure {len(adapters)} adapters",
                details=details,
            )
        for adapter in adapters:
            code, out, err = run_command(
                ["netsh", "interface", "ipv4", "set", "dnsservers", f"name={adapter}",
                 "static", CLOUDFLARE_DNS[0], "primary", "validate=no"],
                timeout=10,
            )
            details.append(f"{adapter}: set primary -> code {code} {out.strip()[:60]} {err.strip()[:60]}")
            if code == 0:
                for index, server in enumerate((CLOUDFLARE_DNS[1], GOOGLE_DNS[0]), start=2):
                    add_code, _, add_err = run_command(
                        ["netsh", "interface", "ipv4", "add", "dnsservers", f"name={adapter}",
                         server, f"index={index}", "validate=no"],
                        timeout=10,
                    )
                    details.append(f"{adapter}: add {server} -> code {add_code} {add_err.strip()[:60]}")
        flush_code, _, _ = run_command(["ipconfig", "/flushdns"], timeout=8)
        details.append(f"ipconfig /flushdns -> code {flush_code}")
        return self.result(
            True,
            f"DNS обновлён на {len(adapters)} адаптерах",
            f"DNS updated on {len(adapters)} adapters",
            details=details,
        )
