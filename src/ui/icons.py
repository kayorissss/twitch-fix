"""Векторные иконки, рисуемые QPainter (без QtSvg и внешних файлов).

Каждая иконка — набор примитивов в координатной сетке 24×24; один и тот же
код используется для кнопок title bar, сайдбара, карточек и системного трея.
"""
from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from src.config.constants import DARK


class _Canvas:
    """Мини-DSL для рисования в нормализованных координатах 0..24."""

    def __init__(self, painter: QPainter, rect: QRectF) -> None:
        self.painter = painter
        self.scale = min(rect.width(), rect.height()) / 24.0
        self.ox = rect.left() + (rect.width() - 24 * self.scale) / 2
        self.oy = rect.top() + (rect.height() - 24 * self.scale) / 2

    def point(self, x: float, y: float) -> QPointF:
        return QPointF(self.ox + x * self.scale, self.oy + y * self.scale)

    def line(self, *points: tuple[float, float]) -> None:
        if len(points) < 2:
            return
        path = QPainterPath()
        path.moveTo(self.point(*points[0]))
        for item in points[1:]:
            path.lineTo(self.point(*item))
        self.painter.drawPath(path)

    def polygon(self, *points: tuple[float, float]) -> None:
        self.line(*points, points[0])

    def rect(self, x: float, y: float, w: float, h: float, radius: float = 2.0) -> None:
        top_left = self.point(x, y)
        self.painter.drawRoundedRect(
            QRectF(top_left, self.point(x + w, y + h)), radius * self.scale, radius * self.scale
        )

    def ellipse(self, cx: float, cy: float, rx: float, ry: float | None = None) -> None:
        ry = rx if ry is None else ry
        self.painter.drawEllipse(
            QRectF(self.point(cx - rx, cy - ry), self.point(cx + rx, cy + ry))
        )


def _draw(canvas: _Canvas, name: str, brush: bool = False) -> None:
    """Нарисовать иконку по имени. Неизвестные имена ->-info-круг."""
    c = canvas
    if name == "home":
        c.polygon((3, 11), (12, 4), (21, 11))
        c.rect(5.5, 11, 13, 9, 1.5)
        c.line((10, 20), (10, 15), (14, 15), (14, 20))
    elif name == "search":
        c.ellipse(10.5, 10.5, 6)
        c.line((15, 15), (20, 20))
    elif name == "wrench":
        c.line((14.5, 4), (19, 8.5), (9.5, 18), (5, 18), (5, 13.5), (14.5, 4))
        c.ellipse(17.5, 6.5, 2)
    elif name == "report":
        c.rect(5, 3, 14, 18, 2)
        c.line((8.5, 8), (15.5, 8), (8.5, 12), (15.5, 12), (8.5, 16), (13, 16))
    elif name == "settings":
        c.ellipse(12, 12, 3)
        for angle in range(0, 360, 45):
            import math  # noqa: PLC0415

            rad = math.radians(angle)
            c.line(
                (12 + 6 * math.cos(rad), 12 + 6 * math.sin(rad)),
                (12 + 9 * math.cos(rad), 12 + 9 * math.sin(rad)),
            )
    elif name == "chevron":
        c.line((9, 5), (16, 12), (9, 19))
    elif name == "chevron_down":
        c.line((5, 9), (12, 16), (19, 9))
    elif name == "minimize":
        c.line((5, 12), (19, 12))
    elif name == "maximize":
        c.rect(5, 5, 14, 14, 1.5)
    elif name == "restore":
        c.rect(8, 5, 11, 11, 1.5)
        c.line((8, 8), (5, 8), (5, 19), (16, 19), (16, 16))
    elif name == "close":
        c.line((6, 6), (18, 18))
        c.line((18, 6), (6, 18))
    elif name == "compact":
        c.rect(6, 4, 12, 16, 1.5)
        c.line((9, 7), (9, 17), (15, 7), (15, 17))
    elif name == "fullscreen":
        c.line((4, 9), (4, 4), (9, 4), (15, 4), (20, 4), (20, 9), (20, 15), (20, 20), (15, 20), (9, 20), (4, 20), (4, 15))
    elif name == "file":
        c.polygon((6, 3), (14, 3), (18, 7), (18, 21), (6, 21))
        c.line((14, 3), (14, 7), (18, 7), (9, 12), (15, 12), (9, 16), (15, 16))
    elif name == "globe":
        c.ellipse(12, 12, 9)
        c.line((3, 12), (21, 12), (12, 3), (12, 21), (6, 7), (18, 7), (6, 17), (18, 17))
    elif name == "lock":
        c.rect(5, 10, 14, 11, 2)
        c.line((8, 10), (8, 7), (12, 4), (16, 7), (16, 10))
        c.ellipse(12, 15, 1.2)
    elif name == "browser":
        c.rect(3, 4, 18, 16, 2)
        c.line((3, 9), (21, 9), (6, 6.5), (6.6, 6.5))
    elif name == "shield":
        c.polygon((12, 3), (20, 6), (20, 12), (12, 21), (4, 12), (4, 6))
        c.line((9, 12), (11.5, 14.5), (16, 9.5))
    elif name == "plug":
        c.rect(7, 3, 10, 7, 1.5)
        c.line((9, 3), (9, 2), (15, 2), (15, 3), (12, 10), (12, 17), (9, 21), (7, 19), (12, 17), (17, 21), (15, 19))
    elif name == "clock":
        c.ellipse(12, 12, 9)
        c.line((12, 7), (12, 12), (16, 14))
    elif name == "route":
        c.ellipse(6, 6, 2)
        c.ellipse(18, 18, 2)
        c.line((8, 6), (16, 6), (16, 16), (8, 16), (8, 18), (16, 18))
    elif name == "network":
        c.rect(3, 14, 7, 6, 1)
        c.rect(14, 14, 7, 6, 1)
        c.rect(9, 4, 6, 5, 1)
        c.line((6.5, 14), (12, 14), (12, 9), (17.5, 14), (17.5, 14))
    elif name == "apps":
        for x in (4, 10, 16):
            for y in (4, 10, 16):
                c.rect(x, y, 4, 4, 1)
    elif name == "pulse":
        c.line((2, 12), (7, 12), (9, 6), (13, 19), (16, 12), (22, 12))
    elif name == "video":
        c.rect(3, 6, 12, 12, 2)
        c.polygon((15, 10), (21, 6), (21, 18), (15, 14))
    elif name == "check":
        c.line((5, 12), (10, 17), (19, 6))
    elif name == "cross":
        c.line((6, 6), (18, 18))
        c.line((18, 6), (6, 18))
    elif name == "warning":
        c.polygon((12, 3), (22, 20), (2, 20))
        c.line((12, 9), (12, 14))
        c.ellipse(12, 17, 0.8)
    elif name == "info":
        c.ellipse(12, 12, 9)
        c.line((12, 11), (12, 16))
        c.ellipse(12, 7.5, 0.8)
    elif name == "copy":
        c.rect(8, 8, 12, 12, 1.5)
        c.line((16, 8), (16, 5), (4, 5), (4, 16), (8, 16))
    elif name == "save":
        c.rect(4, 4, 16, 16, 2)
        c.rect(7, 4, 10, 6, 1)
        c.rect(7, 14, 10, 6, 1)
        c.line((11, 4), (11, 9))
    elif name == "share":
        c.ellipse(6, 12, 2.5)
        c.ellipse(18, 6, 2.5)
        c.ellipse(18, 18, 2.5)
        c.line((8.5, 10.8), (15.5, 7.2), (8.5, 13.2), (15.5, 16.8))
    elif name == "rocket":
        c.line((6, 15), (10, 11), (10, 6), (18, 3), (15, 11), (10, 11), (6, 15), (6, 18), (9, 18))
        c.ellipse(14.5, 7.5, 1.2)
    elif name == "play":
        c.polygon((7, 4), (20, 12), (7, 20))
    elif name == "stop":
        c.rect(6, 6, 12, 12, 1.5)
    elif name == "trash":
        c.rect(5, 7, 14, 14, 1.5)
        c.line((3, 7), (21, 7), (9, 7), (9, 4), (15, 4), (15, 7), (10, 11), (10, 17), (14, 11), (14, 17))
    elif name == "link":
        c.line((10, 14), (14, 10), (9, 7), (7, 9), (11, 5), (15, 9), (17, 7), (19, 9), (15, 13), (17, 15), (13, 19))
    elif name == "refresh":
        c.line((20, 8), (20, 13), (15, 13), (4, 16), (4, 11), (9, 11))
    elif name == "folder":
        c.polygon((3, 6), (9, 6), (11, 8), (21, 8), (21, 20), (3, 20))
    elif name == "sun":
        c.ellipse(12, 12, 4.5)
        for angle in range(0, 360, 45):
            import math  # noqa: PLC0415

            rad = math.radians(angle)
            c.line(
                (12 + 7 * math.cos(rad), 12 + 7 * math.sin(rad)),
                (12 + 9.5 * math.cos(rad), 12 + 9.5 * math.sin(rad)),
            )
    elif name == "moon":
        c.line((18, 15), (14, 19), (9, 18), (6, 14), (6, 9), (9, 5), (14, 5), (12, 7), (10, 11), (12, 15), (16, 17), (18, 15))
    else:
        c.ellipse(12, 12, 9)
        c.line((12, 11), (12, 16))
        c.ellipse(12, 7.5, 0.8)


@lru_cache(maxsize=256)
def icon_pixmap(name: str, color: str = DARK.text, size: int = 24) -> QPixmap:
    """Вернуть QPixmap с иконкой (результат кешируется)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.4, size / 15.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    _draw(_Canvas(painter, QRectF(0, 0, size, size)), name)
    painter.end()
    return pixmap


def icon(name: str, color: str = DARK.text, size: int = 24) -> QIcon:
    """Вернуть QIcon для кнопок и меню."""
    return QIcon(icon_pixmap(name, color, size))


def app_logo_pixmap(size: int = 128) -> QPixmap:
    """Логотип приложения: фиолетовый градиент + глитч-пузырь."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    rect = QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#a970ff"))
    gradient.setColorAt(0.45, QColor("#9146ff"))
    gradient.setColorAt(1.0, QColor("#5a1fc4"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawRoundedRect(rect, size * 0.22, size * 0.22)

    # Белый «чат-пузырь» с глитч-полосками.
    painter.setBrush(QBrush(QColor("#ffffff")))
    path = QPainterPath()
    path.moveTo(size * 0.28, size * 0.24)
    path.lineTo(size * 0.74, size * 0.24)
    path.lineTo(size * 0.74, size * 0.60)
    path.lineTo(size * 0.56, size * 0.60)
    path.lineTo(size * 0.42, size * 0.76)
    path.lineTo(size * 0.42, size * 0.60)
    path.lineTo(size * 0.28, size * 0.60)
    path.closeSubpath()
    painter.drawPath(path)
    painter.setBrush(QBrush(QColor("#9146ff")))
    painter.drawRoundedRect(QRectF(size * 0.39, size * 0.32, size * 0.06, size * 0.18), size * 0.02, size * 0.02)
    painter.drawRoundedRect(QRectF(size * 0.56, size * 0.32, size * 0.06, size * 0.18), size * 0.02, size * 0.02)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    """Иконка приложения из assets/icon.png, с fallback на процедурный логотип."""
    from src.utils.paths import resource_path  # noqa: PLC0415

    path = resource_path("assets/icon.png")
    result = QIcon(str(path)) if path.exists() else QIcon()
    if result.isNull():
        result = QIcon(app_logo_pixmap(128))
    return result
