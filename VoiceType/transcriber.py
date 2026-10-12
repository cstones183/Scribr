# transcriber.py — Handles transcription via Groq Whisper API (fast, near-real-time)
# or OpenAI Whisper API. Groq runs whisper-large-v3-turbo in ~0.3s for 30s of audio,
# enabling chunked progressive transcription during recording.

from __future__ import annotations

import io
import json
import socket
import threading
from collections.abc import Callable
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


def retrying_session(api_key: str) -> requests.Session:
    """Session that retries dropped connections, including on POST.

    Pooled keep-alive connections go stale while the app sits idle; the next
    request then dies instantly with RemoteDisconnected / BrokenPipe. Without
    a retry that silently lost whole recordings.
    """
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {api_key}"
    retry = Retry(
        total=2, connect=1, read=1, status=0,
        allowed_methods=None,  # None = retry any verb; these POSTs are safe to resend
        backoff_factor=0.3,
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class TranscriptionError(Exception):
    """Raised when transcription fails."""

    pass


class NetworkError(TranscriptionError):
    """No internet connection: the audio is fine, so it can be resent later."""


def is_online(url: str, timeout: float = 3.0) -> bool:
    """True if the API host resolves within ``timeout`` seconds.

    Offline, macOS DNS lookups block ~25s each and ignore requests' timeout,
    which (with retries) left the spinner up for 90s. So resolve on a thread
    with a hard deadline.
    ponytail: a slow-but-working DNS (>3s) reads as offline; the recording is
    queued and resent, so the cost is a delay, not lost audio.
    """
    host = urlparse(url).hostname
    found: list[bool] = []

    def _resolve() -> None:
        try:
            socket.getaddrinfo(host, 443)
            found.append(True)
        except OSError:
            pass

    t = threading.Thread(target=_resolve, daemon=True)
    t.start()
    t.join(timeout)
    return bool(found)


CONNECT_TIMEOUT_S = 5


def _post_audio(session: requests.Session, url: str, data: dict, wav_bytes: bytes, timeout: int):
    if not is_online(url):
        raise NetworkError("No internet connection")
    files = {"file": ("recording.wav", io.BytesIO(wav_bytes), "audio/wav")}
    try:
        # Short connect timeout: on Wi-Fi with no internet the TCP connect just
        # hangs, and the default would make the user wait 30s+ per attempt.
        return session.post(url, data=data, files=files, timeout=(CONNECT_TIMEOUT_S, timeout))
    except requests.ConnectionError as e:
        raise NetworkError("No internet connection") from e
    except requests.RequestException as e:
        raise TranscriptionError(f"Network error: {e}") from e


# USD per hour of audio sent. Groq bills at least 10s per request.
# Rates as of Oct 2026; update if provider pricing changes.
GROQ_USD_PER_HOUR = 0.04  # whisper-large-v3-turbo
GROQ_MIN_BILLED_S = 10
OPENAI_USD_PER_HOUR = 0.36  # whisper-1, $0.006/min


def _audio_seconds(wav_bytes: bytes) -> float:
    return max(0, len(wav_bytes) - 44) / (16000 * 2)  # 16kHz mono 16-bit, 44-byte header


class GroqTranscriber:
    """Transcribes audio using Groq's ultra-fast Whisper API.

    Groq runs whisper-large-v3 in ~0.5s for 30s of audio, making it
    ideal for chunked progressive transcription during recording.

    Usage:
        transcriber = GroqTranscriber(api_key="gsk_...")
        text = transcriber.transcribe(wav_bytes)
    """

    def __init__(self, api_key: str, on_cost: Callable[[float], None] | None = None):
        self._api_key = api_key
        self._session = retrying_session(api_key)
        self._on_cost = on_cost  # called with USD for every billed request

    def transcribe(
        self,
        wav_bytes: bytes,
        language: str | None = None,
        model: str = "whisper-large-v3-turbo",
        prompt: str = "",
    ) -> str:
        """Send WAV bytes to Groq Whisper API, return transcribed text.

        Args:
            wav_bytes: Raw WAV file bytes (16kHz mono 16-bit PCM).
            language: ISO 639-1 language code, or None for auto-detect.
            model: Whisper model to use on Groq (turbo is faster and cheaper).
            prompt: Initial prompt to bias transcription style/spelling.

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If the API call fails.
        """
        if not wav_bytes or len(wav_bytes) < 100:
            return ""

        data = {
            "model": model,
            "response_format": "json",
        }
        if language and language != "auto":
            data["language"] = language
        if prompt:
            data["prompt"] = prompt

        resp = _post_audio(self._session, GROQ_ENDPOINT, data, wav_bytes, timeout=30)

        if resp.status_code == 429:
            raise TranscriptionError("Rate limited — please wait a moment and try again.")

        if resp.status_code == 401:
            raise TranscriptionError("Invalid Groq API key.")

        if resp.status_code != 200:
            raise TranscriptionError(f"Groq API error {resp.status_code}: {resp.text[:200]}")
        if self._on_cost:
            billed = max(_audio_seconds(wav_bytes), GROQ_MIN_BILLED_S)
            self._on_cost(billed / 3600 * GROQ_USD_PER_HOUR)

        try:
            result = resp.json()
            return result.get("text", "").strip()
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptionError(f"Invalid API response: {e}") from e


class OpenAITranscriber:
    """Transcribes audio using OpenAI's Whisper API.

    Slower than Groq (~2-5s) but uses the same API key as GPT-4o-mini cleanup.

    Usage:
        transcriber = OpenAITranscriber(api_key="sk-...")
        text = transcriber.transcribe(wav_bytes)
    """

    def __init__(self, api_key: str, on_cost: Callable[[float], None] | None = None):
        self._api_key = api_key
        self._session = retrying_session(api_key)
        self._on_cost = on_cost  # called with USD for every billed request

    def transcribe(
        self,
        wav_bytes: bytes,
        language: str | None = None,
        model: str = "whisper-1",
        prompt: str = "",
    ) -> str:
        """Send WAV bytes to OpenAI Whisper API, return transcribed text."""
        if not wav_bytes or len(wav_bytes) < 100:
            return ""

        data = {
            "model": model,
            "response_format": "json",
        }
        if language and language != "auto":
            data["language"] = language
        if prompt:
            data["prompt"] = prompt

        resp = _post_audio(self._session, OPENAI_ENDPOINT, data, wav_bytes, timeout=60)

        if resp.status_code == 401:
            raise TranscriptionError("Invalid OpenAI API key.")

        if resp.status_code != 200:
            raise TranscriptionError(f"OpenAI API error {resp.status_code}: {resp.text[:200]}")
        if self._on_cost:
            self._on_cost(_audio_seconds(wav_bytes) / 3600 * OPENAI_USD_PER_HOUR)

        try:
            result = resp.json()
            return result.get("text", "").strip()
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptionError(f"Invalid API response: {e}") from e


