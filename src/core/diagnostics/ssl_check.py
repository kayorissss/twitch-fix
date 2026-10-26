"""Проверка №4: TLS-сертификат www.twitch.tv.

Определяет издателя, срок действия и подмену сертификата антивирусом
(HTTPS-сканирование). Даже при ошибке валидации цепочки мы получаем сам
сертификат через unverified-контекст, чтобы показать издателя.
"""
from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone

from src.config.constants import ANTIVIRUS_ISSUERS
from src.core.diagnostics.base_check import BaseCheck, CheckResult, Status

HOST = "www.twitch.tv"
PORT = 443


def issuer_name(cert: dict) -> str:
    """Извлечь читаемое имя издателя из getpeercert()."""
    try:
        for rdn in cert.get("issuer", ()):
            for key, value in rdn:
                if key in ("organizationName", "commonName"):
                    return str(value)
    except (TypeError, ValueError):
        pass
    return "unknown"


def detect_av_issuer(issuer: str) -> str | None:
    """Вернуть название антивируса, если издатель похож на MITM-сертификат."""
    lowered = issuer.lower()
    for vendor in ANTIVIRUS_ISSUERS:
        if vendor.lower() in lowered:
            return vendor
    return None


def fetch_certificate(verified: bool) -> tuple[dict | None, str | None]:
    """Получить сертификат. Возвращает (cert, ошибка)."""
    context = ssl.create_default_context() if verified else ssl._create_unverified_context()
    try:
        with socket.create_connection((HOST, PORT), timeout=4.0) as raw:
            with context.wrap_socket(raw, server_hostname=HOST) as tls:
                return tls.getpeercert(), None
    except Exception as exc:  # ssl.SSLError, socket.timeout, OSError
        return None, f"{type(exc).__name__}: {exc}"


class SSLCheck(BaseCheck):
    id = "ssl"
    title_ru = "SSL сертификат"
    title_en = "SSL certificate"
    icon = "lock"
    fix_id = "ssl"
    timeout = 12.0

    def run(self) -> CheckResult:
        cert, error = fetch_certificate(verified=True)
        details: list[str] = [f"host: {HOST}:{PORT}"]
        if cert is None and error:
            details.append(f"verified handshake failed: {error}")
            cert, unverified_error = fetch_certificate(verified=False)
            if cert is None:
                return self.result(
                    Status.ERROR,
                    f"Не удалось получить сертификат: {error}",
                    f"Could not fetch certificate: {error}",
                    details=details + [f"unverified handshake: {unverified_error}"],
                    fix_id=None,
                )
            details.append("certificate obtained with verification disabled (chain is untrusted)")

        issuer = issuer_name(cert or {})
        subject = str((cert or {}).get("subject", ""))
        not_after = (cert or {}).get("notAfter", "")
        not_before = (cert or {}).get("notBefore", "")
        details.extend(
            [
                f"issuer: {issuer}",
                f"subject: {subject[:160]}",
                f"valid: {not_before} -> {not_after}",
            ]
        )
        data = {
            "issuer": issuer,
            "subject": subject,
            "not_before": not_before,
            "not_after": not_after,
            "verified": error is None,
        }

        # Срок действия в формате OpenSSL: "Aug  1 12:00:00 2026 GMT".
        days_left: int | None = None
        try:
            expires = datetime.strptime(str(not_after), "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            days_left = (expires - datetime.now(timezone.utc)).days
            details.append(f"days until expiry: {days_left}")
            data["days_left"] = days_left
        except (ValueError, TypeError):
            pass

        vendor = detect_av_issuer(issuer)
        if vendor:
            data["antivirus"] = vendor
            return self.result(
                Status.ERROR,
                f"Сертификат подменён: {vendor} (HTTPS-сканирование)",
                f"Certificate replaced by {vendor} (HTTPS scanning)",
                details=details
                + [
                    f"MITM vendor: {vendor}",
                    "Disable HTTPS/SSL scanning for twitch.tv and *.ttvnw.net in the antivirus settings.",
                ],
                data=data,
            )
        if error:
            return self.result(
                Status.ERROR,
                "Цепочка сертификата не доверенна системой",
                "Certificate chain is not trusted",
                details=details + [f"verification error: {error}"],
                data=data,
            )
        if days_left is not None and days_left < 0:
            return self.result(
                Status.ERROR,
                "Сертификат просрочен — проверьте системное время",
                "Certificate expired — check your system clock",
                details=details,
                data=data,
            )
        return self.result(
            Status.OK,
            f"Сертификат валиден, издатель: {issuer}",
            f"Certificate valid, issuer: {issuer}",
            details=details,
            data=data,
            fix_id=None,
        )
