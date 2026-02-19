# recorder.py — Captures microphone audio using sounddevice.
# Streams 16kHz mono PCM audio while emitting live RMS amplitude values
# to a callback for driving the waveform animation.
# Returns WAV bytes in memory (no disk writes) on stop().

import io
import math
import threading
import wave
from collections import deque
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
BLOCK_SIZE = 512          # ~32ms per block at 16kHz → ~31 callbacks/sec
MAX_RECORDING_SECONDS = 300  # 5 minutes auto-stop


class Recorder:
    """Captures microphone audio and provides live RMS for waveform animation.

    Usage:
        rec = Recorder(on_device_error=lambda msg: print(msg))
        rec.start(on_rms_update=lambda rms: overlay.update_rms(rms))
        # ... user speaks ...
        wav_bytes = rec.stop()
    """

    def __init__(self, on_device_error: Optional[Callable[[str], None]] = None):
        self._on_device_error = on_device_error
        self._stream: Optional[sd.InputStream] = None
        self._frames: list[bytes] = []
        self._is_recording = False
        self._rms_history: deque = deque(maxlen=3)
        self._start_time: float = 0.0
        self._auto_stop_timer: Optional[threading.Timer] = None
        self._on_rms_update: Optional[Callable[[float], None]] = None
        self._auto_stopped_wav: Optional[bytes] = None

    def start(self, on_rms_update: Callable[[float], None]):
        """Begin recording from the default input device.

        Args:
            on_rms_update: Called ~30 times/sec with a normalised RMS
                value (0.0–1.0). Called on the audio thread — caller is
                responsible for marshalling to the UI thread.
        """
        if self._is_recording:
            return

        self._frames = []
        self._rms_history.clear()
        self._on_rms_update = on_rms_update
        self._auto_stopped_wav = None

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._is_recording = True
        except (sd.PortAudioError, OSError) as e:
            if self._on_device_error:
                self._on_device_error(
                    f"Microphone not available: {e}"
                )
            return

        # Auto-stop safety timer
        self._auto_stop_timer = threading.Timer(
            MAX_RECORDING_SECONDS, self._auto_stop
        )
        self._auto_stop_timer.daemon = True
        self._auto_stop_timer.start()

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes.

        If the recorder was auto-stopped (exceeded 5 minutes), returns
        the WAV bytes that were captured up to that point.
        """
        if self._auto_stopped_wav is not None:
            wav = self._auto_stopped_wav
            self._auto_stopped_wav = None
            return wav

        self._cancel_auto_stop()

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False
        return self._build_wav()

    def _auto_stop(self):
        """Called by the safety timer after MAX_RECORDING_SECONDS."""
        if not self._is_recording:
            return

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False
        self._auto_stopped_wav = self._build_wav()

    def _cancel_auto_stop(self):
        if self._auto_stop_timer is not None:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info, status):
        """Called by sounddevice on the audio thread for each block.

        Appends raw bytes, computes smoothed RMS, and fires the callback.
        """
        # Store raw audio
        self._frames.append(indata.tobytes())

        # Compute RMS normalised to 0.0–1.0
        samples = indata[:, 0].astype(np.float64)
        rms = math.sqrt(np.mean(samples ** 2)) / 32768.0
        rms = min(rms, 1.0)

        # Smooth with rolling average
        self._rms_history.append(rms)
        smoothed = sum(self._rms_history) / len(self._rms_history)

        if self._on_rms_update:
            self._on_rms_update(smoothed)

    def get_wav_snapshot(self) -> bytes:
        """Return WAV bytes of all audio captured so far, without stopping.

        Thread-safe: takes a snapshot copy of the frames list.
        Useful for progressive/chunked transcription during recording.
        """
        if not self._is_recording:
            return b""
        frames_copy = list(self._frames)
        return self._build_wav_from(frames_copy)

    def _build_wav(self) -> bytes:
        """Assemble all recorded frames into a WAV byte buffer."""
        return self._build_wav_from(self._frames)

    @staticmethod
    def _build_wav_from(frames: list) -> bytes:
        """Assemble a list of raw PCM frames into a WAV byte buffer."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    @property
    def is_recording(self) -> bool:
        return self._is_recording
