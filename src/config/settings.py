"""Пользовательские настройки на базе QSettings (INI в папке приложения).

Все обращения к настройкам идут через этот класс: он знает значения по
умолчанию, приводит типы и рассылает сигнал об изменении (тема/язык/трей).
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from src.utils.paths import app_dirs


class AppSettings(QObject):
    """Обёртка над QSettings с типизированными значениями по умолчанию."""

    changed = pyqtSignal(str, object)

    DEFAULTS: dict[str, Any] = {
        "language": "ru",
        "theme": "dark",
        "notifications": True,
        "autostart": False,
        "monitoring": True,
        "monitor_interval": 5,
        "history_days": 7,
        "restore_point": True,
        "compact": False,
        "geometry": "",
    }

    def __init__(self, path: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        ini = path or str(app_dirs().config / "settings.ini")
        self._settings = QSettings(ini, QSettings.Format.IniFormat)

    def get(self, key: str) -> Any:
        default = self.DEFAULTS.get(key)
        value = self._settings.value(key, default)
        # QSettings.INI хранит bool/int строками — приводим к типу default.
        if isinstance(default, bool):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "on")
        if isinstance(default, int) and not isinstance(default, bool):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        if key not in self.DEFAULTS:
            raise KeyError(f"Unknown setting: {key}")
        self._settings.setValue(key, value)
        self._settings.sync()
        self.changed.emit(key, value)

    def set_language(self, value: str) -> None:
        self.set("language", value if value in ("ru", "en") else "ru")

    def set_theme(self, value: str) -> None:
        self.set("theme", value if value in ("dark", "light") else "dark")

    def reset(self) -> None:
        self._settings.clear()
        self._settings.sync()
        for key, value in self.DEFAULTS.items():
            self.changed.emit(key, value)

    @property
    def file_path(self) -> str:
        return self._settings.fileName()

    def as_dict(self) -> dict[str, Any]:
        return {key: self.get(key) for key in self.DEFAULTS}
