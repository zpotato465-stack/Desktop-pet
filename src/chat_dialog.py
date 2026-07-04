"""Chat dialog — talk to the duck. Frameless, rounded, animated."""

import os
import threading

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QWidget, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QSize
from PySide6.QtGui import QColor, QPixmap, QPainter, QFont

from paths import get_resource_path


def _load_avatar(size: int) -> QPixmap:
    try:
        path = get_resource_path(os.path.join("assets", "duck_idle_proc.png"))
        px = QPixmap(path)
        if not px.isNull():
            return px.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    except Exception:
        pass
    return QPixmap()


class TypingIndicator(QWidget):
    """Three bouncing dots shown while the duck 'thinks'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 34)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start(self):
        self._timer.start(140)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _advance(self):
        self._phase = (self._phase + 1) % 6
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # bubble background
        p.setBrush(QColor(49, 50, 68))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 14, 14)
        # dots
        for i in range(3):
            up = 4 if (self._phase % 3) == i else 0
            p.setBrush(QColor(205, 214, 244))
            cx = 14 + i * 15
            p.drawEllipse(QPoint(cx, 17 - up), 4, 4)
        p.end()


class MessageBubble(QLabel):
    def __init__(self, text: str, is_duck: bool):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setMaximumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        if is_duck:
            self.setStyleSheet("""
                background-color: #313244; color: #e8e8f0;
                border-radius: 16px; border-top-left-radius: 5px;
                padding: 11px 15px; font-size: 13px;
            """)
        else:
            self.setStyleSheet("""
                background-color: #f9c95a; color: #3a2e0f;
                border-radius: 16px; border-bottom-right-radius: 5px;
                padding: 11px 15px; font-size: 13px; font-weight: 600;
            """)


WINDOW_STYLE = """
QWidget#card {
    background-color: #1e1e2e;
    border-radius: 18px;
}
QScrollArea { background: transparent; border: none; }
QWidget#chatArea { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QLineEdit {
    background-color: #313244; color: #cdd6f4;
    border: 2px solid #45475a; border-radius: 18px;
    padding: 11px 16px; font-size: 13px;
}
QLineEdit:focus { border-color: #f9c95a; }
QPushButton#send {
    background-color: #f9c95a; color: #1e1e2e;
    border: none; border-radius: 18px;
    font-size: 16px; font-weight: bold; min-width: 44px; min-height: 44px;
}
QPushButton#send:hover { background-color: #fab387; }
QPushButton#send:disabled { background-color: #45475a; color: #6c7086; }
QPushButton#close {
    background: transparent; color: #cdd6f4;
    border: none; font-size: 17px; font-weight: bold;
    min-width: 28px; min-height: 28px; border-radius: 14px;
}
QPushButton#close:hover { background-color: #45343a; color: #f38ba8; }
"""


class ChatDialog(QDialog):
    message_sent = Signal(str, str)
    # Bridges the Gemini worker thread back onto the GUI thread. Emitting a
    # signal is thread-safe; calling QTimer.singleShot from a plain Python
    # thread is NOT (no event loop there), so responses could vanish.
    _response_ready = Signal(str, str)

    def __init__(self, gemini_client, parent=None):
        super().__init__(parent)
        self.gemini = gemini_client
        self._thinking = False
        self._typing = None
        self._drag_pos = None
        self._response_ready.connect(self._handle_response)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(440, 580)
        self._build_ui()

        QTimer.singleShot(250, lambda: self._add_duck_message(
            "QUACK! Hey there! What's on your mind? 🦆"
        ))

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(WINDOW_STYLE)
        outer.addWidget(card)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        # Chat scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_area = QWidget()
        self.chat_area.setObjectName("chatArea")
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setContentsMargins(14, 14, 14, 14)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_area)
        layout.addWidget(self.scroll, stretch=1)

        layout.addLayout(self._build_input())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("""
            background-color: #f9c95a;
            border-top-left-radius: 18px; border-top-right-radius: 18px;
        """)
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 8, 12, 8)

        avatar = QLabel()
        av = _load_avatar(44)
        if not av.isNull():
            avatar.setPixmap(av)
        else:
            avatar.setText("🦆")
            avatar.setStyleSheet("font-size: 28px;")
        avatar.setFixedSize(46, 46)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(avatar)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        name = QLabel("Quackers")
        name.setStyleSheet("color: #3a2e0f; font-size: 16px; font-weight: bold; background: transparent;")
        status = QLabel("● online · your desktop duck")
        status.setStyleSheet("color: #7a6420; font-size: 10px; background: transparent;")
        title_box.addWidget(name)
        title_box.addWidget(status)
        h.addLayout(title_box)
        h.addStretch()

        close = QPushButton("✕")
        close.setObjectName("close")
        close.setStyleSheet("""
            QPushButton { background: transparent; color: #3a2e0f; border: none;
                          font-size: 16px; font-weight: bold; border-radius: 14px;
                          min-width: 28px; min-height: 28px; }
            QPushButton:hover { background-color: rgba(0,0,0,0.12); }
        """)
        close.clicked.connect(self.accept)
        h.addWidget(close, alignment=Qt.AlignmentFlag.AlignTop)

        self._header = header
        return header

    def _build_input(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(14, 10, 14, 16)
        row.setSpacing(10)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Talk to Quackers…")
        self.input_field.returnPressed.connect(self._send)
        row.addWidget(self.input_field)
        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.send_btn)
        return row

    # ── Drag the frameless window via the header ───────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and \
           self._header.geometry().contains(self._header.mapFromGlobal(e.globalPosition().toPoint())):
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Messages ───────────────────────────────────────────────────────────────
    def _add_duck_message(self, text: str):
        row = QHBoxLayout()
        row.setSpacing(8)
        icon = QLabel()
        av = _load_avatar(26)
        if not av.isNull():
            icon.setPixmap(av)
        else:
            icon.setText("🦆")
        icon.setFixedWidth(28)
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(icon)
        row.addWidget(MessageBubble(text, is_duck=True))
        row.addStretch()
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _add_user_message(self, text: str):
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(MessageBubble(text, is_duck=False))
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _show_typing(self):
        self._typing_row = QHBoxLayout()
        self._typing_row.setSpacing(8)
        icon = QLabel()
        av = _load_avatar(26)
        if not av.isNull():
            icon.setPixmap(av)
        icon.setFixedWidth(28)
        self._typing = TypingIndicator()
        self._typing.start()
        self._typing_row.addWidget(icon)
        self._typing_row.addWidget(self._typing)
        self._typing_row.addStretch()
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, self._typing_row)
        self._scroll_to_bottom()

    def _remove_typing(self):
        if not self._typing:
            return
        for i in range(self._typing_row.count()):
            w = self._typing_row.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.chat_layout.removeItem(self._typing_row)
        self._typing = None

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    # ── Send / receive ─────────────────────────────────────────────────────────
    def _send(self):
        if self._thinking:
            return
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._add_user_message(text)
        self._set_thinking(True)
        self._show_typing()
        threading.Thread(target=self._get_response, args=(text,), daemon=True).start()

    def _get_response(self, user_text: str):
        try:
            response = self.gemini.chat(user_text)
        except Exception as e:
            response = f"QUACK! Something went wrong: {str(e)[:80]}"
        self._response_ready.emit(user_text, response)

    def _handle_response(self, user_text: str, response: str):
        self._remove_typing()
        self._add_duck_message(response)
        self._set_thinking(False)
        self.input_field.setFocus()
        self.message_sent.emit(user_text, response)

    def _set_thinking(self, thinking: bool):
        self._thinking = thinking
        self.send_btn.setEnabled(not thinking)
        self.input_field.setEnabled(not thinking)
