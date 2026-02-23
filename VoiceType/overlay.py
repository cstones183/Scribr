# overlay.py — PyQt6 floating overlay window for Scribr.
# Frameless, always-on-top, anchored to bottom-centre of screen.
# States: IDLE, RECORDING, LIVE_TRANSCRIBING, RESULT_FIELD, RESULT_NOTEPAD
# Pill + connector + notepad — warm coral accent, surface bg.

import math
import time
from enum import Enum, auto

from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPauseAnimation,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyleFactory,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from style import (
    ANIM_NOTEPAD_CLOSE,
    ANIM_NOTEPAD_OPEN,
    ANIM_PILL_ENTER,
    ANIM_PILL_EXIT,
    ANIM_WORD_FADE,
    BAR_COUNT,
    BAR_GAP,
    BAR_MAX_H,
    BAR_MIN_H,
    BAR_WIDTH,
    BOTTOM_MARGIN,
    CONNECTOR_HEIGHT,
    EASE_LIFT,
    EASE_SETTLE,
    EASE_SPRING,
    NOTEPAD_WIDTH,
    PILL_HEIGHT,
    PILL_PADDING_H,
    RADIUS_CARD,
    font_sans,
    font_serif,
    qcolor_to_rgba,
    should_reduce_motion,
    theme,
)

# ── Waveform tuning ───────────────────────────────────────

BAR_SCALE_FACTORS = [0.47, 0.74, 1.0, 0.74, 1.0, 0.74, 0.47]

SPRING_STIFFNESS = 0.3
SPRING_DAMPING = 0.7

BREATHING_FREQ = 0.8
BREATHING_AMP = 3.0
BREATHING_PHASES = [
    0,
    math.pi / 3,
    2 * math.pi / 3,
    math.pi,
    4 * math.pi / 3,
    5 * math.pi / 3,
    2 * math.pi,
]


# ── Pill widget (self-painting background) ────────────────


class PillWidget(QWidget):
    """Pill container that draws its own rounded-rect background and border.

    This ensures the painted background always matches the child widget positions,
    regardless of parent QPainter transforms or QGraphicsEffects.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._border_color: QColor | None = None

    def set_border_color(self, color: QColor) -> None:
        self._border_color = color
        self.update()

    def paintEvent(self, event: object) -> None:
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.height() / 2  # pill radius = half height
        pill_path = QPainterPath()
        pill_path.addRoundedRect(
            0.0, 0.0, float(self.width()), float(self.height()), r, r
        )

        # Fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawPath(pill_path)

        # Border
        border = self._border_color if self._border_color else t.border
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(pill_path)

        p.end()


# ── State enum ──────────────────────────────────────────────


class OverlayState(Enum):
    IDLE = auto()
    RECORDING = auto()
    LIVE_TRANSCRIBING = auto()
    RESULT_FIELD = auto()
    RESULT_NOTEPAD = auto()


# ════════════════════════════════════════════════════════════
#  PULSING DOT
# ════════════════════════════════════════════════════════════


class PulsingDot(QWidget):
    """Small 7px circle that pulses (matches .dot in prototype)."""

    def __init__(self, color: QColor | None = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(7, 7)
        t = theme()
        if color is None:
            color = t.red
        self._color = QColor(color)
        self._glow_color = QColor(color)
        self._glow_color.setAlpha(204)
        self._scale = 1.0
        self._opacity = 1.0
        self._time_start = 0.0
        self._pulse_speed = 1.1  # matches CSS 1.1s

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_color(self, color: QColor):
        self._color = QColor(color)
        self._glow_color = QColor(color)
        self._glow_color.setAlpha(204)
        self.update()

    def set_static(self):
        self._timer.stop()
        self._opacity = 1.0
        self._scale = 1.0
        self.update()
        self.show()

    def start(self, speed: float = 1.1):
        self._pulse_speed = speed
        self._time_start = time.time()
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        # Matches CSS: 0%,100% opacity:1 scale:1 — 50% opacity:0.3 scale:0.75
        elapsed = time.time() - self._time_start
        # Use cosine so it starts at max (1.0) and dips to min at 50%
        phase = math.cos(elapsed * self._pulse_speed * 2 * math.pi)
        # phase goes 1 → -1 → 1.  Map to opacity: 1→0.3, scale: 1→0.75
        self._opacity = 0.65 + 0.35 * phase
        self._scale = 0.875 + 0.125 * phase
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        cx, cy = 3.5, 3.5
        s = self._scale

        # Glow (matches box-shadow: 0 0 7px)
        p.setPen(Qt.PenStyle.NoPen)
        glow = QColor(self._glow_color)
        glow.setAlpha(int(self._opacity * 80))
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), 5 * s, 5 * s)

        # Core dot
        p.setBrush(self._color)
        p.drawEllipse(QPointF(cx, cy), 3.5 * s, 3.5 * s)
        p.end()


# ════════════════════════════════════════════════════════════
#  WAVEFORM WIDGET
# ════════════════════════════════════════════════════════════


class WaveformWidget(QWidget):
    """7 vertical bars with asymmetric spring physics, stagger delays + bar glow."""

    # Stagger delay per bar (seconds) — outer bars respond slightly later
    BAR_STAGGER = [0.06, 0.04, 0.02, 0.0, 0.02, 0.04, 0.06]

    def __init__(self, parent=None):
        super().__init__(parent)
        bar_area_w = int(BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP)
        self.setFixedSize(bar_area_w + 8, 26)  # extra padding for glow

        self._bar_heights = [BAR_MIN_H] * BAR_COUNT
        self._bar_velocities = [0.0] * BAR_COUNT
        self._bar_targets = [BAR_MIN_H] * BAR_COUNT
        self._rms = 0.0
        self._breathing = True
        self._winding_down = False
        self._wind_down_start = 0.0
        self._time_start = time.time()
        self._last_rms_time = [0.0] * BAR_COUNT  # for stagger

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_rms(self, value: float):
        self._rms = max(0.0, min(value, 1.0))
        now = time.time()
        if self._rms > 0.02:
            self._breathing = False
            self._winding_down = False
            for i in range(BAR_COUNT):
                # Stagger: only update target if enough time has passed
                if now - self._last_rms_time[i] >= self.BAR_STAGGER[i]:
                    self._bar_targets[i] = max(
                        BAR_MIN_H, self._rms * BAR_MAX_H * BAR_SCALE_FACTORS[i]
                    )
                    self._last_rms_time[i] = now
        else:
            self._breathing = True

    def start_animation(self):
        self._time_start = time.time()
        self._winding_down = False
        self._timer.start()

    def stop_animation(self):
        """Graceful wind-down instead of abrupt stop."""
        self._winding_down = True
        self._wind_down_start = time.time()

    def reset(self):
        self._bar_heights = [BAR_MIN_H] * BAR_COUNT
        self._bar_velocities = [0.0] * BAR_COUNT
        self._bar_targets = [BAR_MIN_H] * BAR_COUNT
        self._rms = 0.0
        self._breathing = True
        self._winding_down = False
        self.update()

    def _tick(self):
        elapsed = time.time() - self._time_start

        # Wind-down: lerp targets to minimum over 300ms
        if self._winding_down:
            wind_t = min(1.0, (time.time() - self._wind_down_start) / 0.3)
            for i in range(BAR_COUNT):
                self._bar_targets[i] = BAR_MIN_H
            # Stop timer once all bars have settled
            if wind_t >= 1.0:
                all_settled = all(
                    abs(self._bar_heights[i] - BAR_MIN_H) < 0.5
                    for i in range(BAR_COUNT)
                )
                if all_settled:
                    self._timer.stop()
                    return
        elif self._breathing:
            for i in range(BAR_COUNT):
                self._bar_targets[i] = (
                    BAR_MIN_H
                    + BREATHING_AMP
                    + math.sin(elapsed * BREATHING_FREQ * 2 * math.pi + BREATHING_PHASES[i])
                    * BREATHING_AMP
                )

        # Asymmetric spring: stiffer when rising, softer when falling
        for i in range(BAR_COUNT):
            displacement = self._bar_targets[i] - self._bar_heights[i]
            stiffness = 0.4 if displacement > 0 else 0.2
            self._bar_velocities[i] += displacement * stiffness
            self._bar_velocities[i] *= SPRING_DAMPING
            self._bar_heights[i] += self._bar_velocities[i]
            self._bar_heights[i] = max(BAR_MIN_H, self._bar_heights[i])

        self.update()

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        total_w = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        start_x = (self.width() - total_w) / 2
        cy = self.height() / 2

        p.setPen(Qt.PenStyle.NoPen)

        # Glow color: red with reduced alpha
        glow_r = t.red.red()
        glow_g = t.red.green()
        glow_b = t.red.blue()

        for i in range(BAR_COUNT):
            h = self._bar_heights[i]
            x = start_x + i * (BAR_WIDTH + BAR_GAP)
            y = cy - h / 2

            # Soft glow: 3 progressively wider/fainter layers
            for spread, alpha in [(3.0, 18), (2.0, 30), (1.0, 50)]:
                glow = QColor(glow_r, glow_g, glow_b, alpha)
                p.setBrush(glow)
                gw = BAR_WIDTH + spread * 2
                gh = h + spread * 2
                gx = x - spread
                gy = y - spread
                glow_path = QPainterPath()
                glow_path.addRoundedRect(gx, gy, gw, gh, gw / 2, gw / 2)
                p.drawPath(glow_path)

            # Solid bar
            p.setBrush(t.red)
            path = QPainterPath()
            path.addRoundedRect(x, y, BAR_WIDTH, h, BAR_WIDTH / 2, BAR_WIDTH / 2)
            p.drawPath(path)

        p.end()


# ════════════════════════════════════════════════════════════
#  PILL SEPARATOR
# ════════════════════════════════════════════════════════════


class PillSep(QWidget):
    """Thin 1px x 14px vertical separator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(1, 14)

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.border)
        p.drawRect(0, 0, 1, 14)
        p.end()


# ════════════════════════════════════════════════════════════
#  BLINKING CURSOR
# ════════════════════════════════════════════════════════════


class BlinkingCursor(QWidget):
    """Inline blinking cursor (| character) matching CSS blink animation."""

    def __init__(self, color: QColor | None = None, parent=None):
        super().__init__(parent)
        t = theme()
        self._color = color if color is not None else t.red
        self._visible = True
        self._timer = QTimer(self)
        self._timer.setInterval(450)  # 0.9s step-end → toggle every 450ms
        self._timer.timeout.connect(self._toggle)
        self.setFixedSize(3, 15)

    def start(self):
        self._visible = True
        self._timer.start()
        self.show()
        self.update()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _toggle(self):
        self._visible = not self._visible
        self.update()

    def paintEvent(self, event):
        if not self._visible:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        # Glow
        glow = QColor(self._color)
        glow.setAlpha(100)
        p.setBrush(glow)
        p.drawRoundedRect(0, 0, 3, 15, 1.5, 1.5)
        # Core
        p.setBrush(self._color)
        p.drawRoundedRect(0, 0, 2, 15, 1, 1)
        p.end()


# ════════════════════════════════════════════════════════════
#  AI TOGGLE & SKELETON
# ════════════════════════════════════════════════════════════


class AITogglePill(QWidget):
    """Small 34x19 pill toggle for AI Mode with 'AI MODE' label."""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._knob_x = 2.0
        self.setFixedSize(90, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"knob_x")
        self._anim.setDuration(250)
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
        target = 17.0 if checked else 2.0  # 34 - 15 - 2 = 17
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._knob_x = target
            self.update()
        self.toggled.emit(checked)

    def toggle(self):
        self.set_checked(not self._checked)

    def mousePressEvent(self, event):
        self.toggle()

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        y_offset = (self.height() - 19) / 2
        bg_col = t.ai if self._checked else t.border
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg_col)
        p.drawRoundedRect(0, int(y_offset), 34, 19, 9.5, 9.5)

        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(self._knob_x, y_offset + 2, 15, 15))

        text_col = t.ai if self._checked else t.text_light
        p.setPen(text_col)
        from PyQt6.QtGui import QFont # ensure available
        f = font_sans(10, 600)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        p.setFont(f)
        p.drawText(
            QRectF(42, 0, self.width() - 42, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "AI MODE",
        )
        p.end()


class AIShimmerSkeleton(QWidget):
    """Animated placeholder drawing a shimmer gradient across rounded rects."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuart)

    def start(self):
        self._phase = 0.0
        self._progress = 0.0
        self._timer.start()
        if not should_reduce_motion():
            self._anim.start()
        else:
            self._progress = 1.0
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._phase += 0.02
        if self._phase > 2.0:
            self._phase -= 2.0
        self.update()

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, val: float):
        self._progress = val
        self.update()

    progress = pyqtProperty(float, _get_progress, _set_progress)

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        
        if should_reduce_motion():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(t.ai_shimmer)
            c_y = max(0.0, (h - 40) / 2)
            p.drawRoundedRect(16, int(c_y), int(w * 0.7), 12, 6, 6)
            p.drawRoundedRect(16, int(c_y + 24), int(w * 0.4), 12, 6, 6)
            p.end()
            return

        grad = QLinearGradient(0, 0, w, 0)
        x_offset = self._phase * w - (w / 2)
        grad.setStart(x_offset, 0)
        grad.setFinalStop(x_offset + w, 0)
        base = t.ai_shimmer
        highlight = QColor(base.red(), base.green(), base.blue(), int(base.alpha() * 1.5))
        grad.setColorAt(0.0, base)
        grad.setColorAt(0.5, highlight)
        grad.setColorAt(1.0, base)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)

        c_y = 20
        alpha1 = min(1.0, max(0.0, self._progress * 2))
        if alpha1 > 0:
            p.setOpacity(alpha1)
            y1 = c_y + (1.0 - alpha1) * 10
            p.drawRoundedRect(16, int(y1), int(w * 0.8), 12, 6, 6)

        alpha2 = min(1.0, max(0.0, (self._progress - 0.2) * 2))
        if alpha2 > 0:
            p.setOpacity(alpha2)
            y2 = c_y + 24 + (1.0 - alpha2) * 10
            p.drawRoundedRect(16, int(y2), int(w * 0.5), 12, 6, 6)

        p.end()


# ════════════════════════════════════════════════════════════
#  NOTEPAD WIDGET
# ════════════════════════════════════════════════════════════


class NotepadWidget(QWidget):
    """Card notepad that drops below the pill."""

    retryClicked = pyqtSignal()
    copyCloseClicked = pyqtSignal(str)
    closeClicked = pyqtSignal()
    aiToggleClicked = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(NOTEPAD_WIDTH)
        self._target_opacity = 0.0
        self._current_opacity = 0.0
        self._text_scale = 1.0
        self._text_translate_y = 0.0
        self._text_opacity = 1.0
        self._prev_text = ""
        # Per-word animation state
        self._word_fade_timers: list[QTimer] = []
        self._text_anim = None
        self._badge_anim = None
        self._build_ui()

    # ── Animatable text properties ─────────────────────────

    def _get_text_scale(self) -> float:
        return self._text_scale

    def _set_text_scale(self, val: float):
        self._text_scale = val
        vp = self._text_edit.viewport()
        if vp:
            vp.update()

    text_scale = pyqtProperty(float, _get_text_scale, _set_text_scale)

    def _get_text_translate_y(self) -> float:
        return self._text_translate_y

    def _set_text_translate_y(self, val: float):
        self._text_translate_y = val
        vp = self._text_edit.viewport()
        if vp:
            vp.update()

    text_translate_y = pyqtProperty(float, _get_text_translate_y, _set_text_translate_y)

    def _get_text_opacity(self) -> float:
        return self._text_opacity

    def _set_text_opacity(self, val: float):
        self._text_opacity = val
        t = theme()
        alpha = max(0.0, min(1.0, val))
        
        raw_rgba = qcolor_to_rgba(QColor(t.text_mid.red(), t.text_mid.green(), t.text_mid.blue(), int(alpha * 255)))
        ai_rgba = qcolor_to_rgba(QColor(t.text.red(), t.text.green(), t.text.blue(), int(alpha * 255)))
        sel_rgba = qcolor_to_rgba(QColor(t.red.red(), t.red.green(), t.red.blue(), 64))
        scroll_handle = qcolor_to_rgba(QColor(t.text_light.red(), t.text_light.green(), t.text_light.blue(), 60))
        
        base_style = (
            "  background: transparent; border: none;"
            f"  selection-background-color: {sel_rgba};"
            "}"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            f"QScrollBar::handle:vertical {{ background: {scroll_handle}; border-radius: 2px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self._text_edit.setStyleSheet(f"QTextEdit {{ padding: 14px 16px; color: {raw_rgba};" + base_style)
        if hasattr(self, "_ai_text_edit"):
            self._ai_text_edit.setStyleSheet(f"QTextEdit {{ padding: 14px 16px; color: {ai_rgba};" + base_style)

    text_opacity = pyqtProperty(float, _get_text_opacity, _set_text_opacity)

    def _build_ui(self):
        t = theme()
        fusion = QStyleFactory.create("Fusion")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 12, 14, 10)

        title = QLabel("TRANSCRIBED")
        title.setFont(font_sans(10, 600))
        title_color = qcolor_to_rgba(t.green)
        bg_color = qcolor_to_rgba(QColor(t.green.red(), t.green.green(), t.green.blue(), 25))
        border_color = qcolor_to_rgba(QColor(t.green.red(), t.green.green(), t.green.blue(), 60))
        title.setStyleSheet(
            f"color: {title_color};"
            f"background-color: {bg_color};"
            f"border: 1px solid {border_color};"
            f"border-radius: 12px;"
            f"min-height: 24px;"
            f"max-height: 24px;"
            f"padding: 0 10px;"
        )
        h_layout.addWidget(title)

        self._ai_badge = QLabel("✦ AI")
        self._ai_badge.setFont(font_sans(9, 600))
        ai_col = qcolor_to_rgba(t.ai)
        ai_bg = qcolor_to_rgba(t.ai_soft)
        ai_border = qcolor_to_rgba(t.ai_border)
        self._ai_badge.setStyleSheet(
            f"color: {ai_col}; background-color: {ai_bg}; border: 1px solid {ai_border}; "
            "border-radius: 12px; min-height: 24px; max-height: 24px; padding: 0 10px;"
        )
        self._ai_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ai_badge.hide()
        
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._ai_badge_fx = QGraphicsOpacityEffect(self._ai_badge)
        self._ai_badge_fx.setOpacity(0.0)
        self._ai_badge.setGraphicsEffect(self._ai_badge_fx)
        
        h_layout.addSpacing(4)
        h_layout.addWidget(self._ai_badge)

        self._header_dot = PulsingDot(t.text_light, header)
        self._header_dot.set_static()
        self._header_dot.hide()
        h_layout.addWidget(self._header_dot)

        h_layout.addStretch()

        border_rgba = qcolor_to_rgba(t.border)
        text_light_rgba = qcolor_to_rgba(t.text_light)
        text_mid_rgba = qcolor_to_rgba(t.text_mid)
        text_rgba = qcolor_to_rgba(t.text)
        surface_2_rgba = qcolor_to_rgba(t.surface_2)

        close_btn = QPushButton("\u2715")
        close_btn.setStyle(fusion)
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton {"
            f"  background-color: {surface_2_rgba};"
            f"  border: 1px solid {border_rgba};"
            "  border-radius: 10px;"
            f"  color: {text_light_rgba}; font-size: 9px;"
            "  outline: 0;"
            "}"
            f"QPushButton:hover {{ background-color: {border_rgba}; color: {text_rgba}; }}"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.closeClicked.emit)
        h_layout.addWidget(close_btn)
        layout.addWidget(header)

        # Header divider line
        header_line = QFrame()
        header_line.setFrameShape(QFrame.Shape.HLine)
        header_line.setFixedHeight(1)
        header_line.setStyleSheet(f"background: {border_rgba}; border: none;")
        layout.addWidget(header_line)

        # Text area body
        self._body_widget = QWidget()
        b_layout = QVBoxLayout(self._body_widget)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setFont(font_serif(15, 400, italic=True))
        self._text_edit.setMinimumHeight(80)
        self._text_edit.setMaximumHeight(200)
        self._text_edit.setReadOnly(True)
        b_layout.addWidget(self._text_edit)

        self._ai_skeleton = AIShimmerSkeleton()
        self._ai_skeleton.hide()
        b_layout.addWidget(self._ai_skeleton)

        self._ai_text_edit = QTextEdit()
        self._ai_text_edit.setFont(font_sans(14, 400))
        self._ai_text_edit.setMinimumHeight(80)
        self._ai_text_edit.setMaximumHeight(200)
        self._ai_text_edit.setReadOnly(True)
        self._ai_text_edit.hide()
        b_layout.addWidget(self._ai_text_edit)
        
        # apply initial styles
        self._set_text_opacity(self._text_opacity)

        layout.addWidget(self._body_widget)

        # Footer divider line
        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.Shape.HLine)
        footer_line.setFixedHeight(1)
        footer_line.setStyleSheet(f"background: {border_rgba}; border: none;")
        layout.addWidget(footer_line)

        # Footer
        footer = QWidget()
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(14, 10, 14, 14)
        f_layout.setSpacing(7)

        # Ghost style buttons (Retry) — translucent background, border stroke
        bg_color = qcolor_to_rgba(QColor(t.text.red(), t.text.green(), t.text.blue(), 15))
        hover_bg = qcolor_to_rgba(QColor(t.text.red(), t.text.green(), t.text.blue(), 30))
        border_color = qcolor_to_rgba(QColor(t.text.red(), t.text.green(), t.text.blue(), 40))

        ghost_btn_style = (
            "QPushButton {"
            f"  background-color: {bg_color};"
            f"  border: 1px solid {border_color};"
            "  border-radius: 12px;"
            "  min-height: 24px;"
            "  max-height: 24px;"
            "  padding: 0 14px;"
            f"  color: {text_mid_rgba};"
            "  font-size: 11px; font-weight: 500;"
            "  outline: 0;"
            "}"
            f"QPushButton:hover {{ background-color: {hover_bg}; color: {text_rgba}; }}"
        )

        self._ai_toggle = AITogglePill()
        self._ai_toggle.toggled.connect(self.aiToggleClicked.emit)
        f_layout.addWidget(self._ai_toggle)
        
        f_layout.addSpacing(6)

        self._stats_label = QLabel("0:00 · 0 WORDS")
        self._stats_label.setFont(font_sans(10, 600))
        stats_color = qcolor_to_rgba(t.text_light)
        self._stats_label.setStyleSheet(f"color: {stats_color}; border: none;")
        f_layout.addWidget(self._stats_label)

        f_layout.addSpacing(4)

        btn_retry = QPushButton("Retry")
        btn_retry.setStyle(fusion)
        btn_retry.setStyleSheet(ghost_btn_style)
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self.retryClicked.emit)
        f_layout.addWidget(btn_retry)

        f_layout.addStretch()

        # Copy text button — accent red background
        red_rgba = qcolor_to_rgba(t.red)
        red_hover = QColor(
            min(255, t.red.red() + 20),
            min(255, t.red.green() + 20),
            min(255, t.red.blue() + 20),
        )
        red_hover_rgba = qcolor_to_rgba(red_hover)
        self._btn_copy = QPushButton("Copy text")
        self._btn_copy.setStyle(fusion)
        self._btn_copy.setStyleSheet(
            "QPushButton {"
            f"  background-color: {red_rgba};"
            f"  border: 1px solid {red_rgba};"
            "  border-radius: 12px;"
            "  min-height: 24px;"
            "  max-height: 24px;"
            "  padding: 0 18px;"
            "  color: rgba(255,255,255,0.95);"
            "  font-size: 11px; font-weight: 600;"
            "  outline: 0;"
            "}"
            f"QPushButton:hover {{ background-color: {red_hover_rgba}; border: 1px solid {red_hover_rgba}; }}"
        )
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy.clicked.connect(self._on_copy_close)
        f_layout.addWidget(self._btn_copy)

        layout.addWidget(footer)

    def _on_copy_close(self):
        self.copyCloseClicked.emit(self.get_text())

    def set_text(self, text: str, duration: float = 0.0):
        if text == self._prev_text:
            return
        self._prev_text = text
        self._text_edit.setPlainText(text)
        self._text_edit.setReadOnly(True)
        
        words = len(text.split())
        m = int(duration) // 60
        s = int(duration) % 60
        self._stats_label.setText(f"{m}:{s:02d} \u00b7 {words} WORDS")
        
        self._animate_text_popup()

    def append_word(self, word: str):
        """Insert word with 180ms fade-in animation."""
        t = theme()
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        if cursor.position() > 0:
            cursor.insertText(" ")

        # Insert word at opacity 0 (transparent text color)
        start_pos = cursor.position()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(t.text_mid.red(), t.text_mid.green(), t.text_mid.blue(), 0))
        cursor.insertText(word, fmt)
        end_pos = cursor.position()
        count = len(self._text_edit.toPlainText())

        # Animate word opacity: 0 → 1 over ANIM_WORD_FADE (180ms, 80ms if reduce motion)
        fade_ms = 80 if should_reduce_motion() else ANIM_WORD_FADE
        steps = max(1, fade_ms // 16)
        step_i = [0]

        def _fade_step() -> None:
            step_i[0] += 1
            alpha = min(1.0, step_i[0] / steps)
            word_fmt = QTextCharFormat()
            word_fmt.setForeground(
                QColor(t.text_mid.red(), t.text_mid.green(), t.text_mid.blue(),
                       int(alpha * 255))
            )
            c = self._text_edit.textCursor()
            c.setPosition(start_pos)
            c.setPosition(end_pos, c.MoveMode.KeepAnchor)
            c.mergeCharFormat(word_fmt)
            if step_i[0] >= steps:
                fade_timer.stop()
                if fade_timer in self._word_fade_timers:
                    self._word_fade_timers.remove(fade_timer)

        fade_timer = QTimer(self)
        fade_timer.setInterval(16)
        fade_timer.timeout.connect(_fade_step)
        self._word_fade_timers.append(fade_timer)
        fade_timer.start()

    def clear_text(self):
        for timer in self._word_fade_timers:
            timer.stop()
        self._word_fade_timers.clear()
        self._text_edit.clear()

    def get_text(self) -> str:
        if self._ai_text_edit.isVisible():
            return self._ai_text_edit.toPlainText()
        return self._text_edit.toPlainText()

    # ── AI Mode States ──────────────────────────────────────

    def show_raw(self):
        self._ai_skeleton.stop()
        self._ai_text_edit.hide()
        self._text_edit.show()
        if self._ai_badge.isVisible():
            self._fade_badge(0.0)
        self._btn_copy.setText("Copy text")
        self._btn_copy.setEnabled(True)
        self._btn_copy.setGraphicsEffect(None)

    def show_ai_loading(self):
        self._text_edit.hide()
        self._ai_text_edit.hide()
        self._ai_skeleton.start()
        if not self._ai_badge.isVisible():
            self._fade_badge(1.0)
        self._btn_copy.setText("...")
        self._btn_copy.setEnabled(False)
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        fx = QGraphicsOpacityEffect()
        fx.setOpacity(0.55)
        self._btn_copy.setGraphicsEffect(fx)
        
    def show_ai_result(self, formatted_text: str, show_original: bool = False):
        self._ai_skeleton.stop()
        self._ai_text_edit.setPlainText(formatted_text)
        self._ai_text_edit.show()
        if show_original:
            # Show raw transcript below AI result (dimmed, read-only)
            self._text_edit.show()
            self._text_edit.setReadOnly(True)
        else:
            self._text_edit.hide()
        if not self._ai_badge.isVisible():
            self._fade_badge(1.0)
        self._btn_copy.setText("Copy text")
        self._btn_copy.setEnabled(True)
        self._btn_copy.setGraphicsEffect(None)
        self._animate_text_popup()

    def _fade_badge(self, target: float):
        if target > 0:
            self._ai_badge.show()
        anim = QPropertyAnimation(self._ai_badge_fx, b"opacity")
        anim.setDuration(150)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if target <= 0:
            anim.finished.connect(self._ai_badge.hide)
        
        # Keep ref
        self._badge_anim = anim
        anim.start()

    def _animate_text_popup(self):
        """Subtle scale bounce + fade when text updates — matches pill entrance feel."""
        group = QParallelAnimationGroup(self)

        # Opacity: 0.4 → 1.0
        op = QPropertyAnimation(self, b"text_opacity")
        op.setDuration(220)
        op.setStartValue(0.4)
        op.setEndValue(1.0)
        op.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(op)

        # Slide up: 4px → 0px
        ty = QPropertyAnimation(self, b"text_translate_y")
        ty.setDuration(260)
        ty.setStartValue(4.0)
        ty.setEndValue(0.0)
        ty.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(ty)

        # Scale bounce: 0.96 → 1.0
        sc = QPropertyAnimation(self, b"text_scale")
        sc.setDuration(260)
        sc.setStartValue(0.96)
        sc.setEndValue(1.0)
        sc.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(sc)

        # Keep ref alive
        self._text_anim = group
        group.start()

    def start_dot_pulse(self):
        self._header_dot.show()
        self._header_dot.start(speed=0.77)

    def stop_dot_pulse(self):
        t = theme()
        self._header_dot.stop()
        self._header_dot.set_color(t.text_light)
        self._header_dot.set_static()
        self._header_dot.hide()

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), RADIUS_CARD, RADIUS_CARD)

        # Fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(t.surface)
        p.drawPath(path)

        # Border
        p.setPen(QPen(t.border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        p.end()


# ════════════════════════════════════════════════════════════
#  MAIN OVERLAY WINDOW
# ════════════════════════════════════════════════════════════


class OverlayWindow(QWidget):
    """Pill + connector + notepad system. Always bottom-centre of screen."""

    rms_received = pyqtSignal(float)
    transcript_received = pyqtSignal(str)
    request_ai_format = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = OverlayState.IDLE
        self._is_typing_context = False
        self._widget_opacity = 1.0
        self._pill_opacity_val = 1.0
        self._timer_seconds = 0
        self._live_words: list[str] = []
        self._pill_translate_y = 0.0
        self._notepad_translate_y = -8.0
        self._notepad_opacity = 0.0
        self._connector_h = 0.0
        self._animations: list = []  # keep refs alive

        # Shadow blend animation state
        self._shadow_from_state: tuple | None = None  # (blur, oy, color, border)
        self._shadow_to_state: tuple | None = None
        self._shadow_blend_val = 1.0
        self._shadow_anim: QPropertyAnimation | None = None

        # AI mode state (tracked across recording → result lifecycle)
        self._ai_mode_active = False
        self._ai_show_original = False

        # Connector gradient pulse state
        self._streaming = False
        self._pulse_phase = 0.0
        self._pulse_opacity = 0.0
        self._pulse_fade = None
        self._base_y = 0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(16)  # ~60fps
        self._pulse_timer.timeout.connect(self._tick_pulse)

        self._setup_window_flags()
        self._build_widgets()
        self._connect_signals()
        self._start_timer_clock()

        # Focus-check timer for click-away dismiss in RESULT_NOTEPAD
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(500)
        self._focus_timer.timeout.connect(self._check_focus)

        # Start in IDLE (hidden until hotkey press)
        self._enter_idle(None)

    # ── Animatable properties ────────────────────────────────

    def set_is_typing_context(self, context: bool):
        self._is_typing_context = context

    def set_ai_mode(self, active: bool, show_original: bool = False):
        """Set AI mode state before recording starts."""
        self._ai_mode_active = active
        self._ai_show_original = show_original

    def _get_pill_opacity(self) -> float:
        return self._pill_opacity_val

    def _set_pill_opacity(self, val: float):
        # Do NOT use QGraphicsOpacityEffect on the pill — causes SIGSEGV in
        # Cocoa rendering.  Use setWindowOpacity() for whole-window fading.
        self._pill_opacity_val = val
        self.setWindowOpacity(val)

    pill_opacity = pyqtProperty(float, _get_pill_opacity, _set_pill_opacity)

    def _get_widget_opacity(self) -> float:
        return self._widget_opacity

    def _set_widget_opacity(self, val: float):
        self._widget_opacity = val
        self.setWindowOpacity(val)
        self.update()

    widget_opacity = pyqtProperty(float, _get_widget_opacity, _set_widget_opacity)

    def _get_pill_translate_y(self) -> float:
        return self._pill_translate_y

    def _set_pill_translate_y(self, val: float):
        self._pill_translate_y = val
        # Move the actual window position so background + content stay aligned
        if hasattr(self, "_base_y"):
            self.move(self.x(), self._base_y + int(val))

    pill_translate_y = pyqtProperty(float, _get_pill_translate_y, _set_pill_translate_y)

    def _get_notepad_opacity(self) -> float:
        return self._notepad_opacity

    def _set_notepad_opacity(self, val: float):
        self._notepad_opacity = val
        # Notepad visibility controlled by show/hide + window opacity
        self.update()

    notepad_opacity = pyqtProperty(float, _get_notepad_opacity, _set_notepad_opacity)

    def _get_notepad_translate_y(self) -> float:
        return self._notepad_translate_y

    def _set_notepad_translate_y(self, val: float):
        self._notepad_translate_y = val
        self.update()

    notepad_translate_y = pyqtProperty(float, _get_notepad_translate_y, _set_notepad_translate_y)

    def _get_connector_h(self) -> float:
        return self._connector_h

    def _set_connector_h(self, val: float):
        self._connector_h = val
        self._connector.setFixedHeight(max(0, int(val)))
        self.adjustSize()

    connector_h = pyqtProperty(float, _get_connector_h, _set_connector_h)

    def _get_shadow_blend(self) -> float:
        return self._shadow_blend_val

    def _set_shadow_blend(self, val: float):
        self._shadow_blend_val = val
        sf = self._shadow_from_state
        st = self._shadow_to_state
        if sf is None or st is None:
            return
        v = val
        self._pill_shadow_blur = sf[0] + (st[0] - sf[0]) * v
        self._pill_shadow_offset_y = sf[1] + (st[1] - sf[1]) * v
        fc, tc = sf[2], st[2]
        self._pill_shadow_color = QColor(
            int(fc.red() + (tc.red() - fc.red()) * v),
            int(fc.green() + (tc.green() - fc.green()) * v),
            int(fc.blue() + (tc.blue() - fc.blue()) * v),
            int(fc.alpha() + (tc.alpha() - fc.alpha()) * v),
        )
        fb, tb = sf[3], st[3]
        self._pill.set_border_color(QColor(
            int(fb.red() + (tb.red() - fb.red()) * v),
            int(fb.green() + (tb.green() - fb.green()) * v),
            int(fb.blue() + (tb.blue() - fb.blue()) * v),
            int(fb.alpha() + (tb.alpha() - fb.alpha()) * v),
        ))
        self.update()

    shadow_blend = pyqtProperty(float, _get_shadow_blend, _set_shadow_blend)

    # ── Setup ───────────────────────────────────────────────

    def _setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _build_widgets(self):
        t = theme()

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(24, 24, 24, 24)
        self._main_layout.setSpacing(0)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ── PILL ──
        self._pill = PillWidget(self)
        self._pill.setFixedHeight(PILL_HEIGHT)
        pill_layout = QHBoxLayout(self._pill)
        pill_layout.setContentsMargins(PILL_PADDING_H, 0, PILL_PADDING_H, 0)
        pill_layout.setSpacing(10)
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # -- Idle state --
        self._idle_container = QWidget()
        idle_l = QHBoxLayout(self._idle_container)
        idle_l.setContentsMargins(0, 0, 0, 0)
        idle_l.setSpacing(10)
        self._idle_dot = PulsingDot(t.text_light, self._idle_container)
        idle_l.addWidget(self._idle_dot)
        self._idle_label = QLabel("Hold Right \u2325 to record")
        self._idle_label.setFont(font_sans(13, 500))
        idle_label_color = qcolor_to_rgba(t.text_mid)
        self._idle_label.setStyleSheet(f"color: {idle_label_color};")
        idle_l.addWidget(self._idle_label)
        pill_layout.addWidget(self._idle_container)

        # -- Recording state --
        self._rec_container = QWidget()
        rec_l = QHBoxLayout(self._rec_container)
        rec_l.setContentsMargins(0, 0, 0, 0)
        rec_l.setSpacing(10)
        self._rec_dot = PulsingDot(t.red, self._rec_container)
        rec_l.addWidget(self._rec_dot)
        self._waveform = WaveformWidget(self._rec_container)
        rec_l.addWidget(self._waveform)
        self._rec_sep = PillSep(self._rec_container)
        rec_l.addWidget(self._rec_sep)
        self._timer_label = QLabel("0:00")
        self._timer_label.setFont(font_sans(11, 600))
        timer_color = qcolor_to_rgba(t.text_light)
        self._timer_label.setStyleSheet(f"color: {timer_color}; letter-spacing: 0.2px;")
        rec_l.addWidget(self._timer_label)
        self._rec_container.hide()
        pill_layout.addWidget(self._rec_container)

        # -- Live transcribing state --
        self._live_container = QWidget()
        live_l = QHBoxLayout(self._live_container)
        live_l.setContentsMargins(0, 0, 0, 0)
        live_l.setSpacing(10)
        self._live_dot = PulsingDot(t.red, self._live_container)
        live_l.addWidget(self._live_dot)
        self._live_text = QLabel("")
        self._live_text.setFont(font_serif(13, 400, italic=True))
        live_text_color = qcolor_to_rgba(t.text)
        self._live_text.setStyleSheet(f"color: {live_text_color};")
        self._live_text.setMaximumWidth(260)
        live_l.addWidget(self._live_text)
        self._live_cursor = BlinkingCursor(t.red, self._live_container)
        live_l.addWidget(self._live_cursor)
        self._live_sep = PillSep(self._live_container)
        live_l.addWidget(self._live_sep)
        self._live_waveform = WaveformWidget(self._live_container)
        live_l.addWidget(self._live_waveform)
        self._live_container.hide()
        pill_layout.addWidget(self._live_container)

        # -- Notepad pill state (grey dot + label) --
        self._np_pill_container = QWidget()
        np_l = QHBoxLayout(self._np_pill_container)
        np_l.setContentsMargins(0, 0, 0, 0)
        np_l.setSpacing(10)
        self._np_dot = PulsingDot(t.text_light, self._np_pill_container)
        np_l.addWidget(self._np_dot)
        self._np_label = QLabel("Tap to edit \u00b7 Right \u2325 again")
        self._np_label.setFont(font_sans(13, 500))
        np_label_color = qcolor_to_rgba(t.text)
        self._np_label.setStyleSheet(f"color: {np_label_color};")
        np_l.addWidget(self._np_label)
        self._np_pill_container.hide()
        pill_layout.addWidget(self._np_pill_container)

        # -- Success state --
        self._success_container = QWidget()
        suc_l = QHBoxLayout(self._success_container)
        suc_l.setContentsMargins(0, 0, 0, 0)
        suc_l.setSpacing(10)
        self._success_dot = PulsingDot(t.green, self._success_container)
        suc_l.addWidget(self._success_dot)
        self._success_label = QLabel("Typed into field")
        self._success_label.setFont(font_sans(13, 600))
        success_color = qcolor_to_rgba(t.green)
        self._success_label.setStyleSheet(f"color: {success_color};")
        suc_l.addWidget(self._success_label)
        self._success_container.hide()
        pill_layout.addWidget(self._success_container)

        # Shadow config (painted in paintEvent, animated via shadow_blend)
        self._pill_shadow_blur = 16.0
        self._pill_shadow_offset_y = 2.0
        self._pill_shadow_color = QColor(0, 0, 0, 12)

        self._main_layout.addWidget(self._pill, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── CONNECTOR ──
        self._connector = QWidget(self)
        self._connector.setFixedSize(2, 0)
        self._connector.setStyleSheet("background: transparent;")
        self._main_layout.addWidget(self._connector, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── NOTEPAD ──
        self._notepad = NotepadWidget(self)
        self._notepad.hide()
        self._main_layout.addWidget(self._notepad, 0, Qt.AlignmentFlag.AlignHCenter)

        self._pill.adjustSize()
        self.adjustSize()

    def _connect_signals(self):
        self.rms_received.connect(self._on_rms, Qt.ConnectionType.QueuedConnection)
        self.transcript_received.connect(
            self._on_transcript_update, Qt.ConnectionType.QueuedConnection
        )
        self._notepad.copyCloseClicked.connect(self._on_copy_close)
        self._notepad.closeClicked.connect(lambda: self.transition_to(OverlayState.IDLE))
        self._notepad.aiToggleClicked.connect(self._on_ai_toggle_request)

    @pyqtSlot(float)
    def _on_rms(self, value: float):
        self._waveform.set_rms(value)
        self._live_waveform.set_rms(value)

    @pyqtSlot(str)
    def _on_transcript_update(self, text: str):
        if not text.strip():
            return

        if self._state == OverlayState.RECORDING:
            self.transition_to(OverlayState.LIVE_TRANSCRIBING)

        if self._state == OverlayState.LIVE_TRANSCRIBING:
            words = text.strip().split()
            self._live_words = words
            preview = " ".join(words[-4:])
            self._live_text.setText(preview)
            self._notepad.set_text(text)

    def _on_copy_close(self, text: str):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
        self.transition_to(OverlayState.IDLE)

    @pyqtSlot(bool)
    def _on_ai_toggle_request(self, checked: bool):
        # Always track the mode
        self._ai_mode_active = checked

        # During recording/live: just store the flag, no API call
        if self._state in (OverlayState.RECORDING, OverlayState.LIVE_TRANSCRIBING):
            return

        # In result state: trigger format or revert
        raw_text = self._notepad._text_edit.toPlainText()
        if checked:
            self._notepad.show_ai_loading()
            self.request_ai_format.emit(raw_text)
            self.ai_mode_toggled.emit(raw_text, True)
        else:
            self._notepad.show_raw()
            self._animate_notepad_bounce()
            self.ai_mode_toggled.emit(raw_text, False)

    @pyqtSlot(str)
    def on_ai_format_completed(self, text: str):
        if self._state == OverlayState.RESULT_NOTEPAD:
            self._notepad.show_ai_result(text, show_original=self._ai_show_original)
            self._animate_notepad_bounce()

    @pyqtSlot()
    def on_ai_format_failed(self):
        if self._state == OverlayState.RESULT_NOTEPAD:
            self._notepad._ai_toggle.set_checked(False)
            self._notepad.show_raw()
            self._animate_notepad_bounce()

    def _animate_notepad_bounce(self):
        """Bounce effect when layout resizes due to text swap."""
        self.adjustSize()
        self._reposition()
        anim = self._make_anim(b"notepad_translate_y", 8.0, 0.0, 320, EASE_SPRING)
        self._animations.append(anim)
        anim.start()

    # ── Timer clock ─────────────────────────────────────────

    def _start_timer_clock(self):
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_timer)

    def _tick_timer(self):
        self._timer_seconds += 1
        m = self._timer_seconds // 60
        s = self._timer_seconds % 60
        self._timer_label.setText(f"{m}:{s:02d}")

    # ── Positioning ─────────────────────────────────────────

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - BOTTOM_MARGIN
        self._base_y = y  # store for pill_translate_y window movement
        self.move(x, y + int(self._pill_translate_y))

    # ── Pill shadow ───────────────────────────────────────────

    def _animate_shadow_to(
        self, blur: float, oy: float, color: QColor, border_color: QColor
    ) -> None:
        """Animate shadow transition over 200ms (OutCubic)."""
        if self._shadow_from_state is None:
            # First call (init) — set directly, no animation
            self._pill_shadow_blur = blur
            self._pill_shadow_offset_y = oy
            self._pill_shadow_color = QColor(color)
            self._pill.set_border_color(QColor(border_color))
            self._shadow_from_state = (blur, oy, QColor(color), QColor(border_color))
            self.update()
            return
        self._shadow_from_state = (
            float(self._pill_shadow_blur),
            float(self._pill_shadow_offset_y),
            QColor(self._pill_shadow_color),
            QColor(self._pill._border_color) if self._pill._border_color else QColor(0, 0, 0, 0),
        )
        self._shadow_to_state = (float(blur), float(oy), QColor(color), QColor(border_color))
        self._shadow_blend_val = 0.0
        if self._shadow_anim:
            self._shadow_anim.stop()
        self._shadow_anim = self._make_anim(b"shadow_blend", 0.0, 1.0, 200, EASE_SETTLE)
        self._shadow_anim.start()

    def _set_pill_shadow_idle(self):
        """Idle/success: subtle shadow + normal border (CSS spec)."""
        t = theme()
        self._animate_shadow_to(
            blur=16.0, oy=2.0,
            color=QColor(0, 0, 0, 12),
            border_color=QColor(t.border),
        )

    def _set_pill_shadow_active(self):
        """Active: soft red glow + red-tinted border (CSS spec).

        CSS: box-shadow: 0 2px 20px rgba(224,90,71,0.2),
                         0 0 0 4px rgba(224,90,71,0.08)
             border-color: rgba(224,90,71,0.28)
        """
        t = theme()
        self._animate_shadow_to(
            blur=20.0, oy=2.0,
            color=QColor(t.red.red(), t.red.green(), t.red.blue(), 30),
            border_color=QColor(t.red_border),
        )

    # ── Pill state crossfade ─────────────────────────────────

    def _crossfade_pill_state(
        self,
        hide_container: QWidget | None,
        show_container: QWidget,
    ) -> None:
        """Switch between pill state containers.

        Hides ALL other containers, then shows the target.
        No QGraphicsEffect used — avoids Qt rendering offset bugs.
        """
        for container in (
            self._idle_container,
            self._rec_container,
            self._live_container,
            self._np_pill_container,
            self._success_container,
        ):
            if container is not show_container:
                container.hide()

        show_container.show()
        self._pill.adjustSize()
        self.adjustSize()
        self._reposition()

    # ── Connector gradient pulse ─────────────────────────────

    def _start_streaming(self):
        """Start the gradient pulse flowing down the connector."""
        if self._streaming:
            return
        self._streaming = True
        self._pulse_phase = 0.0
        self._pulse_opacity = 0.0
        self._pulse_timer.start()
        # Fade in
        self._pulse_fade = QPropertyAnimation(self, b"pulse_opacity")
        self._pulse_fade.setDuration(300)
        self._pulse_fade.setStartValue(0.0)
        self._pulse_fade.setEndValue(1.0)
        self._pulse_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pulse_fade.start()

    def _stop_streaming(self):
        """Fade out and stop the gradient pulse."""
        if not self._streaming:
            return
        self._streaming = False
        self._pulse_fade = QPropertyAnimation(self, b"pulse_opacity")
        self._pulse_fade.setDuration(300)
        self._pulse_fade.setStartValue(self._pulse_opacity)
        self._pulse_fade.setEndValue(0.0)
        self._pulse_fade.setEasingCurve(QEasingCurve.Type.InCubic)
        self._pulse_fade.finished.connect(self._pulse_timer.stop)
        self._pulse_fade.start()

    def _get_pulse_opacity(self) -> float:
        return self._pulse_opacity

    def _set_pulse_opacity(self, val: float):
        self._pulse_opacity = val
        self.update()

    pulse_opacity = pyqtProperty(float, _get_pulse_opacity, _set_pulse_opacity)

    def _tick_pulse(self):
        """Advance pulse phase — 0.25s per full cycle."""
        self._pulse_phase += 16.0 / 250.0  # 16ms tick / 250ms cycle
        if self._pulse_phase >= 1.0:
            self._pulse_phase -= 1.0
        self.update()

    # ── Animation helpers ───────────────────────────────────

    def _make_anim(
        self,
        prop: bytes,
        start: float,
        end: float,
        duration: int,
        easing: QEasingCurve.Type = EASE_SETTLE,
        target: QWidget | None = None,
    ) -> QPropertyAnimation:
        """Create a QPropertyAnimation with reduce-motion awareness."""
        anim = QPropertyAnimation(target or self, prop)
        if should_reduce_motion():
            duration = min(duration, 150)
            easing = EASE_SETTLE
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing)
        return anim

    def _reset_pill_transforms(self):
        """Reset pill transforms to neutral position."""
        self._pill_translate_y = 0.0
        self._widget_opacity = 1.0
        self.setWindowOpacity(1.0)
        self.pill_opacity = 1.0
        self._notepad_translate_y = -8.0

    def _stop_animations(self):
        for anim in self._animations:
            if hasattr(anim, "stop"):
                anim.stop()
        self._animations.clear()
        self._reset_pill_transforms()

    def _animate_pill_entrance(self):
        """Gravity + gentle rebound: +40px → 0, fade in, 500ms."""
        self._pill_translate_y = 40.0
        self._widget_opacity = 0.0

        group = QParallelAnimationGroup(self)
        group.addAnimation(
            self._make_anim(b"pill_translate_y", 40.0, 0.0, 500, EASE_SPRING)
        )

        op = self._make_anim(b"widget_opacity", 0.0, 1.0, 300, EASE_SETTLE)
        group.addAnimation(op)

        self._animations.append(group)
        group.start()

    def _animate_notepad_open(self):
        """Multi-track staggered: pill nudge → connector draw → notepad entrance."""
        master = QParallelAnimationGroup(self)

        # Track 1 (0ms): Pill nudge up -4px then settle back
        nudge_seq = QSequentialAnimationGroup(self)
        nudge_seq.addAnimation(
            self._make_anim(b"pill_translate_y", 0.0, -4.0, 260, EASE_SETTLE)
        )
        nudge_seq.addAnimation(
            self._make_anim(b"pill_translate_y", -4.0, 0.0, 200, EASE_SETTLE)
        )
        master.addAnimation(nudge_seq)

        # Track 2 (60ms delay): Connector draws down
        conn_seq = QSequentialAnimationGroup(self)
        conn_seq.addPause(60)
        conn_seq.addAnimation(
            self._make_anim(b"connector_h", 0.0, float(CONNECTOR_HEIGHT),
                            ANIM_NOTEPAD_OPEN, EASE_SPRING)
        )
        master.addAnimation(conn_seq)

        # Track 3 (180ms delay): Notepad fades in + slides up
        np_seq = QSequentialAnimationGroup(self)
        np_seq.addPause(180)
        np_group = QParallelAnimationGroup(self)
        np_group.addAnimation(
            self._make_anim(b"notepad_opacity", 0.0, 1.0, 340, EASE_SPRING)
        )
        np_group.addAnimation(
            self._make_anim(b"notepad_translate_y", -12.0, 0.0, 340, EASE_SPRING)
        )
        np_seq.addAnimation(np_group)
        master.addAnimation(np_seq)

        self._animations.append(master)
        master.start()

    def _animate_notepad_close(self):
        """Multi-track reverse: notepad fade → connector collapse → pill settle."""
        self._stop_streaming()
        master = QParallelAnimationGroup(self)

        # Track 1 (0ms): Notepad fades out + slides up
        np_group = QParallelAnimationGroup(self)
        np_group.addAnimation(
            self._make_anim(b"notepad_opacity", self._notepad_opacity, 0.0,
                            ANIM_NOTEPAD_CLOSE, EASE_LIFT)
        )
        np_group.addAnimation(
            self._make_anim(b"notepad_translate_y", 0.0, -8.0,
                            ANIM_NOTEPAD_CLOSE, EASE_LIFT)
        )
        master.addAnimation(np_group)

        # Track 2 (80ms delay): Connector collapses
        conn_seq = QSequentialAnimationGroup(self)
        conn_seq.addPause(80)
        conn_seq.addAnimation(
            self._make_anim(b"connector_h", self._connector_h, 0.0, 240, EASE_LIFT)
        )
        master.addAnimation(conn_seq)

        # Track 3 (120ms delay): Pill settles back to 0
        pill_seq = QSequentialAnimationGroup(self)
        pill_seq.addPause(120)
        pill_seq.addAnimation(
            self._make_anim(b"pill_translate_y", self._pill_translate_y, 0.0,
                            200, EASE_SETTLE)
        )
        master.addAnimation(pill_seq)

        master.finished.connect(self._on_notepad_closed)
        self._animations.append(master)
        master.start()

    def _on_notepad_closed(self):
        self._notepad.hide()
        self._connector.setFixedHeight(0)
        self.adjustSize()
        self._reposition()

    def _animate_exit_success(self):
        """Dismissal: bounce up slightly, then drop down and fade out."""
        group = QParallelAnimationGroup(self)
        
        seq = QSequentialAnimationGroup(self)
        seq.addAnimation(self._make_anim(b"pill_translate_y", 0.0, -12.0, 200, EASE_SETTLE))
        seq.addAnimation(self._make_anim(b"pill_translate_y", -12.0, 40.0, 240, EASE_LIFT))
        group.addAnimation(seq)

        fade_seq = QSequentialAnimationGroup(self)
        fade_seq.addPause(150)
        fade_seq.addAnimation(self._make_anim(b"widget_opacity", 1.0, 0.0, 240, EASE_LIFT))
        group.addAnimation(fade_seq)

        self._animations.append(group)
        group.start()

    # ── State Machine ───────────────────────────────────────

    def transition_to(self, new_state: OverlayState, **kwargs):
        old_state = self._state
        if new_state == old_state:
            return
        self._state = new_state

        dispatch = {
            OverlayState.IDLE: self._enter_idle,
            OverlayState.RECORDING: self._enter_recording,
            OverlayState.LIVE_TRANSCRIBING: self._enter_live_transcribing,
            OverlayState.RESULT_FIELD: self._enter_result_field,
            OverlayState.RESULT_NOTEPAD: self._enter_result_notepad,
        }
        dispatch[new_state](old_state, **kwargs)

    def _container_for_state(self, state: OverlayState) -> QWidget:
        """Return the pill container widget for a given state."""
        return {
            OverlayState.IDLE: self._idle_container,
            OverlayState.RECORDING: self._rec_container,
            OverlayState.LIVE_TRANSCRIBING: self._live_container,
            OverlayState.RESULT_FIELD: self._success_container,
            OverlayState.RESULT_NOTEPAD: self._np_pill_container,
        }[state]

    def _stop_pill_peripherals(self):
        """Stop dots, waveforms, timers — but don't hide containers (crossfade does that)."""
        self._waveform.stop_animation()
        self._live_waveform.stop_animation()
        self._rec_dot.stop()
        self._live_dot.stop()
        self._np_dot.stop()
        self._success_dot.stop()
        self._idle_dot.stop()
        self._live_cursor.stop()
        self._clock_timer.stop()

    def get_notepad_text(self) -> str:
        """Returns the current text in the notepad."""
        return self._notepad._text_edit.toPlainText()

    def _hide_all_pill_states(self):
        self._idle_container.hide()
        self._rec_container.hide()
        self._live_container.hide()
        self._np_pill_container.hide()
        self._success_container.hide()
        self._stop_pill_peripherals()

    def _hide_notepad_instant(self):
        self._connector.setFixedHeight(0)
        self._connector_h = 0.0
        self._notepad_opacity = 0.0
        self._notepad_translate_y = -8.0
        self._notepad.hide()
        self._stop_streaming()

    def _enter_idle(self, from_state, **kwargs):
        t = theme()
        self._stop_animations()
        self._stop_pill_peripherals()
        self._focus_timer.stop()

        # If coming from a state with notepad, animate it closed
        if from_state in (OverlayState.LIVE_TRANSCRIBING, OverlayState.RESULT_NOTEPAD):
            self._animate_notepad_close()
        else:
            self._hide_notepad_instant()

        self._idle_dot.set_color(t.text_light)
        self._idle_dot.set_static()
        self._set_pill_shadow_idle()

        # Crossfade from previous state container
        old_container = self._container_for_state(from_state) if from_state else None
        self._crossfade_pill_state(old_container, self._idle_container)

        # Hide window when idle — nothing visible on screen
        self.hide()

    def _enter_recording(self, from_state, **kwargs):
        is_continuing = kwargs.get("is_continuing", False)
        
        self._stop_animations()
        self._stop_pill_peripherals()
        
        if not is_continuing:
            self._hide_notepad_instant()

        self._rec_dot.start(speed=1.1)
        self._waveform.start_animation()
        self._set_pill_shadow_active()
        self._timer_seconds = 0
        self._timer_label.setText("0:00")
        self._clock_timer.start()
        self._live_words = []

        old_container = self._container_for_state(from_state) if from_state else None
        self._crossfade_pill_state(old_container, self._rec_container)

        self.show()
        self._reposition()

        # Entrance animation from idle or first show
        if from_state in (None, OverlayState.IDLE):
            self._animate_pill_entrance()

    def _enter_live_transcribing(self, from_state, **kwargs):
        is_continuing = kwargs.get("is_continuing", False)
        
        self._stop_animations()
        self._stop_pill_peripherals()

        self._live_dot.start(speed=1.1)
        self._live_waveform.start_animation()
        self._live_text.setText("")
        self._live_cursor.start()
        self._set_pill_shadow_active()

        # Transfer waveform RMS from recording
        self._live_waveform.set_rms(self._waveform._rms)

        # Keep timer running
        self._clock_timer.start()

        # Crossfade pill state
        old_container = self._container_for_state(from_state) if from_state else None
        self._crossfade_pill_state(old_container, self._live_container)

        if self._is_typing_context:
            self._live_text.hide()
            self._live_sep.hide()
            self._live_cursor.hide()
            
            self.adjustSize()
            self._reposition()
        else:
            self._live_text.show()
            self._live_sep.show()
            self._live_cursor.show()
            
            if not is_continuing:
                # Show notepad with animation
                self._notepad.show()
                self._notepad.clear_text()
                self._notepad.start_dot_pulse()

                # Sync AI toggle to current mode
                self._notepad._ai_toggle.blockSignals(True)
                self._notepad._ai_toggle.set_checked(self._ai_mode_active, animate=False)
                self._notepad._ai_toggle.blockSignals(False)

                self.adjustSize()
                self._reposition()

                # Animate notepad dropping down + start connector pulse
                self._animate_notepad_open()
                self._start_streaming()
            else:
                self._notepad.show()
                self._notepad.start_dot_pulse()

                # Sync AI toggle to current mode
                self._notepad._ai_toggle.blockSignals(True)
                self._notepad._ai_toggle.set_checked(self._ai_mode_active, animate=False)
                self._notepad._ai_toggle.blockSignals(False)

                self._connector.setFixedHeight(CONNECTOR_HEIGHT)
                self._connector_h = float(CONNECTOR_HEIGHT)
                self._start_streaming()

    def _enter_result_field(self, from_state, text: str = "", **kwargs):
        t = theme()
        self._stop_animations()
        self._stop_pill_peripherals()

        # If coming from live with notepad open, close notepad
        if from_state in (OverlayState.LIVE_TRANSCRIBING, OverlayState.RESULT_NOTEPAD) and not self._is_typing_context:
            self._animate_notepad_close()
        else:
            self._hide_notepad_instant()

        self._success_dot.set_color(t.green)
        self._success_dot.set_static()
        self._set_pill_shadow_idle()

        old_container = self._container_for_state(from_state) if from_state else None
        self._crossfade_pill_state(old_container, self._success_container)

        self._reposition()

        # Auto-dismiss: exit animation then back to idle
        def _start_exit():
            if self._state == OverlayState.RESULT_FIELD:
                self._animate_exit_success()
                QTimer.singleShot(ANIM_PILL_EXIT + 50, self._finish_success_exit)

        QTimer.singleShot(2200, _start_exit)

    def _finish_success_exit(self):
        if self._state == OverlayState.RESULT_FIELD:
            self.transition_to(OverlayState.IDLE)

    def _enter_result_notepad(self, from_state, text: str = "", **kwargs):
        t = theme()
        self._stop_animations()
        self._stop_pill_peripherals()

        self._np_dot.set_color(t.text_light)
        self._live_cursor.stop()
        self._set_pill_shadow_active()

        self._stop_streaming()

        # Use ai_default kwarg if provided (from app.py), otherwise use tracked state
        entry = kwargs.get("history_entry")
        if entry:
            ai_default = bool(entry.get("ai_text"))
            duration = entry.get("duration_s", 0.0)
            text = entry.get("text", "")
            ai_preloaded_text = entry.get("ai_text", "")
        else:
            ai_default = kwargs.get("ai_default", False)
            duration = kwargs.get("duration", 0.0)
            ai_preloaded_text = ""

        if "ai_default" in kwargs or entry:
            self._ai_mode_active = ai_default
        if "ai_show_original" in kwargs:
            self._ai_show_original = kwargs["ai_show_original"]

        self._notepad.set_text(text, duration=duration)
        self._notepad.stop_dot_pulse()

        # Sync toggle to current AI mode (block signals to avoid double-fire)
        self._notepad._ai_toggle.blockSignals(True)
        self._notepad._ai_toggle.set_checked(self._ai_mode_active, animate=False)
        self._notepad._ai_toggle.blockSignals(False)

        if self._ai_mode_active:
            if ai_preloaded_text:
                self._notepad.show_ai_result(ai_preloaded_text, show_original=self._ai_show_original)
            else:
                self._notepad.show_ai_loading()
                self.request_ai_format.emit(text)
        else:
            self._notepad.show_raw()

        self._notepad.show()

        old_container = self._container_for_state(from_state) if from_state else None
        self._crossfade_pill_state(old_container, self._np_pill_container)

        self.show()
        self.raise_()
        self.adjustSize()
        self._reposition()

        # Don't hide the pill anymore so the user sees the shortcut hint.
        # Just ensure the notepad is fully visible at its position.
        group = QParallelAnimationGroup(self)
        group.addAnimation(self._make_anim(b"connector_h", float(CONNECTOR_HEIGHT), float(CONNECTOR_HEIGHT), 10, EASE_SPRING))
        group.addAnimation(self._make_anim(b"notepad_translate_y", self._notepad_translate_y, 0.0, ANIM_NOTEPAD_CLOSE, EASE_SPRING))
        
        self._animations.append(group)
        group.start()

        # Start focus-check timer for click-away dismiss
        self._focus_timer.start()

    # ── Focus check (click-away dismiss) ─────────────────────

    def _check_focus(self) -> None:
        """Dismiss notepad when the overlay loses focus (click-away)."""
        if self._state != OverlayState.RESULT_NOTEPAD:
            self._focus_timer.stop()
            return
        active = QApplication.activeWindow()
        if active is not self and active is not None:
            print(f"[Overlay] Focus lost → dismissing (active={type(active).__name__})")
            self._notepad.clear_text()
            self.transition_to(OverlayState.IDLE)

    # ── Painting ─────────────────────────────────────────────

    def paintEvent(self, event):
        t = theme()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._widget_opacity)

        # ── Pill shadow — disabled (QPainter can't blur edges) ─

        # ── Connector line + gradient pulse ──────────────────
        conn_rect = self._connector.geometry()
        if conn_rect.height() > 0:
            cx = float(conn_rect.center().x())
            cy_top = float(conn_rect.y())
            cy_bot = float(conn_rect.bottom())
            ch = cy_bot - cy_top

            # Static 2px border-colored line
            p.setPen(QPen(t.border, 2))
            p.drawLine(QPointF(cx, cy_top), QPointF(cx, cy_bot))

            # Animated gradient pulse (when streaming)
            if self._pulse_opacity > 0.01 and ch > 0:
                p.save()
                p.setOpacity(self._widget_opacity * self._pulse_opacity)

                # Clip to connector area
                clip_path = QPainterPath()
                clip_path.addRect(QRectF(cx - 2, cy_top, 4, ch))
                p.setClipPath(clip_path)

                # The gradient band is 2x connector height, sweeps from -100% to +100%
                band_h = ch * 2
                band_top = cy_top + (self._pulse_phase * 2 - 1) * ch
                band_bot = band_top + band_h

                rr, rg, rb = t.red.red(), t.red.green(), t.red.blue()
                pulse_grad = QLinearGradient(
                    QPointF(cx, band_top), QPointF(cx, band_bot)
                )
                pulse_grad.setColorAt(0.00, QColor(0, 0, 0, 0))
                pulse_grad.setColorAt(0.20, QColor(rr, rg, rb, 0))
                pulse_grad.setColorAt(0.48, QColor(rr, rg, rb, 179))   # 0.7 opacity
                pulse_grad.setColorAt(0.52, QColor(255, 255, 255, 242)) # 0.95 opacity
                pulse_grad.setColorAt(0.56, QColor(rr, rg, rb, 179))   # 0.7 opacity
                pulse_grad.setColorAt(0.80, QColor(rr, rg, rb, 0))
                pulse_grad.setColorAt(1.00, QColor(0, 0, 0, 0))

                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(pulse_grad)
                p.drawRect(QRectF(cx - 1, band_top, 2, band_h))

                p.restore()

        p.end()

    # ── Public API ──────────────────────────────────────────

    def update_rms(self, value: float):
        """Thread-safe RMS entry point."""
        self.rms_received.emit(value)

    def update_transcript(self, text: str):
        """Thread-safe transcript entry point."""
        self.transcript_received.emit(text)

    @property
    def state(self) -> OverlayState:
        return self._state
