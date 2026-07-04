"""First-run setup and settings dialog — frameless rounded card."""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from paths import get_resource_path

CARD_STYLE = """
QWidget#card {
    background-color: #1e1e2e;
    border-radius: 18px;
}
QLabel { color: #cdd6f4; font-size: 13px; background: transparent; }
QLabel#title { font-size: 21px; font-weight: bold; color: #f9c95a; }
QLabel#subtitle { color: #7f849c; font-size: 11px; }
QLabel#error { color: #f38ba8; font-size: 12px; }
QLineEdit {
    background-color: #313244; color: #cdd6f4;
    border: 2px solid #45475a; border-radius: 12px;
    padding: 11px 14px; font-size: 13px;
}
QLineEdit:focus { border-color: #f9c95a; }
QPushButton#primary {
    background-color: #f9c95a; color: #1e1e2e;
    border: none; border-radius: 12px;
    padding: 12px 26px; font-size: 14px; font-weight: bold;
}
QPushButton#primary:hover { background-color: #fab387; }
QPushButton#secondary {
    background-color: transparent; color: #a6adc8;
    border: 1px solid #45475a; border-radius: 12px;
    padding: 12px 26px; font-size: 13px;
}
QPushButton#secondary:hover { border-color: #6c7086; color: #cdd6f4; }
QPushButton#ghost {
    background: transparent; color: #7f849c; border: none;
    font-size: 12px; padding: 4px 8px;
}
QPushButton#ghost:hover { color: #cdd6f4; }
"""


class SetupDialog(QDialog):
    def __init__(self, current_key: str = "", parent=None):
        super().__init__(parent)
        self.api_key = current_key
        self._drag_pos = None

        self.setWindowTitle("Duck Pet Setup")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 560)
        self._build_ui(current_key)

    def _load_duck(self, size: int):
        try:
            path = get_resource_path(os.path.join("assets", "duck_wave_proc.png"))
            px = QPixmap(path)
            if not px.isNull():
                return px.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
        return None

    def _build_ui(self, current_key: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(CARD_STYLE)
        outer.addWidget(card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 26, 32, 26)
        layout.setSpacing(12)

        # Duck sprite (falls back to emoji)
        duck_img = QLabel()
        duck_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        px = self._load_duck(88)
        if px is not None:
            duck_img.setPixmap(px)
        else:
            duck_img.setText("🦆")
            duck_img.setStyleSheet("font-size: 56px;")
        layout.addWidget(duck_img)

        title = QLabel("Duck Desktop Pet")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Duck That Carries You Over A\nDisproportionately Small Gap")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #45475a;")
        layout.addWidget(line)

        instructions = QLabel(
            "To enable AI chat, enter your <b>Google Gemini API key</b>.<br>"
            "Get one free at <b>aistudio.google.com</b>"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(instructions)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIza…")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if current_key:
            self.key_input.setText(current_key)
        self.key_input.returnPressed.connect(self._accept)
        layout.addWidget(self.key_input)

        show_btn = QPushButton("👁 Show key")
        show_btn.setObjectName("ghost")
        show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        show_btn.clicked.connect(self._toggle_visibility)
        self._showing = False
        self._show_btn = show_btn
        show_row = QHBoxLayout()
        show_row.addStretch()
        show_row.addWidget(show_btn)
        layout.addLayout(show_row)

        layout.addStretch()

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Skip for now")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Let's Quack!  🦆")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    # Drag the frameless card anywhere
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _toggle_visibility(self):
        self._showing = not self._showing
        if self._showing:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("🙈 Hide key")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("👁 Show key")

    def _accept(self):
        key = self.key_input.text().strip()
        if not key:
            self.error_label.setText("Enter an API key, or click 'Skip for now'.")
            return
        if len(key) < 20:
            self.error_label.setText("That key looks too short — double-check it?")
            return
        self.api_key = key
        self.accept()
