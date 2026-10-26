"""Пути приложения: данные пользователя и ресурсы внутри PyInstaller.

``resource_path`` одинаково работает в режиме разработки и в собранном
one-file exe: PyInstaller распаковывает ресурсы в ``sys._MEIPASS``.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppDirs:
    root: Path
    config: Path
    logs: Path
    backups: Path
    data: Path

    def ensure(self) -> None:
        for path in (self.config, self.logs, self.backups, self.data):
            path.mkdir(parents=True, exist_ok=True)


def _user_root() -> Path:
    override = os.environ.get("TWITCHFIX_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return Path(base) / "TwitchFix"
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / "TwitchFix"


def app_dirs() -> AppDirs:
    root = _user_root()
    dirs = AppDirs(
        root=root,
        config=root / "config",
        logs=root / "logs",
        backups=root / "backups",
        data=root / "data",
    )
    dirs.ensure()
    return dirs


def project_root() -> Path:
    """Корень репозитория (или папка с распакованными ресурсами exe)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def resource_path(relative: str) -> Path:
    """Вернуть путь к ресурсу (assets/icon.png, src/ui/styles/dark_theme.qss …).

    Порядок поиска: ресурсы PyInstaller (sys._MEIPASS) → дерево репозитория →
    sys.prefix (data_files при pip install) → папка пакета src.
    """
    candidate = project_root() / relative
    if candidate.exists():
        return candidate
    prefix_candidate = Path(sys.prefix) / relative
    if prefix_candidate.exists():
        return prefix_candidate
    # Альтернатива для установленного пакета без дерева репозитория.
    return Path(__file__).resolve().parents[1] / relative


def logs_path() -> Path:
    return app_dirs().logs / "twitchfix.log"


def history_path() -> Path:
    return app_dirs().data / "history.jsonl"
