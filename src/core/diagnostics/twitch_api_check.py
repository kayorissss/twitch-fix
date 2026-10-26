"""Проверка №13: доступность сайта, GraphQL API, видео CDN и чата.

Раздельно проверяет четыре подсистемы Twitch, чтобы точно сказать, что именно
не работает: сайт / API / видео / чат. WebSocket-чат проверяется «сырым»
handshake без дополнительных зависимостей.
"""
from __future__ import annotations

import base64
import os
import socket
import ssl

import requests

from src.config.constants import GQL_QUERY, GQL_URL, TWITCH_WEB_CLIENT_ID, USER_AGENT
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status

CHAT_HOST = "irc-ws.chat.twitch.tv"
VIDEO_URL = f"https://usher.ttvnw.net/api/channel/hls/twitch.m3u8?client_id={TWITCH_WEB_CLIENT_ID}"


def websocket_handshake(host: str, port: int = 443, timeout: float = 4.0) -> tuple[bool, str]:
    """Проверить WebSocket upgrade до IRC-чата Twitch. Возвращает (ok, статус)."""
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET / HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            context = ssl.create_default_context()
            with context.wrap_socket(raw, server_hostname=host) as tls:
                tls.settimeout(timeout)
                tls.sendall(request.encode("ascii"))
                response = tls.recv(256).decode("latin-1", errors="replace")
        first = response.splitlines()[0] if response else "empty response"
        return "101" in first, first[:120]
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


class TwitchAPICheck(BaseCheck):
    id = "twitch_api"
    title_ru = "Twitch API / видео / чат"
    title_en = "Twitch API / video / chat"
    icon = "video"
    fix_id = "proxy"
    timeout = 25.0

    def _probe(self, name: str, method: str, url: str, **kwargs: object) -> tuple[bool, str]:
        try:
            response = (
                requests.post(url, timeout=5.0, **kwargs)  # type: ignore[arg-type]
                if method == "POST"
                else requests.get(url, timeout=5.0, **kwargs)  # type: ignore[arg-type]
            )
            ok = response.status_code < 500 and response.status_code not in (0,)
            return ok, f"HTTP {response.status_code} ({len(response.content)} bytes)"
        except requests.RequestException as exc:
            return False, f"{type(exc).__name__}: {str(exc)[:100]}"

    def run(self) -> CheckResult:
        headers = {
            "Client-ID": TWITCH_WEB_CLIENT_ID,
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        }
        checks: dict[str, tuple[bool, str]] = {}
        checks["site"] = self._probe("site", "GET", "https://www.twitch.tv", headers=headers)
        if self.cancelled():
            return self.result(Status.SKIPPED, "Проверка прервана", "Check cancelled", fix_id=None)
        checks["api"] = self._probe("api", "POST", GQL_URL, headers=headers, json={"query": GQL_QUERY})
        checks["video"] = self._probe("video", "GET", VIDEO_URL, headers=headers)
        chat_ok, chat_status = websocket_handshake(CHAT_HOST)
        checks["chat"] = (chat_ok, chat_status)

        details = [f"{name:6s}: {'OK' if ok else 'FAIL'} — {status}" for name, (ok, status) in checks.items()]
        broken = [name for name, (ok, _) in checks.items() if not ok]
        data = {
            "subsystems": {name: {"ok": ok, "status": status} for name, (ok, status) in checks.items()},
            "broken": broken,
        }
        if not broken:
            return self.result(
                Status.OK,
                "Сайт, API, видео и чат доступны",
                "Site, API, video and chat are all reachable",
                details=details,
                data=data,
                fix_id=None,
            )
        status = Status.ERROR if len(broken) >= 2 else Status.WARNING
        return self.result(
            status,
            f"Не работает: {', '.join(broken)}",
            f"Not working: {', '.join(broken)}",
            details=details
            + [
                "gql.twitch.tv failures usually mean DNS/proxy/DPI interference.",
                "Video CDN and chat use different hosts: check them separately in DNS/TCP results.",
            ],
            data=data,
        )
