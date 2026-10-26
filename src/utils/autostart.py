"""Автозапуск через HKCU\\...\\CurrentVersion\\Run (не требует UAC)."""
from __future__ import annotations

import sys
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TwitchFix"


def _launch_command() -> str:
    """Команда запуска: exe в собранном виде, pythonw + main.py из исходников."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = str(pythonw) if pythonw.exists() else sys.executable
    script = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{interpreter}" "{script}"'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg  # noqa: PLC0415

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """Включить/выключить автозапуск. Возвращает успех операции."""
    if sys.platform != "win32":
        log.info("Autostart is Windows-only; ignoring on %s", sys.platform)
        return False
    import winreg  # noqa: PLC0415

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        log.info("Autostart = %s", enabled)
        return True
    except OSError as exc:
        log.error("Cannot change autostart: %s", exc)
        return False
