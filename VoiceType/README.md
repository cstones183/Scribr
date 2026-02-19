# 🎙 VoiceType

Hold **Right ⌥ (Right Option)** to record. Release to transcribe.
Text is typed directly into focused fields, or saved to a floating notepad + clipboard.

## Setup

1. Install dependencies:
   pip install -r requirements.txt

2. Add your OpenAI API key:
   Open ~/Library/Application Support/VoiceType/settings.json
   Set "api_key" to your key from platform.openai.com

3. Grant permissions (macOS will prompt, or go manually):
   - Microphone: System Settings → Privacy & Security → Microphone
   - Accessibility: System Settings → Privacy & Security → Accessibility

4. Run the app:
   python app.py

## Hotkey
Hold Right ⌥ (Right Option key) → speak → release → text appears.

## Modes
- Text field focused: text is typed directly into the field
- No text field: floating notepad appears top-right, copies to clipboard on dismiss

## Cost (API mode)
~$0.006/minute of audio. Typical user: under $1/month.

## Files
- app.py              — Menubar entry point
- hotkey.py           — Right ⌥ hold/release listener
- recorder.py         — Mic capture + live RMS for wave animation
- transcriber.py      — Whisper API + local Whisper modes
- corrector.py        — GPT-4o-mini filler word cleanup
- injector.py         — AppleScript text injection + clipboard
- context_detector.py — Accessibility API: detect focused text field
- overlay.py          — PyQt6 floating UI: waves, spinner, notepad
- settings.py         — JSON settings manager
- history.py          — Last 10 transcriptions
