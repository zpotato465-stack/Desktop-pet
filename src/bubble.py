"""Speech bubble widget for the duck pet — polished comic style."""

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QRectF, QPoint
from PySide6.QtGui import (QPainter, QColor, QPainterPath, QPen, QBrush,
                            QFont, QFontMetrics, QLinearGradient)

# Warm, duck-themed palette
BUBBLE_TOP = QColor(255, 255, 248)
BUBBLE_BOTTOM = QColor(255, 246, 209)
BUBBLE_BORDER = QColor(232, 178, 58)
SHADOW = QColor(40, 30, 10, 70)
TEXT_COLOR = QColor(60, 45, 15)

FONT_FAMILY = "Verdana"
FONT_SIZE = 11
MAX_WIDTH = 280
PAD_X = 16
PAD_Y = 12
POINTER_H = 16
POINTER_W = 18
MARGIN = 14          # room for the drop shadow / glow
RADIUS = 16


class SpeechBubble(QWidget):
    def __init__(self, text: str, parent_duck: QWidget):
        super().__init__(parent=None)
        self.text = text
        self.duck = parent_duck
        self._lines: list[str] = []
        self._bubble_w = 0
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
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _compute_layout(self):
        font = QFont(FONT_FAMILY, FONT_SIZE)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        fm = QFontMetrics(font)
        self._font = font
        self._fm = fm

        words = self.text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if fm.horizontalAdvance(test) > MAX_WIDTH - PAD_X * 2 and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        if not lines:
            lines = [self.text]
        self._lines = lines

        self._bubble_w = max(fm.horizontalAdvance(l) for l in lines) + PAD_X * 2
        self._bubble_h = len(lines) * fm.height() + PAD_Y * 2

        total_w = self._bubble_w + MARGIN * 2
        total_h = self._bubble_h + POINTER_H + MARGIN * 2
        self.resize(total_w, total_h)

    def _position(self):
        duck_global = self.duck.mapToGlobal(self.duck.rect().topLeft())
        duck_cx = duck_global.x() + self.duck.width() // 2

        # BUBBLE_ANCHOR lets the duck report where its head actually is
        # (its window has transparent padding above the sprite).
        anchor = getattr(self.duck, 'BUBBLE_ANCHOR', 0)
        bx = duck_cx - self.width() // 2
        by = duck_global.y() + anchor - self.height() + MARGIN

        screen = QApplication.primaryScreen().geometry()
        bx = max(6, min(bx, screen.width() - self.width() - 6))
        by = max(6, by)
        self.move(bx, by)
        # Remember where the pointer should aim (relative to bubble window)
        self._pointer_x = max(MARGIN + RADIUS + POINTER_W,
                              min(duck_cx - bx, self.width() - MARGIN - RADIUS))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        body = QRectF(MARGIN, MARGIN, self._bubble_w, self._bubble_h)
        px = self._pointer_x
        py = MARGIN + self._bubble_h

        def build_path(dx=0, dy=0):
            path = QPainterPath()
            path.addRoundedRect(body.translated(dx, dy), RADIUS, RADIUS)
            tri = QPainterPath()
            tri.moveTo(px - POINTER_W / 2 + dx, py + dy)
            tri.lineTo(px + POINTER_W / 2 + dx, py + dy)
            tri.lineTo(px + dx, py + POINTER_H + dy)
            tri.closeSubpath()
            return path.united(tri)

        # Drop shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(SHADOW))
        painter.drawPath(build_path(0, 4))

        # Bubble body (vertical gradient)
        grad = QLinearGradient(0, MARGIN, 0, MARGIN + self._bubble_h)
        grad.setColorAt(0.0, BUBBLE_TOP)
        grad.setColorAt(1.0, BUBBLE_BOTTOM)
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(BUBBLE_BORDER, 2.5))
        painter.drawPath(build_path())

        # Text
        painter.setPen(TEXT_COLOR)
        painter.setFont(self._font)
        y = MARGIN + PAD_Y + self._fm.ascent()
        for line in self._lines:
            painter.drawText(int(MARGIN + PAD_X), int(y), line)
            y += self._fm.height()

        painter.end()

    def show_animated(self):
        self.show()
        self._fade_in.start()

    def reposition(self):
        self._position()
        self.update()

    def close_animated(self, callback=None):
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(280)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        if callback:
            fade.finished.connect(callback)
        fade.finished.connect(self.close)
        fade.start()
        self._fade_out = fade
