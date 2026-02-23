# hotkey.py — Listens globally for a configurable key hold and release.
# On press: fires on_press callback. On release: fires on_release callback.
# Uses pynput keyboard.Listener.
# Runs in a background daemon thread — never blocks the main thread.

from collections.abc import Callable

from pynput import keyboard

# Map settings key names → pynput Key objects
_KEY_MAP: dict[str, keyboard.Key] = {
    "alt_r": keyboard.Key.alt_r,
    "cmd_r": keyboard.Key.cmd_r,
    "ctrl_r": keyboard.Key.ctrl_r,
}

# F-keys are on KeyCode, accessed via keyboard.Key
for _i in range(1, 13):
    _name = f"f{_i}"
    _KEY_MAP[_name] = getattr(keyboard.Key, _name)


def key_display_name(key_name: str) -> str:
    """Human-readable label for a key config value."""
    _DISPLAY = {
        "alt_r": "Right ⌥",
        "cmd_r": "Right ⌘",
        "ctrl_r": "Right ⌃",
        "f1": "F1",
        "f2": "F2",
        "f3": "F3",
    }
    return _DISPLAY.get(key_name, key_name)


class HotkeyListener:
    """Listens for a configurable key hold and release.

    Usage:
        listener = HotkeyListener(
            on_press=lambda: print("Recording..."),
            on_release=lambda: print("Stopped."),
            on_permission_error=lambda msg: print(f"Error: {msg}"),
            key_name="alt_r",
        )
        listener.start()
        # ... later ...
        listener.stop()
    """

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        on_permission_error: Callable[[str], None] | None = None,
        key_name: str = "alt_r",
    ):
        self._on_press = on_press
        self._on_release = on_release
        self._on_permission_error = on_permission_error
        self._target_key = _KEY_MAP.get(key_name, keyboard.Key.alt_r)
        self._listener: keyboard.Listener | None = None
        self._is_held = False
        self._running = False

    def start(self):
        """Start listening for Right Option key on a daemon thread.

        If macOS Accessibility permission is not granted, catches the
        exception and calls on_permission_error with a descriptive message.
        """
        if self._running:
            return

        try:
            self._listener = keyboard.Listener(
                on_press=self._handle_press,
                on_release=self._handle_release,
                daemon=True,
            )
            self._listener.start()
            self._running = True
        except Exception as e:
            msg = str(e)
            if self._on_permission_error:
                if "accessibility" in msg.lower() or "trusted" in msg.lower():
                    self._on_permission_error(
                        "Scribr needs Accessibility permission. "
                        "Go to System Settings > Privacy & Security > Accessibility "
                        "and add this app."
                    )
                else:
                    self._on_permission_error(f"Hotkey listener failed: {msg}")

    def stop(self):
        """Stop the listener. Safe to call multiple times."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._running = False
        self._is_held = False

    def set_key(self, key_name: str) -> None:
        """Change the target key at runtime (thread-safe, no restart needed)."""
        self._is_held = False  # reset held state for old key
        self._target_key = _KEY_MAP.get(key_name, keyboard.Key.alt_r)

    def _handle_press(self, key):
        """Filter for target key, fire on_press once per physical key-down."""
        if key == self._target_key and not self._is_held:
            self._is_held = True
            self._on_press()

    def _handle_release(self, key):
        """Filter for target key, reset held state and fire on_release."""
        if key == self._target_key and self._is_held:
            self._is_held = False
            self._on_release()

    @property
    def is_running(self) -> bool:
        return self._running
