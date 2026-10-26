"""Генератор отчёта: форматы, экранирование, сохранение, короткая версия."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.diagnostics.base_check import CheckResult, Status
from src.core.fixes.base_fix import FixResult
from src.core.history import History
from src.core.report_generator import ReportGenerator
from src.utils.system_info import SystemInfo


@pytest.fixture
def generator(tmp_path: Path) -> ReportGenerator:
    results = [
        CheckResult("hosts", "Файл hosts", "Hosts file", Status.ERROR,
                    "Найдено <script>alert(1)</script>", "Found <script>",
                    details=["L4: 0.0.0.0 twitch.tv"], data={}, fix_id="hosts"),
        CheckResult("dns", "DNS", "DNS", Status.OK, "OK", "OK", details=["1.1.1.1"]),
    ]
    fixes = [FixResult("hosts", True, "Готово", "Done", details=["backup: ok"])]
    history = History(path=tmp_path / "history.jsonl")
    history.add(ok=True, score=100)
    history.add(ok=False, score=40, issues=["hosts"])
    return ReportGenerator(
        results=results,
        system=SystemInfo(os="Windows", release="11", architecture="AMD64"),
        fixes=fixes,
        history=history,
        language="ru",
    )


def test_markdown_contains_sections_and_system(generator: ReportGenerator) -> None:
    text = generator.to_markdown()
    assert "# TwitchFix" in text
    assert "Windows" in text
    assert "Файл hosts" in text
    assert "Результаты проверок" in text
    assert "Исправлено" in text or "hosts" in text
    assert "24h" in text


def test_html_escapes_user_content(generator: ReportGenerator) -> None:
    html = generator.to_html()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "TwitchFix" in html


def test_plain_and_share_are_non_empty(generator: ReportGenerator) -> None:
    assert "[ERROR" in generator.to_plain()
    assert "TwitchFix v" in generator.share_text()
    assert "hosts" in generator.share_text()


def test_save_uses_extension(tmp_path: Path, generator: ReportGenerator) -> None:
    md = generator.save(tmp_path / "report.md")
    html = generator.save(tmp_path / "report.html")
    txt = generator.save(tmp_path / "report.txt")
    assert md.exists() and html.exists() and txt.exists()
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert md.read_text(encoding="utf-8").startswith("# TwitchFix")
