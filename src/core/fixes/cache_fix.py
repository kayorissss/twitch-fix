"""Исправление №4: очистка кэша браузеров для доменов Twitch.

Удаляет файлы кэша (Chrome/Edge/Brave/Opera/Firefox), которые заняты не будут:
браузер рекомендуется закрыть заранее. Также выполняется ipconfig /flushdns.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from src.core.diagnostics.browser_check import profile_dirs
from src.core.fixes.base_fix import BaseFix, FixResult
from src.utils.system_info import run_command

CACHE_DIR_NAMES = {"cache", "cache_data", "code cache", "gpucache", "cache2"}


def cache_directories() -> list[Path]:
    """Список каталогов кэша во всех профилях всех найденных браузеров."""
    found: list[Path] = []
    for paths in profile_dirs().values():
        for profile in paths:
            try:
                for directory in profile.rglob("*"):
                    if directory.is_dir() and directory.name.lower() in CACHE_DIR_NAMES:
                        found.append(directory)
            except OSError:
                continue
    return found


def clear_cache(dry_run: bool = False) -> tuple[int, int, list[str]]:
    """Удалить содержимое каталогов кэша. Возвращает (файлов, каталогов, ошибки)."""
    files = directories = 0
    errors: list[str] = []
    for directory in cache_directories():
        if dry_run:
            try:
                files += sum(1 for item in directory.rglob("*") if item.is_file())
            except OSError:
                pass
            continue
        for child in list(directory.iterdir()) if directory.exists() else []:
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                    directories += 1
                else:
                    child.unlink(missing_ok=True)
                    files += 1
            except OSError as exc:
                errors.append(f"{child.name}: {exc}")
    return files, directories, errors[:20]


class CacheFix(BaseFix):
    id = "cache"
    title_ru = "Очистить кэш браузера и DNS"
    title_en = "Clear browser and DNS cache"
    description_ru = "Удалить повреждённый кэш Chrome/Edge/Firefox/Brave и сбросить кэш DNS. Закройте браузер перед запуском."
    description_en = "Remove corrupt Chrome/Edge/Firefox/Brave cache and flush DNS. Close browsers first."
    requires_admin = False

    def apply(self, dry_run: bool = False) -> FixResult:
        if self.backup:
            self.backup.manifest["cache_action"] = (
                "Browser cache files are removed (a cache is disposable and not backed up)."
            )
            self.backup._flush()
        files, directories, errors = clear_cache(dry_run=dry_run)
        details = [
            f"cache files {'to delete' if dry_run else 'deleted'}: {files}",
            f"subdirectories removed: {directories}",
        ]
        if not dry_run:
            code, _, _ = run_command(["ipconfig", "/flushdns"], timeout=8)
            details.append(f"ipconfig /flushdns -> code {code}")
        details.extend(f"warning: {error}" for error in errors)
        if dry_run:
            return self.result(True, f"Будет удалено файлов кэша: {files}", f"Would delete {files} cache files", details=details)
        return self.result(
            True,
            f"Кэш очищен ({files} файлов)",
            f"Cache cleared ({files} files)",
            details=details,
            needs_restart=True,
        )
