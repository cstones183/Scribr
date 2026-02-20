# hotkey.py — Listens globally for Right Option key hold and release.
# On press: fires on_press callback. On release: fires on_release callback.
# Uses pynput keyboard.Listener watching specifically for Key.alt_r.
# Runs in a background daemon thread — never blocks the main thread.

from collections.abc import Callable

from pynput import keyboard


class HotkeyListener:
    """Listens for Right Option (Key.alt_r) hold and release.

    Usage:
        listener = HotkeyListener(
            on_press=lambda: print("Recording..."),
            on_release=lambda: print("Stopped."),
            on_permission_error=lambda msg: print(f"Error: {msg}"),
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
    ):
        self._on_press = on_press
        self._on_release = on_release
        self._on_permission_error = on_permission_error
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

    def _handle_press(self, key):
        """Filter for Key.alt_r, fire on_press once per physical key-down."""
        if key == keyboard.Key.alt_r and not self._is_held:
            self._is_held = True
            self._on_press()

    def _handle_release(self, key):
        """Filter for Key.alt_r, reset held state and fire on_release."""
        if key == keyboard.Key.alt_r and self._is_held:
            self._is_held = False
            self._on_release()

    @property
    def is_running(self) -> bool:
        return self._running
