<p align="center">
  <img src="VoiceType/assets/scribr_logo.svg" width="120" alt="Scribr Logo">
</p>

# 🎙 Scribr

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

**Scribr** is a lightning-fast, highly accurate macOS voice-to-text menubar application. Designed for seamless integration into your daily workflow, Scribr allows you to dictate text directly into any focused application or a floating notepad with a simple hotkey and advanced AI formatting options.

<details>
<summary>Table of Contents</summary>

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Getting Started](#-getting-started)
- [Configuration & Settings](#-configuration--settings)
- [Usage](#-usage)
- [Permissions](#-permissions)
- [Deployment & Packaging](#-deployment--packaging)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)
</details>

---

## ✨ Features

- **Push-to-Talk**: Hold **Right ⌥ (Right Option)** to record, and release to transcribe instantly.
- **Direct Injection**: Text is automatically pasted directly into your currently focused text field using macOS Accessibility Context mapping and simulated keystrokes.
- **Floating Notepad**: If no text field is focused, a sleek floating UI appears with your transcription, which is automatically copied to your clipboard.
- **AI Formatting & Correction**: Utilizes GPT-4o-mini to automatically remove filler words, format specific styles (like structured prompts), or clean up grammar.
- **Ultra-Fast Transcription**: Support for Groq's high-speed Whisper endpoints, standard OpenAI fallback, and optional offline local Whisper models.
- **Native macOS Experience**: Runs identically to a native Application, completely stripped from your Dock and managed via the OS Menubar.
- **Hardware-Accelerated UI**: Built heavily with PyQt6 for 60fps wave animations and loading spinners.

---

## 🏗 Architecture

The repository breaks out functionality natively to prevent single-file monolithic logic:

```bash
VoiceType/
├── app.py                  # Core application lifecycle & thread bridge
├── menubar.py              # macOS top-right icon and system tray interactions
├── history.py              # SQLite/File-based transcription history module
├── hotkey.py               # pynput global keyboard hooks
├── recorder.py             # Audio capture and RMS visualization parsing
├── transcriber.py          # Whisper API controllers (Groq, OpenAI, Local)
├── corrector.py            # Post-processing GPT prompts (Prompt Mode, Formatting)
├── overlay.py              # PyQt6 frameless transparent UI window
├── context_detector.py     # OS-level active text-box detection (Accessibility API)
└── settings/               # Configuration files and setting window management
```

---

## 🛠 Prerequisites

- **macOS** 12.0 or later (Monterey+)
- **Python** 3.9+ (3.11 recommended)
- **API Keys**:
  - `gsk_...` Groq API Key (for high-speed transcription)
  - `sk-...` OpenAI API Key (for GPT-4o-mini text correction/formatting)

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/scribr.git
cd scribr
```

### 2. Environment Setup
It is highly recommended to build this inside a virtual environment to prevent package collision before running PyInstaller.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r VoiceType/requirements.txt
```

### 3. Run Application in Development Mode
Start the application from within the source code folder:
```bash
python3.11 VoiceType/app.py
```

---

## ⚙️ Configuration & Settings

Settings are stored in the user preferences hierarchy (`~/Library/Application Support/Scribr/settings.json`) and managed cleanly inside the app. 
To link your APIs:
1. Click the Scribr icon in the macOS menubar.
2. Click **Settings**.
3. Input your API keys and select your specific AI behaviors (Prompt Generation, UK English grammar enforcement, etc.).

---

## 🎮 Usage

1. **Activate**: Hold down the **Right ⌥ (Right Option)** key and speak.
2. **Process**: Release the key. Scribr will instantly transcribe the audio stream in parallel.
3. **Execution Contexts**:
   - **Text Field Focused**: Scribr will instantly simulate `Cmd+V`, pasting the output seamlessly into your current webpage, document, or terminal.
   - **No Text Field Focused**: The internal Notepad will retain the transcription, keeping it securely on your macOS Clipboard.

---

## 🔒 Permissions

Scribr requires two distinct permissions to function optimally on macOS. Upon the first boot, macOS will traditionally throw prompts, but you can manually toggle these in `System Settings → Privacy & Security`:
1. **Microphone**: Needed to capture your voice.
2. **Accessibility**: Needed for `hotkey.py` to globally intercept your Option key, and for `context_detector.py` to verify if your current window cursor provides `AXTextField` status.

---

## 📦 Deployment & Packaging

To compile Scribr from a python script into an immutable macOS `.app` bundle, use PyInstaller.
A `.spec` generation limits excessive imports (like massive PyTorch libraries if using remote Groq).

```bash
# General build instruction
pyinstaller VoiceType/Scribr.spec --clean
```
The resulting `Scribr.app` will be populated into the `/dist` directory. Due to AppKit initialization inside `app.py`, the resulting icon will never show up in the dock.

---

## 🆘 Troubleshooting

- **Audio not transcribing / App stays "Listening..." forever** 
  macOS might have revoked Microphone access. Check `System Settings -> Microphone`.
- **Text does not auto-paste**
  Ensure the app has **Accessibility** privileges. This is strictly required for the simulated `Cmd+V` keyboard macros.
- **Python script crashes on boot**
  Ensure you are using at least `Python 3.9` and that PyQt6 is correctly installed in your current active `venv`.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built to make writing at the speed of thought a reality.*
