# app.py — Scribr entry point.
# Wires together: hotkey → recorder → transcriber → corrector → clipboard → overlay.

from __future__ import annotations

import logging
import logging.handlers
import sys
import traceback
import threading
import time
from pathlib import Path

# ── Logging setup ─────────────────────────────────────
_LOG_DIR = Path.home() / "Library" / "Logs" / "Scribr"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            _LOG_DIR / "scribr.log", maxBytes=1_000_000, backupCount=3,
        ),
    ],
)
log = logging.getLogger("scribr")


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Log tracebacks instead of letting PyQt6 call qFatal → abort."""
    log.critical("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))


sys.excepthook = _global_exception_handler

from corrector import Corrector, CorrectionError
from history import HistoryManager
from hotkey import HotkeyListener
from menubar import ScribrMenubar
from overlay import OverlayState, OverlayWindow
from context_detector import is_text_field_focused
from recorder import Recorder
from settings import SettingsManager
from stats import StatsManager
from settings_window import SettingsWindow
from transcriber import (
    GroqTranscriber,
    OpenAITranscriber,
    TranscriptionError,
)

from pynput.keyboard import Controller, Key
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMessageBox


class _ThreadBridge(QObject):
    """Signals for marshalling background-thread results to the main thread."""

    final_transcript = pyqtSignal(str)
    live_transcript = pyqtSignal(str)
    transcription_error = pyqtSignal()
    ai_format_completed = pyqtSignal(str)
    ai_format_failed = pyqtSignal()
    hotkey_pressed = pyqtSignal()
    hotkey_released = pyqtSignal()


class ScribrApp:
    """Coordinates all Scribr modules."""

    def __init__(self) -> None:
        self._qt_app = QApplication(sys.argv)

        # ── Hide from macOS Dock (Run as Accessory) ──
        try:
            import AppKit
            # NSApplicationActivationPolicyAccessory = 1 (hides dock icon, allows windows to show)
            ns_app = AppKit.NSApplication.sharedApplication()
            ns_app.setActivationPolicy_(1)
        except ImportError:
            log.warning("AppKit not installed, cannot hide Dock icon.")

        self._settings = SettingsManager()
        self._stats = StatsManager()
        self._history = HistoryManager()
        self._keyboard = Controller()

        # ── Settings window (lazy) ──
        self._settings_window: SettingsWindow | None = None

        # ── Overlay ──
        self._overlay = OverlayWindow(
            position=self._settings.get("overlay_position", "bottom_centre"),
        )

        # ── Menubar ──
        self._menubar = ScribrMenubar(history=self._history)
        self._menubar.open_settings.connect(self._show_settings_window)
        self._menubar.record_toggled.connect(self._on_record_toggle)
        self._menubar.test_mic.connect(self._on_test_mic)
        self._menubar.history_clicked.connect(self._on_history_clicked)
        self._menubar.show()

        # ── Recorder ──
        self._recorder = Recorder(on_device_error=self._on_device_error)

        # ── Hotkey ──
        self._hotkey = HotkeyListener(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            on_permission_error=self._on_permission_error,
            key_name=self._settings.get("hotkey", "alt_r"),
        )
        self._hotkey.start()

        # ── Transcriber / corrector (built from settings) ──
        self._transcriber: GroqTranscriber | OpenAITranscriber | None = None
        self._corrector: Corrector | None = None
        self._rebuild_transcriber()

        log.info("Transcriber: %s", type(self._transcriber).__name__ if self._transcriber else "None")
        log.info("Corrector: %s", self._corrector is not None)

        # ── Thread bridge (signals for bg thread → main thread) ──
        self._bridge = _ThreadBridge()
        self._bridge.final_transcript.connect(self._on_final_transcript)
        self._bridge.live_transcript.connect(self._overlay.update_transcript)
        self._bridge.transcription_error.connect(self._on_transcription_error)
        self._bridge.ai_format_completed.connect(self._on_ai_format_completed)
        self._bridge.ai_format_failed.connect(self._overlay.on_ai_format_failed)

        # Hotkey signals (pynput bg thread → main thread via signal)
        self._bridge.hotkey_pressed.connect(self._start_recording)
        self._bridge.hotkey_released.connect(self._stop_recording)

        # Connect overlay's request signal
        self._overlay.request_ai_format.connect(self._on_ai_format_requested)
        self._overlay.ai_mode_toggled.connect(self._history.update_ai_mode)

        # ── Groq live transcription timer ──
        self._groq_timer = QTimer()
        self._groq_timer.timeout.connect(self._on_groq_tick)
        self._groq_pending = False

        # ── State ──
        self._is_recording = False
        self._is_continuing = False
        self._previous_text = ""
        self._recording_start: float = 0.0
        self._pending_paste_context = False  # cached typing-context for deferred AI paste
        self._cached_typing_context = False  # set on pynput thread before signal delivery
        self._total_duration: float = 0.0

        # ── Watch for system theme changes ──
        self._watch_appearance_changes()

    # ─────────────────────────────────────────────────────
    #  PROVIDER SETUP
    # ─────────────────────────────────────────────────────

    def _rebuild_transcriber(self) -> None:
        """Create transcriber + corrector from current settings."""
        s = self._settings

        # Prefer Groq (live capable), fall back to OpenAI
        groq_key = s.get("groq_api_key", "")
        openai_key = s.get("openai_api_key", "")

        if groq_key:
            self._transcriber = GroqTranscriber(api_key=groq_key)
        elif openai_key:
            self._transcriber = OpenAITranscriber(api_key=openai_key)
        else:
            self._transcriber = None

        # Corrector uses OpenAI key — needed for both ai_cleanup and AI format mode
        openai_key = s.get("openai_api_key", "")
        if openai_key:
            self._corrector = Corrector(api_key=openai_key)
        else:
            self._corrector = None

    # ─────────────────────────────────────────────────────
    #  HOTKEY CALLBACKS (pynput background thread → Qt main thread)
    # ─────────────────────────────────────────────────────

    def _on_hotkey_press(self) -> None:
        # Detect text field focus NOW on the pynput thread — before the
        # modifier key event propagates and disrupts macOS AX focus state.
        self._cached_typing_context = is_text_field_focused()
        log.debug("Hotkey PRESSED (typing_context=%s)", self._cached_typing_context)
        self._bridge.hotkey_pressed.emit()

    def _on_hotkey_release(self) -> None:
        log.debug("Hotkey RELEASED")
        self._bridge.hotkey_released.emit()

    # ─────────────────────────────────────────────────────
    #  RECORDING START / STOP (main thread)
    # ─────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        if self._is_recording:
            return
            
        if self._overlay.state == OverlayState.RESULT_NOTEPAD:
            self._is_continuing = True
            self._previous_text = self._overlay.get_notepad_text()
        else:
            self._is_continuing = False
            self._previous_text = ""
            self._total_duration = 0.0
            
        self._is_recording = True
        self._recording_start = time.time()

        log.info("Starting recording...")
        self._overlay.set_is_typing_context(
            getattr(self, "_cached_typing_context", False)
        )
        self._overlay.set_ai_mode(
            active=self._settings.get("ai_mode_default", False),
            show_original=self._settings.get("ai_show_original", False),
        )
        self._overlay.transition_to(OverlayState.RECORDING, is_continuing=self._is_continuing)
        self._menubar.set_recording(True)

        self._recorder.start(on_rms_update=self._overlay.update_rms)
        log.debug("Recorder started (is_recording=%s)", self._recorder.is_recording)

        # If using Groq, start the live transcription timer
        if isinstance(self._transcriber, GroqTranscriber):
            interval_s = self._settings.get("groq_live_interval", 2)
            self._groq_timer.setInterval(interval_s * 1000)
            self._groq_pending = False
            self._groq_timer.start()
            log.debug("Groq live timer started (every %ds)", interval_s)

    def _stop_recording(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False

        self._groq_timer.stop()
        wav_bytes = self._recorder.stop()
        duration = time.time() - self._recording_start
        self._total_duration += duration
        
        api_cost = 0.0
        if isinstance(self._transcriber, OpenAITranscriber):
            api_cost = (duration / 60.0) * 0.006
        self._stats.add_clip(duration, api_cost)

        log.info("Stopped recording (%.1fs, total=%.1fs, %d bytes)", duration, self._total_duration, len(wav_bytes))
        self._menubar.set_transcribing()

        if isinstance(self._transcriber, GroqTranscriber):
            # Groq: final transcription of full buffer
            self._transcribe_in_background(wav_bytes)
        elif isinstance(self._transcriber, OpenAITranscriber):
            # OpenAI: single transcription after release
            self._overlay.transition_to(OverlayState.LIVE_TRANSCRIBING, is_continuing=self._is_continuing)
            self._transcribe_in_background(wav_bytes)
        else:
            # No transcriber configured
            self._overlay.transition_to(OverlayState.IDLE)
            self._menubar.set_idle()

    # ─────────────────────────────────────────────────────
    #  GROQ LIVE TRANSCRIPTION (timer-based snapshots)
    # ─────────────────────────────────────────────────────

    def _on_groq_tick(self) -> None:
        log.debug("Groq tick: recording=%s pending=%s", self._is_recording, self._groq_pending)
        if not self._is_recording or self._groq_pending:
            return
        wav_snapshot = self._recorder.get_wav_snapshot()
        if not wav_snapshot or len(wav_snapshot) < 100:
            log.debug("Groq tick: snapshot too small (%d bytes)", len(wav_snapshot) if wav_snapshot else 0)
            return
        log.debug("Groq tick: sending %d bytes", len(wav_snapshot))
        self._groq_pending = True
        threading.Thread(
            target=self._groq_snapshot_worker,
            args=(wav_snapshot,),
            daemon=True,
        ).start()

    def _groq_snapshot_worker(self, wav_bytes: bytes) -> None:
        try:
            language = self._settings.get("language", "auto")
            uk = language == "en-uk"
            prompt = "Use UK English spelling and grammar." if uk else ""
            text = self._transcriber.transcribe(wav_bytes, language="en" if uk else language, prompt=prompt)
            log.debug("Groq snapshot result: %r", text[:80] if text else text)
            if text is not None:
                display_text = f"{self._previous_text} {text}".strip() if self._is_continuing else text
                if display_text:
                    self._bridge.live_transcript.emit(display_text)
        except TranscriptionError as e:
            log.warning("Groq snapshot error: %s", e)
        finally:
            self._groq_pending = False

    # ─────────────────────────────────────────────────────
    #  API TRANSCRIPTION (background thread)
    # ─────────────────────────────────────────────────────

    def _transcribe_in_background(self, wav_bytes: bytes) -> None:
        threading.Thread(
            target=self._api_transcribe_worker,
            args=(wav_bytes,),
            daemon=True,
        ).start()

    def _api_transcribe_worker(self, wav_bytes: bytes) -> None:
        try:
            language = self._settings.get("language", "auto")
            uk = language == "en-uk"
            prompt = "Use UK English spelling and grammar." if uk else ""
            log.info("Transcribing %d bytes (lang=%s)", len(wav_bytes), language)
            text = self._transcriber.transcribe(wav_bytes, language="en" if uk else language, prompt=prompt)
            log.debug("Transcription result: %r", text[:100] if text else text)
            if text:
                text = self._maybe_correct(text)
                final_text = f"{self._previous_text} {text}".strip() if self._is_continuing else text
                self._bridge.final_transcript.emit(final_text)
            else:
                log.warning("Empty transcription result")
                self._bridge.transcription_error.emit()
        except TranscriptionError as e:
            log.warning("Transcription failed: %s", e)
            self._bridge.transcription_error.emit()

    # ─────────────────────────────────────────────────────
    #  TEXT CORRECTION (called in background thread)
    # ─────────────────────────────────────────────────────

    def _maybe_correct(self, text: str) -> str:
        """Run AI cleanup if enabled. Returns uncorrected text on failure."""
        if self._corrector and self._settings.get("ai_cleanup", True):
            try:
                uk = self._settings.get("language", "auto") == "en-uk"
                result = self._corrector.clean_text(text, use_uk_english=uk)
                self._stats.add_cost(0.0005)
                return result
            except CorrectionError as e:
                log.warning("Corrector failed: %s", e)
        return text

    # ─────────────────────────────────────────────────────
    #  AI FORMATTING (background thread)
    # ─────────────────────────────────────────────────────

    def _on_ai_format_requested(self, text: str) -> None:
        if not self._corrector:
            log.warning("AI Format requested but no corrector initialized.")
            self._bridge.ai_format_failed.emit()
            return

        threading.Thread(
            target=self._ai_format_worker,
            args=(text,),
            daemon=True,
        ).start()

    def _ai_format_worker(self, text: str) -> None:
        try:
            style = self._settings.get("ai_format_style", "structured")
            uk = self._settings.get("language", "auto") == "en-uk"
            log.info("AI Formatting (%s) %d chars", style, len(text))
            result = self._corrector.format_for_llm(text, style=style, use_uk_english=uk)
            if result:
                log.debug("AI Format result: %r", result[:80])
                self._stats.add_cost(0.0005)
                self._history.update_ai_text(text, result)
                self._bridge.ai_format_completed.emit(result)
            else:
                self._bridge.ai_format_failed.emit()
        except CorrectionError as e:
            log.warning("AI Format error: %s", e)
            self._bridge.ai_format_failed.emit()

    # ─────────────────────────────────────────────────────
    #  FINAL RESULT (main thread)
    # ─────────────────────────────────────────────────────

    def _on_ai_format_completed(self, text: str) -> None:
        log.debug("AI format completed, pending_paste=%s", self._pending_paste_context)
        self._overlay.on_ai_format_completed(text)

        # Auto-copy exactly as we do for raw transcript
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

        # Use cached context — overlay state may have drifted during AI processing
        if self._pending_paste_context:
            self._pending_paste_context = False
            def _do_paste():
                self._keyboard.press(Key.cmd)
                self._keyboard.press('v')
                self._keyboard.release('v')
                self._keyboard.release(Key.cmd)
                log.debug("Auto-pasted AI text via Cmd+V")
                self._overlay.transition_to(OverlayState.RESULT_FIELD, text=text)

            QTimer.singleShot(50, _do_paste)

    def _on_final_transcript(self, text: str) -> None:
        log.info("Final transcript: %r", text[:80])

        # Auto-copy to clipboard
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            log.debug("Copied to clipboard")

        # Cache typing context BEFORE transitioning — overlay state may drift
        # during AI processing (focus timer, state transitions, etc.)
        is_typing = self._overlay.is_typing_context
        is_ai = self._overlay._ai_mode_active
        self._pending_paste_context = is_typing and is_ai
        log.debug("Context cache: typing=%s ai=%s pending_paste=%s", is_typing, is_ai, self._pending_paste_context)

        # Add to history
        self._history.add(text, duration_s=self._total_duration)
        self._menubar.refresh_after_transcription()

        # ALWAYS transition to notepad first so we unroll and evaluate AI states
        self._overlay.transition_to(
            OverlayState.RESULT_NOTEPAD,
            text=text,
            duration=self._total_duration,
            ai_show_original=self._settings.get("ai_show_original", False),
        )

        # If in a typing context AND we are not doing AI formatting, paste immediately
        if is_typing and not is_ai:
            def _do_paste():
                # Simulate Cmd+V (macOS) to paste clipboard contents
                self._keyboard.press(Key.cmd)
                self._keyboard.press('v')
                self._keyboard.release('v')
                self._keyboard.release(Key.cmd)
                log.debug("Auto-pasted raw text via Cmd+V")
                self._overlay.transition_to(OverlayState.RESULT_FIELD, text=text)

            # Small delay to ensure clipboard is populated before pasting
            QTimer.singleShot(50, _do_paste)

        self._menubar.set_idle()
        log.debug("Overlay state: %s", self._overlay.state)

    def _on_transcription_error(self) -> None:
        self._overlay.transition_to(OverlayState.IDLE)
        self._menubar.set_idle()

    def _on_device_error(self, msg: str) -> None:
        log.error("Device error: %s", msg)
        self._is_recording = False
        self._overlay.transition_to(OverlayState.IDLE)
        self._menubar.set_idle()

    def _on_permission_error(self, msg: str) -> None:
        log.error("Permission error: %s", msg)
        QMessageBox.warning(
            None, "Scribr — Permission Required", msg,
        )

    # ─────────────────────────────────────────────────────
    #  MENUBAR CALLBACKS
    # ─────────────────────────────────────────────────────

    def _on_record_toggle(self, recording: bool) -> None:
        if recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _on_test_mic(self) -> None:
        self._start_recording()
        QTimer.singleShot(2000, self._stop_recording)

    def _on_history_clicked(self, entry: dict) -> None:
        log.debug("History item clicked: %s...", entry.get("text", "")[:20])
        self._overlay.transition_to(
            OverlayState.RESULT_NOTEPAD,
            history_entry=entry,
            ai_show_original=self._settings.get("ai_show_original", False),
        )
        self._menubar.set_idle()

    # ─────────────────────────────────────────────────────
    #  SETTINGS
    # ─────────────────────────────────────────────────────

    def _show_settings_window(self) -> None:
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._settings, self._stats)
            self._settings_window.settings_saved.connect(self._on_settings_saved)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

        screen = self._qt_app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self._settings_window.width()) // 2 + geo.x()
            y = (geo.height() - self._settings_window.height()) // 3 + geo.y()
            self._settings_window.move(x, y)

    def _on_settings_saved(self) -> None:
        self._settings.load()
        self._rebuild_transcriber()

        # Swap hotkey target (no listener restart — avoids macOS CGEvent tap race)
        self._hotkey.set_key(self._settings.get("hotkey", "alt_r"))

        # Update overlay position
        self._overlay.set_position(
            self._settings.get("overlay_position", "bottom_centre")
        )

    # ─────────────────────────────────────────────────────
    #  THEME
    # ─────────────────────────────────────────────────────

    def _watch_appearance_changes(self) -> None:
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
        if self._settings_window and self._settings_window.isVisible():
            self._settings_window.update()

    def run(self) -> None:
        sys.exit(self._qt_app.exec())


def main() -> None:
    app = ScribrApp()
    app.run()


if __name__ == "__main__":
    main()
