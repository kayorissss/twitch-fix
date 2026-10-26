"""Базовая модель проверок: сериализация, статусы, защита от исключений."""
from __future__ import annotations

from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status, overall_status
from src.core.diagnostics import all_checks


class ExplodingCheck(BaseCheck):
    id = "explode"
    title_ru = "Падающая"
    title_en = "Exploding"

    def run(self) -> CheckResult:
        raise RuntimeError("boom")


class HealthyCheck(BaseCheck):
    id = "healthy"
    title_ru = "Рабочая"
    title_en = "Healthy"
    fix_id = "dns"

    def run(self) -> CheckResult:
        return self.result(Status.OK, "OK", "OK", details=["fine"], data={"x": 1})


def test_safe_run_converts_exception_to_error() -> None:
    result = ExplodingCheck().safe_run()
    assert result.status == Status.ERROR
    assert "boom" in result.summary
    assert result.duration_ms >= 0


def test_result_default_fix_id_and_explicit_none() -> None:
    assert HealthyCheck().run().fix_id == "dns"
    assert HealthyCheck().safe_run().fix_id == "dns"
    assert HealthyCheck().result(Status.OK, "a", "b", fix_id=None).fix_id is None


def test_check_result_roundtrip() -> None:
    result = HealthyCheck().run()
    restored = CheckResult.from_dict(result.to_dict())
    assert restored.id == result.id
    assert restored.status == Status.OK
    assert restored.data == {"x": 1}


def test_overall_status_uses_worst_result() -> None:
    results = [
        CheckResult("a", "a", "a", Status.OK, "ok", "ok"),
        CheckResult("b", "b", "b", Status.WARNING, "warn", "warn"),
        CheckResult("c", "c", "c", Status.ERROR, "err", "err"),
    ]
    assert overall_status(results) == Status.ERROR
    assert overall_status([]) == Status.INFO


def test_registry_contains_13_checks() -> None:
    checks = all_checks()
    assert len(checks) == 13
    assert len({check.id for check in checks}) == 13
