"""Проверка и запрос прав администратора (UAC) для опасных исправлений.

Приложение запускается обычным пользователем: диагностика работает без прав.
Если исправление требует admin, показываем баннер и перезапускаем приложение
через ShellExecuteW(..., "runas", ...), что вызывает стандартный запрос UAC.
"""
from __future__ import annotations

import ctypes
import os
import sys
from typing import Sequence

from src.utils.logger import get_logger

log = get_logger(__name__)


def is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


def is_admin() -> bool:
    """Есть ли права администратора (Windows) / root (POSIX)."""
    try:
        if is_windows():
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except Exception as exc:  #Windll может отсутствовать в нестандартных сборках
        log.warning("Cannot determine admin status: %s", exc)
        return False


def request_admin_restart(extra_args: Sequence[str] = ("--elevated",)) -> bool:
    """Перезапустить приложение с запросом UAC. Возвращает False при отказе."""
    if is_admin():
        return True
    if not is_windows():
        log.warning("UAC elevation is only available on Windows")
        return False
    try:
        args = list(sys.argv[1:]) + list(extra_args)
        executable = sys.executable
        # sys.executable — python.exe при запуске из исходников, сам exe при сборке.
        # В режиме исходников обязательно передаём путь к main.py первым аргументом.
        if not getattr(sys, "frozen", False):
            from pathlib import Path  # noqa: PLC0415

            script = Path(__file__).resolve().parents[1] / "main.py"
            args = [str(script), *args]
            pythonw = Path(executable).with_name("pythonw.exe")
            if pythonw.exists():
                executable = str(pythonw)
        params = " ".join(f'"{arg}"' for arg in args)
        rc = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
            None, "runas", executable, params, None, 1
        )
        # ShellExecuteW возвращает HINSTANCE (>32 при успехе).
        return int(rc) > 32
    except Exception as exc:
        log.error("UAC elevation failed: %s", exc)
        return False


def relaunch_with_admin() -> bool:
    """Запросить UAC и завершить текущий процесс при успехе."""
    from PyQt6.QtWidgets import QApplication

    if request_admin_restart():
        log.info("Relaunching elevated, exiting current process")
        QApplication.instance().quit() if QApplication.instance() else None
        return True
    return False
