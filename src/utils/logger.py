"""Логирование всех действий приложения в файл (ротация, UTF-8).

Файл: %LOCALAPPDATA%/TwitchFix/logs/twitchfix.log (Linux: ~/.local/share/...).
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from src.utils.paths import logs_path

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"
_configured = False


def setup_logging(debug: bool = False) -> logging.Logger:
    """Настроить корневой логгер один раз за процесс."""
    global _configured
    root = logging.getLogger()
    if _configured:
        return root
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    try:
        file_handler = RotatingFileHandler(
            logs_path(), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
    except OSError as exc:  # например, нет прав на запись — не блокируем запуск
        print(f"[TwitchFix] Cannot create log file: {exc}", file=sys.stderr)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG if debug else logging.WARNING)
    root.addHandler(console)
    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Вернуть именованный логгер (не падает даже до setup_logging)."""
    setup_logging()
    return logging.getLogger(name)


def install_excepthook() -> None:
    """Гарантированно записать любое необработанное исключение в лог."""
    logger = get_logger("twitchfix.uncaught")

    def _hook(exc_type, exc_value, exc_tb) -> None:  # type: ignore[no-untyped-def]
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _hook
