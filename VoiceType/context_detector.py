# context_detector.py — Uses the macOS Accessibility API (pyobjc) to detect
# whether a text field is currently focused.  Covers native AppKit fields,
# Chromium/Safari web inputs, contenteditable divs, and Electron apps.
import logging

from ApplicationServices import (
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue,
)

try:
    from ApplicationServices import AXUIElementSetMessagingTimeout
except ImportError:  # older pyobjc
    AXUIElementSetMessagingTimeout = None

# Hard cap on how long any single Accessibility query may block. Without this,
# querying the focused element of a slow/unresponsive app can stall for the
# system default (~6s) on the calling thread and freeze the app.
_AX_TIMEOUT_S = 0.5


def is_text_field_focused() -> bool:
    """Returns True if the user currently has an editable text input focused."""
    try:
        system_wide = AXUIElementCreateSystemWide()
        if AXUIElementSetMessagingTimeout is not None:
            AXUIElementSetMessagingTimeout(system_wide, _AX_TIMEOUT_S)

        # Get focused UI element (3rd arg is pass-by-reference out pointer → None)
        err, focused = AXUIElementCopyAttributeValue(
            system_wide, "AXFocusedUIElement", None
        )
        if err != 0 or not focused:
            return False
        if AXUIElementSetMessagingTimeout is not None:
            AXUIElementSetMessagingTimeout(focused, _AX_TIMEOUT_S)

        # 1. AXSelectedTextRange — universal marker for editable text.
        #    Present on NSTextField, NSTextView, Chrome/Safari <input>/<textarea>,
        #    contenteditable divs, and most Electron fields.
        err, _ = AXUIElementCopyAttributeValue(
            focused, "AXSelectedTextRange", None
        )
        if err == 0:
            return True

        # 2. AXInsertionPointLineNumber — another strong text-editing signal.
        #    Some web text editors expose this even when AXSelectedTextRange is absent.
        err, _ = AXUIElementCopyAttributeValue(
            focused, "AXInsertionPointLineNumber", None
        )
        if err == 0:
            return True

        # 3. Role-based check for standard input types.
        err, role = AXUIElementCopyAttributeValue(focused, "AXRole", None)
        role_str = str(role) if err == 0 and role else ""
        if role_str in {"AXTextField", "AXTextArea", "AXComboBox"}:
            return True

        # 4. AXRoleDescription — catches web editors where the role is generic
        #    (AXGroup, AXWebArea) but the description says "text entry area",
        #    "editable text", "content editable", etc.
        err, desc = AXUIElementCopyAttributeValue(
            focused, "AXRoleDescription", None
        )
        if err == 0 and desc:
            desc_lower = str(desc).lower()
            if any(kw in desc_lower for kw in (
                "text entry", "text field", "text area",
                "editable", "search field", "input",
            )):
                return True

        # 5. AXValue exists and is a string — many web text inputs expose a
        #    string AXValue even when other text-editing attributes are missing.
        #    Guard: only count it if the role suggests an interactive element
        #    (not a static label or heading).
        if role_str in {"AXGroup", "AXWebArea", "AXUnknown", "AXDocument"}:
            err, val = AXUIElementCopyAttributeValue(focused, "AXValue", None)
            if err == 0 and isinstance(val, str):
                return True

        return False
    except Exception as e:
        logging.getLogger("scribr.context").debug("Error checking focus: %s", e)
        return False
