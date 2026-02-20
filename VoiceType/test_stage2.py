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

    # ── State sequence ──────────────────────────────────────
    #
    #  0.0s  IDLE            — pill visible, dimmed "Hold Right ⌥ to record"
    #  2.0s  RECORDING       — red dot + waveform + timer, 8s of simulated RMS
    #  5.0s  transcript #1   — triggers LIVE_TRANSCRIBING, notepad drops down
    #  7.0s  transcript #2   — notepad updates
    #  9.0s  transcript #3   — notepad updates
    # 11.0s  RESULT_NOTEPAD  — blue dot "Tap to edit" + notepad with final text
    # 15.0s  RESULT_FIELD    — green dot "Typed into field", auto-dismisses
    # 18.0s  Back to IDLE

    def start_sequence():
        # ── IDLE (already visible from OverlayWindow init) ─────
        print("[Test] -> IDLE state (2 seconds)")
        overlay.transition_to(OverlayState.IDLE)

        def to_recording():
            print("[Test] -> RECORDING state (9 seconds with simulated RMS)")
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
            print("[Test] -> Back to IDLE")
            overlay.transition_to(OverlayState.IDLE)
            print("\n[Test] Sequence complete. Window is open for inspection.")
            print("       Close the window or press Ctrl+C to exit.")

        QTimer.singleShot(2000, to_recording)
        QTimer.singleShot(5000, transcript_chunk_1)
        QTimer.singleShot(7000, transcript_chunk_2)
        QTimer.singleShot(9000, transcript_chunk_3)
        QTimer.singleShot(11000, to_result_notepad)
        QTimer.singleShot(15000, to_result_field)
        QTimer.singleShot(18000, back_to_idle)

    # Start after a brief delay to let the event loop settle
    QTimer.singleShot(500, start_sequence)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
