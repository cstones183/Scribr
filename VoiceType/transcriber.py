# transcriber.py — Handles transcription via Groq Whisper API (fast, near-real-time)
# or OpenAI Whisper API. Groq runs whisper-large-v3 in ~0.5s for 30s of audio,
# enabling chunked progressive transcription during recording.

import io
import json
from typing import Optional

import requests


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass


class GroqTranscriber:
    """Transcribes audio using Groq's ultra-fast Whisper API.

    Groq runs whisper-large-v3 in ~0.5s for 30s of audio, making it
    ideal for chunked progressive transcription during recording.

    Usage:
        transcriber = GroqTranscriber(api_key="gsk_...")
        text = transcriber.transcribe(wav_bytes)
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def transcribe(
        self,
        wav_bytes: bytes,
        language: Optional[str] = None,
        model: str = "whisper-large-v3",
    ) -> str:
        """Send WAV bytes to Groq Whisper API, return transcribed text.

        Args:
            wav_bytes: Raw WAV file bytes (16kHz mono 16-bit PCM).
            language: ISO 639-1 language code, or None for auto-detect.
            model: Whisper model to use on Groq.

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

        files = {
            "file": ("recording.wav", io.BytesIO(wav_bytes), "audio/wav"),
        }

        try:
            resp = self._session.post(
                GROQ_ENDPOINT,
                data=data,
                files=files,
                timeout=30,
            )
        except requests.RequestException as e:
            raise TranscriptionError(f"Network error: {e}") from e

        if resp.status_code == 429:
            raise TranscriptionError("Rate limited — please wait a moment and try again.")

        if resp.status_code == 401:
            raise TranscriptionError("Invalid Groq API key.")

        if resp.status_code != 200:
            raise TranscriptionError(
                f"Groq API error {resp.status_code}: {resp.text[:200]}"
            )

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

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def transcribe(
        self,
        wav_bytes: bytes,
        language: Optional[str] = None,
        model: str = "whisper-1",
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

        files = {
            "file": ("recording.wav", io.BytesIO(wav_bytes), "audio/wav"),
        }

        try:
            resp = self._session.post(
                OPENAI_ENDPOINT,
                data=data,
                files=files,
                timeout=60,
            )
        except requests.RequestException as e:
            raise TranscriptionError(f"Network error: {e}") from e

        if resp.status_code == 401:
            raise TranscriptionError("Invalid OpenAI API key.")

        if resp.status_code != 200:
            raise TranscriptionError(
                f"OpenAI API error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            result = resp.json()
            return result.get("text", "").strip()
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptionError(f"Invalid API response: {e}") from e
