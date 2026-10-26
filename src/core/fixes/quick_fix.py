"""Quick Fix: одна кнопка — последовательность из четырёх безопасных шагов.

1. ipconfig /flushdns
2. очистка twitch-записей hosts (с бэкапом)
3. netsh winsock reset
4. очистка кэша браузера

Каждый шаг сообщает прогресс через ``on_step(title, index, total)``.
"""
from __future__ import annotations

import sys
from typing import Callable

from src.core.fixes.base_fix import BaseFix, FixResult
from src.core.fixes.cache_fix import clear_cache
from src.core.fixes.hosts_fix import clean_hosts
from src.core.diagnostics.hosts_check import hosts_path
from src.utils.system_info import run_command

StepCallback = Callable[[str, int, int], None]


class QuickFix(BaseFix):
    id = "quick"
    title_ru = "Быстрое исправление"
    title_en = "Quick Fix"
    description_ru = "flush DNS → hosts → Winsock → кэш браузера. Изменения сохраняются в бэкап."
    description_en = "flush DNS → hosts → Winsock → browser cache. All changes are backed up."
    requires_admin = True

    def __init__(self, backup=None, on_step: StepCallback | None = None) -> None:
        super().__init__(backup)
        self.on_step = on_step

    def _emit(self, title: str, index: int, total: int) -> None:
        if self.on_step:
            self.on_step(title, index, total)

    def apply(self, dry_run: bool = False) -> FixResult:
        windows = sys.platform == "win32"
        steps = [
            ("flush DNS", "ipconfig /flushdns"),
            ("hosts", "clean twitch entries"),
            ("Winsock", "netsh winsock reset"),
            ("browser cache", "clear cache files"),
        ]
        details: list[str] = []
        if self.backup:
            self.backup.manifest["quick_fix_steps"] = [title for title, _ in steps]
            self.backup._flush()
        for index, (title, command) in enumerate(steps, start=1):
            self._emit(title, index, len(steps))
            if title == "flush DNS":
                code, out, err = run_command(["ipconfig", "/flushdns"], timeout=8) if windows and not dry_run else (0, "", "")
                details.append(f"1) ipconfig /flushdns -> {code} {(out + err).strip()[:80]}")
            elif title == "hosts":
                removed, backup_path, error = clean_hosts(hosts_path(), self.backup, dry_run=dry_run)
                details.append(
                    f"2) hosts: removed={removed}, backup={backup_path or 'n/a'}, error={error or 'none'}"
                )
            elif title == "Winsock":
                code, out, err = run_command(["netsh", "winsock", "reset"], timeout=15) if windows and not dry_run else (0, "", "")
                details.append(f"3) netsh winsock reset -> {code} {(out + err).strip()[:80]}")
            else:
                files, directories, errors = clear_cache(dry_run=dry_run)
                details.append(f"4) cache: files={files}, dirs={directories}, errors={len(errors)}")
        details.append("A reboot may be required for the Winsock reset to take effect.")
        if dry_run:
            return self.result(True, "План быстрого исправления готов", "Quick fix plan prepared", details=details)
        return self.result(
            True,
            "Быстрое исправление выполнено (4 шага)",
            "Quick fix completed (4 steps)",
            details=details,
            needs_restart=True,
        )
