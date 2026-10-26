"""Абстрактное исправление и результат его применения.

Контракт: ``apply()`` никогда не бросает исключение наружу (движок всё равно
ловит их, но лучше вернуть внятный FixResult), обязательно делает бэкап через
``BackupManager`` и честно сообщает, нужны ли права администратора.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from src.utils.admin import is_admin
from src.utils.backup import BackupManager
from src.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class FixResult:
    """Итог одного исправления."""

    fix_id: str
    success: bool
    message: str
    message_en: str
    details: list[str] = field(default_factory=list)
    backup_path: str = ""
    needs_admin: bool = False
    needs_restart: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseFix(ABC):
    """Базовый класс исправления."""

    id: ClassVar[str] = "base"
    title_ru: ClassVar[str] = "Исправление"
    title_en: ClassVar[str] = "Fix"
    description_ru: ClassVar[str] = ""
    description_en: ClassVar[str] = ""
    requires_admin: ClassVar[bool] = False
    windows_only: ClassVar[bool] = False
    dangerous: ClassVar[bool] = False

    def __init__(self, backup: BackupManager | None = None) -> None:
        self.backup = backup
        #: Данные проверки, которая предложила это исправление (entries, issuer …).
        self.context: dict[str, Any] = {}
        self.logger = get_logger(f"fix.{self.id}")

    def title_for(self, language: str) -> str:
        return self.title_ru if language == "ru" else self.title_en

    def description_for(self, language: str) -> str:
        return self.description_ru if language == "ru" else self.description_en

    def can_apply(self) -> tuple[bool, str]:
        """Можно ли применять исправление в текущей среде."""
        import sys  # noqa: PLC0415

        if self.windows_only and sys.platform != "win32":
            return False, "Доступно только в Windows / Windows-only"
        if self.requires_admin and not is_admin():
            return False, "Требуются права администратора / Administrator rights required"
        return True, ""

    def result(
        self,
        success: bool,
        message_ru: str,
        message_en: str,
        details: list[str] | None = None,
        needs_admin: bool = False,
        needs_restart: bool = False,
    ) -> FixResult:
        return FixResult(
            fix_id=self.id,
            success=success,
            message=message_ru,
            message_en=message_en,
            details=details or [],
            backup_path=str(self.backup.directory) if self.backup else "",
            needs_admin=needs_admin,
            needs_restart=needs_restart,
        )

    @abstractmethod
    def apply(self, dry_run: bool = False) -> FixResult:
        """Применить исправление (``dry_run`` — только показать план)."""

    def safe_apply(self, dry_run: bool = False) -> FixResult:
        """Защитная обёртка: логирование, перехват исключений, проверка прав."""
        self.logger.info("Fix started (dry_run=%s, admin=%s)", dry_run, is_admin())
        allowed, reason = self.can_apply() if not dry_run else (True, "")
        if not allowed:
            self.logger.warning("Fix blocked: %s", reason)
            return self.result(
                False, reason, reason, needs_admin="admin" in reason.lower()
            )
        try:
            outcome = self.apply(dry_run=dry_run)
        except Exception as exc:
            self.logger.exception("Fix crashed: %s", exc)
            outcome = self.result(
                False,
                f"Ошибка при исправлении: {exc}",
                f"Fix failed with error: {exc}",
                details=[f"{type(exc).__name__}: {exc}"],
            )
        self.logger.info("Fix finished: success=%s — %s", outcome.success, outcome.message)
        return outcome
