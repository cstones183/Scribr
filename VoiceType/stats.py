# stats.py — Rolling usage statistics manager for Scribr.
# Tracks monthly API costs, recording duration, and clip counts.

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Scribr"
STATS_FILE = APP_SUPPORT_DIR / "stats.json"

class StatsManager:
    """Manages monthly rolling statistics for transcriptions and API costs."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or STATS_FILE
        self._current_month = ""
        self._month_clips = 0
        self._month_duration_s = 0.0
        self._month_api_cost = 0.0
        self._ensure_dir()
        self._load()
        self._check_rollover()

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _get_system_month(self) -> str:
        """Returns the current month string, e.g. '2026-02'."""
        return datetime.now().strftime("%Y-%m")

    def _check_rollover(self) -> None:
        """Reset stats if the calendar month changes."""
        system_month = self._get_system_month()
        if not self._current_month:
            # First run
            self._current_month = system_month
            self.save()
            return
        
        if self._current_month != system_month:
            self._current_month = system_month
            self._month_clips = 0
            self._month_duration_s = 0.0
            self._month_api_cost = 0.0
            self.save()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._current_month = data.get("current_month", "")
                self._month_clips = data.get("month_clips", 0)
                self._month_duration_s = data.get("month_duration_s", 0.0)
                self._month_api_cost = data.get("month_api_cost", 0.0)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self._ensure_dir()
        data = {
            "current_month": self._current_month,
            "month_clips": self._month_clips,
            "month_duration_s": self._month_duration_s,
            "month_api_cost": self._month_api_cost
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    @property
    def clips(self) -> int:
        self._check_rollover()
        return self._month_clips

    @property
    def duration_s(self) -> float:
        self._check_rollover()
        return self._month_duration_s

    @property
    def cost(self) -> float:
        self._check_rollover()
        return self._month_api_cost

    def add_clip(self, duration_s: float, cost: float = 0.0) -> None:
        """Increment current month's stats and save persistently."""
        self._check_rollover()
        self._month_clips += 1
        self._month_duration_s += duration_s
        self._month_api_cost += cost
        self.save()

    def add_cost(self, cost: float) -> None:
        """Add incremental API cost (e.g. for ChatGPT cleanup) persistently."""
        if cost <= 0:
            return
        self._check_rollover()
        self._month_api_cost += cost
        self.save()
