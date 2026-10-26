"""QSettings-обёртка: значения по умолчанию, приведение типов, сброс."""
from __future__ import annotations

from pathlib import Path

from src.config.settings import AppSettings


def test_defaults_and_typed_values(tmp_path: Path) -> None:
    settings = AppSettings(path=str(tmp_path / "settings.ini"))
    assert settings.get("language") == "ru"
    assert settings.get("theme") == "dark"
    assert settings.get("monitoring") is True
    assert settings.get("monitor_interval") == 5
    settings.set("monitor_interval", 11)
    settings.set("notifications", False)
    reloaded = AppSettings(path=str(tmp_path / "settings.ini"))
    assert reloaded.get("monitor_interval") == 11
    assert isinstance(reloaded.get("monitor_interval"), int)
    assert reloaded.get("notifications") is False


def test_invalid_language_and_theme_fall_back(tmp_path: Path) -> None:
    settings = AppSettings(path=str(tmp_path / "settings.ini"))
    settings.set_language("xx")
    settings.set_theme("neon")
    assert settings.get("language") == "ru"
    assert settings.get("theme") == "dark"


def test_changed_signal_and_reset(tmp_path: Path) -> None:
    settings = AppSettings(path=str(tmp_path / "settings.ini"))
    seen: list[tuple[str, object]] = []
    settings.changed.connect(lambda key, value: seen.append((key, value)))
    settings.set("theme", "light")
    assert seen[-1] == ("theme", "light")
    settings.reset()
    assert settings.get("theme") == "dark"
