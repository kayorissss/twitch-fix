"""Исправление №1: удаление twitch-записей из hosts (с бэкапом).

``clean_hosts`` — чистая функция: работает с любым файлом, поэтому покрыта
тестами без прав администратора и без реального C:\\Windows.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from src.core.diagnostics.hosts_check import hosts_path, parse_hosts
from src.core.fixes.base_fix import BaseFix, FixResult
from src.utils.backup import BackupManager


def clean_hosts(
    path: str | Path,
    backup: BackupManager | None = None,
    dry_run: bool = False,
) -> tuple[int, Path | None, str]:
    """Удалить twitch-строки. Возвращает (удалено, путь бэкапа, ошибка)."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except OSError as exc:
        return 0, None, f"read: {exc}"
    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")
        encoding = "cp1251"

    entries = parse_hosts(source)
    remove_lines = {entry.line_no for entry in entries}
    if not remove_lines:
        return 0, None, ""

    newline = "\r\n" if "\r\n" in text[:4000] else "\n"
    lines = text.splitlines()
    kept = [line for number, line in enumerate(lines, start=1) if number not in remove_lines]
    new_text = newline.join(kept) + (newline if text.endswith(("\n", "\r")) else "")
    if dry_run:
        return len(remove_lines), None, ""

    backup_path = backup.backup_file(source, label=f"{source.name}.bak") if backup else None
    try:
        # Некоторые инструменты (AdGuard, zapret) выставляют read-only атрибут.
        os.chmod(source, source.stat().st_mode | stat.S_IWRITE)
        temp = source.with_name(source.name + ".twitchfix.tmp")
        temp.write_bytes(new_text.encode(encoding))
        os.replace(temp, source)
    except OSError as exc:
        return 0, backup_path, f"write: {exc}"
    return len(remove_lines), backup_path, ""


class HostsFix(BaseFix):
    id = "hosts"
    title_ru = "Очистить файл hosts"
    title_en = "Clean hosts file"
    description_ru = "Удалить все twitch/ttvnw/usher-записи, которые подменяют DNS. Оригинал сохраняется в бэкап."
    description_en = "Remove Twitch-related hosts entries that override DNS. The original file is backed up."
    requires_admin = True

    def __init__(self, backup: BackupManager | None = None, path: str | Path | None = None) -> None:
        super().__init__(backup)
        self.path = Path(path) if path else hosts_path()

    def apply(self, dry_run: bool = False) -> FixResult:
        removed, backup_path, error = clean_hosts(self.path, self.backup, dry_run=dry_run)
        details = [
            f"file: {self.path}",
            f"lines to remove: {removed}",
            f"backup: {backup_path or ('dry-run' if dry_run else 'unchanged')}",
        ]
        if error:
            return self.result(
                False,
                f"Не удалось изменить hosts: {error}",
                f"Could not update hosts: {error}",
                details=details,
                needs_admin="write" in error,
            )
        if dry_run:
            return self.result(
                True,
                f"Будет удалено строк: {removed}",
                f"Would remove {removed} lines",
                details=details,
            )
        if removed == 0:
            return self.result(
                True, "Удалять нечего — hosts уже чист", "Nothing to remove — hosts already clean", details=details
            )
        return self.result(
            True,
            f"Удалено {removed} строк из hosts",
            f"Removed {removed} hosts lines",
            details=details + ["Run `ipconfig /flushdns` (included in Quick Fix) to apply changes."],
            needs_restart=False,
        )
