# widgets.py — Reusable custom widgets for Scribr settings UI.
# All colours resolved via theme() — no hardcoded hex values.

from __future__ import annotations

from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from style import (
    RADIUS_SM,
    font_sans,
    qcolor_to_rgba,
    theme,
)

# ════════════════════════════════════════════════════════════
#  TOGGLE SWITCH — 42×24, animated knob, warm coral accent
# ════════════════════════════════════════════════════════════


class ToggleSwitch(QWidget):
    """42×24 toggle. Red when on, border fill when off. OutBack knob bounce."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._knob_x = 20.0 if checked else 2.0
        self.setFixedSize(42, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knob_x")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, val: float) -> None:
        self._knob_x = val
        self.update()

    knob_x = pyqtProperty(float, _get_knob_x, _set_knob_x)  # type: ignore[assignment]

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool, animate: bool = True) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        target = 20.0 if checked else 2.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._knob_x = target
            self.update()
        self.toggled.emit(checked)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # type: ignore[override]
        self.set_checked(not self._checked)

    def paintEvent(self, event: QPaintEvent | None) -> None:  # type: ignore[override]
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        if self._checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(t.red)
            p.drawRoundedRect(0, 0, 42, 24, 12, 12)
        else:
            p.setPen(QPen(t.border, 1))
            p.setBrush(t.border)
            p.drawRoundedRect(0, 0, 42, 24, 12, 12)

        # Knob — 20×20 white circle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(self._knob_x + 10, 12), 10, 10)
        p.end()


# ════════════════════════════════════════════════════════════
#  SEGMENTED CONTROL — pill group, surface highlight
# ════════════════════════════════════════════════════════════


class SegmentedControl(QWidget):
    """Segmented control with surface-2 bg and surface active highlight."""

    segmentChanged = pyqtSignal(int)

    def __init__(
        self, options: list[str], selected: int = 0, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._options = options
        self._selected = selected
        self._highlight_x = 0.0
        self._seg_w = 0
        self.setFixedHeight(32)
        self.setMinimumWidth(len(options) * 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"highlight_x")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _get_highlight_x(self) -> float:
        return self._highlight_x

    def _set_highlight_x(self, val: float) -> None:
        self._highlight_x = val
        self.update()

    highlight_x = pyqtProperty(float, _get_highlight_x, _set_highlight_x)  # type: ignore[assignment]

    def selected_index(self) -> int:
        return self._selected

    def set_selected(self, index: int) -> None:
        if index == self._selected:
            return
        self._selected = index
        self._anim.stop()
        self._anim.setStartValue(self._highlight_x)
        self._anim.setEndValue(index * self._seg_w + 3)
        self._anim.start()
        self.segmentChanged.emit(index)

    def resizeEvent(self, event: QResizeEvent | None) -> None:  # type: ignore[override]
        self._seg_w = (self.width() - 6) // len(self._options)
        self._highlight_x = self._selected * self._seg_w + 3

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # type: ignore[override]
        if event is None:
            return
        idx = max(0, int((event.position().x() - 3) / max(self._seg_w, 1)))
        idx = min(idx, len(self._options) - 1)
        self.set_selected(idx)

    def paintEvent(self, event: QPaintEvent | None) -> None:  # type: ignore[override]
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        sw = self._seg_w

        # Background
        p.setPen(QPen(t.border, 1))
        p.setBrush(t.surface_2)
        p.drawRoundedRect(0, 0, w, h, RADIUS_SM, RADIUS_SM)

        # Active highlight — surface bg
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawRoundedRect(int(self._highlight_x), 3, sw, h - 6, 5, 5)

        # Labels
        for i, opt in enumerate(self._options):
            x = 3 + i * sw
            if i == self._selected:
                p.setPen(t.text)
                p.setFont(font_sans(12, 600))
            else:
                p.setPen(t.text_light)
                p.setFont(font_sans(12, 500))
            p.drawText(QRect(x, 0, sw, h), Qt.AlignmentFlag.AlignCenter, opt)
        p.end()


# ════════════════════════════════════════════════════════════
#  POSITION CHIP — overlay position selector
# ════════════════════════════════════════════════════════════


class PositionChip(QFrame):
    """Clickable card for overlay position selection."""

    selected = pyqtSignal()

    def __init__(self, icon: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_text = icon
        self._label_text = label
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(52)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel(icon)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(
            "font-size: 16px; background: transparent; border: none;"
        )
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(label)
        self._text_label.setFont(font_sans(10, 500))
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._text_label)

        self._update_style()

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        self._active = active
        self._update_style()

    def _update_style(self) -> None:
        t = theme()
        if self._active:
            self.setStyleSheet(
                "PositionChip {"
                f"  background: {qcolor_to_rgba(t.red_soft)};"
                f"  border: 1px solid {qcolor_to_rgba(t.red_border)};"
                f"  border-radius: {RADIUS_SM}px;"
                "}"
            )
            self._text_label.setStyleSheet(
                f"color: {t.red.name()}; background: transparent; border: none;"
            )
        else:
            self.setStyleSheet(
                "PositionChip {"
                f"  background: {qcolor_to_rgba(t.surface_2)};"
                f"  border: 1px solid {qcolor_to_rgba(t.border)};"
                f"  border-radius: {RADIUS_SM}px;"
                "}"
                "PositionChip:hover {"
                f"  background: {qcolor_to_rgba(t.surface_3)};"
                f"  border-color: {qcolor_to_rgba(t.border_2)};"
                "}"
            )
            self._text_label.setStyleSheet(
                f"color: {qcolor_to_rgba(t.text_light)};"
                " background: transparent; border: none;"
            )

    def mousePressEvent(self, event: QMouseEvent | None) -> None:  # type: ignore[override]
        self.selected.emit()


# ════════════════════════════════════════════════════════════
#  TOAST WIDGET — pill notification
# ════════════════════════════════════════════════════════════


class ToastWidget(QWidget):
    """Pill toast that slides up and fades in from bottom-centre of parent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(220, 36)
        self._message = ""
        self._text_color = QColor(42, 157, 92)  # green default
        self._border_color = QColor(226, 222, 216)  # border default
        self._opacity = 0.0
        self.hide()

        self._fade_in = QPropertyAnimation(self, b"toast_opacity")
        self._fade_in.setDuration(280)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self, b"toast_opacity")
        self._fade_out.setDuration(220)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade_out.finished.connect(self.hide)

    def _get_toast_opacity(self) -> float:
        return self._opacity

    def _set_toast_opacity(self, val: float) -> None:
        self._opacity = val
        self.update()

    toast_opacity = pyqtProperty(float, _get_toast_opacity, _set_toast_opacity)  # type: ignore[assignment]

    def show_success(self, message: str) -> None:
        t = theme()
        self._message = message
        self._text_color = t.green
        self._border_color = t.border
        self._show_toast()

    def show_error(self, message: str) -> None:
        t = theme()
        self._message = message
        self._text_color = t.red
        self._border_color = t.red_border
        self._show_toast()

    def _show_toast(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            pw = parent.width()
            ph = parent.height()
            self.move((pw - self.width()) // 2, ph - 56)
        self._opacity = 0.0
        self.show()
        self.raise_()

        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        QTimer.singleShot(2500, self._start_fade_out)

    def _start_fade_out(self) -> None:
        self._fade_out.setStartValue(self._opacity)
        self._fade_out.setEndValue(0.0)
        self._fade_out.start()

    def paintEvent(self, event: QPaintEvent | None) -> None:  # type: ignore[override]
        if self._opacity <= 0:
            return
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # Background — surface with border
        p.setPen(QPen(self._border_color, 1))
        p.setBrush(t.surface)
        p.drawRoundedRect(0, 0, w, h, 18, 18)

        # Text
        p.setPen(self._text_color)
        p.setFont(font_sans(13, 500))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._message)
        p.end()
