# style.py — Scribr design tokens
# ALL colour, spacing and font values live here.
# Never hardcode these anywhere else in the codebase.
#
# Supports light + dark mode via the theme() function which checks
# macOS system appearance. Every paintEvent should call t = theme()
# to get the current colour palette.
from __future__ import annotations

import logging
import sys

from dataclasses import dataclass

from pathlib import Path

from PyQt6.QtCore import QEasingCurve
from PyQt6.QtGui import QColor, QFont, QFontDatabase

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

    # AI Mode
    ai: QColor
    ai_soft: QColor
    ai_border: QColor
    ai_shimmer: QColor


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
    ai=QColor(124, 92, 252),            # #7C5CFC
    ai_soft=QColor(124, 92, 252, 25),     # rgba(124,92,252,0.10)
    ai_border=QColor(124, 92, 252, 56),   # rgba(124,92,252,0.22)
    ai_shimmer=QColor(124, 92, 252, 31),  # rgba(124,92,252,0.12)
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
    ai=QColor(155, 130, 255),           # #9B82FF
    ai_soft=QColor(155, 130, 255, 31),    # rgba(155,130,255,0.12)
    ai_border=QColor(155, 130, 255, 64),  # rgba(155,130,255,0.25)
    ai_shimmer=QColor(155, 130, 255, 38), # rgba(155,130,255,0.15)
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


def should_reduce_motion() -> bool:
    """Check macOS accessibility setting for reduce-motion preference."""
    try:
        from AppKit import NSWorkspace  # type: ignore[import-untyped]

        if NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion():
            return True
    except Exception:
        pass
    return False


# ════════════════════════════════════════════════════════════
#  ASSET PATH RESOLVER
# ════════════════════════════════════════════════════════════

def _base_dir() -> Path:
    """Return the base directory for asset lookups.

    When running from a PyInstaller bundle, assets live under
    sys._MEIPASS.  During development, they live next to this file.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def asset_path(*parts: str) -> str:
    """Resolve an asset path that works in both dev and frozen mode.

    Usage: asset_path("assets", "menubar_idle.png")
    """
    return str(_base_dir().joinpath(*parts))


# ════════════════════════════════════════════════════════════
#  TYPOGRAPHY
# ════════════════════════════════════════════════════════════

_FONTS_DIR = _base_dir() / "assets" / "fonts"
_fonts_loaded = False


def load_fonts() -> None:
    """Load bundled Lora + Plus Jakarta Sans from assets/fonts/.

    Call once after QApplication is created.
    """
    global _fonts_loaded
    if _fonts_loaded:
        return
    _fonts_loaded = True
    for ttf in _FONTS_DIR.glob("*.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(ttf))
        if font_id < 0:
            logging.getLogger("scribr.style").warning("Failed to load font %s", ttf.name)


def font_serif(size: int, weight: int = 400, italic: bool = False) -> QFont:
    """Lora — headings, transcript text, subheadings."""
    load_fonts()
    f = QFont("Lora")
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
    load_fonts()
    f = QFont("Plus Jakarta Sans")
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

# ── Named easing curves ─────────────────────────
EASE_SPRING = QEasingCurve.Type.OutBack      # overshoot for entrances
EASE_SETTLE = QEasingCurve.Type.OutCubic     # smooth deceleration
EASE_LIFT = QEasingCurve.Type.InCubic        # accelerating exits
EASE_SNAP = QEasingCurve.Type.OutElastic     # small elastic snap

# ── Physics-based timing tokens ──────────────────
ANIM_PILL_ENTER = 380
ANIM_PILL_EXIT = 240
ANIM_CROSSFADE = 200
ANIM_NOTEPAD_OPEN = 420
ANIM_NOTEPAD_CLOSE = 280
ANIM_WORD_FADE = 180

# ── Layout ───────────────────────────────────────
PILL_HEIGHT = 40
PILL_PADDING_H = 18
NOTEPAD_WIDTH = 400
CONNECTOR_HEIGHT = 32
BOTTOM_MARGIN = 32

# ── Waveform ─────────────────────────────────────
BAR_COUNT = 7
BAR_WIDTH = 2
BAR_GAP = 2
BAR_MAX_H = 19
BAR_MIN_H = 3
