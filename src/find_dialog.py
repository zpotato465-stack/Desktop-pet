"""Styled 'find a file' prompt — matches the app's card look."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

CARD_STYLE = """
QWidget#card { background-color: #1e1e2e; border-radius: 18px; }
QLabel { color: #cdd6f4; background: transparent; }
QLabel#title { font-size: 17px; font-weight: bold; color: #f9c95a; }
QLabel#hint { color: #7f849c; font-size: 11px; }
QLineEdit {
    background-color: #313244; color: #cdd6f4;
    border: 2px solid #45475a; border-radius: 12px;
    padding: 11px 14px; font-size: 13px;
}
QLineEdit:focus { border-color: #f9c95a; }
QPushButton#primary {
    background-color: #f9c95a; color: #1e1e2e; border: none;
    border-radius: 12px; padding: 11px 22px; font-size: 13px; font-weight: bold;
}
QPushButton#primary:hover { background-color: #fab387; }
QPushButton#secondary {
    background: transparent; color: #a6adc8;
    border: 1px solid #45475a; border-radius: 12px;
    padding: 11px 22px; font-size: 13px;
}
QPushButton#secondary:hover { border-color: #6c7086; color: #cdd6f4; }
"""


class FindFileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filename = ""
        self._drag_pos = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 240)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        outer.addWidget(card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("🔍  File hunt!")
        title.setObjectName("title")
        layout.addWidget(title)

        hint = QLabel("What should Quackers track down? (music included)")
        hint.setObjectName("hint")
        layout.addWidget(hint)

        self.input = QLineEdit()
        self.input.setPlaceholderText("report.pdf   or just   report")
        self.input.returnPressed.connect(self._go)
        layout.addWidget(self.input)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel = QPushButton("Never mind")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        go = QPushButton("QUACK, GO!  🎵")
        go.setObjectName("primary")
        go.clicked.connect(self._go)
        btn_row.addWidget(go)
        layout.addLayout(btn_row)

        self.input.setFocus()

    def _go(self):
        name = self.input.text().strip()
        if name:
            self.filename = name
            self.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
