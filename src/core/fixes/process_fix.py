"""Исправление №9: остановка конфликтующих программ.

Закрываем ТОЛЬКО процессы из категорий DPI-обход / локальный прокси / VPN,
которые были обнаружены диагностикой. Антивирусы и системные службы не
трогаются. Пользователь подтверждает действие в UI.
"""
from __future__ import annotations

from src.config.constants import SAFE_TO_TERMINATE
from src.core.fixes.base_fix import BaseFix, FixResult


class ProcessFix(BaseFix):
    id = "process"
    title_ru = "Закрыть конфликтующие программы"
    title_en = "Close conflicting software"
    description_ru = (
        "Мягко завершить процессы DPI-обход / прокси / VPN из категорий с конфликтом. "
        "Антивирусы не затрагиваются."
    )
    description_en = (
        "Gracefully stop DPI-bypass / proxy / VPN processes involved in conflicts. "
        "Antivirus engines are never touched."
    )
    requires_admin = False
    dangerous = True

    def apply(self, dry_run: bool = False) -> FixResult:
        import psutil  # noqa: PLC0415

        groups: dict[str, list[str]] = self.context.get("groups", {}) if self.context else {}
        targets: list[str] = []
        for category in SAFE_TO_TERMINATE:
            targets.extend(groups.get(category, []))
        targets = list(dict.fromkeys(target.lower() for target in targets))
        details = [f"candidate processes: {', '.join(targets[:15]) if targets else 'none'}"]
        if self.backup:
            self.backup.manifest["processes_to_terminate"] = targets
            self.backup._flush()
        if dry_run:
            return self.result(
                True,
                f"Будет закрыто процессов: {len(targets)}",
                f"Would close {len(targets)} processes",
                details=details,
            )
        if not targets:
            return self.result(True, "Закрывать нечего", "Nothing to close", details=details)

        stopped = 0
        for process in psutil.process_iter(["name"], ad_value=""):
            name = str(process.info.get("name") or "").lower()
            if not any(name.startswith(target.removesuffix(".exe")) for target in targets):
                continue
            try:
                process.terminate()  # мягкое завершение, не kill
                stopped += 1
                details.append(f"terminated: {name} (pid={process.pid})")
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError) as exc:
                details.append(f"skip {name}: {exc}")
        return self.result(
            True,
            f"Закрыто процессов: {stopped}",
            f"Closed {stopped} processes",
            details=details,
            needs_restart=True,
        )
