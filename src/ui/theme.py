"""Загрузка QSS-тем и доступ к цветовой палитре виджетов."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.config.constants import DARK, LIGHT, Palette, STATUS_COLORS
from src.utils.paths import resource_path

_current_theme = "dark"


def current_theme() -> str:
    return _current_theme


def palette() -> Palette:
    return LIGHT if _current_theme == "light" else DARK


def status_color(status: str) -> str:
    """Цвет статуса с учётом текущей темы."""
    light_map = {
        "ok": LIGHT.ok, "warning": LIGHT.warn, "error": LIGHT.error,
        "info": LIGHT.info, "skipped": LIGHT.text_muted, "running": LIGHT.accent,
    }
    dark_map = STATUS_COLORS
    return (light_map if _current_theme == "light" else dark_map).get(status, palette().accent)


def load_theme(name: str = "dark") -> str:
    """Загрузить QSS из resources и применить к QApplication."""
    global _current_theme
    _current_theme = name if name in ("dark", "light") else "dark"
    path = resource_path(f"src/ui/styles/{_current_theme}_theme.qss")
    try:
        stylesheet = path.read_text(encoding="utf-8")
    except OSError:
        stylesheet = ""
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(stylesheet)
    return stylesheet
