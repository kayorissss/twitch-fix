"""Проверка №1: файл hosts.

Ищет ВСЕ строки, содержащие twitch/ttvnw/usher/video-weaver/jtvnw/
live-video/cloudfront, показывает номера строк и пытается определить, какая
программа их добавила (zapret, AdGuard, GoodbyeDPI, BlockCheck ...).
"""
from __future__ import annotations

import sys
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.config.constants import (
    DEFAULT_HOSTS_PATHS,
    HOSTS_KEYWORDS,
    HOSTS_TOOL_SIGNATURES,
)
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status


@dataclass(frozen=True)
class HostEntry:
    """Одна подозрительная строка hosts."""

    line_no: int
    raw: str
    ip: str
    domains: str
    keyword: str
    tool: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def hosts_path() -> Path:
    """Путь к системному hosts для текущей ОС (переопределяется в тестах)."""
    key = "nt" if sys.platform == "win32" else "posix"
    return Path(DEFAULT_HOSTS_PATHS[key])


def _read_text(path: Path) -> tuple[str, str]:
    """Прочитать hosts с учётом BOM и cp1251, вернуть (текст, кодировка)."""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


def _guess_tool(comments: Iterable[str], ip: str) -> str:
    """Определить источник строки по комментариям и типу IP."""
    text = " ".join(comments).lower()
    for tool, signatures in HOSTS_TOOL_SIGNATURES.items():
        if any(signature in text for signature in signatures):
            return tool
    if ip in ("0.0.0.0", "127.0.0.1", "::1"):
        return "Ручная блокировка / adblock"
    return "Неизвестно"


def parse_hosts(path: str | Path) -> list[HostEntry]:
    """Вернуть все twitch-related записи из файла hosts.

    Чистая функция: работает с любым путём, не требует прав администратора.
    """
    source = Path(path)
    if not source.exists():
        return []
    text, _ = _read_text(source)
    entries: list[HostEntry] = []
    recent_comments: deque[str] = deque(maxlen=6)

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            recent_comments.append(stripped)
            continue
        body = stripped.split("#", 1)[0].strip()
        lower = body.lower()
        keyword = next((word for word in HOSTS_KEYWORDS if word in lower), "")
        if not keyword:
            continue
        parts = body.split()
        ip = parts[0] if parts else ""
        domains = " ".join(parts[1:]) if len(parts) > 1 else ""
        comment = stripped.split("#", 1)[1] if "#" in stripped else ""
        entries.append(
            HostEntry(
                line_no=line_no,
                raw=raw_line,
                ip=ip,
                domains=domains[:200],
                keyword=keyword,
                tool=_guess_tool(list(recent_comments) + [comment], ip),
            )
        )
    return entries


class HostsCheck(BaseCheck):
    id = "hosts"
    title_ru = "Файл hosts"
    title_en = "Hosts file"
    icon = "file"
    fix_id = "hosts"
    timeout = 5.0

    def run(self) -> CheckResult:
        path = hosts_path()
        self.logger.info("Reading hosts: %s", path)
        if not path.exists():
            return self.result(
                Status.WARNING,
                "Не удалось найти файл hosts",
                "Could not find the hosts file",
                details=[f"path: {path}"],
                fix_id=None,
            )
        try:
            entries = parse_hosts(path)
        except OSError as exc:
            return self.result(
                Status.ERROR,
                f"Нет доступа к файлу hosts: {exc}",
                f"Cannot read hosts file: {exc}",
                details=[f"path: {path}", f"error: {exc}"],
            )

        details = [f"path: {path}"]
        for entry in entries[:40]:
            details.append(
                f"L{entry.line_no}: {entry.raw.strip()[:120]}  [{entry.keyword}, {entry.tool}]"
            )
        if len(entries) > 40:
            details.append(f"... and {len(entries) - 40} more lines")
        if not entries:
            details.append("twitch-related entries: 0")

        data = {
            "hosts_path": str(path),
            "entries": [entry.as_dict() for entry in entries],
            "tools": sorted({entry.tool for entry in entries}),
        }
        if not entries:
            return self.result(
                Status.OK,
                "Подозрительных записей нет — hosts чист",
                "No suspicious entries — hosts file is clean",
                details=details,
                data=data,
                fix_id=None,
            )

        # cloudfront используется не только Twitch — такие строки лишь предупреждение.
        only_cloudfront = all(entry.keyword == "cloudfront" for entry in entries)
        status = Status.WARNING if only_cloudfront else Status.ERROR
        return self.result(
            status,
            f"Найдено {len(entries)} twitch-записей в hosts",
            f"Found {len(entries)} Twitch-related hosts entries",
            details=details
            + [
                f"possible sources: {', '.join(data['tools']) or 'unknown'}",
                "These lines override DNS and usually cause ERR_CONNECTION_* errors.",
            ],
            data=data,
        )
