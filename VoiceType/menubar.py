# menubar.py — macOS menubar app using QSystemTrayIcon.
# Provides system tray icon, dropdown menu, recording control,
# history display, and launches the settings window.
# Scribr brand — warm coral accent, Lora + Plus Jakarta Sans fonts.

from __future__ import annotations

from history import HistoryManager
from PyQt6.QtCore import QObject, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from style import qcolor_to_rgba, theme


def _load_icon(path: str, is_template: bool = False) -> QIcon:
    """Load a PNG icon for the menubar, optionally as a template."""
    icon = QIcon(path)
    icon.setIsMask(is_template)
    return icon


class ScribrMenubar(QObject):
    """System tray menubar app for Scribr.

    Icon states:
      idle  — muted grey mic
      rec   — warm coral mic (pulsing)
      busy  — coral mic (static)
    """

    record_toggled = pyqtSignal(bool)
    open_settings = pyqtSignal()
    test_mic = pyqtSignal()
    history_clicked = pyqtSignal(dict)

    def __init__(
        self, history: HistoryManager | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)

        self._history = history or HistoryManager()
        self._recording = False

        # Pre-render icons
        self._icon_idle = _load_icon("assets/menubar_idle.png", is_template=True)
        # Using QIcon to dynamically read retina scaling, then freezing the pixmap size
        self._icon_rec = QIcon("assets/menubar_recording.png")
        self._pix_rec = self._icon_rec.pixmap(22, 22)

        # Animation states
        from enum import Enum
        class AnimState(Enum):
            IDLE = 0
            FADE_IN = 1
            PULSE = 2
            STATIC_BUSY = 3

        self._anim_state = AnimState.IDLE
        self._anim_phase = 0.0
        
        from PyQt6.QtCore import QTimer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._tick_anim)

        # ── System tray ──────────────────────────────────
        self._tray = QSystemTrayIcon(self._icon_idle)
        self._tray.setToolTip("Scribr \u2014 Ready")

        self._menu = QMenu()
        self._status_action: QAction | None = None
        self._record_action: QAction | None = None
        self._history_menu: QMenu | None = None
        self._build_menu()
        self._tray.setContextMenu(self._menu)

    def _tick_anim(self) -> None:
        """60fps animation loop for the menubar icon."""
        if self._anim_state == 0:  # IDLE
            return

        dt = 16.0 / 1000.0
        opacity = 1.0

        if self._anim_state.name == "FADE_IN":
            self._anim_phase += dt / 0.2  # 0.2s duration
            if self._anim_phase >= 1.0:
                self._anim_phase = 0.0
                self._anim_state = self._anim_state.PULSE
            opacity = min(1.0, self._anim_phase)
        
        elif self._anim_state.name == "PULSE":
            # Pulse opacity 1.0 <-> 0.5 over 1.2s
            import math
            self._anim_phase += dt / 1.2
            if self._anim_phase >= 1.0:
                self._anim_phase -= 1.0
            # Sine wave: 0.5 to 1.0
            sine = (math.sin(self._anim_phase * math.pi * 2) + 1.0) / 2.0
            opacity = 0.5 + (sine * 0.5)

        elif self._anim_state.name == "STATIC_BUSY":
            opacity = 1.0

        # Render current frame
        pix = self._pix_rec.copy()
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setOpacity(opacity)
        p.drawPixmap(0, 0, self._pix_rec)
        p.end()

        self._tray.setIcon(QIcon(pix))

    def show(self) -> None:
        self._tray.show()

    # ─────────────────────────────────────────────────────
    #  MENU CONSTRUCTION
    # ─────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        t = theme()
        self._menu.clear()
        self._menu.setStyleSheet(
            "QMenu {"
            f"  background: {t.surface.name()};"
            f"  border: 1px solid {qcolor_to_rgba(t.border)};"
            "  border-radius: 12px;"
            "  padding: 6px 0;"
            "}"
            "QMenu::item {"
            "  padding: 8px 14px;"
            f"  color: {t.text.name()};"
            "  font-size: 13px;"
            "  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;"
            "}"
            "QMenu::item:selected {"
            f"  background: {qcolor_to_rgba(t.surface_2)};"
            "}"
            "QMenu::item:disabled {"
            f"  color: {qcolor_to_rgba(t.text_light)};"
            "}"
            "QMenu::separator {"
            "  height: 1px;"
            f"  background: {qcolor_to_rgba(t.border)};"
            "  margin: 4px 0;"
            "}"
        )

        # Header — non-clickable
        self._status_action = self._menu.addAction("Scribr \u2014 Ready")
        if self._status_action:
            self._status_action.setEnabled(False)
        self._menu.addSeparator()

        # Record button
        self._record_action = self._menu.addAction(
            "\U0001f399  Start Recording        Right \u2325"
        )
        if self._record_action:
            self._record_action.triggered.connect(self._on_record_click)
        self._menu.addSeparator()

        # History sub-menu
        self._history_menu = self._menu.addMenu("\U0001f4cb  History")
        self._refresh_history()
        self._menu.addSeparator()

        # Settings
        settings_action = self._menu.addAction(
            "\u2699\ufe0f  Settings                    \u2318,"
        )
        if settings_action:
            settings_action.triggered.connect(self.open_settings.emit)

        # Test Microphone
        test_action = self._menu.addAction("\U0001f3a4  Test Microphone")
        if test_action:
            test_action.triggered.connect(self.test_mic.emit)
        self._menu.addSeparator()

        # Quit
        quit_action = self._menu.addAction("\u2715  Quit Scribr")
        if quit_action:
            quit_action.triggered.connect(QApplication.quit)

    # ─────────────────────────────────────────────────────
    #  HISTORY
    # ─────────────────────────────────────────────────────

    def _refresh_history(self) -> None:
        """Rebuild the history sub-menu from HistoryManager."""
        if self._history_menu is None:
            return
        self._history_menu.clear()

        items = self._history.get_recent(5)
        if not items:
            empty = self._history_menu.addAction("Nothing yet \u2014 give it a try!")
            if empty:
                empty.setEnabled(False)
        else:
            self._history_menu.setTitle("\U0001f4cb  History")
            for entry in items:
                text = str(entry.get("text", ""))
                truncated = (text[:42] + "\u2026") if len(text) > 45 else text
                action = self._history_menu.addAction(truncated)
                if action:
                    action.triggered.connect(lambda checked=False, e=entry: self._on_history_clicked(e))

    def _on_history_clicked(self, entry: dict) -> None:
        self.history_clicked.emit(entry)

    def refresh_after_transcription(self) -> None:
        """Call after a new transcription is added to history."""
        self._refresh_history()

    # ─────────────────────────────────────────────────────
    #  STATE UPDATES
    # ─────────────────────────────────────────────────────

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if recording:
            self._anim_state = self._anim_state.FADE_IN
            self._anim_phase = 0.0
            self._anim_timer.start()

            self._tray.setToolTip("Scribr \u2014 Recording")
            if self._status_action:
                self._status_action.setText("Scribr \u2014 Recording")
            if self._record_action:
                self._record_action.setText(
                    "\u23f9  Stop Recording          Right \u2325"
                )
        else:
            self._anim_timer.stop()
            self._anim_state = self._anim_state.IDLE
            self._tray.setIcon(self._icon_idle)
            
            self._tray.setToolTip("Scribr \u2014 Ready")
            if self._status_action:
                self._status_action.setText("Scribr \u2014 Ready")
            if self._record_action:
                self._record_action.setText(
                    "\U0001f399  Start Recording        Right \u2325"
                )

    def set_transcribing(self) -> None:
        self._anim_state = self._anim_state.STATIC_BUSY
        self._tray.setIcon(self._icon_rec)
        self._tray.setToolTip("Scribr \u2014 Transcribing...")
        if self._status_action:
            self._status_action.setText("Scribr \u2014 Transcribing...")
        if self._record_action:
            self._record_action.setText("\u231b  Transcribing...")

    def set_idle(self) -> None:
        self._recording = False
        self._anim_timer.stop()
        self._anim_state = self._anim_state.IDLE
        self._tray.setIcon(self._icon_idle)
        self._tray.setToolTip("Scribr \u2014 Ready")
        if self._status_action:
            self._status_action.setText("Scribr \u2014 Ready")
        if self._record_action:
            self._record_action.setText(
                "\U0001f399  Start Recording        Right \u2325"
            )

    # ─────────────────────────────────────────────────────
    #  CALLBACKS
    # ─────────────────────────────────────────────────────

    def _on_record_click(self) -> None:
        new_state = not self._recording
        self.set_recording(new_state)
        self.record_toggled.emit(new_state)
