"""Main duck pet widget."""

import os
import sys
import random
import threading
from typing import Optional

import numpy as np
from PIL import Image

from PySide6.QtWidgets import QWidget, QApplication, QMenu, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QObject
from PySide6.QtGui import (QPainter, QPixmap, QImage, QColor, QFont,
                            QPainterPath, QPen, QBrush, QIcon, QCursor,
                            QAction)

from main import get_resource_path

# ── Sprite helpers ──────────────────────────────────────────────────────────

def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


def load_sprite(path: str) -> QPixmap:
    img = Image.open(path).convert("RGBA")
    return pil_to_qpixmap(img)


# ── Sprite manager ───────────────────────────────────────────────────────────

class SpriteSet:
    """Holds all animation frames for the duck."""

    def __init__(self, assets_dir: str):
        self.frames: dict[str, list[QPixmap]] = {}
        self._load(assets_dir)

    def _load(self, assets_dir: str):
        idle = load_sprite(os.path.join(assets_dir, "duck_idle_proc.png"))
        wave = load_sprite(os.path.join(assets_dir, "duck_wave_proc.png"))

        walk_frames = [
            load_sprite(os.path.join(assets_dir, f"duck_walk_{i}_proc.png"))
            for i in range(4)
        ]
        walk_left = [self._flip(f) for f in walk_frames]

        self.frames["idle"] = [idle]
        self.frames["wave"] = [wave, idle]          # alternates for talking
        self.frames["walk_right"] = walk_frames
        self.frames["walk_left"] = walk_left
        self.frames["sleep"] = [idle]
        self.frames["search"] = walk_frames         # waddle in-place

    def _flip(self, px: QPixmap) -> QPixmap:
        img = px.toImage()
        return QPixmap.fromImage(img.mirrored(True, False))

    def get(self, state: str, tick: int) -> QPixmap:
        frames = self.frames.get(state, self.frames["idle"])
        return frames[tick % len(frames)]

    @property
    def duck_width(self) -> int:
        return max(px.width() for lst in self.frames.values() for px in lst)

    @property
    def duck_height(self) -> int:
        return max(px.height() for lst in self.frames.values() for px in lst)


# ── Gemini worker (runs in QThread via signals) ───────────────────────────────

class GeminiSignals(QObject):
    result = Signal(str)


# ── Main pet widget ──────────────────────────────────────────────────────────

WIN_PAD_X = 20
WIN_PAD_Y = 40   # extra vertical room for Zs / bounce


class DuckPet(QWidget):
    _bubble_signal = Signal(str)   # thread-safe bubble trigger

    def __init__(self, api_key: str, config: dict, save_config_fn):
        super().__init__()

        self.api_key = api_key
        self.config = config
        self.save_config = save_config_fn

        # ── State ───────────────────────────────────────────────────────────
        self.state = "idle"
        self.direction = 1          # +1 = right, -1 = left
        self._tick = 0              # animation tick
        self._anim_speed = 6        # ticks per frame flip
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._idle_secs = 0
        self._bubble_cooldown = 0
        self._drag_start: Optional[QPoint] = None
        self._dragging = False

        # ── Sprites ─────────────────────────────────────────────────────────
        assets = get_resource_path("assets")
        self.sprites = SpriteSet(assets)
        dw = self.sprites.duck_width + WIN_PAD_X * 2
        dh = self.sprites.duck_height + WIN_PAD_Y * 2
        self.resize(dw, dh)

        # ── Window flags ─────────────────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Duck That Carries You Over A Disproportionately Small Gap")

        # ── Screen geometry ──────────────────────────────────────────────────
        screen = QApplication.primaryScreen().availableGeometry()
        self._sw = screen.width()
        self._sh = screen.height()
        self._sx = screen.x()
        self._sy = screen.y()

        # Start near bottom-centre
        sx = random.randint(self._sw // 4, 3 * self._sw // 4)
        sy = self._sh - dh - 60
        self.move(sx, sy)

        # ── Gemini ──────────────────────────────────────────────────────────
        self._gemini = None
        if api_key:
            try:
                from gemini import GeminiClient
                self._gemini = GeminiClient(api_key)
            except Exception:
                pass

        # ── Bubble ──────────────────────────────────────────────────────────
        self._bubble = None
        self._bubble_signal.connect(self._show_bubble_main)

        # ── System tray ──────────────────────────────────────────────────────
        self._setup_tray()

        # ── Timers ──────────────────────────────────────────────────────────
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(50)          # 20 fps

        self._move_timer = QTimer(self)
        self._move_timer.timeout.connect(self._on_move_tick)
        self._move_timer.start(50)

        self._behavior_timer = QTimer(self)
        self._behavior_timer.timeout.connect(self._on_behavior_tick)
        self._behavior_timer.start(4000)    # every 4 s

        self._peek_timer = QTimer(self)
        self._peek_timer.timeout.connect(self._peek_at_screen)
        self._peek_timer.start(random.randint(90_000, 150_000))  # 1.5-2.5 min

        # Greeting after a short delay
        QTimer.singleShot(1500, lambda: self._show_bubble_main(
            random.choice([
                "QUACK! I have arrived. Your screen is my pond now.",
                "Greetings, human! Your friendly duck overlord is here. QUACK!",
                "Hello! I'm Quackers. I'll be waddling around your desktop today.",
                "*splashes onto your desktop* QUACK QUACK! Let's go!",
            ])
        ))

    # ── Tray ────────────────────────────────────────────────────────────────

    def _setup_tray(self):
        icon_px = self.sprites.get("idle", 0).scaled(
            32, 32, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self._tray = QSystemTrayIcon(QIcon(icon_px), self)
        self._tray.setToolTip("Quackers — Duck Desktop Pet")
        menu = QMenu()
        menu.addAction("💬 Talk to Quackers", self._open_chat)
        menu.addAction("🔍 Find a file…", self._prompt_find_file)
        menu.addAction("📸 What am I doing?", self._peek_at_screen)
        menu.addSeparator()
        menu.addAction("⚙️  Settings", self._open_settings)
        menu.addAction("❌ Quit", QApplication.instance().quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self._open_chat()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self._tray.show()

    # ── Animation / movement ─────────────────────────────────────────────────

    def _on_anim_tick(self):
        self._tick += 1
        self.update()

    def _on_move_tick(self):
        if self.state == "walking":
            nx = self.x() + self._vel_x
            ny = self.y() + self._vel_y

            # Bounce off edges
            if nx < self._sx or nx > self._sx + self._sw - self.width():
                self._vel_x *= -1
                self.direction *= -1
            if ny < self._sy or ny > self._sy + self._sh - self.height():
                self._vel_y *= -1

            self.move(int(nx), int(ny))

        if self._bubble:
            try:
                self._bubble.reposition()
            except RuntimeError:
                self._bubble = None

    def _on_behavior_tick(self):
        self._idle_secs += 4
        if self._bubble_cooldown > 0:
            self._bubble_cooldown -= 4

        if self.state == "idle":
            if self._idle_secs > 300:           # 5 min → sleep
                self._set_state("sleep")
            elif random.random() < 0.35:
                self._start_walk()
            elif random.random() < 0.15 and self._bubble_cooldown <= 0:
                self._bubble_cooldown = 30
                threading.Thread(target=self._async_random_comment, daemon=True).start()

        elif self.state == "walking":
            if random.random() < 0.18:
                self._set_state("idle")

        elif self.state == "sleep":
            if random.random() < 0.08:
                self._set_state("idle")
                self._bubble_signal.emit("*yawn* Quack… was just resting my beak.")

    def _start_walk(self):
        self._set_state("walking")
        self.direction = random.choice([-1, 1])
        speed = random.uniform(1.8, 3.2)
        self._vel_x = speed * self.direction
        self._vel_y = random.choice([-0.6, 0, 0, 0.6])

    def _set_state(self, new_state: str):
        self.state = new_state
        if new_state not in ("walking", "search"):
            self._vel_x = 0.0
            self._vel_y = 0.0
        if new_state == "idle":
            self._idle_secs = 0

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Choose sprite set
        draw_state = {
            "idle":    "idle",
            "sleep":   "sleep",
            "walking": "walk_right" if self.direction > 0 else "walk_left",
            "talking": "wave",
            "search":  "search",
        }.get(self.state, "idle")

        frame_idx = self._tick // self._anim_speed
        sprite = self.sprites.get(draw_state, frame_idx)

        # Centre the sprite in the window
        x = (self.width() - sprite.width()) // 2
        y = WIN_PAD_Y + (self.sprites.duck_height - sprite.height())

        painter.drawPixmap(x, y, sprite)

        # Floating Zs while sleeping
        if self.state == "sleep":
            self._paint_zs(painter, x + sprite.width() - 10, y)

        # Searching sparkle effect
        if self.state == "search":
            self._paint_search_fx(painter)

        painter.end()

    def _paint_zs(self, painter: QPainter, ox: int, oy: int):
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        phase = self._tick % 60
        for i, letter in enumerate(["z", "Z", "Z"]):
            alpha = int(255 * abs((phase - i * 20) % 60 - 30) / 30)
            painter.setPen(QColor(160, 160, 255, max(0, alpha)))
            offset = i * 14
            painter.drawText(ox + i * 8, oy - offset, letter)

    def _paint_search_fx(self, painter: QPainter):
        phase = (self._tick % 30) / 30.0
        r = int(8 + 4 * phase)
        cx, cy = self.width() // 2 + 50, self.height() // 2
        painter.setPen(QPen(QColor(255, 220, 60, int(200 * (1 - phase))), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    # ── Mouse events ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        self._idle_secs = 0
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._dragging = False
            if self.state == "sleep":
                self._set_state("idle")
                self._bubble_signal.emit("*startled quack* I WAS AWAKE! Totally.")
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_start
            if delta.manhattanLength() > 5:
                self._dragging = True
            if self._dragging:
                self.move(self.pos() + delta)
                self._drag_start = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragging:
                self._open_chat()
            self._drag_start = None
            self._dragging = False

    # ── Context menu ─────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background-color: #313244; }
        """)
        menu.addAction("💬 Talk to Quackers", self._open_chat)
        menu.addAction("🔍 Find a file…", self._prompt_find_file)
        menu.addAction("📸 What am I doing?", self._peek_at_screen)
        menu.addSeparator()
        menu.addAction("⚙️  Settings", self._open_settings)
        menu.addAction("❌ Quit", QApplication.instance().quit)
        menu.exec(pos)

    # ── Chat ─────────────────────────────────────────────────────────────────

    def _open_chat(self):
        if not self._gemini:
            self._bubble_signal.emit("QUACK! I need a Gemini API key to chat. Right-click → Settings!")
            return
        from chat_dialog import ChatDialog
        dlg = ChatDialog(self._gemini, parent=None)
        dlg.message_sent.connect(self._on_chat_message)
        dlg.exec()

    def _on_chat_message(self, user_msg: str, duck_response: str):
        # Check for file-find intent
        if self._gemini and self._gemini.is_file_request(user_msg):
            filename = self._gemini.extract_filename(user_msg)
            if filename:
                self._do_find_file(filename)
                return
        self._set_state("talking")
        self._bubble_signal.emit(duck_response)
        QTimer.singleShot(5000, lambda: self._set_state("idle"))

    # ── File finding ─────────────────────────────────────────────────────────

    def _prompt_find_file(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            None, "Find a File 🦆",
            "What file are we hunting for? QUACK!"
        )
        if ok and name.strip():
            self._do_find_file(name.strip())

    def _do_find_file(self, filename: str):
        self._set_state("search")
        self._bubble_signal.emit(
            f"QUACK! On the case! Searching for '{filename}'… *intense waddling*"
        )

        from audio import play_search_music
        play_search_music()

        from file_ops import find_file_async, open_in_explorer
        import os

        def on_found(path: Optional[str]):
            from audio import stop_music
            stop_music()

            if path:
                msg = (f"Found it! *victory quack* \n'{os.path.basename(path)}'"
                       f"\nis in:\n{os.path.dirname(path)}")
            else:
                msg = (f"Couldn't find '{filename}'… "
                       "Opening your home folder instead. QUACK!")
                path = os.path.expanduser("~")

            open_in_explorer(path)
            self._set_state("idle")
            self._bubble_signal.emit(msg)

        find_file_async(filename, on_found=on_found)

    # ── Screen peek ──────────────────────────────────────────────────────────

    def _peek_at_screen(self):
        if self.state in ("sleep", "search"):
            return
        self._peek_timer.start(random.randint(90_000, 150_000))

        if not self._gemini:
            return
        threading.Thread(target=self._async_peek, daemon=True).start()

    def _async_peek(self):
        try:
            response = self._gemini.ask_about_screen()
            self._bubble_signal.emit(response)
        except Exception as e:
            self._bubble_signal.emit(f"QUACK! I tried to look at your screen but something went wrong. ({str(e)[:40]})")

    # ── Random comments ──────────────────────────────────────────────────────

    def _async_random_comment(self):
        if not self._gemini:
            return
        try:
            comment = self._gemini.get_random_comment()
            self._bubble_signal.emit(comment)
        except Exception:
            pass

    # ── Bubble ───────────────────────────────────────────────────────────────

    def _show_bubble_main(self, text: str):
        """Must be called on the main thread (via signal)."""
        if self._bubble:
            try:
                self._bubble.close()
            except RuntimeError:
                pass
            self._bubble = None

        from bubble import SpeechBubble
        self._bubble = SpeechBubble(text, parent_duck=self)
        self._bubble.show_animated()

        # Auto-dismiss
        display_ms = min(4000 + len(text) * 40, 9000)
        QTimer.singleShot(display_ms, self._dismiss_bubble)

    def _dismiss_bubble(self):
        if self._bubble:
            try:
                self._bubble.close_animated()
            except RuntimeError:
                pass
            self._bubble = None

    def show_bubble(self, text: str):
        """Thread-safe: can be called from any thread."""
        self._bubble_signal.emit(text)

    # ── Settings ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        from setup_dialog import SetupDialog
        from PySide6.QtWidgets import QDialog
        dlg = SetupDialog(current_key=self.api_key)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.api_key = dlg.api_key
            self.config["gemini_api_key"] = self.api_key
            self.save_config(self.config)
            if self._gemini:
                self._gemini.update_api_key(self.api_key)
            else:
                try:
                    from gemini import GeminiClient
                    self._gemini = GeminiClient(self.api_key)
                except Exception:
                    pass
            self._bubble_signal.emit("QUACK! Settings saved! I'm smarter now!")
