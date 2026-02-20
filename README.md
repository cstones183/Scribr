# 🎙 Scribr

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Scribr is a lightning-fast, highly accurate macOS voice-to-text menubar application. Designed for seamless integration into your daily workflow, Scribr allows you to dictate text directly into any focused application or a floating notepad with a simple hotkey.

## ✨ Features

- **Push-to-Talk**: Hold **Right ⌥ (Right Option)** to record, and release to transcribe instantly.
- **Direct Injection**: Text is automatically typed into your currently focused text field (using macOS Accessibility API and AppleScript).
- **Floating Notepad**: If no text field is focused, a sleek floating UI appears with your transcription, automatically copied to your clipboard.
- **Advanced Transcription**: Supports OpenAI's Whisper API, Groq's ultra-fast Whisper API, and optional offline local Whisper models.
- **Smart Cleanup**: Utilizes GPT-4o-mini to automatically remove filler words and clean up the transcribed text.
- **Smooth UI**: Built with PyQt6 for beautiful, 60fps wave animations and loading spinners.

## 🛠 Prerequisites

- **macOS** 12.0 or later
- **Python 3.9+**
- An **OpenAI API Key** (for Whisper API and GPT-4o-mini cleanup) or **Groq API Key** (for fast transcription).

## 🚀 Setup & Installation

1. **Clone the repository** (or download the source code):
   ```bash
   git clone https://github.com/yourusername/scribr.git
   cd scribr
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Settings**:
   Run the application once to generate the default settings file, or manually create it at `~/Library/Application Support/Scribr/settings.json`.
   Add your API key:
   ```json
   {
       "api_key": "your-openai-api-key-here"
   }
   ```

4. **Grant macOS Permissions**:
   The first time you run the app, macOS will prompt you for permissions. You can also configure these manually in `System Settings → Privacy & Security`:
   - **Microphone**: Required for audio capture.
   - **Accessibility**: Required to detect focused text fields and inject text.

5. **Run the Application**:
   ```bash
   python app.py
   ```

## 🎮 Usage

1. **Start Dictating**: Hold the **Right ⌥ (Right Option)** key and start speaking.
2. **Transcribe**: Release the key. Scribr will instantly process your speech.
3. **Modes**:
   - **Text Field Focused**: The transcribed text is typed directly wherever your cursor is.
   - **No Text Field**: A floating notepad appears in the top-right corner with your text. It is automatically copied to your clipboard. Dismiss the notepad to continue.

## 💸 Cost Estimation (API Mode)

Using the OpenAI Whisper API costs approximately **~$0.006 per minute** of audio. A typical user dictating daily usually spends under **$1.00 per month**.

## 📂 Project Structure

- `app.py` — Application entry point and Qt main loop.
- `menubar.py` — Menubar icon and dropdown menu standard controls.
- `hotkey.py` — Global keyboard listener for the Left/Right Option keys.
- `recorder.py` — Microphone audio capture and live RMS calculation for UI wave animations.
- `transcriber.py` — Handles API calls to Whisper (OpenAI/Groq) and manages local offline transcription.
- `corrector.py` — Applies LLM-based text cleanup (e.g., removing filler words).
- `injector.py` — Uses AppleScript to inject text and manages clipboard operations.
- `context_detector.py` — macOS Accessibility API hooks to detect the active text field.
- `overlay.py` — PyQt6-based floating UI elements (waves, spinner, notepad).
- `settings.py` & `settings_window.py` — JSON settings management and preferences UI.
- `history.py` — Stores and manages the last 10 transcriptions.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built to make writing at the speed of thought a reality.*
