"""Проверка №8: исходящие правила файрвола Windows.

Ищет включённые блокирующие правила, в имени/программе которых встречаются
twitch, ttvnw или названия браузеров. Также сообщает, если файрвол выключен.
"""
from __future__ import annotations

import sys

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.system_info import run_command

INTERESTING = ("twitch", "ttvnw", "chrome", "firefox", "msedge", "opera", "brave", "browser")


def parse_blocking_rules(output: str) -> list[dict[str, str]]:
    """Разобрать вывод `netsh advfirewall firewall show rule name=all dir=out`.

    Возвращает только Enabled=Yes + Action=Block, релевантные для Twitch.
    """
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines() + ["---"]:
        if line.startswith("---") or (line.startswith("Rule Name:") and current):
            if _keep(current):
                blocks.append(current.copy())
            current = {}
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        current[key.strip().lower()] = value.strip()
    return blocks


def _keep(rule: dict[str, str]) -> bool:
    if rule.get("enabled", "").lower() != "yes":
        return False
    if "block" not in rule.get("action", "").lower():
        return False
    text = " ".join(rule.values()).lower()
    return any(word in text for word in INTERESTING)


class FirewallCheck(BaseCheck):
    id = "firewall"
    title_ru = "Файрвол Windows"
    title_en = "Windows Firewall"
    icon = "shield"
    fix_id = "firewall"
    timeout = 25.0

    def run(self) -> CheckResult:
        if sys.platform != "win32":
            return self.result(
                Status.SKIPPED,
                "Проверка доступна только в Windows",
                "This check is Windows-only",
                details=[f"platform: {sys.platform}"],
                fix_id=None,
            )

        details: list[str] = []
        _, profile_out, _ = run_command(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=8)
        state_off = "OFF" in profile_out.upper()
        details.append("firewall profiles: " + ("some disabled" if state_off else "enabled"))

        code, out, err = run_command(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=all", "dir=out"],
            timeout=20,
        )
        if code != 0 or not out.strip():
            details.append(f"netsh show rule failed (code={code}): {err[:120]}")
            return self.result(
                Status.WARNING,
                "Не удалось прочитать правила файрвола",
                "Could not read firewall rules",
                details=details,
                fix_id=None,
            )
        blocking = parse_blocking_rules(out)
        for rule in blocking[:15]:
            details.append(
                f"BLOCK: {rule.get('rule name', '?')} | program={rule.get('program', '-')[:80]}"
            )
        details.append(f"relevant outbound block rules: {len(blocking)}")
        data = {"blocking_rules": blocking[:30], "profiles_disabled": state_off}

        if blocking:
            return self.result(
                Status.ERROR,
                f"Найдено {len(blocking)} блокирующих правил для Twitch/браузеров",
                f"Found {len(blocking)} blocking rules for Twitch/browsers",
                details=details,
                data=data,
            )
        if state_off:
            return self.result(
                Status.WARNING,
                "Файрвол отключён для одного или нескольких профилей",
                "Firewall is disabled for one or more profiles",
                details=details,
                data=data,
                fix_id=None,
            )
        return self.result(
            Status.OK,
            "Блокирующих правил для Twitch нет",
            "No blocking rules for Twitch",
            details=details,
            data=data,
            fix_id=None,
        )
