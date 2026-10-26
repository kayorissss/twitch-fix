"""Исправление №3: отключение системного прокси и PAC.

Сбрасывает HKCU\\Internet Settings (ProxyEnable/ProxyServer/AutoConfigURL),
WinHTTP-прокси и пользовательские переменные окружения. Значения реестра и
переменных окружения предварительно сохраняются в бэкап-манифест.
"""
from __future__ import annotations

import os
import sys

from src.core.fixes.base_fix import BaseFix, FixResult
from src.utils.system_info import run_command

WINREG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
ENV_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


class ProxyFix(BaseFix):
    id = "proxy"
    title_ru = "Отключить системный прокси"
    title_en = "Disable system proxy"
    description_ru = "Выключить ProxyEnable, удалить ProxyServer/AutoConfigURL, сбросить WinHTTP и proxy-переменные окружения."
    description_en = "Disable ProxyEnable, remove ProxyServer/AutoConfigURL, reset WinHTTP and proxy environment variables."
    requires_admin = True

    def apply(self, dry_run: bool = False) -> FixResult:
        details: list[str] = []
        env_before = {name: os.environ.get(name, "") for name in ENV_NAMES if os.environ.get(name)}
        if self.backup:
            self.backup.manifest["proxy_env"] = env_before
            self.backup.backup_registry(
                "HKCU", WINREG_KEY, ["ProxyEnable", "ProxyServer", "AutoConfigURL"]
            )
            self.backup._flush()
        details.append(f"env vars to clear: {', '.join(env_before) if env_before else 'none'}")
        if dry_run:
            return self.result(
                True,
                "Прокси и PAC будут отключены",
                "Proxy and PAC would be disabled",
                details=details,
            )

        if sys.platform == "win32":
            import winreg  # noqa: PLC0415

            try:
                with winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER, WINREG_KEY, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                    for name in ("ProxyServer", "AutoConfigURL"):
                        try:
                            winreg.DeleteValue(key, name)
                        except FileNotFoundError:
                            pass
                details.append("HKCU Internet Settings: ProxyEnable=0, PAC removed")
            except OSError as exc:
                details.append(f"registry error: {exc}")
            code, out, err = run_command(["netsh", "winhttp", "reset", "proxy"], timeout=10)
            details.append(f"netsh winhttp reset proxy -> {code}: {(out + err).strip()[:120]}")
            for name in env_before:
                run_command(["setx", name, ""], timeout=5)

        for name in ENV_NAMES:
            os.environ.pop(name, None)
        details.append("process environment cleaned (restart open browsers to take effect)")
        return self.result(
            True,
            "Системный прокси отключён",
            "System proxy disabled",
            details=details,
            needs_restart=True,
        )
