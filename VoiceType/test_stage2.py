# test_stage2.py — Visual integration test for Stage 2.
# Imports all modules, launches the overlay with simulated RMS
# and progressive transcript updates, transitions through all states.

import math
import sys

from hotkey import HotkeyListener
from overlay import OverlayState, OverlayWindow
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from recorder import Recorder
from settings import SettingsManager


def main():
    app = QApplication(sys.argv)

    # ── Verify all imports ──────────────────────────────────
    print("=== Scribr Stage 2 Integration Test ===\n")

    _sm = SettingsManager()
    print("[OK] SettingsManager loaded")

    hl = HotkeyListener(
        on_press=lambda: print("[Hotkey] press"),
        on_release=lambda: print("[Hotkey] release"),
    )
    print(f"[OK] HotkeyListener created (running={hl.is_running})")

    rec = Recorder()
    print(f"[OK] Recorder created (recording={rec.is_recording})")

    print("[OK] GroqTranscriber class loaded")
    print("[OK] OpenAITranscriber class loaded")

    overlay = OverlayWindow()
    print(f"[OK] OverlayWindow created (state={overlay.state})\n")

    # ── Simulated RMS: sine wave at 2Hz ─────────────────────
    frame_counter = [0]

    def send_rms():
        t = frame_counter[0] / 30.0
        rms = 0.4 + 0.4 * math.sin(2 * math.pi * 2.0 * t)
        overlay.update_rms(rms)
        frame_counter[0] += 1

    rms_timer = QTimer()
    rms_timer.timeout.connect(send_rms)

    # Disable the focus timer so click-away dismiss doesn't interfere
    # with the visual test (no window is "active" in test context).
    overlay._focus_timer.stop()
    overlay._focus_timer.setInterval(999999)

    # ── State sequence ──────────────────────────────────────
    #
    #  0.0s  RECORDING       — red dot + waveform + timer (IDLE is hidden)
    #  3.0s  transcript #1   — triggers LIVE_TRANSCRIBING, notepad drops down
    #  5.0s  transcript #2   — notepad updates
    #  7.0s  transcript #3   — notepad updates
    #  9.0s  RESULT_NOTEPAD  — blue dot "Tap to edit" + notepad with final text
    # 13.0s  RESULT_FIELD    — green dot "Typed into field", auto-dismisses
    # 16.0s  Back to IDLE (hidden)

    def start_sequence():
        # ── Skip IDLE (hidden) — go straight to RECORDING ─────
        print("[Test] -> IDLE state is now hidden (overlay.hide())")
        overlay.transition_to(OverlayState.IDLE)

        def to_recording():
            print("[Test] -> RECORDING state (6 seconds with simulated RMS)")
            overlay.transition_to(OverlayState.RECORDING)
            rms_timer.start(33)  # ~30fps

        # ── Progressive transcript simulation ──────────────────
        def transcript_chunk_1():
            print("[Test] -> Progressive transcript: chunk 1")
            overlay.update_transcript("The quick brown")

        def transcript_chunk_2():
            print("[Test] -> Progressive transcript: chunk 2")
            overlay.update_transcript("The quick brown fox jumps")

        def transcript_chunk_3():
            print("[Test] -> Progressive transcript: chunk 3")
            overlay.update_transcript("The quick brown fox jumps over the lazy dog")

        def to_result_notepad():
            rms_timer.stop()
            print("[Test] -> RESULT_NOTEPAD state (4 seconds)")
            overlay.transition_to(
                OverlayState.RESULT_NOTEPAD,
                text="The quick brown fox jumps over the lazy dog",
            )

        def to_result_field():
            print("[Test] -> RESULT_FIELD state (auto-dismiss ~2.2s)")
            overlay.transition_to(OverlayState.RESULT_FIELD)

        def back_to_idle():
            print("[Test] -> Back to IDLE (window hides)")
            overlay.transition_to(OverlayState.IDLE)
            print("\n[Test] Sequence complete. Overlay is hidden (IDLE).")
            print("       Press Ctrl+C to exit.")

        QTimer.singleShot(500, to_recording)
        QTimer.singleShot(3000, transcript_chunk_1)
        QTimer.singleShot(5000, transcript_chunk_2)
        QTimer.singleShot(7000, transcript_chunk_3)
        QTimer.singleShot(9000, to_result_notepad)
        QTimer.singleShot(13000, to_result_field)
        QTimer.singleShot(16000, back_to_idle)

    # Start after a brief delay to let the event loop settle
    QTimer.singleShot(500, start_sequence)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
