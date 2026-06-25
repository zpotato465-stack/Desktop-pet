"""Speech bubble widget for the duck pet."""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import (QPainter, QColor, QPainterPath, QPen, QBrush,
                            QFont, QFontMetrics)

BUBBLE_BG = QColor(255, 253, 220, 235)
BUBBLE_BORDER = QColor(200, 170, 60, 255)
TEXT_COLOR = QColor(40, 30, 10)
FONT_FAMILY = "Arial"
FONT_SIZE = 11
MAX_WIDTH = 280
PADDING = 12
POINTER_H = 16


class SpeechBubble(QWidget):
    def __init__(self, text: str, parent_duck: QWidget):
        super().__init__(parent=None)
        self.text = text
        self.duck = parent_duck
        self._lines: list[str] = []
        self._bubble_h = 0

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._compute_layout()
        self._position()

        self.setWindowOpacity(0.0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _compute_layout(self):
        font = QFont(FONT_FAMILY, FONT_SIZE)
        fm = QFontMetrics(font)
        self._font = font
        self._fm = fm

        words = self.text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if fm.horizontalAdvance(test) > MAX_WIDTH - PADDING * 2:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        if not lines:
            lines = [self.text]
        self._lines = lines

        content_w = max(fm.horizontalAdvance(l) for l in lines) + PADDING * 2
        content_h = len(lines) * fm.height() + PADDING * 2
        self._bubble_h = content_h
        total_h = content_h + POINTER_H

        self.resize(content_w, total_h)

    def _position(self):
        duck_global = self.duck.mapToGlobal(self.duck.rect().topLeft())
        duck_cx = duck_global.x() + self.duck.width() // 2

        bx = duck_cx - self.width() // 2
        by = duck_global.y() - self.height() - 6

        screen = QApplication.primaryScreen().geometry()
        bx = max(6, min(bx, screen.width() - self.width() - 6))
        by = max(6, by)

        self.move(bx, by)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw bubble body
        body = QRect(0, 0, self.width(), self._bubble_h)
        path = QPainterPath()
        path.addRoundedRect(body, 10, 10)

        painter.setBrush(QBrush(BUBBLE_BG))
        painter.setPen(QPen(BUBBLE_BORDER, 2))
        painter.drawPath(path)

        # Draw pointer (triangle at bottom center)
        px = self.width() // 2
        py = self._bubble_h
        tri = QPainterPath()
        tri.moveTo(px - 8, py)
        tri.lineTo(px + 8, py)
        tri.lineTo(px, py + POINTER_H)
        tri.closeSubpath()

        painter.setBrush(QBrush(BUBBLE_BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(tri)

        # Border for pointer sides only
        painter.setPen(QPen(BUBBLE_BORDER, 2))
        painter.drawLine(px - 8, py, px, py + POINTER_H)
        painter.drawLine(px + 8, py, px, py + POINTER_H)

        # Draw text
        painter.setPen(TEXT_COLOR)
        painter.setFont(self._font)
        y = PADDING + self._fm.ascent()
        for line in self._lines:
            painter.drawText(PADDING, y, line)
            y += self._fm.height()

        painter.end()

    def show_animated(self):
        self.show()
        self._fade_in.start()

    def reposition(self):
        """Call this if the duck moves while the bubble is visible."""
        self._position()

    def close_animated(self, callback=None):
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(300)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        if callback:
            fade.finished.connect(callback)
        fade.finished.connect(self.close)
        fade.start()
        self._fade_out = fade
