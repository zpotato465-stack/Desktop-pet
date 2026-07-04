"""Main duck pet widget."""

import math
import os
import random
import threading
from typing import Optional

from PySide6.QtWidgets import QWidget, QApplication, QMenu, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QPen, QIcon

from paths import get_resource_path

MENU_STYLE = """
QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 7px 22px; border-radius: 6px; }
QMenu::item:selected { background-color: #313244; }
QMenu::separator { height: 1px; background: #45475a; margin: 5px 10px; }
"""

# ── Sprite manager ───────────────────────────────────────────────────────────

class SpriteSet:
    """Holds all animation frames for the duck."""

    def __init__(self, assets_dir: str):
        self.frames: dict[str, list[QPixmap]] = {}
        self._load(assets_dir)

    def _load(self, assets_dir: str):
        idle = QPixmap(os.path.join(assets_dir, "duck_idle_proc.png"))
        wave = QPixmap(os.path.join(assets_dir, "duck_wave_proc.png"))

        walk_frames = [
            QPixmap(os.path.join(assets_dir, f"duck_walk_{i}_proc.png"))
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
        return QPixmap.fromImage(px.toImage().mirrored(True, False))

    def get(self, state: str, tick: int) -> QPixmap:
        frames = self.frames.get(state, self.frames["idle"])
        return frames[tick % len(frames)]

    @property
    def duck_width(self) -> int:
        return max(px.width() for lst in self.frames.values() for px in lst)

    @property
    def duck_height(self) -> int:
        return max(px.height() for lst in self.frames.values() for px in lst)


# ── Main pet widget ──────────────────────────────────────────────────────────

WIN_PAD_X = 20
WIN_PAD_Y = 40   # extra vertical room for Zs / hearts / bounce

PET_RESPONSES = [
    "❤ QUACK! That's the spot!",
    "*happy tail wiggle* More pets please!",
    "I am now legally your best friend. No take-backs. QUACK!",
    "*purrs* ...wait, ducks don't purr. *quacks affectionately*",
    "Best. Human. Ever. ❤",
]


class DuckPet(QWidget):
    # Thread-safe bridges: worker threads emit, main thread handles.
    _bubble_signal = Signal(str)
    _found_signal = Signal(str)     # found path, or "" when not found

    def __init__(self, api_key: str, config: dict, save_config_fn):
        super().__init__()

        self.api_key = api_key
        self.config = config
        self.save_config = save_config_fn

        # ── State ───────────────────────────────────────────────────────────
        self.state = "idle"
        self.direction = 1          # +1 = right, -1 = left
        self._tick = 0              # animation tick (20/s)
        self._anim_speed = 6        # ticks per frame flip
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._idle_secs = 0
        self._bubble_cooldown = 0
        self._hearts_until = 0      # tick until which hearts float
        self._search_filename = ""
        self._drag_start: Optional[QPoint] = None
        self._dragging = False
        self._chat_dlg = None

        # ── Sprites ─────────────────────────────────────────────────────────
        assets = get_resource_path("assets")
        self.sprites = SpriteSet(assets)
        dw = self.sprites.duck_width + WIN_PAD_X * 2
        dh = self.sprites.duck_height + WIN_PAD_Y * 2
        self.resize(dw, dh)

        # Where speech bubbles should anchor (top of the duck's head).
        self.BUBBLE_ANCHOR = WIN_PAD_Y - 6

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

        # ── Signals (queued from worker threads onto the GUI thread) ─────────
        self._bubble = None
        self._bubble_signal.connect(self._show_bubble_main)
        self._found_signal.connect(self._on_file_found)

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
        self._behavior_timer.start(4000)

        self._peek_timer = QTimer(self)
        self._peek_timer.timeout.connect(self._peek_at_screen)
        self._peek_timer.start(random.randint(90_000, 150_000))  # 1.5-2.5 min

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
        # Keep a reference: setContextMenu() does NOT take ownership, and a
        # local QMenu would be garbage-collected (menu silently vanishes).
        self._tray_menu = QMenu()
        self._tray_menu.setStyleSheet(MENU_STYLE)
        self._fill_menu(self._tray_menu)
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(
            lambda r: self._open_chat()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self._tray.show()

    def _fill_menu(self, menu: QMenu):
        menu.addAction("💬 Talk to Quackers", self._open_chat)
        menu.addAction("🔍 Find a file…", self._prompt_find_file)
        menu.addAction("📸 What am I doing?", self._peek_at_screen)
        menu.addAction("❤️ Pet the duck", self._pet_duck)
        menu.addSeparator()
        menu.addAction("⚙️  Settings", self._open_settings)
        menu.addAction("❌ Quit", QApplication.instance().quit)

    # ── Animation / movement ─────────────────────────────────────────────────

    def _on_anim_tick(self):
        self._tick += 1
        self.update()

    def _on_move_tick(self):
        if self.state == "walking":
            nx = self.x() + self._vel_x
            ny = self.y() + self._vel_y

            # Bounce off edges (clamped so the duck never escapes the screen)
            min_x, max_x = self._sx, self._sx + self._sw - self.width()
            min_y, max_y = self._sy, self._sy + self._sh - self.height()
            if nx < min_x or nx > max_x:
                self._vel_x *= -1
                self.direction *= -1
                nx = max(min_x, min(nx, max_x))
            if ny < min_y or ny > max_y:
                self._vel_y *= -1
                ny = max(min_y, min(ny, max_y))

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        draw_state = {
            "idle":    "idle",
            "sleep":   "sleep",
            "walking": "walk_right" if self.direction > 0 else "walk_left",
            "talking": "wave",
            "search":  "search",
        }.get(self.state, "idle")

        frame_idx = self._tick // self._anim_speed
        sprite = self.sprites.get(draw_state, frame_idx)

        # Gentle vertical "breathing" bob so the duck feels alive
        bob = 0.0
        if self.state == "idle":
            bob = math.sin(self._tick * 0.12) * 2.4
        elif self.state == "sleep":
            bob = math.sin(self._tick * 0.05) * 1.6
        elif self.state == "search":
            bob = abs(math.sin(self._tick * 0.4)) * 3.0   # eager waddle hop

        x = (self.width() - sprite.width()) // 2
        base_y = WIN_PAD_Y + (self.sprites.duck_height - sprite.height())
        y = base_y - bob

        # Soft grounding shadow at the duck's feet
        foot_y = WIN_PAD_Y + self.sprites.duck_height + 5
        lift = max(0.0, bob)
        shadow_w = sprite.width() * 0.60 * (1.0 - lift * 0.03)
        shadow_h = shadow_w * 0.20
        cx = self.width() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 55))
        painter.drawEllipse(QRectF(cx - shadow_w / 2, foot_y - shadow_h / 2,
                                   shadow_w, shadow_h))

        # Pixel-art sprite: keep it crisp (no smoothing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(int(x), int(y), sprite)

        if self.state == "sleep":
            self._paint_zs(painter, int(x + sprite.width() - 10), int(y))
        if self.state == "search":
            self._paint_search_fx(painter)
        if self._tick < self._hearts_until:
            self._paint_hearts(painter, int(x + sprite.width() // 2), int(y))

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

    def _paint_hearts(self, painter: QPainter, cx: int, top: int):
        painter.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        remaining = self._hearts_until - self._tick
        for i, dx in enumerate((-26, 2, 24)):
            phase = (self._tick * 2 + i * 17) % 50
            rise = phase * 1.1
            alpha = max(0, min(255, int(255 * (1 - phase / 50)), remaining * 12))
            painter.setPen(QColor(255, 105, 140, alpha))
            wobble = math.sin((self._tick + i * 9) * 0.3) * 4
            painter.drawText(int(cx + dx + wobble), int(top - 4 - rise), "♥")

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

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pet_duck()

    # ── Context menu ─────────────────────────────────────────────────────────

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        self._fill_menu(menu)
        menu.exec(pos)

    # ── Petting ──────────────────────────────────────────────────────────────

    def _pet_duck(self):
        self._hearts_until = self._tick + 55     # ~2.7 s of hearts
        if self.state == "sleep":
            self._set_state("idle")
        self._bubble_signal.emit(random.choice(PET_RESPONSES))

    # ── Chat ─────────────────────────────────────────────────────────────────

    def _open_chat(self):
        if not self._gemini:
            self._bubble_signal.emit(
                "QUACK! I need a Gemini API key to chat. Right-click → Settings!")
            return
        from chat_dialog import ChatDialog
        dlg = ChatDialog(self._gemini)
        self._chat_dlg = dlg
        dlg.message_sent.connect(self._on_chat_message)
        dlg.exec()
        self._chat_dlg = None

    def _on_chat_message(self, user_msg: str, duck_response: str):
        # File-find intent takes over: close the chat, start the hunt.
        if self._gemini and self._gemini.is_file_request(user_msg):
            filename = self._gemini.extract_filename(user_msg)
            if filename:
                if self._chat_dlg:
                    self._chat_dlg.accept()
                self._do_find_file(filename)
                return
        self._set_state("talking")
        self._bubble_signal.emit(duck_response)
        # Only stand down if still talking — never cancel a search/sleep.
        QTimer.singleShot(5000, lambda: (
            self._set_state("idle") if self.state == "talking" else None))

    # ── File finding ─────────────────────────────────────────────────────────

    def _prompt_find_file(self):
        from find_dialog import FindFileDialog
        dlg = FindFileDialog()
        if dlg.exec() and dlg.filename:
            self._do_find_file(dlg.filename)

    def _do_find_file(self, filename: str):
        self._search_filename = filename
        self._set_state("search")
        self._bubble_signal.emit(
            f"QUACK! On the case! Searching for '{filename}'… *intense waddling*"
        )

        from audio import play_search_music
        play_search_music()

        from file_ops import find_file_async
        # Worker thread reports back via signal → handled on the GUI thread.
        find_file_async(filename,
                        on_found=lambda path: self._found_signal.emit(path or ""))

    def _on_file_found(self, path: str):
        """Runs on the GUI thread (queued signal from the search worker)."""
        from audio import stop_music
        from file_ops import open_in_explorer
        stop_music()

        if path:
            msg = (f"Found it! *victory quack* '{os.path.basename(path)}' "
                   f"is in {os.path.dirname(path)}")
        else:
            msg = (f"Couldn't find '{self._search_filename}'… "
                   "Opening your home folder instead. QUACK!")
            path = os.path.expanduser("~")

        open_in_explorer(path)
        self._set_state("idle")
        self._bubble_signal.emit(msg)

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
            self._bubble_signal.emit(
                f"QUACK! I tried to look at your screen but something went wrong. "
                f"({str(e)[:40]})")

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
        from PySide6.QtWidgets import QDialog
        from setup_dialog import SetupDialog
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
