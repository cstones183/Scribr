"""Tests for Recorder failure and auto-stop paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import recorder
from recorder import Recorder


def test_failed_start_closes_stream_and_reports() -> None:
    stream = MagicMock()
    stream.start.side_effect = recorder.sd.PortAudioError("boom")
    errors: list[str] = []
    with patch.object(recorder.sd, "InputStream", return_value=stream):
        ok = Recorder(on_device_error=errors.append).start(lambda _: None)
    assert ok is False
    stream.close.assert_called_once()
    assert errors and "boom" in errors[0]


def test_auto_stop_notifies_app_and_keeps_audio() -> None:
    fired: list[bool] = []
    with patch.object(recorder.sd, "InputStream", return_value=MagicMock()):
        rec = Recorder(on_auto_stop=lambda: fired.append(True))
        assert rec.start(lambda _: None) is True
        rec._cancel_auto_stop()
        rec._frames = [b"\x00\x00" * 160]
        rec._auto_stop()
    assert fired == [True]
    assert len(rec.stop()) > 44  # WAV header + captured frames
