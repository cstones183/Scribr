"""Tests for Corrector (GPT-4o-mini text cleanup)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from corrector import CorrectionError, Corrector


class TestCorrector:
    def test_empty_text_returns_unchanged(self) -> None:
        c = Corrector(api_key="sk-test")
        assert c.clean_text("") == ""
        assert c.clean_text("   ") == "   "

    @patch("corrector.requests.Session")
    def test_clean_text_returns_cleaned(self, mock_session_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello."}}]
        }
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        c = Corrector(api_key="sk-test")
        c._session = mock_session
        result = c.clean_text("um so yeah hello")
        assert result == "Hello."

    @patch("corrector.requests.Session")
    def test_raises_on_api_error(self, mock_session_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        c = Corrector(api_key="sk-test")
        c._session = mock_session
        with pytest.raises(CorrectionError, match="500"):
            c.clean_text("hello world")
