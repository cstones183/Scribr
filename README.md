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

- [Download](#-download)
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

## ⬇️ Download

Grab the latest packaged build from the [Releases page](https://github.com/cstones183/Scribr/releases/latest). Download `Scribr.dmg`, open it, and drag Scribr into Applications.

The build is **Apple Silicon (arm64)** only. Intel Macs need to run from source (see Getting Started).

### Opening it the first time (the security warning is expected)

Scribr is **not code-signed or notarized by Apple**, so the first time you open it macOS will warn that *"Apple could not verify Scribr is free of malware."* This is normal for open-source apps distributed outside the App Store, and it is safe to bypass. You only have to do this once.

First, drag Scribr into your **Applications** folder and double-click it. When the warning appears, click **Done** (not "Move to Bin"). Then use whichever method you prefer:

**System Settings (recommended on macOS Sequoia and later)**
1. Open **System Settings → Privacy & Security**.
2. Scroll to the **Security** section. You'll see *"Scribr" was blocked to protect your Mac.*
3. Click **Open Anyway** and confirm with Touch ID or your password.
4. Click **Open** in the final dialog.

**Terminal (quickest)**
Run this once to remove the quarantine flag, then open Scribr normally:

```bash
xattr -dr com.apple.quarantine /Applications/Scribr.app
```

> Note: on older macOS you could right-click the app and choose **Open** to bypass this. macOS Sequoia (15) and later removed that shortcut, so use one of the methods above.

After that, Scribr launches normally every time. On first launch, grant **Microphone** and **Accessibility / Input Monitoring** when prompted; the welcome screen has a button that takes you straight there.

Releases are built automatically by GitHub Actions. To cut one, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

That triggers the [`Build & Release DMG`](.github/workflows/release.yml) workflow, which builds the app on a macOS runner and publishes the DMG to a new Release. You can also run the workflow manually from the Actions tab to get a DMG as a downloadable build artifact without creating a Release.

---

## ✨ Features

- **Tap-to-Talk**: Tap **Right ⌥ (Right Option)** to start recording, tap again to transcribe.
- **Direct Injection**: Text is automatically pasted directly into your currently focused text field using macOS Accessibility Context mapping and simulated keystrokes.
- **Floating Notepad**: If no text field is focused, a sleek floating UI appears with your transcription, which is automatically copied to your clipboard.
- **AI Formatting & Correction**: Utilizes GPT-4o-mini to automatically remove filler words, format specific styles (like structured prompts), or clean up grammar.
- **Ultra-Fast Transcription**: Support for Groq's high-speed Whisper endpoints, with a standard OpenAI fallback.
- **Welcome Screen**: A first-launch guide that points you to where API keys go and helps you grant the macOS permissions.
- **Native macOS Experience**: Runs identically to a native Application, completely stripped from your Dock and managed via the OS Menubar.
- **Hardware-Accelerated UI**: Built heavily with PyQt6 for 60fps wave animations and a finalizing spinner that confirms the moment you stop recording.

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
├── transcriber.py          # Whisper API controllers (Groq, OpenAI)
├── corrector.py            # Post-processing GPT prompts (Prompt Mode, Formatting)
├── overlay.py              # PyQt6 frameless transparent UI window
├── context_detector.py     # OS-level active text-box detection (Accessibility API)
└── settings/               # Configuration files and setting window management
```

---

## 🛠 Prerequisites

- **macOS** 12.0 or later (Monterey+)
- **Python** 3.9+ (3.11 recommended)
- **API Keys** (you need at least one to transcribe):
  - `gsk_...` Groq API Key for high-speed transcription and live preview. Get one at [console.groq.com/keys](https://console.groq.com/keys)
  - `sk-...` OpenAI API Key for GPT-4o-mini text cleanup and formatting. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

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

Settings, including your API keys, are stored in `~/Library/Application Support/Scribr/settings.json` and managed inside the app. This file stays on your machine and is listed in `.gitignore`, so your keys are never committed.

To link your APIs:
1. Click the Scribr icon in the macOS menubar.
2. Click **Settings**, or use the **Open Settings to add keys** button on the welcome screen.
3. Input your API keys and select your AI behaviours (prompt generation, UK English grammar enforcement, and so on).

---

## 🎮 Usage

1. **Start**: Tap the **Right ⌥ (Right Option)** key once and speak.
2. **Stop**: Tap **Right ⌥** again. The recording timer turns into a spinner while Scribr transcribes the audio.
3. **Execution Contexts**:
   - **Text Field Focused**: Scribr will instantly simulate `Cmd+V`, pasting the output seamlessly into your current webpage, document, or terminal.
   - **No Text Field Focused**: The internal Notepad will retain the transcription, keeping it on your macOS Clipboard.

---

## 🔒 Permissions

Scribr requires two permissions on macOS. On the first launch it asks for them once, and the welcome screen offers a **Grant permissions** button. After that Scribr never re-prompts on startup. You can always toggle them manually in `System Settings → Privacy & Security`:
1. **Microphone**: Needed to capture your voice.
2. **Accessibility / Input Monitoring**: Needed for `hotkey.py` to globally detect your Option key, and for `context_detector.py` to check whether the focused element is a text field.

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

- **Audio not transcribing** 
  macOS might have revoked Microphone access. Check `System Settings -> Microphone`. You can also grab logs from the menubar via **Open Logs** when reporting an issue.
- **Text does not auto-paste**
  Ensure the app has **Accessibility** privileges. This is strictly required for the simulated `Cmd+V` keyboard macros.
- **Python script crashes on boot**
  Ensure you are using at least `Python 3.9` and that PyQt6 is correctly installed in your current active `venv`.
- **More detail when reporting bugs**
  Run with `SCRIBR_DEBUG=1` to capture verbose logs, then open them with **Open Logs** in the menubar.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Built to make writing at the speed of thought a reality.*
