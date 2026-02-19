# style.py — VoiceType design tokens
# ALL colour, spacing and font values live here.
# Never hardcode these anywhere else in the codebase.

from PyQt6.QtGui import QColor, QFont

# ── Colours ──────────────────────────────────────
NAVY        = QColor(6,   9,  17)
GLASS       = QColor(8,  12,  24, 200)   # 78% opacity
GLASS2      = QColor(10, 16,  32, 230)   # 90% opacity
GLASS3      = QColor(13, 19,  38, 245)   # 96% opacity — settings window bg
BORDER      = QColor(255, 255, 255, 18)
BORDER_HI   = QColor(255, 255, 255, 33)
BORDER_FOCUS = QColor(77, 184, 255, 140)

BLUE        = QColor(91,  196, 255)
BLUE_SOFT   = QColor(91,  196, 255, 56)   # 0.22
BLUE_GLOW   = QColor(91,  196, 255, 46)
BLUE_DIM    = QColor(91,  196, 255, 20)
BLUE_BORDER = QColor(91,  196, 255, 51)   # 0.20

GREEN       = QColor(61,  232, 160)
GREEN_DIM   = QColor(61,  232, 160, 38)   # 0.15
RED         = QColor(255,  90, 110)
AMBER       = QColor(255, 200,  74)

T1          = QColor(255, 255, 255, 237)  # 93%
T2          = QColor(255, 255, 255, 140)  # 55%
T3          = QColor(255, 255, 255, 71)   # 28%
T4          = QColor(255, 255, 255, 30)   # 12%
T5          = QColor(255, 255, 255, 15)   # 6%

# ── Typography ───────────────────────────────────
FONT_STACK  = "-apple-system, 'SF Pro Display', 'Helvetica Neue', sans-serif"

def font(size: int, weight: int = 400) -> QFont:
    f = QFont("SF Pro Display")
    if not f.exactMatch():
        f = QFont("Inter")
    if not f.exactMatch():
        f = QFont("-apple-system")
    if not f.exactMatch():
        f = QFont("Helvetica Neue")
    f.setPixelSize(size)
    f.setWeight(QFont.Weight.Medium if weight >= 500 else QFont.Weight.Normal)
    return f

# ── Radii ────────────────────────────────────────
RADIUS_PILL = 20   # half of PILL_HEIGHT for true pill shape
RADIUS_CARD = 20
RADIUS_MD   = 12
RADIUS_SM   = 8
RADIUS_XS   = 6
RADIUS_BTN  = 8

# ── Animation timings (ms) ───────────────────────
ANIM_ENTER  = 320
ANIM_EXIT   = 280
ANIM_EXPAND = 380
ANIM_FAST   = 180

# ── Layout ───────────────────────────────────────
PILL_HEIGHT     = 40
PILL_PADDING_H  = 18
NOTEPAD_WIDTH   = 340
CONNECTOR_HEIGHT = 56
BOTTOM_MARGIN   = 32

# ── Waveform ─────────────────────────────────────
BAR_COUNT   = 7
BAR_WIDTH   = 2.5
BAR_GAP     = 2.5
BAR_MAX_H   = 19
BAR_MIN_H   = 3
