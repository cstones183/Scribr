# settings_window.py — Tabbed settings dialog matching the HTML prototype.
# Frameless, glass-backed, 560px wide, 4 tabs.

from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGridLayout,
    QStackedWidget, QLineEdit, QComboBox, QPushButton, QFrame,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPointF, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient,
)

from style import (
    NAVY, GLASS, GLASS2, GLASS3,
    BORDER, BORDER_HI, BORDER_FOCUS,
    BLUE, BLUE_SOFT, BLUE_GLOW, BLUE_DIM, BLUE_BORDER,
    GREEN, GREEN_DIM, RED, AMBER,
    T1, T2, T3, T4, T5,
    font,
    RADIUS_CARD, RADIUS_MD, RADIUS_SM, RADIUS_XS, RADIUS_BTN,
)
from settings import SettingsManager, LANGUAGES
from widgets import ToggleSwitch, SegmentedControl, PositionChip, ThemeChip, ToastWidget


# ════════════════════════════════════════════════════════════
#  SHARED STYLESHEET SNIPPETS
# ════════════════════════════════════════════════════════════

INPUT_SS = (
    "QLineEdit {"
    "  background: rgba(255,255,255,0.04);"
    "  border: 1px solid rgba(255,255,255,0.09);"
    f"  border-radius: {RADIUS_SM}px;"
    "  color: rgba(255,255,255,0.93);"
    "  font-size: 13px;"
    "  padding: 9px 38px 9px 12px;"
    "}"
    "QLineEdit:focus {"
    "  border-color: rgba(77,184,255,0.50);"
    "  background: rgba(255,255,255,0.055);"
    "}"
)

SELECT_SS = (
    "QComboBox {"
    "  background: rgba(255,255,255,0.04);"
    "  border: 1px solid rgba(255,255,255,0.09);"
    f"  border-radius: {RADIUS_SM}px;"
    "  color: rgba(255,255,255,0.93);"
    "  font-size: 13px;"
    "  padding: 9px 12px;"
    "}"
    "QComboBox:focus {"
    "  border-color: rgba(77,184,255,0.50);"
    "}"
    "QComboBox::drop-down {"
    "  border: none;"
    "  width: 28px;"
    "}"
    "QComboBox::down-arrow {"
    "  image: none;"
    "  width: 0; height: 0;"
    "}"
    "QComboBox QAbstractItemView {"
    "  background: rgb(15,21,37);"
    "  color: rgba(255,255,255,0.90);"
    "  border: 1px solid rgba(255,255,255,0.12);"
    f"  border-radius: {RADIUS_SM}px;"
    "  selection-background-color: rgba(91,196,255,0.16);"
    "  selection-color: rgb(91,196,255);"
    "  outline: none;"
    "  padding: 4px;"
    "}"
)

BTN_GHOST_SS = (
    "QPushButton {"
    f"  border-radius: {RADIUS_SM}px;"
    "  background: transparent;"
    "  border: 1px solid rgba(255,255,255,0.10);"
    "  color: rgba(255,255,255,0.55);"
    "  font-size: 12px;"
    "  font-weight: 500;"
    "  padding: 7px 16px;"
    "}"
    "QPushButton:hover {"
    "  background: rgba(255,255,255,0.06);"
    "  color: rgba(255,255,255,0.93);"
    "}"
)

BTN_SAVE_SS = (
    "QPushButton {"
    f"  border-radius: {RADIUS_SM}px;"
    "  background: rgb(91,196,255);"
    "  border: none;"
    "  color: rgba(0,0,0,0.85);"
    "  font-size: 12px;"
    "  font-weight: 600;"
    "  padding: 7px 20px;"
    "}"
    "QPushButton:hover {"
    "  background: rgb(125,212,255);"
    "}"
)


# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════

def _section_title(text: str) -> QLabel:
    """Blue section heading with trailing line."""
    lbl = QLabel(text)
    lbl.setFont(font(9, 700))
    lbl.setStyleSheet(
        "color: rgb(91,196,255);"
        "letter-spacing: 2.5px;"
        "text-transform: uppercase;"
        "background: transparent;"
        "border: none;"
    )
    return lbl


def _section_line() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet("background: rgba(91,196,255,0.15); border: none;")
    return line


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font(11, 500))
    lbl.setStyleSheet("color: rgba(255,255,255,0.55); background: transparent; border: none;")
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font(10, 400))
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: rgba(255,255,255,0.28); background: transparent; border: none;")
    return lbl


def _badge(text: str, active: bool = True) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(font(9, 700))
    if active:
        lbl.setStyleSheet(
            "background: rgba(91,196,255,0.10);"
            "color: rgb(91,196,255);"
            "border: 1px solid rgba(91,196,255,0.20);"
            f"border-radius: 4px;"
            "padding: 2px 7px;"
        )
    else:
        lbl.setStyleSheet(
            "background: rgba(255,255,255,0.04);"
            "color: rgba(255,255,255,0.28);"
            "border: 1px solid rgba(255,255,255,0.07);"
            f"border-radius: 4px;"
            "padding: 2px 7px;"
        )
    return lbl


def _section_header(text: str) -> QWidget:
    """Section title + trailing gradient line in a row."""
    row = QWidget()
    row.setStyleSheet("background: transparent; border: none;")
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    h.addWidget(_section_title(text))
    h.addWidget(_section_line(), 1)
    return row


# ════════════════════════════════════════════════════════════
#  TAB BUTTON
# ════════════════════════════════════════════════════════════

class _TabButton(QPushButton):
    """Single tab in the tab bar."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"{icon}  {label}", parent)
        self._active = False
        self.setFont(font(12, 500))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(
                "QPushButton {"
                "  color: rgb(91,196,255);"
                "  background: rgba(91,196,255,0.08);"
                "  border: none;"
                "  border-bottom: 2px solid rgb(91,196,255);"
                f"  border-radius: {RADIUS_XS}px {RADIUS_XS}px 0px 0px;"
                "  padding: 8px 14px 10px;"
                "  letter-spacing: 0.2px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                "  color: rgba(255,255,255,0.28);"
                "  background: transparent;"
                "  border: none;"
                "  border-bottom: 2px solid transparent;"
                f"  border-radius: {RADIUS_XS}px {RADIUS_XS}px 0px 0px;"
                "  padding: 8px 14px 10px;"
                "  letter-spacing: 0.2px;"
                "}"
                "QPushButton:hover {"
                "  color: rgba(255,255,255,0.55);"
                "  background: rgba(255,255,255,0.03);"
                "}"
            )


# ════════════════════════════════════════════════════════════
#  SETTINGS WINDOW
# ════════════════════════════════════════════════════════════

class SettingsWindow(QWidget):
    """Frameless, glass-backed settings dialog — 560px wide, 4 tabs."""

    settings_saved = pyqtSignal()

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings = settings

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(560)

        self._drag_pos = None

        # ── Main layout ──────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Titlebar ─────────────────────────────────────
        self._titlebar = self._build_titlebar()
        root.addWidget(self._titlebar)

        # ── Tab bar ──────────────────────────────────────
        self._tab_bar_widget, self._tabs = self._build_tab_bar()
        root.addWidget(self._tab_bar_widget)

        # ── Stacked body ─────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")
        self._stack.addWidget(self._build_api_tab())
        self._stack.addWidget(self._build_transcription_tab())
        self._stack.addWidget(self._build_appearance_tab())
        self._stack.addWidget(self._build_about_tab())
        root.addWidget(self._stack, 1)

        # ── Footer ───────────────────────────────────────
        root.addWidget(self._build_footer())

        # ── Toast overlay ────────────────────────────────
        self._toast = ToastWidget(self)

        # ── Load values from settings ────────────────────
        self._load_values()

        # ── Activate first tab ───────────────────────────
        self._switch_tab(0)

    # ─────────────────────────────────────────────────────
    #  GLASS PAINT
    # ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = RADIUS_CARD

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, r, r)
        p.setClipPath(path)

        # Glass fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GLASS3)
        p.drawPath(path)

        # Border
        p.setPen(QPen(BORDER_HI, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # Top sheen
        sheen = QLinearGradient(QPointF(14, 0), QPointF(w - 14, 0))
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.25, QColor(255, 255, 255, 26))
        sheen.setColorAt(0.50, QColor(255, 255, 255, 41))
        sheen.setColorAt(0.75, QColor(255, 255, 255, 26))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(sheen), 1))
        p.drawLine(14, 0, w - 14, 0)
        p.end()

    # ─────────────────────────────────────────────────────
    #  TITLEBAR
    # ─────────────────────────────────────────────────────

    def _build_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            "background: rgba(255,255,255,0.02);"
            "border-bottom: 1px solid rgba(255,255,255,0.07);"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(0)

        # Traffic lights
        for color in ["#ff5f57", "#febc2e", "#28c840"]:
            dot = QPushButton()
            dot.setFixedSize(12, 12)
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            dot.setStyleSheet(
                f"QPushButton {{ background: {color}; border-radius: 6px; border: none; }}"
                f"QPushButton:hover {{ background: {color}; }}"
            )
            if color == "#ff5f57":
                dot.clicked.connect(self.close)
            h.addWidget(dot)
            h.addSpacing(6)

        h.addStretch()

        title = QLabel("VoiceType Settings")
        title.setFont(font(13, 600))
        title.setStyleSheet("color: rgba(255,255,255,0.93); background: transparent; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(title)

        h.addStretch()
        # Spacer to balance traffic lights
        spacer = QWidget()
        spacer.setFixedWidth(52)
        spacer.setStyleSheet("background: transparent; border: none;")
        h.addWidget(spacer)

        return bar

    # ─────────────────────────────────────────────────────
    #  TAB BAR
    # ─────────────────────────────────────────────────────

    def _build_tab_bar(self) -> tuple[QWidget, list[_TabButton]]:
        bar = QWidget()
        bar.setStyleSheet(
            "background: rgba(255,255,255,0.01);"
            "border-bottom: 1px solid rgba(255,255,255,0.07);"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(18, 12, 18, 0)
        h.setSpacing(2)

        tab_defs = [
            ("\U0001f511", "API Keys"),
            ("\u2699\ufe0f", "Transcription"),
            ("\U0001f3a8", "Appearance"),
            ("\u2139\ufe0f", "About"),
        ]

        tabs = []
        for i, (icon, label) in enumerate(tab_defs):
            btn = _TabButton(icon, label)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            h.addWidget(btn)
            tabs.append(btn)
        h.addStretch()

        return bar, tabs

    def _switch_tab(self, idx: int):
        for i, tab in enumerate(self._tabs):
            tab.set_active(i == idx)
        self._stack.setCurrentIndex(idx)

    # ─────────────────────────────────────────────────────
    #  TAB 1 — API KEYS
    # ─────────────────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(20)

        # ── Active Provider section ──
        v.addWidget(_section_header("Active Provider"))

        # OpenAI key row
        row_label = QWidget()
        row_label.setStyleSheet("background: transparent; border: none;")
        rl = QHBoxLayout(row_label)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(_field_label("OpenAI API Key"))
        rl.addStretch()
        rl.addWidget(_badge("Active", True))
        v.addWidget(row_label)

        # Input + eye toggle
        input_wrap = QWidget()
        input_wrap.setStyleSheet("background: transparent; border: none;")
        il = QHBoxLayout(input_wrap)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(0)
        self._openai_input = QLineEdit()
        self._openai_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._openai_input.setPlaceholderText("sk-...")
        self._openai_input.setStyleSheet(INPUT_SS)
        self._openai_input.setMinimumHeight(38)
        il.addWidget(self._openai_input)

        self._eye_btn = QPushButton("\U0001f441")
        self._eye_btn.setFixedSize(38, 38)
        self._eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._eye_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 14px;"
            " color: rgba(255,255,255,0.28); }"
            "QPushButton:hover { color: rgba(255,255,255,0.55);"
            " background: rgba(255,255,255,0.06); border-radius: 4px; }"
        )
        self._eye_btn.clicked.connect(self._toggle_eye)
        il.addWidget(self._eye_btn)
        v.addWidget(input_wrap)

        v.addWidget(_hint(
            "Powers: Whisper transcription · GPT-4o-mini cleanup · ~$0.006/min"
        ))

        # ── Coming Soon section ──
        v.addSpacing(8)
        v.addWidget(_section_header("Coming Soon"))

        cs_frame = QFrame()
        cs_frame.setStyleSheet(
            "QFrame {"
            "  background: rgba(255,255,255,0.02);"
            "  border: 1px solid rgba(255,255,255,0.07);"
            f"  border-radius: {RADIUS_MD}px;"
            "}"
        )
        cs_v = QVBoxLayout(cs_frame)
        cs_v.setContentsMargins(12, 12, 12, 12)
        cs_v.setSpacing(8)

        providers = [
            ("\U0001f30a", "rgba(255,140,80,0.15)", "Deepgram", "Ultra-fast streaming transcription"),
            ("\u26a1", "rgba(140,80,255,0.15)", "Groq", "Whisper at 10x inference speed"),
            ("\U0001f50a", "rgba(80,180,255,0.15)", "AssemblyAI", "Speaker detection + smart formatting"),
        ]
        for emoji, bg, name, desc in providers:
            row = QWidget()
            row.setStyleSheet("background: transparent; border: none;")
            rh = QHBoxLayout(row)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(8)

            logo = QLabel(emoji)
            logo.setFixedSize(22, 22)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet(
                f"background: {bg}; border-radius: 5px; font-size: 11px;"
                " border: none; opacity: 0.45;"
            )
            rh.addWidget(logo)

            info = QWidget()
            info.setStyleSheet("background: transparent; border: none;")
            iv = QVBoxLayout(info)
            iv.setContentsMargins(0, 0, 0, 0)
            iv.setSpacing(1)
            n = QLabel(name)
            n.setFont(font(12, 400))
            n.setStyleSheet("color: rgba(255,255,255,0.28); background: transparent; border: none;")
            iv.addWidget(n)
            d = QLabel(desc)
            d.setFont(font(10, 400))
            d.setStyleSheet("color: rgba(255,255,255,0.12); background: transparent; border: none;")
            iv.addWidget(d)
            rh.addWidget(info, 1)

            rh.addWidget(_badge("Soon", False))
            cs_v.addWidget(row)

        v.addWidget(cs_frame)
        v.addStretch()
        return page

    def _toggle_eye(self):
        if self._openai_input.echoMode() == QLineEdit.EchoMode.Password:
            self._openai_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye_btn.setText("\U0001f648")
        else:
            self._openai_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye_btn.setText("\U0001f441")

    # ─────────────────────────────────────────────────────
    #  TAB 2 — TRANSCRIPTION
    # ─────────────────────────────────────────────────────

    def _build_transcription_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(20)

        # ── Mode section ──
        v.addWidget(_section_header("Mode"))

        v.addWidget(_field_label("Transcription Engine"))
        self._mode_seg = SegmentedControl(["☁️  API (OpenAI)", "💻  Local (Offline)"])
        v.addWidget(self._mode_seg)
        v.addWidget(_hint(
            "Local mode uses Whisper running on your Mac. Free, offline, ~1s on Apple Silicon."
        ))

        v.addWidget(_field_label("Local Model Size"))
        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(SELECT_SS)
        self._model_combo.setMinimumHeight(38)
        self._model_combo.addItems([
            "tiny — 75MB · Fastest",
            "base — 145MB · Recommended",
            "small — 460MB · Better accuracy",
            "medium — 1.5GB · Best accuracy",
        ])
        v.addWidget(self._model_combo)
        v.addWidget(_hint("Only used in Local mode. Downloads once on first use."))

        # ── Language & Cleanup section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Language & Cleanup"))

        v.addWidget(_field_label("Language"))
        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(SELECT_SS)
        self._lang_combo.setMinimumHeight(38)
        for display, code in LANGUAGES:
            self._lang_combo.addItem(display, code)
        v.addWidget(self._lang_combo)

        # AI Cleanup toggle row
        self._ai_cleanup_toggle = ToggleSwitch(True)
        v.addWidget(self._toggle_row(
            "AI Cleanup",
            "Remove filler words (um, uh, like) and fix punctuation via GPT-4o-mini",
            self._ai_cleanup_toggle,
        ))

        # Confidence toggle row
        self._confidence_toggle = ToggleSwitch(True)
        v.addWidget(self._toggle_row(
            "Show Confidence Highlights",
            "Underline low-confidence words in amber for easy review",
            self._confidence_toggle,
        ))

        # ── Hotkey section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Hotkey"))
        v.addWidget(_field_label("Current Shortcut"))

        hotkey_row = QWidget()
        hotkey_row.setStyleSheet("background: transparent; border: none;")
        hk = QHBoxLayout(hotkey_row)
        hk.setContentsMargins(0, 0, 0, 0)
        hk.setSpacing(8)
        key_cap = QLabel("Right ⌥")
        key_cap.setFont(font(12, 500))
        key_cap.setStyleSheet(
            "background: rgba(255,255,255,0.06);"
            "border: 1px solid rgba(255,255,255,0.12);"
            "border-bottom: 2px solid rgba(255,255,255,0.18);"
            "border-radius: 6px;"
            "color: rgba(255,255,255,0.93);"
            "padding: 4px 10px;"
        )
        hk.addWidget(key_cap)
        hk.addWidget(_hint("Hold to record · Release to transcribe"))
        hk.addStretch()
        v.addWidget(hotkey_row)

        v.addWidget(_hint("To change: edit settings.json or re-run setup wizard"))
        v.addStretch()
        return page

    # ─────────────────────────────────────────────────────
    #  TAB 3 — APPEARANCE
    # ─────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(20)

        # ── Overlay section ──
        v.addWidget(_section_header("Overlay"))

        self._overlay_toggle = ToggleSwitch(True)
        v.addWidget(self._toggle_row(
            "Show Recording Overlay",
            "Floating pill with waveform and live transcript while recording",
            self._overlay_toggle,
        ))

        v.addWidget(_field_label("Overlay Position"))

        # 2×3 position grid
        pos_grid = QWidget()
        pos_grid.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(pos_grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        positions = [
            ("↖", "Top Left",       "top_left"),
            ("⬆", "Top Centre",     "top_centre"),
            ("↗", "Top Right",      "top_right"),
            ("↙", "Bottom Left",    "bottom_left"),
            ("⬇", "Bottom Centre",  "bottom_centre"),
            ("↘", "Bottom Right",   "bottom_right"),
        ]
        self._pos_chips: list[tuple[PositionChip, str]] = []
        for i, (icon, label, key) in enumerate(positions):
            chip = PositionChip(icon, label)
            chip.selected.connect(lambda k=key: self._select_position(k))
            row_idx, col_idx = divmod(i, 3)
            grid.addWidget(chip, row_idx, col_idx)
            self._pos_chips.append((chip, key))
        v.addWidget(pos_grid)

        # ── Theme section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Theme"))
        v.addWidget(_field_label("Background Colour"))

        theme_row = QWidget()
        theme_row.setStyleSheet("background: transparent; border: none;")
        th = QHBoxLayout(theme_row)
        th.setContentsMargins(0, 0, 0, 0)
        th.setSpacing(8)

        themes = [
            ("Navy",  "#06080f", "#0d1530", "navy"),
            ("Slate", "#0f1117", "#1a2235", "slate"),
            ("Black", "#000000", "#0a0a0a", "black"),
        ]
        self._theme_chips: list[tuple[ThemeChip, str, QLabel]] = []
        for name, c1, c2, key in themes:
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent; border: none;")
            wv = QVBoxLayout(wrap)
            wv.setContentsMargins(0, 0, 0, 0)
            wv.setSpacing(4)
            chip = ThemeChip(name, c1, c2)
            chip.selected.connect(lambda k=key: self._select_theme(k))
            wv.addWidget(chip)
            lbl = QLabel(name)
            lbl.setFont(font(9, 600))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "color: rgba(255,255,255,0.28); background: transparent;"
                " border: none; letter-spacing: 1px;"
            )
            wv.addWidget(lbl)
            th.addWidget(wrap, 1)
            self._theme_chips.append((chip, key, lbl))
        v.addWidget(theme_row)

        # Reduce Motion toggle
        self._motion_toggle = ToggleSwitch(False)
        v.addWidget(self._toggle_row(
            "Reduce Motion",
            "Simpler transitions for accessibility or performance",
            self._motion_toggle,
        ))

        v.addStretch()
        return page

    def _select_position(self, key: str):
        for chip, k in self._pos_chips:
            chip.set_active(k == key)
        self._current_position = key

    def _select_theme(self, key: str):
        for chip, k, lbl in self._theme_chips:
            chip.set_active(k == key)
        self._current_theme = key

    # ─────────────────────────────────────────────────────
    #  TAB 4 — ABOUT
    # ─────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 24, 20, 20)
        v.setSpacing(16)
        v.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # App icon
        icon = QLabel("\U0001f399")
        icon.setFixedSize(64, 64)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "font-size: 32px;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 rgba(91,196,255,0.18), stop:1 rgba(91,196,255,0.06));"
            "border: 1px solid rgba(91,196,255,0.20);"
            "border-radius: 16px;"
        )
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        name = QLabel("VoiceType")
        name.setFont(font(18, 600))
        name.setStyleSheet("color: rgba(255,255,255,0.93); background: transparent; border: none;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(name)

        ver = QLabel("Version 1.0.0 · Built with Python + PyQt6")
        ver.setFont(font(12, 400))
        ver.setStyleSheet("color: rgba(255,255,255,0.28); background: transparent; border: none;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(ver)

        desc = QLabel(
            "Hold Right ⌥ to record. Release to transcribe.\n"
            "Text flows into any app — directly into focused\n"
            "fields or to a floating notepad."
        )
        desc.setFont(font(13, 400))
        desc.setStyleSheet("color: rgba(255,255,255,0.55); background: transparent; border: none;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        v.addWidget(desc)

        # Stats row
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            "QFrame {"
            "  background: rgba(9,13,26,0.82);"
            "  border: 1px solid rgba(255,255,255,0.07);"
            f"  border-radius: {RADIUS_MD}px;"
            "}"
        )
        sh = QHBoxLayout(stats_frame)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(1)

        for val, label in [("0:04", "AVG CLIP"), ("23", "THIS MONTH"), ("$0.09", "API COST")]:
            cell = QWidget()
            cell.setStyleSheet("background: transparent; border: none;")
            cv = QVBoxLayout(cell)
            cv.setContentsMargins(12, 12, 12, 12)
            cv.setSpacing(2)
            num = QLabel(val)
            num.setFont(font(18, 600))
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet("color: rgba(255,255,255,0.93); background: transparent; border: none;")
            cv.addWidget(num)
            lab = QLabel(label)
            lab.setFont(font(9, 600))
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet(
                "color: rgba(255,255,255,0.28); background: transparent;"
                " border: none; letter-spacing: 1.5px;"
            )
            cv.addWidget(lab)
            sh.addWidget(cell, 1)

        v.addWidget(stats_frame)

        # Links row
        links_row = QWidget()
        links_row.setStyleSheet("background: transparent; border: none;")
        lh = QHBoxLayout(links_row)
        lh.setContentsMargins(0, 0, 0, 0)
        lh.setSpacing(8)
        lh.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        for label in ["📄  Docs", "🐛  Report Bug", "⭐  GitHub"]:
            btn = QPushButton(label)
            btn.setFont(font(11, 500))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "  padding: 6px 14px;"
                "  border-radius: 99px;"
                "  background: rgba(255,255,255,0.05);"
                "  border: 1px solid rgba(255,255,255,0.08);"
                "  color: rgba(255,255,255,0.55);"
                "}"
                "QPushButton:hover {"
                "  background: rgba(255,255,255,0.10);"
                "  color: rgba(255,255,255,0.93);"
                "}"
            )
            lh.addWidget(btn)
        v.addWidget(links_row)

        v.addStretch()
        return page

    # ─────────────────────────────────────────────────────
    #  FOOTER
    # ─────────────────────────────────────────────────────

    def _build_footer(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            "background: rgba(255,255,255,0.01);"
            "border-top: 1px solid rgba(255,255,255,0.07);"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)

        ver = QLabel("VoiceType v1.0 · Right ⌥ to record")
        ver.setFont(font(11, 400))
        ver.setStyleSheet("color: rgba(255,255,255,0.28); background: transparent; border: none;")
        h.addWidget(ver)
        h.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setFont(font(12, 500))
        cancel.setStyleSheet(BTN_GHOST_SS)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.close)
        h.addWidget(cancel)

        h.addSpacing(8)

        save = QPushButton("Save Settings")
        save.setFont(font(12, 600))
        save.setStyleSheet(BTN_SAVE_SS)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        h.addWidget(save)

        return bar

    # ─────────────────────────────────────────────────────
    #  TOGGLE ROW HELPER
    # ─────────────────────────────────────────────────────

    def _toggle_row(self, title: str, hint: str, toggle: ToggleSwitch) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)

        info = QWidget()
        info.setStyleSheet("background: transparent; border: none;")
        iv = QVBoxLayout(info)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(2)
        iv.addWidget(_field_label(title))
        iv.addWidget(_hint(hint))
        h.addWidget(info, 1)
        h.addWidget(toggle)
        return row

    # ─────────────────────────────────────────────────────
    #  LOAD / SAVE
    # ─────────────────────────────────────────────────────

    def _load_values(self):
        s = self._settings

        self._openai_input.setText(s.get("openai_api_key", ""))

        # Transcription mode
        mode = s.get("transcription_mode", "api")
        self._mode_seg.set_selected(0 if mode == "api" else 1)

        # Model size
        sizes = ["tiny", "base", "small", "medium"]
        idx = sizes.index(s.get("local_model_size", "base")) if s.get("local_model_size") in sizes else 1
        self._model_combo.setCurrentIndex(idx)

        # Language
        lang = s.get("language", "auto")
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == lang:
                self._lang_combo.setCurrentIndex(i)
                break

        # Toggles
        self._ai_cleanup_toggle.set_checked(s.get("ai_cleanup", True), animate=False)
        self._confidence_toggle.set_checked(s.get("confidence_highlights", True), animate=False)
        self._overlay_toggle.set_checked(s.get("show_overlay", True), animate=False)
        self._motion_toggle.set_checked(s.get("reduce_motion", False), animate=False)

        # Position
        self._current_position = s.get("overlay_position", "bottom_centre")
        for chip, k in self._pos_chips:
            chip.set_active(k == self._current_position)

        # Theme
        self._current_theme = s.get("theme", "navy")
        for chip, k, lbl in self._theme_chips:
            chip.set_active(k == self._current_theme)

    def _save(self):
        key = self._openai_input.text().strip()

        # Validate OpenAI key
        if key and not key.startswith("sk-"):
            self._toast.show_error("OpenAI key must start with sk-")
            return

        s = self._settings
        s.set("openai_api_key", key)
        s.set("transcription_mode", "api" if self._mode_seg.selected_index() == 0 else "local")

        sizes = ["tiny", "base", "small", "medium"]
        s.set("local_model_size", sizes[self._model_combo.currentIndex()])

        lang_idx = self._lang_combo.currentIndex()
        s.set("language", self._lang_combo.itemData(lang_idx) or "auto")

        s.set("ai_cleanup", self._ai_cleanup_toggle.is_checked())
        s.set("confidence_highlights", self._confidence_toggle.is_checked())
        s.set("show_overlay", self._overlay_toggle.is_checked())
        s.set("reduce_motion", self._motion_toggle.is_checked())
        s.set("overlay_position", self._current_position)
        s.set("theme", self._current_theme)

        s.save()
        self._toast.show_success("Settings saved")
        self.settings_saved.emit()

    # ─────────────────────────────────────────────────────
    #  WINDOW DRAGGING
    # ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.position().y() < 48:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
