"""Генератор отчёта: Markdown, HTML и короткая версия «Поделиться».

Все пользовательские строки экранируются в HTML. Отчёт не содержит паролей,
токенов, Proxy-логинов (они маскируются ещё на этапе диагностики) и имён
пользователя Windows.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from src.config.constants import APP_NAME, APP_VERSION
from src.config.i18n import i18n
from src.core.diagnostics.base_check import CheckResult, Status, overall_status
from src.core.fixes.base_fix import FixResult
from src.core.history import History
from src.utils.system_info import SystemInfo, quick_system_info

STATUS_LABELS = {
    "ok": ("OK", "#00ff88"),
    "warning": ("WARN", "#ffa502"),
    "error": ("ERROR", "#ff4757"),
    "info": ("INFO", "#54a0ff"),
    "skipped": ("SKIP", "#98a2c8"),
    "running": ("...", "#9146ff"),
}


class ReportGenerator:
    """Строит отчёт из результатов диагностики и применённых исправлений."""

    def __init__(
        self,
        results: list[CheckResult] | None = None,
        system: SystemInfo | None = None,
        fixes: Iterable[FixResult] | None = None,
        history: History | None = None,
        language: str | None = None,
    ) -> None:
        self.results = results or []
        # quick_system_info не запускает консольные команды — отчёт можно
        # пересобирать прямо из UI-потока без зависаний.
        self.system = system or quick_system_info()
        self.fixes = list(fixes or [])
        self.history = history or History()
        self.language = language or i18n.language
        self.generated = datetime.now(timezone.utc).astimezone()

    @property
    def status(self) -> Status:
        return overall_status(self.results) if self.results else Status.INFO

    @property
    def issues(self) -> list[CheckResult]:
        return [item for item in self.results if item.is_problem]

    def _tr(self, key: str, *args: object) -> str:
        index = 0 if self.language == "ru" else 1
        from src.config.i18n import TR  # noqa: PLC0415

        pair = TR.get(key)
        text = pair[index] if pair else key
        try:
            return text.format(*args) if args else text
        except (IndexError, KeyError, ValueError):
            return text

    # ------------------------------------------------------------------ Markdown
    def to_markdown(self) -> str:
        ru = self.language == "ru"
        status = self.status.value.upper() if self.results else "NO DATA"
        lines = [
            f"# {APP_NAME} — {self._tr('report.title')}",
            "",
            f"**{self._tr('report.generated')}:** {self.generated.strftime('%Y-%m-%d %H:%M:%S %z')}  ",
            f"**{APP_NAME}:** v{APP_VERSION}  ",
            f"**{self._tr('report.status')}:** {status}  ",
            f"**{self._tr('report.issues', len(self.issues))}**",
            "",
            f"## {self._tr('report.section_system')}",
            "",
            "| | |",
            "|---|---|",
            f"| OS | {self.system.os} {self.system.release} |",
            f"| {self._tr('common.system')} | {self.system.architecture}, Python {self.system.python} |",
            f"| Admin | {'yes' if self.system.admin else 'no'} |",
            f"| Local IP | {self.system.local_ip or 'n/a'} |",
            f"| Gateway | {self.system.gateway or 'n/a'} |",
            f"| DNS | {', '.join(self.system.dns_servers) or 'n/a'} |",
            f"| MTU | {self.system.mtu or 'n/a'} |",
            f"| Connection | {self.system.connection_type} |",
            f"| Browsers | {', '.join(self.system.browsers) or 'n/a'} |",
            "",
            f"## {self._tr('report.section_checks')}",
            "",
            "| # | " + ("Проверка" if ru else "Check") + " | " + ("Статус" if ru else "Status")
            + " | " + ("Время" if ru else "Time") + " | " + ("Итог" if ru else "Summary") + " |",
            "|---:|---|---|---:|---|",
        ]
        for index, result in enumerate(self.results, start=1):
            summary = result.summary_for(self.language).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {index} | {result.title_for(self.language)} | {result.status.value.upper()} "
                f"| {result.duration_ms} ms | {summary} |"
            )
        lines += ["", f"### {self._tr('common.details')}", ""]
        for result in self.results:
            lines += [f"#### {result.title_for(self.language)} — {result.status.value.upper()}", "", "```text"]
            lines += [str(line).replace("`", "'")[:300] for line in (result.details or ["-"])]
            lines += ["```", ""]

        if self.fixes:
            lines += [f"## {self._tr('report.section_fixes')}", ""]
            for fix in self.fixes:
                lines.append(
                    f"- **{fix.fix_id}**: {'OK' if fix.success else 'FAIL'} — "
                    f"{fix.message if ru else fix.message_en}"
                )
                for detail in fix.details:
                    lines.append(f"  - {detail[:200]}")
            lines.append("")

        availability_24 = self.history.availability(24)
        availability_week = self.history.availability(24 * 7)
        lines += [
            f"## {self._tr('report.section_history')}",
            "",
            f"- 24h: {availability_24 if availability_24 is not None else 'n/a'}%",
            f"- 7d: {availability_week if availability_week is not None else 'n/a'}%",
            "",
            "---",
            "",
            f"*{self._tr('report.disclaimer')}*",
            "",
        ]
        return "\n".join(lines)

    # ---------------------------------------------------------------------- HTML
    def to_html(self) -> str:
        parts = [
            "<!doctype html><html lang='" + self.language + "'><head><meta charset='utf-8'>",
            f"<title>{APP_NAME} — {html.escape(self._tr('report.title'))}</title>",
            "<style>",
            "body{background:#12121f;color:#eef1ff;font:13px/1.6 'Segoe UI',Arial,sans-serif;"
            "margin:0;padding:32px;max-width:980px;margin:auto}",
            "h1,h2,h3{color:#fff}h1{font-size:26px;margin-bottom:4px}",
            ".meta{color:#98a2c8;font-size:12px;margin-bottom:26px}",
            ".card{background:#16213e;border:1px solid #2b3663;border-radius:12px;"
            "padding:16px 20px;margin-bottom:18px}",
            "table{border-collapse:collapse;width:100%;font-size:12px}",
            "td,th{border-bottom:1px solid #2b3663;padding:7px 9px;text-align:left;vertical-align:top}",
            "th{color:#98a2c8;font-weight:600}pre{white-space:pre-wrap;word-break:break-word;"
            "background:#12121f;border-radius:8px;padding:10px;font:11px Consolas,monospace;color:#b9c4e8}"
            ".chip{display:inline-block;padding:2px 9px;border-radius:20px;font-weight:700;font-size:11px;color:#12121f}",
            ".muted{color:#98a2c8}.ok{color:#00ff88}.warn{color:#ffa502}.err{color:#ff4757}",
            "</style></head><body>",
            f"<h1>{APP_NAME} — {html.escape(self._tr('report.title'))}</h1>",
            "<div class='meta'>"
            f"{html.escape(self._tr('report.generated'))}: {self.generated.strftime('%Y-%m-%d %H:%M:%S')}"
            f" &nbsp;|&nbsp; v{APP_VERSION} &nbsp;|&nbsp; {self.system.os} {html.escape(self.system.release)}"
            "</div>",
        ]
        status = self.status.value if self.results else "info"
        label, color = STATUS_LABELS.get(status, STATUS_LABELS["info"])
        parts += [
            "<div class='card'>",
            f"<h2>{html.escape(self._tr('report.section_summary'))}</h2>",
            f"<p><span class='chip' style='background:{color}'>{label}</span> &nbsp; "
            f"{html.escape(self._tr('report.issues', len(self.issues)))}</p>",
            "<table><tr><th>#</th><th>" + html.escape("Проверка" if self.language == "ru" else "Check")
            + "</th><th>" + html.escape("Статус" if self.language == "ru" else "Status")
            + "</th><th>ms</th><th>" + html.escape("Итог" if self.language == "ru" else "Summary")
            + "</th></tr>",
        ]
        for index, result in enumerate(self.results, start=1):
            label, color = STATUS_LABELS.get(result.status.value, STATUS_LABELS["info"])
            parts.append(
                f"<tr><td>{index}</td><td>{html.escape(result.title_for(self.language))}</td>"
                f"<td><span class='chip' style='background:{color}'>{label}</span></td>"
                f"<td>{result.duration_ms}</td><td>{html.escape(result.summary_for(self.language))}</td></tr>"
            )
        parts += ["</table></div>", "<div class='card'><h2>" + html.escape(self._tr('common.details')) + "</h2>"]
        for result in self.results:
            parts.append(f"<h3>{html.escape(result.title_for(self.language))}</h3>")
            parts.append("<pre>" + html.escape("\n".join(str(line)[:300] for line in result.details)) + "</pre>")
        parts.append("</div>")
        if self.fixes:
            parts.append("<div class='card'><h2>" + html.escape(self._tr('report.section_fixes')) + "</h2><ul>")
            for fix in self.fixes:
                parts.append(
                    f"<li><b>{html.escape(fix.fix_id)}</b>: "
                    f"{'OK' if fix.success else 'FAIL'} — {html.escape(fix.message)}</li>"
                )
            parts.append("</ul></div>")
        parts += [
            "<p class='muted'>" + html.escape(self._tr('report.disclaimer')) + "</p>",
            "</body></html>",
        ]
        return "".join(parts)

    def to_plain(self) -> str:
        """Текстовая версия Markdown без разметки таблиц (для .txt)."""
        lines = [f"{APP_NAME} v{APP_VERSION} — {self._tr('report.title')}", "=" * 60]
        for result in self.results:
            lines.append(
                f"[{result.status.value.upper():7s}] {result.title_for(self.language)}: "
                f"{result.summary_for(self.language)}"
            )
            lines += [f"      {line}" for line in result.details[:12]]
        return "\n".join(lines)

    def share_text(self) -> str:
        """Короткий текст для форума/поддержки (копируется кнопкой «Поделиться»)."""
        ru = self.language == "ru"
        lines = [
            f"[{APP_NAME} v{APP_VERSION}] {self.generated.strftime('%Y-%m-%d %H:%M')}",
            f"OS: {self.system.os} {self.system.release} ({self.system.architecture})",
            f"{'Статус' if ru else 'Status'}: {self.status.value.upper()} | "
            f"{'Проблем' if ru else 'Issues'}: {len(self.issues)}",
        ]
        for result in self.issues[:8]:
            lines.append(f"  - {result.title_for(self.language)}: {result.summary_for(self.language)}")
        if not self.issues:
            lines.append("  - " + ("Все проверки пройдены" if ru else "All checks passed"))
        availability = self.history.availability(24)
        if availability is not None:
            lines.append(f"{'Доступность 24ч' if ru else '24h availability'}: {availability}%")
        if self.fixes:
            lines.append(
                ("Применено исправлений" if ru else "Fixes applied") + ": "
                + ", ".join(f"{f.fix_id}={'OK' if f.success else 'FAIL'}" for f in self.fixes)
            )
        return "\n".join(lines)

    def save(self, path: str | Path) -> Path:
        """Сохранить отчёт в формате по расширению (.md, .html, .txt)."""
        destination = Path(path)
        suffix = destination.suffix.lower()
        content = self.to_html() if suffix == ".html" else (
            self.to_plain() if suffix == ".txt" else self.to_markdown()
        )
        destination.write_text(content, encoding="utf-8")
        return destination
