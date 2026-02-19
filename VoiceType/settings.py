# settings.py — JSON settings manager (data layer only).
# Persists to ~/Library/Application Support/VoiceType/settings.json
# UI lives in settings_window.py + widgets.py.

import json
import os
from pathlib import Path
from typing import Any


# ── Paths & Defaults ────────────────────────────────────────

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VoiceType"
SETTINGS_FILE = APP_SUPPORT_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "openai_api_key": "",
    "deepgram_api_key": "",
    "assemblyai_api_key": "",
    "groq_api_key": "",
    "transcription_mode": "api",        # "api" | "local"
    "local_model_size": "base",          # "tiny" | "base" | "small" | "medium"
    "language": "auto",
    "ai_cleanup": True,
    "confidence_highlights": True,
    "hotkey": "alt_r",
    "show_overlay": True,
    "overlay_position": "bottom_centre",
    "theme": "navy",                     # "navy" | "slate" | "black"
    "reduce_motion": False,
}

LANGUAGES = [
    ("Auto-detect", "auto"),
    ("English", "en"), ("Spanish", "es"), ("French", "fr"),
    ("German", "de"), ("Italian", "it"), ("Portuguese", "pt"),
    ("Russian", "ru"), ("Japanese", "ja"), ("Korean", "ko"),
    ("Chinese", "zh"), ("Arabic", "ar"), ("Hindi", "hi"),
    ("Dutch", "nl"), ("Polish", "pl"), ("Turkish", "tr"),
    ("Swedish", "sv"), ("Czech", "cs"), ("Danish", "da"),
    ("Finnish", "fi"), ("Greek", "el"),
]


# ════════════════════════════════════════════════════════════
#  DATA LAYER — SettingsManager (no Qt dependency)
# ════════════════════════════════════════════════════════════

class SettingsManager:
    """Pure data class for reading/writing settings JSON.
    Thread-safe reads via as_dict() copy."""

    def __init__(self):
        self._path = SETTINGS_FILE
        self._data: dict = {}
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    stored = json.load(f)
            except (json.JSONDecodeError, OSError):
                stored = {}
        else:
            stored = {}
        # Merge with defaults — stored values override defaults
        self._data = {**DEFAULT_SETTINGS, **stored}

    def save(self):
        self._ensure_dir()
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def as_dict(self) -> dict:
        return dict(self._data)
