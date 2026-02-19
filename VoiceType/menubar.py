# menubar.py — macOS menubar app using rumps.
# Provides system tray icon, dropdown menu, recording control,
# history display, and launches the settings window.

import rumps

from history import HistoryManager


class VoiceTypeMenubar(rumps.App):
    """System tray menubar app for VoiceType.

    Title states:
      🎙  — idle / ready
      🔴  — recording
      ⏳  — transcribing
    """

    def __init__(self, history: HistoryManager | None = None):
        super().__init__(
            name="VoiceType",
            title="🎙",
            quit_button=None,  # we add our own styled quit
        )

        self._history = history or HistoryManager()
        self._recording = False

        # ── Callbacks (wired by app.py) ──────────────────
        self.on_record_toggle = None   # callable(bool) — start/stop
        self.on_open_settings = None   # callable()
        self.on_test_mic = None        # callable()

        self._build_menu()

    # ─────────────────────────────────────────────────────
    #  MENU CONSTRUCTION
    # ─────────────────────────────────────────────────────

    def _build_menu(self):
        self.menu.clear()

        # Header info — non-clickable
        self._status_item = rumps.MenuItem("VoiceType — Ready", callback=None)
        self._status_item.set_callback(None)
        self.menu.add(self._status_item)
        self.menu.add(rumps.separator)

        # Record button
        self._record_item = rumps.MenuItem(
            "🎙  Start Recording        Right ⌥",
            callback=self._on_record_click,
        )
        self.menu.add(self._record_item)
        self.menu.add(rumps.separator)

        # History sub-menu
        self._history_menu = rumps.MenuItem("📋  History")
        self._refresh_history()
        self.menu.add(self._history_menu)
        self.menu.add(rumps.separator)

        # Settings
        self._settings_item = rumps.MenuItem(
            "⚙️  Settings               ⌘,",
            callback=self._on_settings_click,
        )
        self.menu.add(self._settings_item)

        # Test Microphone
        self._test_mic_item = rumps.MenuItem(
            "🎤  Test Microphone",
            callback=self._on_test_mic_click,
        )
        self.menu.add(self._test_mic_item)
        self.menu.add(rumps.separator)

        # Quit
        self._quit_item = rumps.MenuItem(
            "✕  Quit VoiceType",
            callback=self._on_quit,
        )
        self.menu.add(self._quit_item)

    # ─────────────────────────────────────────────────────
    #  HISTORY
    # ─────────────────────────────────────────────────────

    def _refresh_history(self):
        """Rebuild the history sub-menu from HistoryManager."""
        # Clear existing sub-items
        for key in list(self._history_menu.keys()):
            del self._history_menu[key]

        items = self._history.get_recent(5)
        if not items:
            empty = rumps.MenuItem("No clips yet", callback=None)
            empty.set_callback(None)
            self._history_menu.add(empty)
        else:
            count = self._history.count()
            self._history_menu.title = f"📋  History ({count} clip{'s' if count != 1 else ''})"
            for entry in items:
                text = entry.get("text", "")
                truncated = (text[:42] + "...") if len(text) > 45 else text
                item = rumps.MenuItem(truncated, callback=None)
                item.set_callback(None)
                self._history_menu.add(item)

    def refresh_after_transcription(self):
        """Call after a new transcription is added to history."""
        self._refresh_history()

    # ─────────────────────────────────────────────────────
    #  STATE UPDATES
    # ─────────────────────────────────────────────────────

    def set_recording(self, recording: bool):
        self._recording = recording
        if recording:
            self.title = "🔴"
            self._status_item.title = "VoiceType — Recording"
            self._record_item.title = "⏹  Stop Recording         Right ⌥"
        else:
            self.title = "🎙"
            self._status_item.title = "VoiceType — Ready"
            self._record_item.title = "🎙  Start Recording        Right ⌥"

    def set_transcribing(self):
        self.title = "⏳"
        self._status_item.title = "VoiceType — Transcribing..."
        self._record_item.title = "⏳  Transcribing..."

    def set_idle(self):
        self._recording = False
        self.title = "🎙"
        self._status_item.title = "VoiceType — Ready"
        self._record_item.title = "🎙  Start Recording        Right ⌥"

    # ─────────────────────────────────────────────────────
    #  CALLBACKS
    # ─────────────────────────────────────────────────────

    def _on_record_click(self, sender):
        new_state = not self._recording
        self.set_recording(new_state)
        if self.on_record_toggle:
            self.on_record_toggle(new_state)

    def _on_settings_click(self, sender):
        if self.on_open_settings:
            self.on_open_settings()

    def _on_test_mic_click(self, sender):
        if self.on_test_mic:
            self.on_test_mic()

    def _on_quit(self, sender):
        rumps.quit_application()
