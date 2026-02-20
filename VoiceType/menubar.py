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


def _mic_icon(color: QColor, size: int = 22) -> QIcon:
    """Render a rounded square with mic knockout for the menubar."""
    pix = QPixmap(QSize(size, size))
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded square background
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    r = size * 0.22
    p.drawRoundedRect(0, 0, size, size, r, r)

    # Mic knockout via composition mode
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
    p.setBrush(QColor(255, 255, 255))
    pen = QPen(QColor(255, 255, 255))

    s = size  # alias for readability
    # Mic body — rounded rect
    mic_w = s * 0.25
    mic_h = s * 0.46
    mic_x = (s - mic_w) / 2
    mic_y = s * 0.09
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(mic_x, mic_y, mic_w, mic_h), mic_w / 2, mic_w / 2)

    # Arc
    pen.setWidthF(s * 0.09)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    arc_path = QPainterPath()
    arc_x = s * 0.23
    arc_y = s * 0.27
    arc_w = s * 0.54
    arc_h = s * 0.40
    arc_path.arcMoveTo(QRectF(arc_x, arc_y, arc_w, arc_h), 180)
    arc_path.arcTo(QRectF(arc_x, arc_y, arc_w, arc_h), 180, -180)
    p.drawPath(arc_path)

    # Stem
    cx = s / 2
    p.drawLine(int(cx), int(s * 0.67), int(cx), int(s * 0.82))

    # Base
    base_w = s * 0.25
    p.drawLine(int(cx - base_w / 2), int(s * 0.82), int(cx + base_w / 2), int(s * 0.82))

    p.end()
    return QIcon(pix)


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

    def __init__(
        self, history: HistoryManager | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)

        self._history = history or HistoryManager()
        self._recording = False

        # Pre-render icons
        t = theme()
        self._icon_idle = _mic_icon(t.text_light)
        self._icon_rec = _mic_icon(t.red)

        # ── System tray ──────────────────────────────────
        self._tray = QSystemTrayIcon(self._icon_idle)
        self._tray.setToolTip("Scribr \u2014 Ready")

        self._menu = QMenu()
        self._status_action: QAction | None = None
        self._record_action: QAction | None = None
        self._history_menu: QMenu | None = None
        self._build_menu()
        self._tray.setContextMenu(self._menu)

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
            count = self._history.count()
            self._history_menu.setTitle(
                f"\U0001f4cb  History ({count} clip{'s' if count != 1 else ''})"
            )
            for entry in items:
                text = str(entry.get("text", ""))
                truncated = (text[:42] + "\u2026") if len(text) > 45 else text
                action = self._history_menu.addAction(truncated)
                if action:
                    action.setEnabled(False)

    def refresh_after_transcription(self) -> None:
        """Call after a new transcription is added to history."""
        self._refresh_history()

    # ─────────────────────────────────────────────────────
    #  STATE UPDATES
    # ─────────────────────────────────────────────────────

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if recording:
            self._tray.setIcon(self._icon_rec)
            self._tray.setToolTip("Scribr \u2014 Recording")
            if self._status_action:
                self._status_action.setText("Scribr \u2014 Recording")
            if self._record_action:
                self._record_action.setText(
                    "\u23f9  Stop Recording          Right \u2325"
                )
        else:
            self._tray.setIcon(self._icon_idle)
            self._tray.setToolTip("Scribr \u2014 Ready")
            if self._status_action:
                self._status_action.setText("Scribr \u2014 Ready")
            if self._record_action:
                self._record_action.setText(
                    "\U0001f399  Start Recording        Right \u2325"
                )

    def set_transcribing(self) -> None:
        self._tray.setIcon(self._icon_rec)
        self._tray.setToolTip("Scribr \u2014 Transcribing...")
        if self._status_action:
            self._status_action.setText("Scribr \u2014 Transcribing...")
        if self._record_action:
            self._record_action.setText("\u231b  Transcribing...")

    def set_idle(self) -> None:
        self._recording = False
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
