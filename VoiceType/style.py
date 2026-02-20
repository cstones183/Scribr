# style.py — Scribr design tokens
# ALL colour, spacing and font values live here.
# Never hardcode these anywhere else in the codebase.
#
# Supports light + dark mode via the theme() function which checks
# macOS system appearance. Every paintEvent should call t = theme()
# to get the current colour palette.

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QColor, QFont

# ════════════════════════════════════════════════════════════
#  THEME DATACLASS
# ════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Theme:
    """All colour tokens for a single appearance mode."""

    # Backgrounds
    bg: QColor
    surface: QColor
    surface_2: QColor
    surface_3: QColor

    # Borders
    border: QColor
    border_2: QColor

    # Text hierarchy
    text: QColor
    text_mid: QColor
    text_light: QColor

    # Accent — warm coral
    red: QColor
    red_soft: QColor
    red_border: QColor
    red_focus: QColor

    # Semantic
    green: QColor
    green_dim: QColor
    amber: QColor


# ── Light mode ─────────────────────────────────────────────

_LIGHT = Theme(
    bg=QColor(247, 245, 242),           # #F7F5F2  linen
    surface=QColor(255, 255, 255),      # #FFFFFF  cloud
    surface_2=QColor(239, 237, 233),    # #EFEDE9
    surface_3=QColor(232, 228, 223),    # #E8E4DF
    border=QColor(226, 222, 216),       # #E2DED8
    border_2=QColor(212, 206, 199),     # #D4CEC7
    text=QColor(45, 41, 38),            # #2D2926  espresso
    text_mid=QColor(107, 101, 96),      # #6B6560  stone
    text_light=QColor(168, 162, 156),   # #A8A29C
    red=QColor(217, 79, 61),            # #D94F3D  warm coral
    red_soft=QColor(245, 234, 232),     # #F5EAE8  blush
    red_border=QColor(217, 79, 61, 56),   # rgba(217,79,61,0.22)
    red_focus=QColor(217, 79, 61, 115),   # rgba(217,79,61,0.45)
    green=QColor(71, 184, 129),         # #47B881
    green_dim=QColor(71, 184, 129, 31),   # rgba(71,184,129,0.12)
    amber=QColor(192, 122, 26),         # #C07A1A
)

# ── Dark mode ──────────────────────────────────────────────

_DARK = Theme(
    bg=QColor(26, 23, 20),              # #1A1714
    surface=QColor(36, 32, 25),         # #242019
    surface_2=QColor(46, 42, 35),       # #2E2A23
    surface_3=QColor(56, 51, 43),       # #38332B
    border=QColor(61, 56, 48),          # #3D3830
    border_2=QColor(74, 68, 60),        # #4A443C
    text=QColor(240, 237, 232),         # #F0EDE8
    text_mid=QColor(163, 155, 146),     # #A39B92
    text_light=QColor(107, 99, 89),     # #6B6359
    red=QColor(224, 90, 71),            # #E05A47
    red_soft=QColor(224, 90, 71, 36),     # rgba(224,90,71,0.14)
    red_border=QColor(224, 90, 71, 71),   # rgba(224,90,71,0.28)
    red_focus=QColor(224, 90, 71, 102),   # rgba(224,90,71,0.40)
    green=QColor(42, 157, 92),          # #2A9D5C
    green_dim=QColor(42, 157, 92, 31),    # rgba(42,157,92,0.12)
    amber=QColor(192, 122, 26),         # #C07A1A
)


# ════════════════════════════════════════════════════════════
#  THEME DETECTION
# ════════════════════════════════════════════════════════════


def _is_dark_mode() -> bool:
    """Check macOS system appearance."""
    try:
        from Foundation import NSUserDefaults  # type: ignore[import-untyped]

        style = NSUserDefaults.standardUserDefaults().stringForKey_("AppleInterfaceStyle")
        return bool(style == "Dark")
    except Exception:
        return False


def theme() -> Theme:
    """Return the active theme based on macOS system appearance."""
    return _DARK if _is_dark_mode() else _LIGHT


# ════════════════════════════════════════════════════════════
#  TYPOGRAPHY
# ════════════════════════════════════════════════════════════


def font_serif(size: int, weight: int = 400, italic: bool = False) -> QFont:
    """Lora — headings, transcript text, subheadings."""
    f = QFont("Lora")
    if not f.exactMatch():
        f = QFont("Georgia")
    f.setPixelSize(size)
    if weight >= 600:
        f.setWeight(QFont.Weight.DemiBold)
    elif weight >= 500:
        f.setWeight(QFont.Weight.Medium)
    else:
        f.setWeight(QFont.Weight.Normal)
    f.setItalic(italic)
    return f


def font_sans(size: int, weight: int = 400) -> QFont:
    """Plus Jakarta Sans — UI labels, buttons, inputs."""
    f = QFont("Plus Jakarta Sans")
    if not f.exactMatch():
        f = QFont("Inter")
    if not f.exactMatch():
        f = QFont("Helvetica Neue")
    f.setPixelSize(size)
    if weight >= 600:
        f.setWeight(QFont.Weight.DemiBold)
    elif weight >= 500:
        f.setWeight(QFont.Weight.Medium)
    else:
        f.setWeight(QFont.Weight.Normal)
    return f


# Backward-compat alias — will be removed once all call sites are updated
font = font_sans


# ════════════════════════════════════════════════════════════
#  STYLESHEET HELPER
# ════════════════════════════════════════════════════════════


def qcolor_to_rgba(c: QColor) -> str:
    """Convert QColor to CSS rgba() string for use in stylesheets."""
    return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha() / 255:.2f})"


# ════════════════════════════════════════════════════════════
#  RADII
# ════════════════════════════════════════════════════════════

RADIUS_PILL = 999       # true pill shape
RADIUS_CARD = 16        # cards, windows, dropdowns
RADIUS_MD = 12          # standard corners
RADIUS_SM = 8           # inputs, selects, inner cards
RADIUS_XS = 6           # small chips
RADIUS_BTN = 8          # buttons

# ── Animation timings (ms) ───────────────────────
ANIM_ENTER = 320
ANIM_EXIT = 280
ANIM_EXPAND = 380
ANIM_FAST = 180

# ── Layout ───────────────────────────────────────
PILL_HEIGHT = 40
PILL_PADDING_H = 18
NOTEPAD_WIDTH = 340
CONNECTOR_HEIGHT = 56
BOTTOM_MARGIN = 32

# ── Waveform ─────────────────────────────────────
BAR_COUNT = 7
BAR_WIDTH = 2
BAR_GAP = 2
BAR_MAX_H = 19
BAR_MIN_H = 3
