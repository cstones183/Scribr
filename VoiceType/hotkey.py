# hotkey.py — Listens globally for a configurable hotkey tap (toggle).
# First tap fires on_toggle(True), second tap fires on_toggle(False).
#
# Uses dual detection for reliability in PyInstaller bundles:
#   1. QTimer polling CGEventSourceKeyState every 50ms
#   2. pynput keyboard.Listener as fallback
# Only key-down is detected — no release tracking needed.

import logging
import threading
import time

from collections.abc import Callable

from PyQt6.QtCore import QTimer

log = logging.getLogger("scribr.hotkey")

# macOS virtual key codes for CGEventSourceKeyState
_VKEY_MAP: dict[str, int] = {
    "alt_r": 0x3D,    # 61
    "cmd_r": 0x36,    # 54
    "ctrl_r": 0x3E,   # 62
    "f1": 0x7A, "f2": 0x78, "f3": 0x63, "f4": 0x76,
    "f5": 0x60, "f6": 0x61, "f7": 0x62, "f8": 0x64,
    "f9": 0x65, "f10": 0x6D, "f11": 0x67, "f12": 0x6F,
}

# Debounce: ignore a repeated key-down edge within this window (seconds).
# Only needs to absorb hardware bounce / poll jitter while the key is held —
# a deliberate second tap requires a physical release first, so a tight
# window keeps tap-to-stop responsive without swallowing real taps.
_DEBOUNCE_S = 0.25


def key_display_name(key_name: str) -> str:
    """Human-readable label for a key config value."""
    _DISPLAY = {
        "alt_r": "Right \u2325",
        "cmd_r": "Right \u2318",
        "ctrl_r": "Right \u2303",
        "f1": "F1",
        "f2": "F2",
        "f3": "F3",
    }
    return _DISPLAY.get(key_name, key_name)


class HotkeyListener:
    """Listens for a configurable hotkey tap to toggle recording.

    First tap fires on_toggle(True)  — start recording.
    Second tap fires on_toggle(False) — stop recording.

    Uses dual detection:
      1. QTimer polls CGEventSourceKeyState every 50ms (main thread)
      2. pynput keyboard.Listener as fallback (background thread)
    """

    def __init__(
        self,
        on_toggle: Callable[[bool], None],
        on_permission_error: Callable[[str], None] | None = None,
        key_name: str = "alt_r",
    ):
        self._on_toggle = on_toggle
        self._on_permission_error = on_permission_error
        self._target_vkey = _VKEY_MAP.get(key_name, 0x3D)
        self._key_name = key_name
        self._active = False          # True = recording, False = idle
        self._key_down = False         # physical key state
        self._last_toggle_time = 0.0   # debounce
        self._running = False
        self._lock = threading.Lock()

        # CGEventSourceKeyState function reference
        self._cg_key_state = None
        self._cg_source_state = None

        # QTimer for polling
        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._poll_tick)
        self._tick_count = 0

        # pynput listener (fallback)
        self._pynput_listener = None
        self._pynput_target_key = None

    def start(self) -> None:
        """Start both polling and pynput listener."""
        if self._running:
            return
        self._running = True

        # ── 1. Start CGEventSourceKeyState polling ──
        try:
            from Quartz import CGEventSourceKeyState
            from Quartz import kCGEventSourceStateHIDSystemState
            self._cg_key_state = CGEventSourceKeyState
            self._cg_source_state = kCGEventSourceStateHIDSystemState
            self._timer.start()
            log.info(
                "Hotkey polling started (key=%s, vkey=0x%02X)",
                self._key_name, self._target_vkey,
            )
        except ImportError:
            log.warning("Quartz not available — polling disabled")

        # ── 2. Start pynput listener as fallback ──
        try:
            from pynput import keyboard

            key_map = {
                "alt_r": keyboard.Key.alt_r,
                "cmd_r": keyboard.Key.cmd_r,
                "ctrl_r": keyboard.Key.ctrl_r,
            }
            for i in range(1, 13):
                key_map[f"f{i}"] = getattr(keyboard.Key, f"f{i}")

            self._pynput_target_key = key_map.get(self._key_name, keyboard.Key.alt_r)
            self._pynput_listener = keyboard.Listener(
                on_press=self._pynput_press,
                daemon=True,
            )
            self._pynput_listener.start()
            log.info("pynput listener started as fallback")
        except Exception as e:
            log.warning("pynput listener failed: %s", e)

    def stop(self) -> None:
        """Stop all listeners. Safe to call multiple times."""
        self._timer.stop()
        if self._pynput_listener is not None:
            self._pynput_listener.stop()
            self._pynput_listener = None
        self._running = False
        self._key_down = False

    def set_key(self, key_name: str) -> None:
        """Change the target key at runtime."""
        with self._lock:
            self._key_down = False
        self._target_vkey = _VKEY_MAP.get(key_name, 0x3D)
        self._key_name = key_name

        try:
            from pynput import keyboard
            key_map = {
                "alt_r": keyboard.Key.alt_r,
                "cmd_r": keyboard.Key.cmd_r,
                "ctrl_r": keyboard.Key.ctrl_r,
            }
            for i in range(1, 13):
                key_map[f"f{i}"] = getattr(keyboard.Key, f"f{i}")
            self._pynput_target_key = key_map.get(key_name, keyboard.Key.alt_r)
        except ImportError:
            pass

        log.debug("Hotkey changed to %s (vkey=0x%02X)", key_name, self._target_vkey)

    def reset(self) -> None:
        """Reset toggle state to idle (e.g. after cancel)."""
        with self._lock:
            self._active = False

    def set_active(self, active: bool) -> None:
        """Reconcile the toggle state to the app's real recording state.

        Called whenever recording is started or stopped from any source
        (hotkey, menubar, auto-stop) so a later tap always toggles in the
        right direction instead of becoming a silent no-op.
        """
        with self._lock:
            self._active = active

    # ── CGEventSourceKeyState polling (main thread) ───────

    def _poll_tick(self) -> None:
        """Check physical key state via macOS HID system state."""
        self._tick_count += 1

        if self._tick_count % 200 == 0:
            log.debug("Hotkey poll alive (tick=%d, active=%s)", self._tick_count, self._active)

        if self._cg_key_state is None:
            return

        try:
            pressed = self._cg_key_state(self._cg_source_state, self._target_vkey)
        except Exception as e:
            if self._tick_count % 200 == 1:
                log.error("CGEventSourceKeyState error: %s", e)
            return

        self._handle_key_event(pressed, source="poll")

    # ── pynput fallback (background thread) ───────────────

    def _pynput_press(self, key) -> None:
        if key == self._pynput_target_key:
            self._handle_key_event(True, source="pynput")

    # ── Shared key event handler ──────────────────────────

    def _handle_key_event(self, pressed: bool, source: str) -> None:
        """Detect key-down edge and toggle recording state.

        Both detection paths (QTimer poll + pynput) funnel through here.
        We act only on the key-down edge (False → True) and debounce to
        absorb hardware key-repeat/bounce from the two sources observing
        the same physical tap. The callback is fired outside the lock
        based on an explicit flag captured inside it.
        """
        should_fire = False
        new_state = False

        with self._lock:
            was_down = self._key_down
            self._key_down = pressed

            # Only act on the key-down edge (False → True)
            if pressed and not was_down:
                now = time.monotonic()
                if now - self._last_toggle_time >= _DEBOUNCE_S:
                    self._last_toggle_time = now
                    self._active = not self._active
                    new_state = self._active
                    should_fire = True
                    log.info(
                        "Hotkey TOGGLED → %s (by %s)",
                        "RECORDING" if new_state else "IDLE", source,
                    )

        # Fire callback outside the lock
        if should_fire:
            self._on_toggle(new_state)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_active(self) -> bool:
        return self._active
