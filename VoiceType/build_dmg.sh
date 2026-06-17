#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$SCRIPT_DIR/dist/Scribr.app"
DMG_PATH="$SCRIPT_DIR/dist/Scribr.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: Scribr.app not found at $APP_PATH"
    echo "Run 'pyinstaller Scribr.spec' first."
    exit 1
fi

# Reset macOS permissions (each rebuild gets a new code signature)
echo "Resetting macOS permissions for com.scribr.app..."
tccutil reset Accessibility com.scribr.app 2>/dev/null || true
tccutil reset ListenEvent com.scribr.app 2>/dev/null || true
tccutil reset Microphone com.scribr.app 2>/dev/null || true

# Remove old DMG if present
rm -f "$DMG_PATH"

create-dmg \
    --volname "Scribr" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 128 \
    --icon "Scribr.app" 175 200 \
    --app-drop-link 425 200 \
    --no-internet-enable \
    "$DMG_PATH" \
    "$APP_PATH"

echo ""
echo "DMG created: $DMG_PATH"
