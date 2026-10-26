"""Резервное копирование ВСЕХ изменяемых данных перед исправлением.

- файлы (hosts) копируются с сохранением содержимого и атрибутов;
- значения реестра сохраняются в JSON-манифест;
- при желании создаётся точка восстановления Windows (System Restore).

Манифест каждой операции лежит рядом с копиями: backups/<session>/manifest.json.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger
from src.utils.paths import app_dirs

log = get_logger(__name__)


def _no_window() -> int:
    """Флаг CREATE_NO_WINDOW, чтобы консольные команды не мигали окном."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class BackupManager:
    """Создаёт папку сессии, копирует файлы/реестр, пишет manifest.json."""

    def __init__(self, session: str | None = None) -> None:
        stamp = session or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.directory = app_dirs().backups / stamp
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest: dict[str, Any] = {
            "created": datetime.now().isoformat(timespec="seconds"),
            "files": [],
            "registry": [],
            "restore_point": None,
            "platform": sys.platform,
        }
        self._flush()

    def _flush(self) -> None:
        try:
            (self.directory / "manifest.json").write_text(
                json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            log.error("Cannot write backup manifest: %s", exc)

    def backup_file(self, path: str | Path, label: str | None = None) -> Path | None:
        """Скопировать файл. Возвращает путь копии или None, если файла нет."""
        source = Path(path)
        if not source.exists():
            log.warning("Backup source missing: %s", source)
            return None
        name = label or source.name
        destination = self.directory / name
        counter = 1
        while destination.exists():
            destination = self.directory / f"{destination.stem}.{counter}{destination.suffix}"
            counter += 1
        try:
            shutil.copy2(source, destination)
            self.manifest["files"].append(
                {
                    "original": str(source),
                    "backup": str(destination),
                    "bytes": source.stat().st_size,
                }
            )
            self._flush()
            log.info("Backed up %s -> %s", source, destination)
            return destination
        except OSError as exc:
            log.error("Backup of %s failed: %s", source, exc)
            return None

    def backup_registry(self, hive: str, key: str, values: list[str]) -> bool:
        """Сохранить значения реестра в JSON-манифест (только Windows)."""
        if sys.platform != "win32":
            return False
        import winreg  # noqa: PLC0415 - импорт только на Windows

        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        root = hives.get(hive.upper())
        if root is None:
            return False
        stored: dict[str, Any] = {}
        try:
            with winreg.OpenKey(root, key, 0, winreg.KEY_READ) as handle:
                for value in values:
                    try:
                        item, kind = winreg.QueryValueEx(handle, value)
                        stored[value] = {"data": item, "type": int(kind)}
                    except FileNotFoundError:
                        stored[value] = None  # значения не было — при откате удаляем
        except OSError as exc:
            log.warning("Cannot read registry %s\\%s: %s", hive, key, exc)
            return False
        self.manifest["registry"].append({"hive": hive, "key": key, "values": stored})
        self._flush()
        log.info("Backed up registry %s\\%s", hive, key)
        return True

    def create_restore_point(self, description: str = "TwitchFix autofix") -> bool:
        """Создать точку восстановления Windows (нужны права администратора).

        System Restore может быть отключён — это нормально, бэкап файлов всё
        равно остаётся основным механизмом отката.
        """
        if sys.platform != "win32":
            self.manifest["restore_point"] = "unsupported"
            self._flush()
            return False
        script = (
            "try { Checkpoint-Computer -Description "
            f"'{description}' -RestorePointType 'MODIFY_SETTINGS' "
            "-ErrorAction Stop; 'OK' } catch { 'FAIL: ' + $_.Exception.Message }"
        )
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=180, creationflags=_no_window(),
            )
            output = (proc.stdout or "").strip()
            success = "OK" in output and "FAIL" not in output
            self.manifest["restore_point"] = output or f"exit={proc.returncode}"
            self._flush()
            log.info("Restore point: %s", self.manifest["restore_point"])
            return success
        except (OSError, subprocess.SubprocessError) as exc:
            self.manifest["restore_point"] = f"error: {exc}"
            self._flush()
            log.warning("Restore point failed: %s", exc)
            return False

    def restore_file(self, original: str | Path) -> bool:
        """Откатить один файл из бэкапа (используется в тестах и вручную)."""
        original = str(original)
        for item in self.manifest["files"]:
            if item["original"] == original:
                try:
                    shutil.copy2(item["backup"], item["original"])
                    log.info("Restored %s", original)
                    return True
                except OSError as exc:
                    log.error("Restore failed: %s", exc)
        return False
