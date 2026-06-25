"""Chat dialog — talk to the duck."""

import threading

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

STYLE = """
QDialog {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QScrollArea {
    background-color: #181825;
    border: none;
    border-radius: 8px;
}
QWidget#chatArea {
    background-color: #181825;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 2px solid #45475a;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QPushButton#send {
    background-color: #f9e2af;
    color: #1e1e2e;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 70px;
}
QPushButton#send:hover {
    background-color: #fab387;
}
QPushButton#send:disabled {
    background-color: #45475a;
    color: #6c7086;
}
"""


class MessageBubble(QLabel):
    def __init__(self, text: str, is_duck: bool):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setMaximumWidth(320)

        if is_duck:
            self.setStyleSheet("""
                background-color: #313244;
                color: #cdd6f4;
                border-radius: 14px 14px 14px 4px;
                padding: 10px 14px;
                font-size: 13px;
            """)
        else:
            self.setStyleSheet("""
                background-color: #89b4fa;
                color: #1e1e2e;
                border-radius: 14px 14px 4px 14px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
            """)


class ChatDialog(QDialog):
    message_sent = Signal(str, str)  # (user_msg, duck_response)

    def __init__(self, gemini_client, parent=None):
        super().__init__(parent)
        self.gemini = gemini_client
        self._thinking = False

        self.setWindowTitle("Talk to Quackers 🦆")
        self.setFixedSize(420, 540)
        self.setStyleSheet(STYLE)
        self._build_ui()

        QTimer.singleShot(300, lambda: self._add_duck_message(
            "QUACK! Hey there! What's on your mind? 🦆"
        ))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("🦆  Quackers")
        header.setStyleSheet("color: #f9e2af; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Chat scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.chat_area = QWidget()
        self.chat_area.setObjectName("chatArea")
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_area)
        layout.addWidget(self.scroll, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type to Quackers...")
        self.input_field.returnPressed.connect(self._send)
        input_row.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("send")
        self.send_btn.clicked.connect(self._send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

    def _add_duck_message(self, text: str):
        row = QHBoxLayout()
        row.setSpacing(8)
        icon = QLabel("🦆")
        icon.setFixedWidth(24)
        icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        bubble = MessageBubble(text, is_duck=True)
        row.addWidget(icon)
        row.addWidget(bubble)
        row.addStretch()
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _add_user_message(self, text: str):
        row = QHBoxLayout()
        row.setSpacing(8)
        bubble = MessageBubble(text, is_duck=False)
        row.addStretch()
        row.addWidget(bubble)
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _send(self):
        if self._thinking:
            return
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self._add_user_message(text)
        self._set_thinking(True)
        self._add_duck_message("*thinking noises* ...")
        self._pending_msg_index = self.chat_layout.count() - 2

        threading.Thread(target=self._get_response, args=(text,), daemon=True).start()

    def _get_response(self, user_text: str):
        try:
            response = self.gemini.chat(user_text)
        except Exception as e:
            response = f"QUACK! Something went wrong: {str(e)[:80]}"

        QTimer.singleShot(0, lambda: self._handle_response(user_text, response))

    def _handle_response(self, user_text: str, response: str):
        # Remove the "thinking..." bubble and add real response
        item = self.chat_layout.itemAt(self._pending_msg_index)
        if item and item.layout():
            layout = item.layout()
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            self.chat_layout.removeItem(item)

        self._add_duck_message(response)
        self._set_thinking(False)
        self.message_sent.emit(user_text, response)

    def _set_thinking(self, thinking: bool):
        self._thinking = thinking
        self.send_btn.setEnabled(not thinking)
        self.input_field.setEnabled(not thinking)
