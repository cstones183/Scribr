# widgets.py — Reusable custom widgets for VoiceType settings UI.
# All colours imported from style.py — no hardcoded hex values.

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PyQt6.QtCore import (
    Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve,
    QTimer, QRect, QPointF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient,
)

from style import (
    BLUE, BLUE_DIM, BLUE_BORDER,
    GREEN, GREEN_DIM, RED,
    T1, T2, T3, T4, T5,
    BORDER, BORDER_HI,
    GLASS3,
    font,
    RADIUS_SM, RADIUS_XS,
)


# ════════════════════════════════════════════════════════════
#  TOGGLE SWITCH — 38×22, animated knob
# ════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    """Matches HTML .toggle: 38×22px, OutBack bounce on knob."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._knob_x = 18.0 if checked else 2.0
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knob_x")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, val: float):
        self._knob_x = val
        self.update()

    knob_x = pyqtProperty(float, _get_knob_x, _set_knob_x)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool, animate: bool = True):
        if self._checked == checked:
            return
        self._checked = checked
        target = 18.0 if checked else 2.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._knob_x = target
            self.update()
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        self.set_checked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        if self._checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(BLUE)
            p.drawRoundedRect(0, 0, 38, 22, 11, 11)
            # Glow shadow effect
            glow = QColor(91, 196, 255, 90)
            p.setBrush(glow)
            p.drawRoundedRect(0, 0, 38, 22, 11, 11)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 18), 1))
            p.setBrush(QColor(255, 255, 255, 26))
            p.drawRoundedRect(0, 0, 38, 22, 11, 11)

        # Knob — 16×16 white circle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawEllipse(QPointF(self._knob_x + 8, 11), 8, 8)
        p.end()


# ════════════════════════════════════════════════════════════
#  SEGMENTED CONTROL — pill group
# ════════════════════════════════════════════════════════════

class SegmentedControl(QWidget):
    """Pill-style segmented control matching HTML .seg."""

    segmentChanged = pyqtSignal(int)

    def __init__(self, options: list[str], selected: int = 0, parent=None):
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

    def _set_highlight_x(self, val: float):
        self._highlight_x = val
        self.update()

    highlight_x = pyqtProperty(float, _get_highlight_x, _set_highlight_x)

    def selected_index(self) -> int:
        return self._selected

    def set_selected(self, index: int):
        if index == self._selected:
            return
        self._selected = index
        self._anim.stop()
        self._anim.setStartValue(self._highlight_x)
        self._anim.setEndValue(index * self._seg_w + 3)
        self._anim.start()
        self.segmentChanged.emit(index)

    def resizeEvent(self, event):
        self._seg_w = (self.width() - 6) // len(self._options)
        self._highlight_x = self._selected * self._seg_w + 3

    def mousePressEvent(self, event):
        idx = max(0, int((event.position().x() - 3) / max(self._seg_w, 1)))
        idx = min(idx, len(self._options) - 1)
        self.set_selected(idx)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        sw = self._seg_w

        # Background
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        p.setBrush(QColor(255, 255, 255, 10))
        p.drawRoundedRect(0, 0, w, h, RADIUS_SM, RADIUS_SM)

        # Active highlight
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(91, 196, 255, 41))  # blue-dim stronger
        p.drawRoundedRect(int(self._highlight_x), 3, sw, h - 6, 5, 5)

        # Labels
        f = font(11, 500)
        p.setFont(f)
        for i, opt in enumerate(self._options):
            x = 3 + i * sw
            color = BLUE if i == self._selected else T3
            p.setPen(color)
            p.drawText(QRect(x, 0, sw, h), Qt.AlignmentFlag.AlignCenter, opt)
        p.end()


# ════════════════════════════════════════════════════════════
#  POSITION CHIP — overlay position selector
# ════════════════════════════════════════════════════════════

class PositionChip(QFrame):
    """Clickable card for overlay position selection."""

    selected = pyqtSignal()

    def __init__(self, icon: str, label: str, parent=None):
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
        self._icon_label.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(label)
        self._text_label.setFont(font(10, 500))
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._text_label)

        self._update_style()

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(
                "PositionChip {"
                f"  background: rgba(91,196,255,0.10);"
                f"  border: 1px solid rgba(91,196,255,0.20);"
                f"  border-radius: {RADIUS_SM}px;"
                "}"
            )
            self._text_label.setStyleSheet(
                f"color: rgb(91,196,255); background: transparent; border: none;"
            )
        else:
            self.setStyleSheet(
                "PositionChip {"
                "  background: rgba(255,255,255,0.03);"
                "  border: 1px solid rgba(255,255,255,0.07);"
                f"  border-radius: {RADIUS_SM}px;"
                "}"
                "PositionChip:hover {"
                "  background: rgba(255,255,255,0.06);"
                "  border-color: rgba(255,255,255,0.12);"
                "}"
            )
            self._text_label.setStyleSheet(
                "color: rgba(255,255,255,0.30); background: transparent; border: none;"
            )

    def mousePressEvent(self, event):
        self.selected.emit()


# ════════════════════════════════════════════════════════════
#  THEME CHIP — colour theme selector
# ════════════════════════════════════════════════════════════

class ThemeChip(QWidget):
    """Gradient-filled chip for theme selection."""

    selected = pyqtSignal()

    def __init__(self, name: str, color1: str, color2: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._color1 = QColor(color1)
        self._color2 = QColor(color2)
        self._active = False
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def mousePressEvent(self, event):
        self.selected.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Gradient fill
        grad = QLinearGradient(QPointF(0, 0), QPointF(w, h))
        grad.setColorAt(0.0, self._color1)
        grad.setColorAt(1.0, self._color2)

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, RADIUS_SM, RADIUS_SM)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Active border
        if self._active:
            p.setPen(QPen(BLUE, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, w - 2, h - 2, RADIUS_SM - 1, RADIUS_SM - 1)

        p.end()


# ════════════════════════════════════════════════════════════
#  TOAST WIDGET — pill notification
# ════════════════════════════════════════════════════════════

class ToastWidget(QWidget):
    """Pill toast that slides up and fades in from bottom-centre of parent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 36)
        self._message = ""
        self._color = GREEN
        self._border_color = QColor(61, 232, 160, 64)
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

    def _set_toast_opacity(self, val: float):
        self._opacity = val
        self.update()

    toast_opacity = pyqtProperty(float, _get_toast_opacity, _set_toast_opacity)

    def show_success(self, message: str):
        self._message = message
        self._color = GREEN
        self._border_color = QColor(61, 232, 160, 64)
        self._show_toast()

    def show_error(self, message: str):
        self._message = message
        self._color = RED
        self._border_color = QColor(255, 90, 110, 64)
        self._show_toast()

    def _show_toast(self):
        if self.parent():
            pw = self.parent().width()
            ph = self.parent().height()
            self.move((pw - self.width()) // 2, ph - 56)
        self._opacity = 0.0
        self.show()
        self.raise_()

        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

        QTimer.singleShot(2500, self._start_fade_out)

    def _start_fade_out(self):
        self._fade_out.setStartValue(self._opacity)
        self._fade_out.setEndValue(0.0)
        self._fade_out.start()

    def paintEvent(self, event):
        if self._opacity <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # Background
        p.setPen(QPen(self._border_color, 1))
        p.setBrush(GLASS3)
        p.drawRoundedRect(0, 0, w, h, 18, 18)

        # Text
        p.setPen(self._color)
        f = font(13, 500)
        p.setFont(f)
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._message)
        p.end()
