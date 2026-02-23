# context_detector.py — Uses the macOS Accessibility API (pyobjc) to detect whether a text field is currently focused.
from ApplicationServices import (
    AXUIElementCreateSystemWide,
    AXUIElementCopyAttributeValue,
)

def is_text_field_focused() -> bool:
    """Returns True if the user currently has a text input field focused."""
    try:
        system_wide = AXUIElementCreateSystemWide()
        
        # Get focused UI element
        err, focused_element = AXUIElementCopyAttributeValue(system_wide, "AXFocusedUIElement")
        if err != 0 or not focused_element:
            return False
            
        # Get the role of the focused element
        err, role = AXUIElementCopyAttributeValue(focused_element, "AXRole")
        if err == 0 and role:
            # Common text input roles
            text_roles = {"AXTextField", "AXTextArea", "AXComboBox", "AXWebArea", "AXDocument"}
            if role in text_roles:
                return True
                
        # Also check subrole just to be safe (some apps use generic role + text subrole)
        err, subrole = AXUIElementCopyAttributeValue(focused_element, "AXSubrole")
        if err == 0 and subrole:
            subrole_str = str(subrole)
            if "Text" in subrole_str or "Document" in subrole_str:
                return True
                
        return False
    except Exception as e:
        print(f"[ContextDetector] Error checking focus: {e}")
        return False
