# welcome_window.py — First-run / launch welcome screen for Scribr.
# Frameless, brand-matched. Greets the user, explains the hotkey, points to
# where API keys go (and where to get them), and offers a permission button.

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from settings import SettingsManager
from style import (
    RADIUS_CARD,
    font_sans,
    font_serif,
    qcolor_to_rgba,
    theme,
)
from widgets import ToggleSwitch

WELCOME_WIDTH = 460


def _primary_btn_ss() -> str:
    t = theme()
    return (
        "QPushButton {"
        "  min-height: 36px;"
        "  border-radius: 18px;"
        f"  background: {t.red.name()};"
        "  border: none;"
        "  color: white;"
        "  font-size: 13px; font-weight: 600;"
        "  padding: 0px 22px;"
        "}"
        "QPushButton:hover { background: #c44434; }"
    )


def _ghost_btn_ss() -> str:
    t = theme()
    return (
        "QPushButton {"
        "  min-height: 36px;"
        "  border-radius: 18px;"
        "  background: transparent;"
        f"  border: 1px solid {qcolor_to_rgba(t.border)};"
        f"  color: {qcolor_to_rgba(t.text_mid)};"
        "  font-size: 13px; font-weight: 500;"
        "  padding: 0px 18px;"
        "}"
        "QPushButton:hover {"
        f"  background: {qcolor_to_rgba(t.surface_3)};"
        f"  color: {t.text.name()};"
        "}"
    )


class WelcomeWindow(QWidget):
    """Brand-matched welcome / onboarding screen."""

    open_settings = pyqtSignal()
    request_permission = pyqtSignal()

    def __init__(
        self,
        settings: SettingsManager,
        hotkey_label: str = "Right ⌥",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setFixedWidth(WELCOME_WIDTH)

        self._drag_pos: QPoint | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._titlebar = self._build_titlebar()
        root.addWidget(self._titlebar)

        body = self._build_body(hotkey_label)
        root.addWidget(body, 1)

        self._footer = self._build_footer()
        root.addWidget(self._footer)

    # ── Paint (rounded surface + chrome) ──────────────────

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = RADIUS_CARD

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setClipPath(clip)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawRect(0, 0, w, h)

        tb = self._titlebar.geometry()
        p.setBrush(t.surface_2)
        p.drawRect(0, 0, w, tb.bottom() + 1)

        ft = self._footer.geometry()
        p.drawRect(0, ft.y(), w, h - ft.y())

        p.setPen(QPen(t.border, 1))
        p.drawLine(0, tb.bottom(), w, tb.bottom())
        p.drawLine(0, ft.y(), w, ft.y())

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
        p.end()

    # ── Titlebar ──────────────────────────────────────────

    def _build_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(bar)
        h.setContentsMargins(18, 0, 18, 0)
        h.setSpacing(0)

        close_dot = QPushButton()
        close_dot.setFixedSize(12, 12)
        close_dot.setCursor(Qt.CursorShape.PointingHandCursor)
        close_dot.setStyleSheet(
            "QPushButton { background: #ff5f57; border-radius: 6px; border: none; }"
            "QPushButton:hover { background: #e04640; }"
        )
        close_dot.clicked.connect(self.hide)
        h.addWidget(close_dot)
        h.addStretch(1)
        return bar

    # ── Body ──────────────────────────────────────────────

    def _build_body(self, hotkey_label: str) -> QWidget:
        t = theme()
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        v = QVBoxLayout(body)
        v.setContentsMargins(28, 8, 28, 20)
        v.setSpacing(10)

        title = QLabel("Welcome to Scribr")
        title.setFont(font_serif(24, 600))
        title.setStyleSheet(f"color: {t.text.name()};")
        v.addWidget(title)

        subtitle = QLabel(
            "Speak anywhere on your Mac and Scribr turns it into text, "
            "ready to paste."
        )
        subtitle.setFont(font_sans(13, 400))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {qcolor_to_rgba(t.text_mid)};")
        v.addWidget(subtitle)

        v.addSpacing(6)

        # How it works
        v.addWidget(self._section_label("How it works"))
        how = QLabel(
            f"Tap <b>{hotkey_label}</b> to start recording, then tap it again "
            f"to stop. Your words land on the clipboard, and into the field "
            f"you are typing in."
        )
        how.setFont(font_sans(13, 400))
        how.setWordWrap(True)
        how.setStyleSheet(f"color: {qcolor_to_rgba(t.text_mid)};")
        v.addWidget(how)

        v.addSpacing(6)

        # API keys
        v.addWidget(self._section_label("Add your API keys"))
        link = f'style="color:{t.red.name()}; text-decoration:none;"'
        keys = QLabel(
            "Scribr needs an API key to transcribe. Add one in "
            "Settings → API Keys. You only need one of the two:"
            "<br><br>"
            "&nbsp;&nbsp;• <b>Groq</b> — fast transcription and live preview. "
            f'Get a key at <a {link} href="https://console.groq.com/keys">'
            "console.groq.com/keys</a>"
            "<br>"
            "&nbsp;&nbsp;• <b>OpenAI</b> — used for AI cleanup and formatting. "
            f'Get a key at <a {link} href="https://platform.openai.com/api-keys">'
            "platform.openai.com/api-keys</a>"
        )
        keys.setFont(font_sans(13, 400))
        keys.setWordWrap(True)
        keys.setOpenExternalLinks(True)
        keys.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        keys.setStyleSheet(f"color: {qcolor_to_rgba(t.text_mid)};")
        v.addWidget(keys)

        open_settings_btn = QPushButton("Open Settings to add keys")
        open_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_settings_btn.setStyleSheet(_ghost_btn_ss())
        open_settings_btn.clicked.connect(self.open_settings.emit)
        v.addWidget(open_settings_btn)

        v.addSpacing(6)

        # Permissions
        v.addWidget(self._section_label("Permissions"))
        perms = QLabel(
            "macOS needs to allow Scribr to use your <b>microphone</b> and to "
            "watch for the <b>keyboard shortcut</b> (Accessibility / Input "
            "Monitoring). You can grant these now."
        )
        perms.setFont(font_sans(13, 400))
        perms.setWordWrap(True)
        perms.setStyleSheet(f"color: {qcolor_to_rgba(t.text_mid)};")
        v.addWidget(perms)

        perm_btn = QPushButton("Grant permissions")
        perm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        perm_btn.setStyleSheet(_ghost_btn_ss())
        perm_btn.clicked.connect(self.request_permission.emit)
        v.addWidget(perm_btn)

        return body

    def _section_label(self, text: str) -> QLabel:
        t = theme()
        lbl = QLabel(text.upper())
        lbl.setFont(font_sans(11, 700))
        lbl.setStyleSheet(
            f"color: {t.red.name()}; letter-spacing: 0.6px;"
        )
        return lbl

    # ── Footer ────────────────────────────────────────────

    def _build_footer(self) -> QWidget:
        t = theme()
        footer = QWidget()
        footer.setFixedHeight(56)
        footer.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(footer)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(10)

        self._show_toggle = ToggleSwitch(
            checked=self._settings.get("show_welcome_on_launch", True)
        )
        self._show_toggle.toggled.connect(self._on_show_toggled)
        h.addWidget(self._show_toggle)

        toggle_label = QLabel("Show on startup")
        toggle_label.setFont(font_sans(12, 500))
        toggle_label.setStyleSheet(f"color: {qcolor_to_rgba(t.text_mid)};")
        h.addWidget(toggle_label)

        h.addStretch(1)

        start_btn = QPushButton("Get started")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(_primary_btn_ss())
        start_btn.clicked.connect(self.hide)
        h.addWidget(start_btn)

        return footer

    def _on_show_toggled(self, checked: bool) -> None:
        self._settings.set("show_welcome_on_launch", checked)
        self._settings.save()

    # ── Drag to move (titlebar area) ──────────────────────

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        if isinstance(event, QMouseEvent) and event.position().y() < 48:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: object) -> None:  # type: ignore[override]
        if self._drag_pos is not None and isinstance(event, QMouseEvent):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: object) -> None:  # type: ignore[override]
        self._drag_pos = None
