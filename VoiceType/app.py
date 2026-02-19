# app.py — Entry point. Runs the rumps menubar app and wires all modules together.
# QApplication runs in main thread (required for overlay animations).
# rumps runs in a daemon thread.

import sys
import threading

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from settings import SettingsManager
from history import HistoryManager
from settings_window import SettingsWindow
from menubar import VoiceTypeMenubar


class VoiceTypeApp:
    """Wires together: menubar, settings window, overlay, and future modules."""

    def __init__(self):
        self._qt_app = QApplication(sys.argv)

        self._settings = SettingsManager()
        self._history = HistoryManager()

        # ── Settings window (singleton, created on demand) ──
        self._settings_window: SettingsWindow | None = None

        # ── Menubar ──────────────────────────────────────
        self._menubar = VoiceTypeMenubar(history=self._history)
        self._menubar.on_open_settings = self._open_settings
        self._menubar.on_record_toggle = self._on_record_toggle
        self._menubar.on_test_mic = self._on_test_mic

    def run(self):
        """Start rumps in a daemon thread, then run Qt event loop."""
        rumps_thread = threading.Thread(
            target=self._menubar.run,
            daemon=True,
        )
        rumps_thread.start()

        sys.exit(self._qt_app.exec())

    # ─────────────────────────────────────────────────────
    #  SETTINGS WINDOW
    # ─────────────────────────────────────────────────────

    def _open_settings(self):
        """Open settings window (create if needed). Thread-safe via QTimer."""
        QTimer.singleShot(0, self._show_settings_window)

    def _show_settings_window(self):
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

    def _on_settings_saved(self):
        """Re-read settings after save."""
        self._settings.load()

    # ─────────────────────────────────────────────────────
    #  RECORDING (placeholder — will wire to recorder/transcriber)
    # ─────────────────────────────────────────────────────

    def _on_record_toggle(self, recording: bool):
        """Called from menubar record button."""
        pass  # TODO: wire to recorder.Recorder + transcriber

    def _on_test_mic(self):
        """Called from menubar test microphone."""
        pass  # TODO: wire to recorder.Recorder test mode


def main():
    app = VoiceTypeApp()
    app.run()


if __name__ == "__main__":
    main()
