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


def _session_returning(content: str) -> MagicMock:
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    session = MagicMock()
    session.post.return_value = resp
    return session


def test_cleanup_wraps_transcript_and_includes_example() -> None:
    c = Corrector(api_key="sk-test")
    c._session = _session_returning("Write an email to John.")
    c.clean_text("write an email to john")
    msgs = c._session.post.call_args.kwargs["json"]["messages"]
    assert msgs[-1]["content"] == "<transcript>write an email to john</transcript>"
    assert len(msgs) == 4  # system + few-shot pair + transcript


def test_cleanup_rejects_output_that_acts_on_instruction() -> None:
    c = Corrector(api_key="sk-test")
    email = "Subject: Meeting\n\nHi John,\n\n" + "I hope this finds you well. " * 10
    c._session = _session_returning(email)
    with pytest.raises(CorrectionError, match="grew"):
        c.clean_text("write an email to john about the meeting")


def test_retrying_session_retries_post() -> None:
    from transcriber import retrying_session

    retry = retrying_session("k").get_adapter("https://api.groq.com").max_retries
    assert retry.allowed_methods is None and retry.read >= 1


@pytest.mark.parametrize("content,finish", [(None, "stop"), ("", "stop"), ("Half a sen", "length")])
def test_unusable_reply_raises_so_raw_text_is_kept(content, finish) -> None:
    c = Corrector(api_key="sk-test")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": content}, "finish_reason": finish}]}
    c._session = MagicMock(post=MagicMock(return_value=resp))
    with pytest.raises(CorrectionError):
        c.clean_text("hello there how are you")


def test_short_fulfilled_email_is_rejected() -> None:
    c = Corrector(api_key="sk-test")
    c._session = _session_returning("Hi John, I'm running late today. Thanks, Chris")
    with pytest.raises(CorrectionError, match="new words"):
        c.clean_text("write an email to john saying i'll be late")
