# settings_window.py — Tabbed settings dialog for Scribr.
# Frameless, 560px wide, 4 tabs, warm coral accent.

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from settings import LANGUAGES, SettingsManager
from stats import StatsManager
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
        "  min-height: 34px;"
        "  border-radius: 17px;"
        "  background: transparent;"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  color: {qcolor_to_rgba(t.text_mid)};"
        "  font-size: 13px; font-weight: 500;"
        "  padding: 0px 16px;"
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
        "  min-height: 34px;"
        "  border-radius: 17px;"
        f"  background: {t.red.name()};"
        "  border: none;"
        "  color: white;"
        "  font-size: 13px; font-weight: 600;"
        "  padding: 0px 22px;"
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
    lbl.setFixedHeight(22)
    if active:
        lbl.setStyleSheet(
            f"background: {qcolor_to_rgba(t.red_soft)};"
            f"color: {t.red.name()};"
            f"border: 1px solid {qcolor_to_rgba(t.red_border)};"
            "border-radius: 11px; padding: 3px 9px;"
            " letter-spacing: 0.1em; text-transform: uppercase;"
        )
    else:
        lbl.setStyleSheet(
            f"background: {qcolor_to_rgba(t.surface_2)};"
            f"color: {qcolor_to_rgba(t.text_light)};"
            f"border: 1px solid {qcolor_to_rgba(t.border)};"
            "border-radius: 11px; padding: 3px 9px;"
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


class _CardFrame(QFrame):
    """Rounded card container matching HTML .row group pattern.

    Usage::

        card = _CardFrame()
        card.add_row(row_widget_1)
        card.add_row(row_widget_2)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Transparent stylesheet — painting handled in paintEvent
        self.setStyleSheet("QFrame#cardFrame { background: transparent; border: none; }")
        self.setObjectName("cardFrame")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(1, 1, 1, 1)  # room for border
        self._layout.setSpacing(0)
        self._rows: list[QWidget] = []

    def add_row(self, widget: QWidget) -> None:
        """Add a row. All rows except the last get a bottom border."""
        self._rows.append(widget)
        self._layout.addWidget(widget)
        self._refresh_borders()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = RADIUS_SM

        # Clip to rounded rect so child backgrounds don't overpaint corners
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)

        # Fill background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawRect(0, 0, w, h)

        # Draw row separator lines
        for i, row in enumerate(self._rows[:-1]):
            y = row.geometry().bottom() + 1
            p.setPen(QPen(t.border, 1))
            p.drawLine(0, y, w, y)

        # Outer border
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(t.border, 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.end()

    def _refresh_borders(self) -> None:
        t = theme()
        for row in self._rows:
            row.setStyleSheet(
                f"background: transparent; border: none;"
            )


def _card_row(
    title: str,
    hint_text: str | None = None,
    right_widget: QWidget | None = None,
    badge: QLabel | None = None,
) -> QWidget:
    """Standard settings row matching HTML .row pattern."""
    t = theme()
    row = QWidget()
    row.setMinimumHeight(52)
    h = QHBoxLayout(row)
    h.setContentsMargins(18, 13, 18, 13)
    h.setSpacing(14)

    info = QWidget()
    info.setStyleSheet("background: transparent; border: none;")
    iv = QVBoxLayout(info)
    iv.setContentsMargins(0, 0, 0, 0)
    iv.setSpacing(2)
    iv.addWidget(_field_label(title))
    if hint_text:
        iv.addWidget(_hint(hint_text))
    h.addWidget(info, 1)

    if badge:
        h.addWidget(badge)
    if right_widget:
        h.addWidget(right_widget)
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
        self.setFixedHeight(52)
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
                "  padding: 6px 4px 7px;"
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
                "  padding: 6px 4px 7px;"
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

    def __init__(self, settings: SettingsManager, stats: StatsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._stats = stats

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
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
        self._stack.setMinimumHeight(420)
        self._stack.addWidget(self._build_api_tab())
        self._stack.addWidget(self._build_transcription_tab())
        self._stack.addWidget(self._build_ai_tab())
        self._stack.addWidget(self._build_appearance_tab())
        self._stack.addWidget(self._build_about_tab())
        root.addWidget(self._stack, 1)

        # ── Footer ───────────────────────────────────────
        self._footer = self._build_footer()
        root.addWidget(self._footer)

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

        # Clip everything to the rounded window shape (antialiased)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)

        # Body fill (surface colour covers the whole window)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawRect(0, 0, w, h)

        # Titlebar background (surface_2) — fills top area including corners
        tb = self._titlebar.geometry()
        p.setBrush(t.surface_2)
        p.drawRect(0, 0, w, tb.bottom() + 1)

        # Tab bar background (surface_2)
        tab = self._tab_bar_widget.geometry()
        p.drawRect(0, tab.y(), w, tab.height())

        # Footer background (surface_2)
        ft = self._footer.geometry()
        p.setBrush(t.surface_2)
        p.drawRect(0, ft.y(), w, h - ft.y())

        # Separator lines
        p.setPen(QPen(t.border, 1))
        p.drawLine(0, tb.bottom(), w, tb.bottom())          # below titlebar
        p.drawLine(0, tab.bottom(), w, tab.bottom())         # below tab bar
        p.drawLine(0, ft.y(), w, ft.y())                     # above footer

        # Outer border (drawn last, on top of everything)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.end()

    def resizeEvent(self, event: object) -> None:  # type: ignore[override]
        super().resizeEvent(event)  # type: ignore[arg-type]
        # WA_TranslucentBackground makes unpainted areas transparent and
        # click-through on macOS, so no QRegion mask is needed.
        # (QRegion is pixel-based and creates jagged corners.)

    # ─────────────────────────────────────────────────────
    #  TITLEBAR
    # ─────────────────────────────────────────────────────

    def _build_titlebar(self) -> QWidget:
        t = theme()
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(0)

        # Close button
        close_dot = QPushButton()
        close_dot.setFixedSize(12, 12)
        close_dot.setCursor(Qt.CursorShape.PointingHandCursor)
        close_dot.setStyleSheet(
            "QPushButton { background: #ff5f57; border-radius: 6px; border: none; }"
            "QPushButton:hover { background: #e04640; }"
        )
        close_dot.clicked.connect(self.hide)
        h.addWidget(close_dot)

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
        spacer.setFixedWidth(16)
        spacer.setStyleSheet("background: transparent; border: none;")
        h.addWidget(spacer)

        return bar

    # ─────────────────────────────────────────────────────
    #  TAB BAR
    # ─────────────────────────────────────────────────────

    def _build_tab_bar(self) -> tuple[QWidget, list[_TabButton]]:
        t = theme()
        bar = QWidget()
        bar.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        tab_defs = [
            ("\U0001f511", "API Keys"),
            ("\u2699\ufe0f", "Transcription"),
            ("\u2728", "AI Mode"),
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
    #  SCROLL AREA HELPER
    # ─────────────────────────────────────────────────────

    def _styled_scroll_area(self) -> QScrollArea:
        """Create a scroll area with a styled thin scrollbar."""
        t = theme()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        handle_col = qcolor_to_rgba(t.text_light)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical {"
            "  background: transparent; width: 6px;"
            "  margin: 4px 1px 4px 0px;"
            "}"
            f"QScrollBar::handle:vertical {{"
            f"  background: {handle_col}; border-radius: 3px;"
            f"  min-height: 30px;"
            f"}}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px;"
            "}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            "  background: transparent;"
            "}"
        )
        return scroll

    # ─────────────────────────────────────────────────────
    #  TAB 1 — API KEYS
    # ─────────────────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        t = theme()
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(4)

        # ── Active Provider section ──
        v.addWidget(_section_header("Active Provider"))

        card = _CardFrame()

        # OpenAI key row — title/hint left, input+badge right
        oai_row = QWidget()
        oai_row.setMinimumHeight(52)
        rh = QHBoxLayout(oai_row)
        rh.setContentsMargins(18, 13, 18, 13)
        rh.setSpacing(14)

        oai_info = QWidget()
        oai_info.setStyleSheet("background: transparent; border: none;")
        oai_v = QVBoxLayout(oai_info)
        oai_v.setContentsMargins(0, 0, 0, 0)
        oai_v.setSpacing(2)
        oai_v.addWidget(_field_label("OpenAI API Key"))
        oai_v.addWidget(
            _hint("Whisper transcription \u00b7 GPT-4o-mini cleanup \u00b7 ~$0.006/min")
        )
        rh.addWidget(oai_info, 1)

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
        self._openai_input.setMaximumWidth(220)
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
        rh.addWidget(input_wrap)

        rh.addWidget(_badge("Active", active=True))
        card.add_row(oai_row)

        # Groq key row — same structure as OpenAI row
        groq_row = QWidget()
        groq_row.setMinimumHeight(52)
        grh = QHBoxLayout(groq_row)
        grh.setContentsMargins(18, 13, 18, 13)
        grh.setSpacing(14)

        groq_info = QWidget()
        groq_info.setStyleSheet("background: transparent; border: none;")
        groq_v = QVBoxLayout(groq_info)
        groq_v.setContentsMargins(0, 0, 0, 0)
        groq_v.setSpacing(2)
        groq_v.addWidget(_field_label("Groq API Key"))
        groq_v.addWidget(
            _hint("Whisper at 10\u00d7 speed \u00b7 enables live transcription")
        )
        grh.addWidget(groq_info, 1)

        groq_input_wrap = QWidget()
        groq_input_wrap.setStyleSheet("background: transparent; border: none;")
        gil = QHBoxLayout(groq_input_wrap)
        gil.setContentsMargins(0, 0, 0, 0)
        gil.setSpacing(0)
        self._groq_input = QLineEdit()
        self._groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_input.setPlaceholderText("gsk_...")
        self._groq_input.setStyleSheet(_input_ss())
        self._groq_input.setMinimumHeight(38)
        self._groq_input.setMaximumWidth(220)
        gil.addWidget(self._groq_input)

        self._groq_eye_btn = QPushButton("\U0001f441")
        self._groq_eye_btn.setFixedSize(38, 38)
        self._groq_eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._groq_eye_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 14px;"
            f" color: {qcolor_to_rgba(t.text_light)}; }}"
            "QPushButton:hover {"
            f" color: {qcolor_to_rgba(t.text_mid)};"
            f" background: {qcolor_to_rgba(t.surface_2)}; border-radius: 4px; }}"
        )
        self._groq_eye_btn.clicked.connect(self._toggle_groq_eye)
        gil.addWidget(self._groq_eye_btn)
        grh.addWidget(groq_input_wrap)

        grh.addWidget(_badge("Active", active=True))
        card.add_row(groq_row)

        v.addWidget(card)
        v.addStretch()
        return page

    def _toggle_eye(self) -> None:
        if self._openai_input.echoMode() == QLineEdit.EchoMode.Password:
            self._openai_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye_btn.setText("\U0001f648")
        else:
            self._openai_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye_btn.setText("\U0001f441")

    def _toggle_groq_eye(self) -> None:
        if self._groq_input.echoMode() == QLineEdit.EchoMode.Password:
            self._groq_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._groq_eye_btn.setText("\U0001f648")
        else:
            self._groq_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._groq_eye_btn.setText("\U0001f441")

    # ─────────────────────────────────────────────────────
    #  TAB 2 — TRANSCRIPTION
    # ─────────────────────────────────────────────────────

    def _build_transcription_tab(self) -> QWidget:
        t = theme()
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = self._styled_scroll_area()
        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(4)

        # ── Engine section ──
        v.addWidget(_section_header("Engine"))

        engine_card = _CardFrame()

        # Live Update Interval (Groq)
        self._interval_combo = QComboBox()
        self._interval_combo.setStyleSheet(_select_ss())
        self._interval_combo.setMinimumHeight(38)
        self._interval_combo.setMinimumWidth(120)
        self._interval_combo.addItems(["1 second", "2 seconds", "3 seconds"])
        engine_card.add_row(
            _card_row(
                "Live Update Interval",
                "How often Groq receives audio snapshots during recording",
                self._interval_combo,
            )
        )
        v.addWidget(engine_card)

        # ── Language & Cleanup section ──
        v.addSpacing(8)
        v.addWidget(_section_header("Language & Cleanup"))

        lang_card = _CardFrame()

        # Language row
        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(_select_ss())
        self._lang_combo.setMinimumHeight(38)
        self._lang_combo.setMinimumWidth(160)
        for display, code in LANGUAGES:
            self._lang_combo.addItem(display, code)
        lang_card.add_row(_card_row("Language", None, self._lang_combo))

        # AI Cleanup toggle
        self._ai_cleanup_toggle = ToggleSwitch(True)
        lang_card.add_row(
            _card_row(
                "AI Cleanup",
                "Remove filler words via GPT-4o-mini \u00b7 ~$0.01/month",
                self._ai_cleanup_toggle,
            )
        )

        # Confidence toggle
        self._confidence_toggle = ToggleSwitch(True)
        lang_card.add_row(
            _card_row(
                "Confidence Highlights",
                "Underline uncertain words for easy review",
                self._confidence_toggle,
            )
        )
        v.addWidget(lang_card)

        # ── Shortcut section ──
        v.addSpacing(8)
        v.addWidget(_section_header("Shortcut"))

        shortcut_card = _CardFrame()
        self._hotkey_combo = QComboBox()
        self._hotkey_combo.setStyleSheet(_select_ss())
        self._hotkey_combo.setMinimumHeight(38)
        self._hotkey_combo.setMinimumWidth(140)
        _hotkey_choices = [
            ("Right \u2325 Option", "alt_r"),
            ("Right \u2318 Command", "cmd_r"),
            ("Right \u2303 Control", "ctrl_r"),
            ("F1", "f1"),
            ("F2", "f2"),
            ("F3", "f3"),
        ]
        for display, code in _hotkey_choices:
            self._hotkey_combo.addItem(display, code)
        shortcut_card.add_row(
            _card_row(
                "Record Shortcut",
                "Hold to record \u00b7 release to transcribe",
                self._hotkey_combo,
            )
        )
        v.addWidget(shortcut_card)

        v.addStretch()
        scroll.setWidget(inner)
        page_layout.addWidget(scroll)
        return page

    # ─────────────────────────────────────────────────────
    #  TAB 3 — AI MODE
    # ─────────────────────────────────────────────────────

    def _build_ai_tab(self) -> QWidget:
        t = theme()
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = self._styled_scroll_area()
        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(4)

        # ── LLM Formatting section ──
        v.addWidget(_section_header("LLM Formatting"))

        ai_card = _CardFrame()

        # AI Mode Default toggle
        self._ai_default_toggle = ToggleSwitch(False)
        ai_card.add_row(
            _card_row(
                "AI Mode Default",
                "Automatically format transcripts for LLM input",
                self._ai_default_toggle,
            )
        )

        # AI Format Style segmented control
        self._ai_style_seg = SegmentedControl(["Structured", "Condensed", "Bullets", "Prompt"])
        self._ai_style_row = _card_row(
            "Format Style",
            "How to structure the formatted output",
            self._ai_style_seg,
        )
        ai_card.add_row(self._ai_style_row)

        # Show original toggle
        self._ai_show_original_toggle = ToggleSwitch(False)
        ai_card.add_row(
            _card_row(
                "Show Original",
                "Display raw transcript below the formatted version",
                self._ai_show_original_toggle,
            )
        )

        v.addWidget(ai_card)

        # Connect AI Default to enable/disable the Style row
        self._ai_default_toggle.toggled.connect(self._on_ai_default_toggled)

        # ── How It Works section ──
        v.addSpacing(8)
        v.addWidget(_section_header("How It Works"))

        info_card = _CardFrame()
        info_row = QWidget()
        info_row.setMinimumHeight(52)
        info_h = QHBoxLayout(info_row)
        info_h.setContentsMargins(18, 16, 18, 16)

        info_label = QLabel(
            "When AI Mode is active, your transcription is sent to GPT-4o-mini "
            "to restructure it into clean, labelled context optimised for pasting "
            "into an LLM chat.\n\n"
            "Toggle AI Mode per-transcription using the switch in the notepad footer, "
            "or enable it by default above."
        )
        info_label.setFont(font_serif(12, 400, italic=True))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_mid)};"
            " background: transparent; border: none; line-height: 1.5;"
        )
        info_h.addWidget(info_label)
        info_card.add_row(info_row)
        v.addWidget(info_card)

        v.addStretch()
        scroll.setWidget(inner)
        page_layout.addWidget(scroll)
        return page

    def _on_ai_default_toggled(self, checked: bool) -> None:
        self._ai_style_row.setEnabled(checked)

    # ─────────────────────────────────────────────────────
    #  TAB 3 — APPEARANCE
    # ─────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        t = theme()
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(page)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(4)

        # ── Overlay section ──
        v.addWidget(_section_header("Overlay"))

        overlay_card = _CardFrame()

        # Show Recording Overlay toggle row
        self._overlay_toggle = ToggleSwitch(True)
        overlay_card.add_row(
            _card_row(
                "Show Recording Overlay",
                "Floating pill with waveform during recording",
                self._overlay_toggle,
            )
        )

        # Position row — column layout with grid inside
        pos_row = QWidget()
        pos_row.setMinimumHeight(52)
        pos_v = QVBoxLayout(pos_row)
        pos_v.setContentsMargins(18, 13, 18, 13)
        pos_v.setSpacing(12)
        pos_v.addWidget(_field_label("Position"))

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
        pos_v.addWidget(pos_grid)
        overlay_card.add_row(pos_row)

        v.addWidget(overlay_card)

        # ── Accessibility section ──
        v.addSpacing(8)
        v.addWidget(_section_header("Accessibility"))

        access_card = _CardFrame()
        self._motion_toggle = ToggleSwitch(False)
        access_card.add_row(
            _card_row(
                "Reduce Motion",
                "Simpler transitions for accessibility",
                self._motion_toggle,
            )
        )
        v.addWidget(access_card)

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

        # Scroll area so content is never clipped
        page = QWidget()
        page.setStyleSheet("background: transparent; border: none;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 0px; }"
        )

        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(18, 32, 18, 12)
        v.setSpacing(14)

        # ── App icon — SVG from assets ──
        icon_wrap = QWidget()
        icon_wrap.setStyleSheet("background: transparent; border: none;")
        icon_h = QHBoxLayout(icon_wrap)
        icon_h.setContentsMargins(0, 0, 0, 0)
        icon = QLabel()
        icon.setFixedSize(72, 72)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_path = Path(__file__).parent / "assets" / "scribr_icon.svg"
        pm = QPixmap(str(icon_path))
        if not pm.isNull():
            icon.setPixmap(
                pm.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
            )
        icon.setStyleSheet("background: transparent; border: none;")
        icon_h.addStretch()
        icon_h.addWidget(icon)
        icon_h.addStretch()
        v.addWidget(icon_wrap)

        # ── App name ──
        name = QLabel(
            f'<span style="color:{t.text.name()};">Scrib</span>'
            f'<span style="color:{t.red.name()};">r</span>'
        )
        name.setTextFormat(Qt.TextFormat.RichText)
        name.setFont(font_serif(24, 600))
        name.setStyleSheet(
            "background: transparent; border: none;"
            " letter-spacing: -0.02em;"
        )
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(name)

        # ── Version ──
        ver = QLabel("Version 1.0.0 \u00b7 Python 3.12 + PyQt6")
        ver.setFont(font_serif(12, 400, italic=True))
        ver.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_light)};"
            " background: transparent; border: none;"
        )
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addSpacing(-8)
        v.addWidget(ver)

        # ── Description ──
        # IMPORTANT: Do NOT use addWidget(..., AlignHCenter) with word-wrapped
        # labels — Qt calculates height at full layout width but renders the
        # widget at sizeHint width, causing height to be halved and text to clip.
        # Instead, center via a wrapper HBoxLayout with stretches on both sides.
        desc = QLabel(
            "Hold Right \u2325 to record. Release to transcribe.\n"
            "Your words appear ready to share."
        )
        desc.setFont(font_serif(14, 400, italic=True))
        desc.setStyleSheet(
            f"color: {qcolor_to_rgba(t.text_mid)};"
            " background: transparent; border: none;"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setFixedWidth(320)

        desc_wrap = QWidget()
        desc_wrap.setStyleSheet("background: transparent; border: none;")
        dh = QHBoxLayout(desc_wrap)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.addStretch()
        dh.addWidget(desc)
        dh.addStretch()
        v.addWidget(desc_wrap)

        # ── Stats row ──
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

        avg_s = self._stats.duration_s / self._stats.clips if self._stats.clips > 0 else 0.0
        stats = [
            (str(self._stats.clips), "THIS MONTH", True),
            (f"{int(avg_s // 60)}:{int(avg_s % 60):02d}", "AVG CLIP", False),
            (f"${self._stats.cost:.2f}", "API COST", False),
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

        # ── Links row ──
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
                "  min-height: 32px; padding: 0px 16px; border-radius: 16px;"
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

        scroll.setWidget(inner)
        page_layout.addWidget(scroll)
        return page

    # ─────────────────────────────────────────────────────
    #  FOOTER
    # ─────────────────────────────────────────────────────

    def _build_footer(self) -> QWidget:
        t = theme()
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet("background: transparent; border: none;")
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
        cancel.clicked.connect(self.hide)
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
        self._groq_input.setText(s.get("groq_api_key", ""))

        # Groq live interval (1, 2, or 3 seconds)
        interval = s.get("groq_live_interval", 2)
        self._interval_combo.setCurrentIndex(max(0, min(2, interval - 1)))

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

        # AI Mode
        ai_default = s.get("ai_mode_default", False)
        self._ai_default_toggle.set_checked(ai_default, animate=False)
        self._on_ai_default_toggled(ai_default)

        ai_styles = ["structured", "condensed", "bullets", "prompt"]
        ai_style_str = s.get("ai_format_style", "structured")
        idx = ai_styles.index(ai_style_str) if ai_style_str in ai_styles else 0
        self._ai_style_seg.set_selected(idx)

        self._ai_show_original_toggle.set_checked(s.get("ai_show_original", False), animate=False)

        # Hotkey
        hotkey = s.get("hotkey", "alt_r")
        for i in range(self._hotkey_combo.count()):
            if self._hotkey_combo.itemData(i) == hotkey:
                self._hotkey_combo.setCurrentIndex(i)
                break

        # Position
        self._current_position = s.get("overlay_position", "bottom_centre")
        for chip, k in self._pos_chips:
            chip.set_active(k == self._current_position)

    def _save(self) -> None:
        oai_key = self._openai_input.text().strip()
        groq_key = self._groq_input.text().strip()

        # Validate OpenAI key
        if oai_key and not oai_key.startswith("sk-"):
            self._toast.show_error(
                "OpenAI keys start with sk-"
            )
            return

        # Validate Groq key
        if groq_key and not groq_key.startswith("gsk_"):
            self._toast.show_error(
                "Groq keys start with gsk_"
            )
            return

        s = self._settings
        s.set("openai_api_key", oai_key)
        s.set("groq_api_key", groq_key)
        s.set("groq_live_interval", self._interval_combo.currentIndex() + 1)

        lang_idx = self._lang_combo.currentIndex()
        s.set("language", self._lang_combo.itemData(lang_idx) or "auto")

        s.set("ai_cleanup", self._ai_cleanup_toggle.is_checked())
        s.set("confidence_highlights", self._confidence_toggle.is_checked())
        s.set("show_overlay", self._overlay_toggle.is_checked())
        s.set("reduce_motion", self._motion_toggle.is_checked())
        s.set("hotkey", self._hotkey_combo.currentData() or "alt_r")
        s.set("overlay_position", self._current_position)

        s.set("ai_mode_default", self._ai_default_toggle.is_checked())
        ai_styles = ["structured", "condensed", "bullets", "prompt"]
        s.set("ai_format_style", ai_styles[self._ai_style_seg.selected_index()])
        s.set("ai_show_original", self._ai_show_original_toggle.is_checked())

        s.save()
        self.settings_saved.emit()
        self.hide()

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
