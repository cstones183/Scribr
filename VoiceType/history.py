# history.py — Stores and retrieves the last 10 transcriptions
# for display in the Scribr menubar history list.

from __future__ import annotations

import json
import time
from pathlib import Path

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Scribr"
_OLD_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VoiceType"
HISTORY_FILE = APP_SUPPORT_DIR / "history.json"
MAX_ITEMS = 10


class HistoryManager:
    """Stores recent transcription clips in a JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or HISTORY_FILE
        self._items: list[dict[str, object]] = []
        self._ensure_dir()
        self._maybe_migrate()
        self._load()

    def _maybe_migrate(self) -> None:
        """One-time migration from old VoiceType data directory."""
        old_file = _OLD_SUPPORT_DIR / "history.json"
        if old_file.exists() and not self._path.exists():
            import shutil

            shutil.copy2(old_file, self._path)

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._items = data[:MAX_ITEMS]
                    return
            except (json.JSONDecodeError, OSError):
                pass
        self._items = []

    def _save(self) -> None:
        self._ensure_dir()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._items, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def add(self, text: str, duration_s: float = 0.0) -> None:
        """Add a transcription to the top of the history list."""
        entry: dict[str, object] = {
            "text": text,
            "duration_s": round(duration_s, 1),
            "timestamp": time.time(),
        }
        self._items.insert(0, entry)
        self._items = self._items[:MAX_ITEMS]
        self._save()

    def get_all(self) -> list[dict[str, object]]:
        """Return all history items (newest first)."""
        return list(self._items)

    def get_recent(self, n: int = 5) -> list[dict[str, object]]:
        """Return the N most recent items."""
        return list(self._items[:n])

    def count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._save()
