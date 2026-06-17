"""Tests for SettingsManager and AppSettings dataclass."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from settings import AppSettings, SettingsManager


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Path:
    """Return a temporary settings.json path."""
    return tmp_path / "settings.json"


@pytest.fixture(autouse=True)
def _isolate_migration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Stop the one-time legacy migration from reading the real user's
    ~/Library/Application Support/VoiceType during tests, which would make
    default-value assertions depend on the developer's machine."""
    monkeypatch.setattr("settings._OLD_SUPPORT_DIR", tmp_path / "no_old_support")


class TestAppSettings:
    def test_defaults(self) -> None:
        s = AppSettings()
        assert s.language == "en"
        assert s.ai_cleanup is True
        assert s.reduce_motion is False
        assert s.groq_live_interval == 2
        assert s.show_welcome_on_launch is True
        assert s.accessibility_prompted is False
        # Removed providers should not exist
        assert not hasattr(s, "deepgram_api_key")
        assert not hasattr(s, "assemblyai_api_key")

    def test_to_dict_roundtrip(self) -> None:
        s = AppSettings(openai_api_key="sk-test", language="fr")
        d = s.to_dict()
        assert d["openai_api_key"] == "sk-test"
        assert d["language"] == "fr"

    def test_from_dict_ignores_unknown_keys(self) -> None:
        data = {"openai_api_key": "sk-x", "unknown_key": 42}
        s = AppSettings.from_dict(data)
        assert s.openai_api_key == "sk-x"
        assert not hasattr(s, "unknown_key")

    def test_from_dict_ignores_removed_provider_keys(self) -> None:
        """Old JSON files with deepgram/assemblyai keys should load fine."""
        data = {
            "openai_api_key": "sk-x",
            "deepgram_api_key": "old_key",
            "assemblyai_api_key": "old_key",
        }
        s = AppSettings.from_dict(data)
        assert s.openai_api_key == "sk-x"
        assert not hasattr(s, "deepgram_api_key")

    def test_from_dict_uses_defaults_for_missing(self) -> None:
        s = AppSettings.from_dict({"language": "fr"})
        assert s.language == "fr"
        assert s.ai_cleanup is True  # default preserved


class TestSettingsManager:
    def test_creates_file_on_save(self, tmp_settings: Path) -> None:
        mgr = SettingsManager(path=tmp_settings)
        mgr.set("openai_api_key", "sk-hello")
        mgr.save()
        assert tmp_settings.exists()
        data = json.loads(tmp_settings.read_text())
        assert data["openai_api_key"] == "sk-hello"

    def test_load_merges_with_defaults(self, tmp_settings: Path) -> None:
        tmp_settings.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings.write_text(json.dumps({"language": "fr"}))
        mgr = SettingsManager(path=tmp_settings)
        assert mgr.get("language") == "fr"
        assert mgr.get("ai_cleanup") is True  # default

    def test_get_returns_default_for_missing(self, tmp_settings: Path) -> None:
        mgr = SettingsManager(path=tmp_settings)
        assert mgr.get("nonexistent", "fallback") == "fallback"

    def test_set_and_get(self, tmp_settings: Path) -> None:
        mgr = SettingsManager(path=tmp_settings)
        mgr.set("language", "fr")
        assert mgr.get("language") == "fr"

    def test_as_dict_returns_copy(self, tmp_settings: Path) -> None:
        mgr = SettingsManager(path=tmp_settings)
        d = mgr.as_dict()
        d["language"] = "MUTATED"
        assert mgr.get("language") == "en"  # original unaffected

    def test_load_handles_corrupt_json(self, tmp_settings: Path) -> None:
        tmp_settings.parent.mkdir(parents=True, exist_ok=True)
        tmp_settings.write_text("{corrupt json!!")
        mgr = SettingsManager(path=tmp_settings)
        assert mgr.get("language") == "en"  # fell back to defaults

    def test_save_is_atomic(self, tmp_settings: Path) -> None:
        mgr = SettingsManager(path=tmp_settings)
        mgr.save()
        # No .tmp file should remain
        assert not tmp_settings.with_suffix(".tmp").exists()
