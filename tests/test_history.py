"""Tests for HistoryManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from history import HistoryManager


@pytest.fixture
def tmp_history(tmp_path: Path) -> Path:
    """Return a temporary history.json path."""
    return tmp_path / "history.json"


class TestHistoryManager:
    def test_starts_empty(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        assert mgr.count() == 0
        assert mgr.get_all() == []

    def test_add_and_retrieve(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        mgr.add("Hello world", duration_s=2.5)
        assert mgr.count() == 1
        items = mgr.get_all()
        assert items[0]["text"] == "Hello world"
        assert items[0]["duration_s"] == 2.5

    def test_newest_first(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        mgr.add("First")
        mgr.add("Second")
        mgr.add("Third")
        items = mgr.get_all()
        assert items[0]["text"] == "Third"
        assert items[2]["text"] == "First"

    def test_max_10_items(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        for i in range(15):
            mgr.add(f"Item {i}")
        assert mgr.count() == 10
        assert mgr.get_all()[0]["text"] == "Item 14"

    def test_get_recent(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        for i in range(8):
            mgr.add(f"Item {i}")
        recent = mgr.get_recent(3)
        assert len(recent) == 3
        assert recent[0]["text"] == "Item 7"

    def test_clear(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        mgr.add("Something")
        mgr.clear()
        assert mgr.count() == 0

    def test_persists_to_disk(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        mgr.add("Persisted text")

        # Load fresh instance
        mgr2 = HistoryManager(path=tmp_history)
        assert mgr2.count() == 1
        assert mgr2.get_all()[0]["text"] == "Persisted text"

    def test_handles_corrupt_json(self, tmp_history: Path) -> None:
        tmp_history.parent.mkdir(parents=True, exist_ok=True)
        tmp_history.write_text("not valid json!!")
        mgr = HistoryManager(path=tmp_history)
        assert mgr.count() == 0

    def test_handles_non_list_json(self, tmp_history: Path) -> None:
        tmp_history.parent.mkdir(parents=True, exist_ok=True)
        tmp_history.write_text(json.dumps({"not": "a list"}))
        mgr = HistoryManager(path=tmp_history)
        assert mgr.count() == 0

    def test_get_all_returns_copy(self, tmp_history: Path) -> None:
        mgr = HistoryManager(path=tmp_history)
        mgr.add("Test")
        items = mgr.get_all()
        items.clear()
        assert mgr.count() == 1  # original unaffected
