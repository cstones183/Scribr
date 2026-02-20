# app.py — Scribr entry point. Everything runs in Qt's main thread.
# QSystemTrayIcon for menubar — no thread conflicts.

from __future__ import annotations

import sys

from history import HistoryManager
from menubar import ScribrMenubar
from PyQt6.QtWidgets import QApplication
from settings import SettingsManager
from settings_window import SettingsWindow


class ScribrApp:
    """Wires together: menubar, settings window, overlay, and future modules."""

    def __init__(self) -> None:
        self._qt_app = QApplication(sys.argv)

        self._settings = SettingsManager()
        self._history = HistoryManager()

        # ── Settings window (created on demand) ──
        self._settings_window: SettingsWindow | None = None

        # ── Menubar ──────────────────────────────────────
        self._menubar = ScribrMenubar(history=self._history)
        self._menubar.open_settings.connect(self._show_settings_window)
        self._menubar.record_toggled.connect(self._on_record_toggle)
        self._menubar.test_mic.connect(self._on_test_mic)
        self._menubar.show()

        # ── Watch for system theme changes ──
        self._watch_appearance_changes()

    def run(self) -> None:
        """Run Qt event loop."""
        sys.exit(self._qt_app.exec())

    # ─────────────────────────────────────────────────────
    #  THEME CHANGE OBSERVER
    # ─────────────────────────────────────────────────────

    def _watch_appearance_changes(self) -> None:
        """Observe macOS appearance changes to refresh themed components."""
        try:
            from Foundation import (  # type: ignore[import-untyped]
                NSDistributedNotificationCenter,
            )

            center = NSDistributedNotificationCenter.defaultCenter()
            center.addObserverForName_object_queue_usingBlock_(
                "AppleInterfaceThemeChangedNotification",
                None,
                None,
                lambda note: self._on_theme_changed(),
            )
        except ImportError:
            pass

    def _on_theme_changed(self) -> None:
        """Called when macOS appearance changes."""
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.update()

    # ─────────────────────────────────────────────────────
    #  SETTINGS WINDOW
    # ─────────────────────────────────────────────────────

    def _show_settings_window(self) -> None:
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._settings)
            self._settings_window.settings_saved.connect(self._on_settings_saved)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

        # Centre on screen
        screen = self._qt_app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self._settings_window.width()) // 2 + geo.x()
            y = (geo.height() - self._settings_window.height()) // 3 + geo.y()
            self._settings_window.move(x, y)

    def _on_settings_saved(self) -> None:
        """Re-read settings after save."""
        self._settings.load()

    # ─────────────────────────────────────────────────────
    #  RECORDING (placeholder — will wire to recorder/transcriber)
    # ─────────────────────────────────────────────────────

    def _on_record_toggle(self, recording: bool) -> None:
        """Called from menubar record button."""
        pass  # TODO: wire to recorder.Recorder + transcriber

    def _on_test_mic(self) -> None:
        """Called from menubar test microphone."""
        pass  # TODO: wire to recorder.Recorder test mode


def main() -> None:
    app = ScribrApp()
    app.run()


if __name__ == "__main__":
    main()
