# settings.py — JSON settings manager (data layer only).
# Persists to ~/Library/Application Support/Scribr/settings.json
# UI lives in settings_window.py + widgets.py.

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Scribr"
_OLD_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VoiceType"
SETTINGS_FILE = APP_SUPPORT_DIR / "settings.json"


# ── Settings dataclass ─────────────────────────────────────


@dataclass
class AppSettings:
    """Typed, validated settings with defaults."""

    openai_api_key: str = ""
    deepgram_api_key: str = ""
    assemblyai_api_key: str = ""
    groq_api_key: str = ""
    transcription_mode: str = "api"  # "api" | "local"
    local_model_size: str = "base"  # "tiny" | "base" | "small" | "medium"
    language: str = "auto"
    ai_cleanup: bool = True
    confidence_highlights: bool = True
    hotkey: str = "alt_r"
    show_overlay: bool = True
    overlay_position: str = "bottom_centre"
    reduce_motion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        """Create from dict, ignoring unknown keys."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# Back-compat alias for code that references DEFAULT_SETTINGS dict
DEFAULT_SETTINGS = AppSettings().to_dict()


LANGUAGES: list[tuple[str, str]] = [
    ("Auto-detect", "auto"),
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Russian", "ru"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Chinese", "zh"),
    ("Arabic", "ar"),
    ("Hindi", "hi"),
    ("Dutch", "nl"),
    ("Polish", "pl"),
    ("Turkish", "tr"),
    ("Swedish", "sv"),
    ("Czech", "cs"),
    ("Danish", "da"),
    ("Finnish", "fi"),
    ("Greek", "el"),
]


# ════════════════════════════════════════════════════════════
#  DATA LAYER — SettingsManager (no Qt dependency)
# ════════════════════════════════════════════════════════════


class SettingsManager:
    """Pure data class for reading/writing settings JSON.
    Thread-safe reads via as_dict() copy."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or SETTINGS_FILE
        self._settings = AppSettings()
        self._ensure_dir()
        self._maybe_migrate()
        self.load()

    def _maybe_migrate(self) -> None:
        """One-time migration from old VoiceType data directory."""
        old_file = _OLD_SUPPORT_DIR / "settings.json"
        if old_file.exists() and not self._path.exists():
            import shutil

            shutil.copy2(old_file, self._path)

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        if self._path.exists():
            try:
                stored = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                stored = {}
        else:
            stored = {}
        # Merge: stored values override defaults
        merged = {**self._settings.to_dict(), **stored}
        self._settings = AppSettings.from_dict(merged)

    def save(self) -> None:
        self._ensure_dir()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._settings.to_dict(), indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.to_dict().get(key, default)

    def set(self, key: str, value: Any) -> None:
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)

    def as_dict(self) -> dict[str, Any]:
        return self._settings.to_dict()
