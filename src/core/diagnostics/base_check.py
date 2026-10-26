"""Абстрактный класс проверки и модель результата.

Каждая проверка — отдельный модуль с классом-наследником BaseCheck. Метод
``run()`` выполняется в QThreadPool и обязан вернуть CheckResult; ``safe_run``
гарантирует, что любое исключение превратится в результат со статусом ERROR,
а не в падение приложения.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, ClassVar

from src.utils.logger import get_logger

log = get_logger(__name__)

_UNSET = object()  # sentinel: «взять fix_id из класса»


class Status(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    SKIPPED = "skipped"
    RUNNING = "running"

    @property
    def is_problem(self) -> bool:
        return self in (Status.WARNING, Status.ERROR)


@dataclass
class CheckResult:
    """Результат одной проверки (сериализуется в историю и отчёт)."""

    id: str
    title: str
    title_en: str
    status: Status
    summary: str
    summary_en: str
    details: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    fix_id: str | None = None
    duration_ms: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_problem(self) -> bool:
        return self.status.is_problem

    def summary_for(self, language: str) -> str:
        return self.summary if language == "ru" else (self.summary_en or self.summary)

    def title_for(self, language: str) -> str:
        return self.title if language == "ru" else (self.title_en or self.title)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CheckResult":
        values = dict(payload)
        values["status"] = Status(values.get("status", "info"))
        known = {key for key in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{key: value for key, value in values.items() if key in known})


_SEVERITY: dict[Status, int] = {
    Status.OK: 0, Status.INFO: 0, Status.SKIPPED: 0, Status.RUNNING: 0,
    Status.WARNING: 1, Status.ERROR: 2,
}


def overall_status(results: list[CheckResult]) -> Status:
    """Общий статус по всем проверкам: худший результат побеждает."""
    if not results:
        return Status.INFO
    return max((item.status for item in results), key=lambda status: _SEVERITY[status])


class BaseCheck(ABC):
    """Базовый класс проверки.

    ``cancelled`` — функция, которую движок устанавливает для корректной
    остановки длинных сетевых операций между шагами.
    """

    id: ClassVar[str] = "base"
    title_ru: ClassVar[str] = "Проверка"
    title_en: ClassVar[str] = "Check"
    icon: ClassVar[str] = "shield"
    fix_id: ClassVar[str | None] = None
    timeout: ClassVar[float] = 20.0

    def __init__(self, cancelled: Callable[[], bool] | None = None) -> None:
        self.cancelled = cancelled or (lambda: False)
        self.logger = get_logger(f"check.{self.id}")

    @abstractmethod
    def run(self) -> CheckResult:
        """Выполнить проверку. Должна быть устойчивой к ошибкам сети."""

    def result(
        self,
        status: Status,
        summary_ru: str,
        summary_en: str,
        details: list[str] | None = None,
        data: dict[str, Any] | None = None,
        fix_id: Any = _UNSET,
    ) -> CheckResult:
        """Собрать результат с локализованными заголовками.

        ``fix_id`` по умолчанию берётся из класса; ``None`` отключает
        предложение исправления для конкретного результата.
        """
        return CheckResult(
            id=self.id,
            title=self.title_ru,
            title_en=self.title_en,
            status=status,
            summary=summary_ru,
            summary_en=summary_en,
            details=details or [],
            data=data or {},
            fix_id=self.fix_id if fix_id is _UNSET else fix_id,
        )

    def safe_run(self) -> CheckResult:
        """Обернуть ``run()``: замер времени, логирование, защита от падений."""
        started = time.perf_counter()
        self.logger.info("Check started")
        try:
            result = self.run()
        except Exception as exc:  # ни одна проверка не должна уронить приложение
            self.logger.exception("Check crashed: %s", exc)
            result = self.result(
                Status.ERROR,
                f"Проверка завершилась с ошибкой: {exc}",
                f"Check failed with an error: {exc}",
                details=[f"{type(exc).__name__}: {exc}"],
            )
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        self.logger.info(
            "Check finished: status=%s duration=%d ms", result.status.value, result.duration_ms
        )
        return result
