# history.py — Stores and retrieves the last 10 transcriptions
# for display in the menubar history list.

import json
import os
import time
from pathlib import Path
from typing import Any

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VoiceType"
HISTORY_FILE = APP_SUPPORT_DIR / "history.json"
MAX_ITEMS = 10


class HistoryManager:
    """Stores recent transcription clips in a JSON file."""

    def __init__(self):
        self._path = HISTORY_FILE
        self._items: list[dict] = []
        self._ensure_dir()
        self._load()

    def _ensure_dir(self):
        APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._items = data[:MAX_ITEMS]
                    return
            except (json.JSONDecodeError, OSError):
                pass
        self._items = []

    def _save(self):
        self._ensure_dir()
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._items, f, indent=2)
        os.replace(tmp, self._path)

    def add(self, text: str, duration_s: float = 0.0):
        """Add a transcription to the top of the history list."""
        entry = {
            "text": text,
            "duration_s": round(duration_s, 1),
            "timestamp": time.time(),
        }
        self._items.insert(0, entry)
        self._items = self._items[:MAX_ITEMS]
        self._save()

    def get_all(self) -> list[dict]:
        """Return all history items (newest first)."""
        return list(self._items)

    def get_recent(self, n: int = 5) -> list[dict]:
        """Return the N most recent items."""
        return list(self._items[:n])

    def count(self) -> int:
        return len(self._items)

    def clear(self):
        self._items.clear()
        self._save()
