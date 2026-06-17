# -*- mode: python ; coding: utf-8 -*-
# Scribr.spec — PyInstaller build configuration
# Build with:  cd VoiceType && pyinstaller Scribr.spec

from pathlib import Path

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/fonts", "assets/fonts"),
        ("assets/menubar_idle.png", "assets"),
        ("assets/menubar_idle@2x.png", "assets"),
        ("assets/menubar_recording.png", "assets"),
        ("assets/menubar_recording@2x.png", "assets"),
    ],
    hiddenimports=[
        "Foundation",
        "AppKit",
        "ApplicationServices",
        "Quartz",
        "objc",
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "whisper",
        "torchaudio",
        "torchvision",
        "matplotlib",
        "PIL",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Scribr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Scribr",
)

app = BUNDLE(
    coll,
    name="Scribr.app",
    icon="assets/Scribr.icns",
    bundle_identifier="com.scribr.app",
    info_plist={
        "CFBundleName": "Scribr",
        "CFBundleDisplayName": "Scribr",
        "CFBundleIdentifier": "com.scribr.app",
        "CFBundleVersion": "1.0.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": (
            "Scribr requires microphone access to transcribe your voice."
        ),
        "NSAppleEventsUsageDescription": (
            "Scribr needs to automate the pasting of your transcription."
        ),
    },
)
