"""First-run setup and settings dialog."""

import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap


STYLE = """
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QLabel {
    color: #cdd6f4;
    font-size: 13px;
}
QLabel#title {
    font-size: 20px;
    font-weight: bold;
    color: #f9e2af;
}
QLabel#subtitle {
    color: #a6adc8;
    font-size: 12px;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 2px solid #45475a;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QPushButton#primary {
    background-color: #f9e2af;
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton#primary:hover {
    background-color: #fab387;
}
QPushButton#secondary {
    background-color: transparent;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 13px;
}
QPushButton#secondary:hover {
    border-color: #6c7086;
    color: #cdd6f4;
}
"""


class SetupDialog(QDialog):
    def __init__(self, current_key: str = "", parent=None):
        super().__init__(parent)
        self.api_key = current_key
        self.setWindowTitle("Duck Pet Setup")
        self.setFixedSize(480, 380)
        self.setStyleSheet(STYLE)
        self._build_ui(current_key)

    def _load_duck(self, size: int):
        try:
            from main import get_resource_path
            path = get_resource_path(os.path.join("assets", "duck_wave_proc.png"))
            px = QPixmap(path)
            if not px.isNull():
                return px.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
        return None

    def _build_ui(self, current_key: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(14)

        # Actual duck sprite (falls back to emoji)
        duck_img = QLabel()
        duck_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        px = self._load_duck(84)
        if px is not None and not px.isNull():
            duck_img.setPixmap(px)
        else:
            duck_img.setText("🦆")
            duck_img.setStyleSheet("font-size: 56px;")
        layout.addWidget(duck_img)

        # Title
        title = QLabel("Duck Desktop Pet")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Duck That Carries You Over A Disproportionately Small Gap")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #45475a;")
        layout.addWidget(line)

        layout.addSpacing(4)

        # Instructions
        instructions = QLabel(
            "To enable AI chat, enter your <b>Google Gemini API key</b>.<br>"
            "Get one free at <b>aistudio.google.com</b>"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #a6adc8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(instructions)

        # API key input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIza...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if current_key:
            self.key_input.setText(current_key)
        layout.addWidget(self.key_input)

        # Show/hide toggle
        show_btn = QPushButton("Show key")
        show_btn.setObjectName("secondary")
        show_btn.setFixedWidth(100)
        show_btn.clicked.connect(self._toggle_visibility)
        self._showing = False
        show_row = QHBoxLayout()
        show_row.addStretch()
        show_row.addWidget(show_btn)
        layout.addLayout(show_row)
        self._show_btn = show_btn

        layout.addStretch()

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        cancel_btn = QPushButton("Skip (no AI)")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Let's Quack!")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _toggle_visibility(self):
        self._showing = not self._showing
        if self._showing:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Hide key")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Show key")

    def _accept(self):
        key = self.key_input.text().strip()
        if not key:
            self.error_label.setText("Please enter an API key (or click 'Skip').")
            return
        if not key.startswith("AI") or len(key) < 20:
            self.error_label.setText("That doesn't look like a valid Gemini key.")
            return
        self.api_key = key
        self.accept()
