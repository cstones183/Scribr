"""Tests for offline detection in the transcriber."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

import transcriber
from transcriber import GroqTranscriber, NetworkError, is_online


def test_is_online_gives_up_on_hanging_dns() -> None:
    # Offline macOS DNS blocks ~25s; we must answer within the deadline.
    with patch.object(transcriber.socket, "getaddrinfo", side_effect=lambda *a: time.sleep(5)):
        t = time.time()
        assert is_online("https://api.groq.com/x", timeout=0.2) is False
        assert time.time() - t < 1


def test_offline_raises_network_error_without_posting() -> None:
    g = GroqTranscriber(api_key="k")
    g._session = MagicMock()
    with patch.object(transcriber, "is_online", return_value=False):
        with pytest.raises(NetworkError):
            g.transcribe(b"x" * 200)
    g._session.post.assert_not_called()


def test_connection_error_maps_to_network_error() -> None:
    g = GroqTranscriber(api_key="k")
    g._session = MagicMock()
    g._session.post.side_effect = requests.ConnectionError("unreachable")
    with patch.object(transcriber, "is_online", return_value=True):
        with pytest.raises(NetworkError):
            g.transcribe(b"x" * 200)


def test_groq_reports_cost_with_10s_minimum() -> None:
    costs: list[float] = []
    g = GroqTranscriber(api_key="k", on_cost=costs.append)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"text": "hi"}
    g._session = MagicMock(post=MagicMock(return_value=resp))
    one_sec = b"\x00" * (44 + 32000)
    sixty_sec = b"\x00" * (44 + 32000 * 60)
    with patch.object(transcriber, "is_online", return_value=True):
        g.transcribe(one_sec)
        g.transcribe(sixty_sec)
    assert costs == pytest.approx([10 / 3600 * 0.04, 60 / 3600 * 0.04])
