"""Проверка №7: системные прокси и PAC-файлы.

Источники: переменные окружения, реестр Windows (Internet Settings),
конфигурация WinHTTP и содержимое PAC-файла (ищем упоминания Twitch).
Пароли в URL маскируются — в отчёт они не попадают.
"""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlsplit

import requests

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status
from src.utils.system_info import run_command

ENV_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
WINREG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def mask_url(value: str) -> str:
    """Убрать логин/пароль из proxy URL перед выводом в лог и отчёт."""
    try:
        parsed = urlsplit(value if "://" in value else f"http://{value}")
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        prefix = "***@" if parsed.username else ""
        return f"{parsed.scheme}://{prefix}{host}{port}{parsed.path}" if parsed.scheme else f"{prefix}{host}{port}"
    except ValueError:
        return re.sub(r"//[^/@]+@", "//***@", value)


def read_windows_proxy() -> dict[str, str]:
    """Прочитать ProxyEnable/ProxyServer/AutoConfigURL из HKCU."""
    if sys.platform != "win32":
        return {}
    import winreg  # noqa: PLC0415

    values: dict[str, str] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINREG_KEY) as key:
            for name in ("ProxyEnable", "ProxyServer", "AutoConfigURL"):
                try:
                    item, _ = winreg.QueryValueEx(key, name)
                    values[name] = str(item)
                except FileNotFoundError:
                    values[name] = ""
    except OSError:
        return {}
    return values


class ProxyCheck(BaseCheck):
    id = "proxy"
    title_ru = "Прокси и PAC"
    title_en = "Proxy and PAC"
    icon = "route"
    fix_id = "proxy"
    timeout = 12.0

    def run(self) -> CheckResult:
        details: list[str] = []
        data: dict[str, object] = {}
        enabled: list[str] = []

        env_values = {name: os.environ.get(name, "") for name in ENV_NAMES if os.environ.get(name)}
        for name, value in env_values.items():
            details.append(f"env {name} = {mask_url(value)}")
            enabled.append(f"env:{name}")
        data["env"] = {name: mask_url(value) for name, value in env_values.items()}

        registry = read_windows_proxy()
        if registry:
            data["registry"] = {k: (mask_url(v) if "://" in v or k == "ProxyServer" else v) for k, v in registry.items()}
            details.append(f"registry ProxyEnable = {registry.get('ProxyEnable', '')}")
            for name in ("ProxyServer", "AutoConfigURL"):
                if registry.get(name):
                    details.append(f"registry {name} = {mask_url(registry[name])}")
            if registry.get("ProxyEnable") in ("1", "True", "true") or registry.get("ProxyServer"):
                enabled.append("registry:ProxyEnable")
            if registry.get("AutoConfigURL"):
                enabled.append("registry:AutoConfigURL")

        if sys.platform == "win32":
            _, out, _ = run_command(["netsh", "winhttp", "show", "proxy"], timeout=6)
            if "Direct access" not in out and out.strip():
                details.append("WinHTTP proxy: " + " / ".join(out.splitlines()[:4]).strip())
                enabled.append("winhttp")
            else:
                details.append("WinHTTP proxy: direct access")

        # PAC: скачиваем только если он задан явно (и ищем twitch-правила).
        pac_url = registry.get("AutoConfigURL", "") or env_values.get("HTTP_PROXY", "")
        if pac_url.lower().endswith(".pac") or "pac" in pac_url.lower():
            try:
                response = requests.get(mask_url(pac_url), timeout=3.0)
                body = response.text[:20_000]
                twitch_rules = [line.strip()[:100] for line in body.splitlines() if "twitch" in line.lower()]
                details.append(f"PAC fetched: {response.status_code}, twitch rules: {len(twitch_rules)}")
                for rule in twitch_rules[:5]:
                    details.append(f"PAC rule: {rule}")
                data["pac_twitch_rules"] = twitch_rules[:20]
                if twitch_rules:
                    enabled.append("pac:twitch-rules")
            except requests.RequestException as exc:
                details.append(f"PAC fetch failed: {type(exc).__name__}")

        if not enabled:
            return self.result(
                Status.OK,
                "Системный прокси не используется",
                "No system proxy configured",
                details=details or ["env / registry / WinHTTP: direct"],
                data=data,
                fix_id=None,
            )
        return self.result(
            Status.WARNING,
            f"Обнаружен активный прокси ({', '.join(enabled[:3])})",
            f"Active proxy detected ({', '.join(enabled[:3])})",
            details=details
            + [
                "A proxy/PAC can intercept Twitch traffic and break gql/websocket connections.",
                "If you do not use it intentionally, disable it with the auto-fix.",
            ],
            data=data,
        )
