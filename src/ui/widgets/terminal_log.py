"""Лог в стиле терминала: моноширинный шрифт, цветные уровни, лимит строк."""
from __future__ import annotations

import html
import time

from PyQt6.QtWidgets import QPlainTextEdit

LEVEL_COLORS = {
    "info": "#b9c4e8",
    "ok": "#00ff88",
    "warn": "#ffa502",
    "err": "#ff4757",
    "debug": "#7f8bb5",
}


class TerminalLog(QPlainTextEdit):
    """Цветной лог диагностики/исправлений с авто-прокруткой."""

    def __init__(self, parent=None, max_blocks: int = 500) -> None:
        super().__init__(parent)
        self.setObjectName("terminalLog")
        self.setReadOnly(True)
        self.setMaximumBlockCount(max_blocks)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def append_line(self, message: str, level: str = "info", timestamp: bool = True) -> None:
        color = LEVEL_COLORS.get(level, LEVEL_COLORS["info"])
        prefix = f"<span style='color:#6f7aa3'>[{time.strftime('%H:%M:%S')}]</span> " if timestamp else ""
        tag = {"ok": "OK  ", "warn": "WARN", "err": "ERR ", "debug": "    "}.get(level, "INFO")
        self.appendHtml(
            f"{prefix}<span style='color:{color}'>{html.escape(tag)}</span> "
            f"<span style='color:{color}'>{html.escape(str(message))}</span>"
        )
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_log(self) -> None:
        self.clear()

    def set_level_color(self, level: str, color: str) -> None:
        LEVEL_COLORS[level] = color
