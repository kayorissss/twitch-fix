"""Проверка №5: HTTP-ответы сайта и GraphQL API.

GET https://www.twitch.tv с реальным User-Agent, поиск провайдерской заглушки
в HTML, затем POST к gql.twitch.tv (тот самый запрос, который часто ломается).
"""
from __future__ import annotations

import requests

from src.config.constants import BLOCK_PAGE_MARKERS, GQL_QUERY, GQL_URL, TWITCH_WEB_CLIENT_ID, USER_AGENT
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status

SITE_URL = "https://www.twitch.tv"


def looks_like_block_page(html: str, status_code: int) -> str | None:
    """Вернуть маркер блокировки, если HTML похож на заглушку провайдера."""
    lowered = html.lower()
    for marker in BLOCK_PAGE_MARKERS:
        if marker in lowered:
            return marker
    if status_code in (403, 451) or (status_code == 200 and len(html) < 5000):
        return f"suspicious HTTP {status_code} / short body ({len(html)} bytes)"
    return None


class HTTPCheck(BaseCheck):
    id = "http"
    title_ru = "HTTP-ответ"
    title_en = "HTTP response"
    icon = "browser"
    fix_id = "proxy"
    timeout = 18.0

    def run(self) -> CheckResult:
        details: list[str] = []
        data: dict[str, object] = {}
        problems: list[str] = []

        try:
            response = requests.get(
                SITE_URL,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                timeout=6.0,
                allow_redirects=True,
            )
            html = response.text[:200_000]
            details.append(f"GET {SITE_URL} -> {response.status_code} ({len(response.content)} bytes)")
            details.append(f"final URL: {response.url}")
            data["site_status"] = response.status_code
            data["site_bytes"] = len(response.content)
            if response.status_code >= 400:
                problems.append(f"site HTTP {response.status_code}")
            marker = looks_like_block_page(html, response.status_code)
            if marker:
                problems.append(f"block page marker: {marker}")
                data["block_marker"] = marker
                details.append(f"BLOCK-PAGE MARKER: {marker}")
            if "twitch" not in html.lower():
                problems.append("HTML does not contain 'twitch'")
                details.append("warning: HTML does not contain 'twitch'")
        except requests.RequestException as exc:
            details.append(f"GET {SITE_URL} failed: {exc}")
            problems.append(f"site request failed: {type(exc).__name__}")
            data["site_error"] = str(exc)

        if self.cancelled():
            return self.result(Status.SKIPPED, "Проверка прервана", "Check cancelled", details=details, data=data, fix_id=None)

        try:
            gql = requests.post(
                GQL_URL,
                headers={
                    "Client-ID": TWITCH_WEB_CLIENT_ID,
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                },
                json={"query": GQL_QUERY},
                timeout=6.0,
            )
            details.append(f"POST {GQL_URL} -> {gql.status_code} ({len(gql.content)} bytes)")
            data["gql_status"] = gql.status_code
            if gql.status_code >= 500:
                problems.append(f"GraphQL HTTP {gql.status_code}")
            elif gql.status_code in (401, 403):
                details.append("GraphQL rejected Client-ID (Twitch may have rotated it)")
            elif gql.status_code == 200 and "errors" in gql.text.lower() and '"data"' not in gql.text:
                details.append("GraphQL returned errors object")
        except requests.RequestException as exc:
            details.append(f"POST {GQL_URL} failed: {exc}")
            problems.append(f"GraphQL request failed: {type(exc).__name__}")
            data["gql_error"] = str(exc)

        if not problems:
            return self.result(
                Status.OK,
                "Сайт и GraphQL API отвечают корректно",
                "Website and GraphQL API respond correctly",
                details=details,
                data=data,
                fix_id=None,
            )
        block = data.get("block_marker")
        status = Status.ERROR if block or len(problems) == 2 else Status.WARNING
        return self.result(
            status,
            f"Проблемы с HTTP: {', '.join(problems[:2])}",
            f"HTTP problems: {', '.join(problems[:2])}",
            details=details + ["problems: " + "; ".join(problems)],
            data=data,
        )
