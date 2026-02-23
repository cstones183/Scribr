# corrector.py — Optional GPT-4o-mini post-processing to remove filler words
# and fix grammar in transcribed text.

from __future__ import annotations

import json

import requests

OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a transcription cleanup assistant. "
    "Fix grammar, remove filler words (um, uh, like, you know, so yeah), "
    "fix punctuation, and capitalize properly. "
    "Do NOT change the meaning or add new information. "
    "Return ONLY the cleaned text, nothing else."
)

LLM_FORMAT_PROMPT_STRUCTURED = (
    "You are a context formatter for an AI assistant interface. Your job is to take raw, spoken transcriptions and reformat them into clean, structured context that is optimised for input into an LLM.\n\n"
    "Rules:\n"
    "- Remove all filler words (um, uh, like, you know, sort of, kind of, basically)\n"
    "- Remove false starts and repetitions\n"
    "- Identify the primary intent of the message\n"
    "- Extract key entities: people, times, dates, actions, blockers, goals\n"
    "- Format the output as labelled fields, not prose\n"
    "- Use short, direct language — no padding, no pleasantries\n"
    "- If there is a clear action required, make it the first field\n"
    "- Never add information that wasn't in the original — only restructure what's there\n"
    "- Output only the formatted fields, no preamble or explanation\n\n"
    "Format example:\n"
    "Intent: [one sentence]\n"
    "Action required: [what needs doing]\n"
    "Key details: [supporting info]\n"
    "People involved: [if any]\n"
    "Deadline/time: [if any]\n"
    "Context: [any other relevant background]\n\n"
    "Only include fields that are relevant. Do not include empty fields."
)

LLM_FORMAT_PROMPT_CONDENSED = (
    "Rewrite this spoken transcript as a single clean paragraph. Remove all filler words, false starts, and repetition. Keep all meaningful information. Target 40-50% of the original word count. Write in first person, matching the speaker's intent. Output only the rewritten paragraph."
)

LLM_FORMAT_PROMPT_BULLETS = (
    "Convert this spoken transcript into a bulleted list of key points. Remove filler words and false starts. Each bullet should be one clear, actionable or informational item. Order by importance. Output only the bullet points, no preamble."
)

LLM_FORMAT_PROMPT_PROMPT_MODE = (
    "You are an expert prompt engineer. The user has spoken a transcript of their thoughts. "
    "Your job is to convert this raw transcript into a highly structured, optimized prompt "
    "that the user can copy and paste into another AI model (like ChatGPT or Claude) to get the best results. "
    "Expand on the implicit intent, organize the requirements into bullet points if necessary, "
    "and ensure the resulting prompt is clear and explicit. "
    "Return ONLY the formulated prompt, with no extra conversational filler."
)


class CorrectionError(Exception):
    """Raised when text correction fails."""


class Corrector:
    """Cleans transcribed text using GPT-4o-mini.

    Usage:
        corrector = Corrector(api_key="sk-...")
        clean = corrector.clean_text("um so yeah hello")
        # -> "Hello."
    """

    def __init__(self, api_key: str) -> None:
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"
        self._session.headers["Content-Type"] = "application/json"

    def clean_text(self, raw_text: str, use_uk_english: bool = False) -> str:
        """Send raw transcription to GPT-4o-mini for cleanup.

        Returns cleaned text, or raises CorrectionError on failure.
        """
        if not raw_text.strip():
            return raw_text

        sys_prompt = SYSTEM_PROMPT
        if use_uk_english:
            sys_prompt += "\n\nCRITICAL RULE: You must exclusively use UK English spelling (e.g., colour, organise), vocabulary, and grammar conventions."

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": raw_text},
            ],
            "temperature": 0.3,
            "max_tokens": max(len(raw_text) * 2, 256),
        }

        try:
            resp = self._session.post(
                OPENAI_CHAT_ENDPOINT,
                json=payload,
                timeout=15,
            )
        except requests.RequestException as e:
            raise CorrectionError(f"Network error: {e}") from e

        if resp.status_code != 200:
            raise CorrectionError(
                f"OpenAI API error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise CorrectionError(f"Invalid API response: {e}") from e

    def format_for_llm(self, raw_text: str, style: str = "structured", use_uk_english: bool = False) -> str:
        """Restructure spoken transcript into clean, labelled context for an LLM."""
        if not raw_text.strip():
            return raw_text
            
        word_count = len(raw_text.split())
        if word_count < 3:
            return raw_text  # Skip if too short

        if style == "condensed":
            sys_prompt = LLM_FORMAT_PROMPT_CONDENSED
        elif style == "bullets":
            sys_prompt = LLM_FORMAT_PROMPT_BULLETS
        elif style == "prompt":
            sys_prompt = LLM_FORMAT_PROMPT_PROMPT_MODE
        else:
            sys_prompt = LLM_FORMAT_PROMPT_STRUCTURED

        if use_uk_english:
            sys_prompt += "\n\nCRITICAL RULE: You must exclusively use UK English spelling (e.g., colour, organise), vocabulary, and grammar conventions."

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": raw_text},
            ],
            "temperature": 0.2,
            "max_tokens": max(len(raw_text) * 2, 512),
        }

        try:
            resp = self._session.post(
                OPENAI_CHAT_ENDPOINT,
                json=payload,
                timeout=20,
            )
        except requests.RequestException as e:
            raise CorrectionError(f"Network error: {e}") from e

        if resp.status_code != 200:
            raise CorrectionError(
                f"OpenAI API error {resp.status_code}: {resp.text[:200]}"
            )

        try:
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise CorrectionError(f"Invalid API response: {e}") from e
