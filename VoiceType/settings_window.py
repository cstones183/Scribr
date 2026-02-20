# settings_window.py — Tabbed settings dialog for Scribr.
# Frameless, 560px wide, 4 tabs, warm coral accent.

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from settings import LANGUAGES, SettingsManager
from style import (
    RADIUS_CARD,
    RADIUS_MD,
    RADIUS_SM,
    font_sans,
    font_serif,
    qcolor_to_rgba,
    theme,
)
from widgets import PositionChip, SegmentedControl, ToastWidget, ToggleSwitch

# ════════════════════════════════════════════════════════════
#  STYLESHEET GENERATORS
# ════════════════════════════════════════════════════════════


def _input_ss() -> str:
    t = theme()
    return (
        "QLineEdit {"
        f"  background: {qcolor_to_rgba(t.surface_2)};"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  border-radius: {RADIUS_SM}px;"
        f"  color: {t.text.name()};"
        "  font-size: 13px;"
        "  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;"
        "  padding: 9px 38px 9px 12px;"
        "}"
        "QLineEdit:focus {"
        f"  border-color: {qcolor_to_rgba(t.red_focus)};"
        "}"
    )


def _select_ss() -> str:
    t = theme()
    return (
        "QComboBox {"
        f"  background: {qcolor_to_rgba(t.surface_2)};"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  border-radius: {RADIUS_SM}px;"
        f"  color: {t.text.name()};"
        "  font-size: 13px;"
        "  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;"
        "  padding: 9px 28px 9px 12px;"
        "}"
        "QComboBox:focus {"
        f"  border-color: {qcolor_to_rgba(t.red_focus)};"
        "}"
        "QComboBox::drop-down { border: none; width: 28px; }"
        "QComboBox::down-arrow { image: none; width: 0; height: 0; }"
        "QComboBox QAbstractItemView {"
        f"  background: {t.surface.name()};"
        f"  color: {t.text.name()};"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  border-radius: {RADIUS_SM}px;"
        f"  selection-background-color: {qcolor_to_rgba(t.red_soft)};"
        f"  selection-color: {t.red.name()};"
        "  outline: none; padding: 4px;"
        "}"
    )


def _btn_ghost_ss() -> str:
    t = theme()
    return (
        "QPushButton {"
        "  border-radius: 999px;"
        "  background: transparent;"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  color: {qcolor_to_rgba(t.text_mid)};"
        "  font-size: 13px; font-weight: 500;"
        "  padding: 8px 16px;"
        "}"
        "QPushButton:hover {"
        f"  background: {qcolor_to_rgba(t.surface_3)};"
        f"  color: {t.text.name()};"
        "}"
    )


def _btn_save_ss() -> str:
    t = theme()
    return (
        "QPushButton {"
        "  border-radius: 999px;"
        f"  background: {t.red.name()};"
        "  border: none;"
        "  color: white;"
        "  font-size: 13px; font-weight: 600;"
        "  padding: 8px 22px;"
        "  letter-spacing: -0.01em;"
        "}"
        "QPushButton:hover { background: #c44434; }"
    )


# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════


def _section_title(text: str) -> QLabel:
    """Red section heading label."""
    t = theme()
    lbl = QLabel(text)
    lbl.setFont(font_sans(9, 600))
    lbl.setStyleSheet(
        f"color: {t.red.name()};"
        "letter-spacing: 2.5px;"
        "text-transform: uppercase;"
        "background: transparent; border: none;"
    )
    return lbl


def _section_line() -> QFrame:
    t = theme()
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {qcolor_to_rgba(t.border)}; border: none;")
    return line


def _field_label(text: str) -> QLabel:
    t = theme()
    lbl = QLabel(text)
    lbl.setFont(font_sans(13, 500))
    lbl.setStyleSheet(
        f"color: {t.text.name()}; background: transparent; border: none;"
        " letter-spacing: -0.01em;"
    )
    return lbl


def _hint(text: str) -> QLabel:
    t = theme()
    lbl = QLabel(text)
    lbl.setFont(font_serif(11, 400, italic=True))
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {qcolor_to_rgba(t.text_light)};"
        " background: transparent; border: none; line-height: 1.5;"
    )
    return lbl


def _badge(text: str, active: bool = True) -> QLabel:
    t = theme()
    lbl = QLabel(text)
    lbl.setFont(font_sans(9, 600))
    if active:
        lbl.setStyleSheet(
            f"background: {qcolor_to_rgba(t.red_soft)};"
            f"color: {t.red.name()};"
            f"border: 1px solid {qcolor_to_rgba(t.red_border)};"
            "border-radius: 999px; padding: 3px 9px;"
            " letter-spacing: 0.1em; text-transform: uppercase;"
        )
    else:
        lbl.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"color: {qcolor_to_rgba(t.text_light)};"
            f"border: 1px solid {qcolor_to_rgba(t.border)};"
            "border-radius: 999px; padding: 3px 9px;"
            " letter-spacing: 0.1em; text-transform: uppercase;"
        )
    return lbl


def _section_header(text: str) -> QWidget:
    """Section title + trailing line in a row."""
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
    """Single tab in the tab bar — icon above label."""

    def __init__(self, icon: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_text = icon
        self._label_text = label
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._apply_style()

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_style()

    def _apply_style(self) -> None:
        t = theme()
        if self._active:
            self.setStyleSheet(
                "QPushButton {"
                f"  color: {t.red.name()};"
                "  background: transparent; border: none;"
                f"  border-bottom: 2px solid {t.red.name()};"
                "  padding: 10px 4px 9px;"
                "  font-size: 11px; font-weight: 600;"
                "  letter-spacing: 0.03em;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                f"  color: {qcolor_to_rgba(t.text_light)};"
                "  background: transparent; border: none;"
                "  border-bottom: 2px solid transparent;"
                "  padding: 10px 4px 9px;"
                "  font-size: 11px; font-weight: 600;"
                "  letter-spacing: 0.03em;"
                "}"
                "QPushButton:hover {"
                f"  color: {qcolor_to_rgba(t.text_mid)};"
                "}"
            )
        self.setText(f"{self._icon_text}\n{self._label_text}")


# ════════════════════════════════════════════════════════════
#  SETTINGS WINDOW
# ════════════════════════════════════════════════════════════


class SettingsWindow(QWidget):
    """Frameless settings dialog — 560px wide, 4 tabs, Scribr brand."""

    settings_saved = pyqtSignal()

    def __init__(self, settings: SettingsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(560)

        self._drag_pos: QPoint | None = None

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
    #  PAINT — solid surface fill
    # ─────────────────────────────────────────────────────

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = RADIUS_CARD

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, r, r)
        p.setClipPath(path)

        # Solid surface fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawPath(path)

        # Border
        p.setPen(QPen(t.border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(0, 0, w, h, r, r)
        p.end()

    # ─────────────────────────────────────────────────────
    #  TITLEBAR
    # ─────────────────────────────────────────────────────

    def _build_titlebar(self) -> QWidget:
        t = theme()
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"border-bottom: 1px solid {qcolor_to_rgba(t.border)};"
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
                f"QPushButton:hover {{ filter: brightness(0.88); }}"
            )
            if color == "#ff5f57":
                dot.clicked.connect(self.close)
            h.addWidget(dot)
            h.addSpacing(6)

        h.addStretch()

        title = QLabel("Scribr Settings")
        title.setFont(font_serif(14, 600))
        title.setStyleSheet(
            f"color: {t.text.name()}; background: transparent; border: none;"
            " letter-spacing: -0.01em;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(title)

        h.addStretch()
        spacer = QWidget()
        spacer.setFixedWidth(52)
        spacer.setStyleSheet("background: transparent; border: none;")
        h.addWidget(spacer)

        return bar

    # ─────────────────────────────────────────────────────
    #  TAB BAR
    # ─────────────────────────────────────────────────────

    def _build_tab_bar(self) -> tuple[QWidget, list[_TabButton]]:
        t = theme()
        bar = QWidget()
        bar.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"border-bottom: 1px solid {qcolor_to_rgba(t.border)};"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        tab_defs = [
            ("\U0001f511", "API Keys"),
            ("\u2699\ufe0f", "Transcription"),
            ("\U0001f3a8", "Appearance"),
            ("\u2139\ufe0f", "About"),
        ]

        tabs: list[_TabButton] = []
        for i, (icon, label) in enumerate(tab_defs):
            btn = _TabButton(icon, label)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            h.addWidget(btn, 1)
            tabs.append(btn)

        return bar, tabs

    def _switch_tab(self, idx: int) -> None:
        for i, tab in enumerate(self._tabs):
            tab.set_active(i == idx)
        self._stack.setCurrentIndex(idx)

    # ─────────────────────────────────────────────────────
    #  TAB 1 — API KEYS
    # ─────────────────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        t = theme()
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
        rl.addWidget(_badge("Active", active=True))
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
        self._openai_input.setStyleSheet(_input_ss())
        self._openai_input.setMinimumHeight(38)
        il.addWidget(self._openai_input)

        self._eye_btn = QPushButton("\U0001f441")
        self._eye_btn.setFixedSize(38, 38)
        self._eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._eye_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 14px;"
            f" color: {qcolor_to_rgba(t.text_light)}; }}"
            "QPushButton:hover {"
            f" color: {qcolor_to_rgba(t.text_mid)};"
            f" background: {qcolor_to_rgba(t.surface_2)}; border-radius: 4px; }}"
        )
        self._eye_btn.clicked.connect(self._toggle_eye)
        il.addWidget(self._eye_btn)
        v.addWidget(input_wrap)

        v.addWidget(
            _hint("Whisper transcription \u00b7 GPT-4o-mini cleanup \u00b7 ~$0.006/min")
        )

        # ── Coming Soon section ──
        v.addSpacing(8)
        v.addWidget(_section_header("Coming Soon"))

        cs_frame = QFrame()
        cs_frame.setStyleSheet(
            "QFrame {"
            f"  background: {t.surface.name()};"
            f"  border: 1px solid {qcolor_to_rgba(t.border)};"
            f"  border-radius: {RADIUS_SM}px;"
            "}"
        )
        cs_v = QVBoxLayout(cs_frame)
        cs_v.setContentsMargins(0, 0, 0, 0)
        cs_v.setSpacing(0)

        providers = [
            ("\U0001f30a", "Deepgram", "Ultra-fast streaming transcription"),
            ("\u26a1", "Groq", "Whisper at 10x inference speed"),
            ("\U0001f50a", "AssemblyAI", "Speaker detection + smart formatting"),
        ]
        for i, (emoji, name, desc) in enumerate(providers):
            row = QWidget()
            row.setStyleSheet(
                f"background: {qcolor_to_rgba(t.surface_2)}; border: none;"
                + (
                    f" border-bottom: 1px solid {qcolor_to_rgba(t.border)};"
                    if i < len(providers) - 1
                    else ""
                )
            )
            row.setFixedHeight(52)
            rh = QHBoxLayout(row)
            rh.setContentsMargins(14, 0, 14, 0)
            rh.setSpacing(12)

            logo = QLabel(emoji)
            logo.setFixedSize(28, 28)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet(
                f"background: {t.surface.name()};"
                f" border: 1px solid {qcolor_to_rgba(t.border)};"
                f" border-radius: {RADIUS_SM}px; font-size: 14px;"
            )
            rh.addWidget(logo)

            info = QWidget()
            info.setStyleSheet("background: transparent; border: none;")
            iv = QVBoxLayout(info)
            iv.setContentsMargins(0, 0, 0, 0)
            iv.setSpacing(1)
            n = QLabel(name)
            n.setFont(font_sans(13, 500))
            n.setStyleSheet(
                f"color: {t.text.name()}; background: transparent; border: none;"
            )
            iv.addWidget(n)
            d = QLabel(desc)
            d.setFont(font_serif(11, 400, italic=True))
            d.setStyleSheet(
                f"color: {qcolor_to_rgba(t.text_light)};"
                " background: transparent; border: none;"
            )
            iv.addWidget(d)
            rh.addWidget(info, 1)

            rh.addWidget(_badge("Soon", active=False))
            cs_v.addWidget(row)

        # Dim the whole coming-soon frame
        cs_frame.setGraphicsEffect(None)
        v.addWidget(cs_frame)
        v.addStretch()
        return page

    def _toggle_eye(self) -> None:
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

        # ── Engine section ──
        v.addWidget(_section_header("Engine"))

        v.addWidget(_field_label("Transcription Mode"))
        self._mode_seg = SegmentedControl(["\u2601\ufe0f  API", "\U0001f4bb  Local"])
        v.addWidget(self._mode_seg)
        v.addWidget(
            _hint(
                "Local mode uses Whisper on your Mac. Free, offline, ~1s on Apple Silicon."
            )
        )

        v.addWidget(_field_label("Local Model Size"))
        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(_select_ss())
        self._model_combo.setMinimumHeight(38)
        self._model_combo.addItems([
            "tiny \u2014 75MB \u00b7 Fastest",
            "base \u2014 145MB \u00b7 Recommended",
            "small \u2014 460MB \u00b7 Better accuracy",
            "medium \u2014 1.5GB \u00b7 Best accuracy",
        ])
        v.addWidget(self._model_combo)

        # ── Language & Cleanup section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Language & Cleanup"))

        v.addWidget(_field_label("Language"))
        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(_select_ss())
        self._lang_combo.setMinimumHeight(38)
        for display, code in LANGUAGES:
            self._lang_combo.addItem(display, code)
        v.addWidget(self._lang_combo)

        # AI Cleanup toggle
        self._ai_cleanup_toggle = ToggleSwitch(True)
        v.addWidget(
            self._toggle_row(
                "AI Cleanup",
                "Remove filler words and fix punctuation via GPT-4o-mini",
                self._ai_cleanup_toggle,
            )
        )

        # Confidence toggle
        self._confidence_toggle = ToggleSwitch(True)
        v.addWidget(
            self._toggle_row(
                "Confidence Highlights",
                "Underline uncertain words in amber for easy review",
                self._confidence_toggle,
            )
        )

        # ── Shortcut section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Shortcut"))

        hotkey_row = QWidget()
        hotkey_row.setStyleSheet("background: transparent; border: none;")
        hk = QHBoxLayout(hotkey_row)
        hk.setContentsMargins(0, 0, 0, 0)
        hk.setSpacing(14)

        info = QWidget()
        info.setStyleSheet("background: transparent; border: none;")
        iv = QVBoxLayout(info)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(2)
        iv.addWidget(_field_label("Record Shortcut"))
        iv.addWidget(_hint("Hold to record \u00b7 Release to transcribe"))
        hk.addWidget(info, 1)

        t = theme()
        key_cap = QLabel("Right \u2325")
        key_cap.setFont(font_sans(12, 600))
        key_cap.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"border: 1px solid {qcolor_to_rgba(t.border_2)};"
            f"border-bottom: 2px solid {qcolor_to_rgba(t.border_2)};"
            f"border-radius: 7px;"
            f"color: {t.text.name()};"
            "padding: 4px 12px;"
        )
        hk.addWidget(key_cap)
        v.addWidget(hotkey_row)

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
        v.addWidget(
            self._toggle_row(
                "Show Recording Overlay",
                "Floating pill with waveform and live transcript while recording",
                self._overlay_toggle,
            )
        )

        v.addWidget(_field_label("Overlay Position"))

        # 2x3 position grid
        pos_grid = QWidget()
        pos_grid.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(pos_grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        positions = [
            ("\u2196", "Top Left", "top_left"),
            ("\u2b06", "Top Centre", "top_centre"),
            ("\u2197", "Top Right", "top_right"),
            ("\u2199", "Bot Left", "bottom_left"),
            ("\u2b07", "Bot Centre", "bottom_centre"),
            ("\u2198", "Bot Right", "bottom_right"),
        ]
        self._pos_chips: list[tuple[PositionChip, str]] = []
        for i, (icon, label, key) in enumerate(positions):
            chip = PositionChip(icon, label)
            chip.selected.connect(lambda k=key: self._select_position(k))
            row_idx, col_idx = divmod(i, 3)
            grid.addWidget(chip, row_idx, col_idx)
            self._pos_chips.append((chip, key))
        v.addWidget(pos_grid)

        # ── Accessibility section ──
        v.addSpacing(4)
        v.addWidget(_section_header("Accessibility"))

        self._motion_toggle = ToggleSwitch(False)
        v.addWidget(
            self._toggle_row(
                "Reduce Motion",
                "Simpler transitions for accessibility or performance",
                self._motion_toggle,
            )
        )

        v.addStretch()
        return page

    def _select_position(self, key: str) -> None:
        for chip, k in self._pos_chips:
            chip.set_active(k == key)
        self._current_position = key

    # ─────────────────────────────────────────────────────
    #  TAB 4 — ABOUT
    # ─────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        t = theme()
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 32, 20, 8)
        v.setSpacing(14)
        v.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # App icon — red rounded square with mic
        icon = QLabel("\U0001f399")
        icon.setFixedSize(72, 72)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "font-size: 32px;"
            f"background: {t.red.name()};"
            f"border-radius: 18px;"
            "color: white;"
        )
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        name = QLabel("Scribr")
        name.setFont(font_serif(24, 600))
        name.setStyleSheet(
            f"color: {t.text.name()}; background: transparent; border: none;"
            " letter-spacing: -0.02em;"
        )
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(name)

        ver = QLabel("Version 1.0.0 \u00b7 Python + PyQt6")
        ver.setFont(font_serif(12, 400, italic=True))
        ver.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_light)};"
            " background: transparent; border: none;"
        )
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(ver)

        desc = QLabel(
            "Just tap, talk, and it\u2019s done.\n"
            "Your voice, turned into text \u2014 ready\n"
            "to read in seconds."
        )
        desc.setFont(font_serif(14, 400, italic=True))
        desc.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_mid)};"
            " background: transparent; border: none;"
            " line-height: 1.7;"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setMaximumWidth(320)
        v.addWidget(desc, 0, Qt.AlignmentFlag.AlignHCenter)

        # Stats row
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            "QFrame {"
            f"  background: {qcolor_to_rgba(t.border)};"
            f"  border: 1px solid {qcolor_to_rgba(t.border)};"
            f"  border-radius: {RADIUS_MD}px;"
            "}"
        )
        sh = QHBoxLayout(stats_frame)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(1)

        stats = [
            ("23", "THIS MONTH", True),
            ("0:04", "AVG CLIP", False),
            ("$0.09", "API COST", False),
        ]
        for val, label, accent in stats:
            cell = QWidget()
            cell.setStyleSheet(
                f"background: {qcolor_to_rgba(t.surface_2)}; border: none;"
            )
            cv = QVBoxLayout(cell)
            cv.setContentsMargins(12, 16, 12, 16)
            cv.setSpacing(3)
            num = QLabel(val)
            num.setFont(font_serif(26, 600))
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = t.red.name() if accent else t.text.name()
            num.setStyleSheet(
                f"color: {color}; background: transparent; border: none;"
                " letter-spacing: -0.03em;"
            )
            cv.addWidget(num)
            lab = QLabel(label)
            lab.setFont(font_sans(9, 600))
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet(
                f"color: {qcolor_to_rgba(t.text_light)}; background: transparent;"
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

        for label in [
            "\U0001f4c4  Docs",
            "\U0001f41b  Report Bug",
            "\u2b50  GitHub",
        ]:
            btn = QPushButton(label)
            btn.setFont(font_sans(12, 500))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                "  padding: 7px 16px; border-radius: 999px;"
                f"  background: {qcolor_to_rgba(t.surface_2)};"
                f"  border: 1px solid {qcolor_to_rgba(t.border)};"
                f"  color: {qcolor_to_rgba(t.text_mid)};"
                "}"
                "QPushButton:hover {"
                f"  background: {qcolor_to_rgba(t.surface_3)};"
                f"  color: {t.text.name()};"
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
        t = theme()
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"border-top: 1px solid {qcolor_to_rgba(t.border)};"
        )
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)

        ver = QLabel("Scribr v1.0 \u00b7 Just tap, talk, and it\u2019s done.")
        ver.setFont(font_serif(11, 400, italic=True))
        ver.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_light)};"
            " background: transparent; border: none;"
        )
        h.addWidget(ver)
        h.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setFont(font_sans(13, 500))
        cancel.setStyleSheet(_btn_ghost_ss())
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.close)
        h.addWidget(cancel)

        h.addSpacing(8)

        save = QPushButton("Save")
        save.setFont(font_sans(13, 600))
        save.setStyleSheet(_btn_save_ss())
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        h.addWidget(save)

        return bar

    # ─────────────────────────────────────────────────────
    #  TOGGLE ROW HELPER
    # ─────────────────────────────────────────────────────

    def _toggle_row(self, title: str, hint_text: str, toggle: ToggleSwitch) -> QWidget:
        t = theme()
        row = QWidget()
        row.setStyleSheet(
            "background: transparent; border: none;"
            f" border-bottom: 1px solid {qcolor_to_rgba(t.border)};"
        )
        row.setMinimumHeight(52)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 13, 0, 13)
        h.setSpacing(14)

        info = QWidget()
        info.setStyleSheet("background: transparent; border: none;")
        iv = QVBoxLayout(info)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(2)
        iv.addWidget(_field_label(title))
        iv.addWidget(_hint(hint_text))
        h.addWidget(info, 1)
        h.addWidget(toggle)
        return row

    # ─────────────────────────────────────────────────────
    #  LOAD / SAVE
    # ─────────────────────────────────────────────────────

    def _load_values(self) -> None:
        s = self._settings

        self._openai_input.setText(s.get("openai_api_key", ""))

        # Transcription mode
        mode = s.get("transcription_mode", "api")
        self._mode_seg.set_selected(0 if mode == "api" else 1)

        # Model size
        sizes = ["tiny", "base", "small", "medium"]
        model = s.get("local_model_size", "base")
        idx = sizes.index(model) if model in sizes else 1
        self._model_combo.setCurrentIndex(idx)

        # Language
        lang = s.get("language", "auto")
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == lang:
                self._lang_combo.setCurrentIndex(i)
                break

        # Toggles
        self._ai_cleanup_toggle.set_checked(s.get("ai_cleanup", True), animate=False)
        self._confidence_toggle.set_checked(
            s.get("confidence_highlights", True), animate=False
        )
        self._overlay_toggle.set_checked(s.get("show_overlay", True), animate=False)
        self._motion_toggle.set_checked(s.get("reduce_motion", False), animate=False)

        # Position
        self._current_position = s.get("overlay_position", "bottom_centre")
        for chip, k in self._pos_chips:
            chip.set_active(k == self._current_position)

    def _save(self) -> None:
        key = self._openai_input.text().strip()

        # Validate OpenAI key (friendly error message per brand)
        if key and not key.startswith("sk-"):
            self._toast.show_error(
                "That doesn\u2019t look right \u2014 keys start with sk-"
            )
            return

        s = self._settings
        s.set("openai_api_key", key)
        s.set(
            "transcription_mode",
            "api" if self._mode_seg.selected_index() == 0 else "local",
        )

        sizes = ["tiny", "base", "small", "medium"]
        s.set("local_model_size", sizes[self._model_combo.currentIndex()])

        lang_idx = self._lang_combo.currentIndex()
        s.set("language", self._lang_combo.itemData(lang_idx) or "auto")

        s.set("ai_cleanup", self._ai_cleanup_toggle.is_checked())
        s.set("confidence_highlights", self._confidence_toggle.is_checked())
        s.set("show_overlay", self._overlay_toggle.is_checked())
        s.set("reduce_motion", self._motion_toggle.is_checked())
        s.set("overlay_position", self._current_position)

        s.save()
        self._toast.show_success("\u2713 Done")
        self.settings_saved.emit()

    # ─────────────────────────────────────────────────────
    #  WINDOW DRAGGING
    # ─────────────────────────────────────────────────────

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        from PyQt6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent) and event.position().y() < 48:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: object) -> None:  # type: ignore[override]
        from PyQt6.QtGui import QMouseEvent

        if self._drag_pos is not None and isinstance(event, QMouseEvent):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: object) -> None:  # type: ignore[override]
        self._drag_pos = None
