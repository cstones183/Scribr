# overlay.py — PyQt6 floating overlay window.
# Frameless, always-on-top, anchored to bottom-centre of screen.
# States: IDLE, RECORDING, LIVE_TRANSCRIBING, RESULT_FIELD, RESULT_NOTEPAD
# Pill + connector + notepad design matching the HTML prototype.

import math
import random
import time
from enum import Enum, auto

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QApplication, QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QSequentialAnimationGroup,
    pyqtSignal, pyqtSlot, pyqtProperty, QRect, QPoint, QSize,
    QPointF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont,
    QLinearGradient,
)

from style import (
    NAVY, GLASS, GLASS2, BORDER, BORDER_HI, BORDER_FOCUS,
    BLUE, BLUE_SOFT, BLUE_GLOW, BLUE_DIM,
    GREEN, RED, AMBER,
    T1, T2, T3, T4,
    font,
    RADIUS_PILL, RADIUS_CARD,
    ANIM_ENTER, ANIM_EXIT, ANIM_EXPAND, ANIM_FAST,
    PILL_HEIGHT, PILL_PADDING_H, NOTEPAD_WIDTH, CONNECTOR_HEIGHT,
    BOTTOM_MARGIN,
    BAR_COUNT, BAR_WIDTH, BAR_GAP, BAR_MAX_H, BAR_MIN_H,
)


# ── Waveform tuning ───────────────────────────────────────

BAR_SCALE_FACTORS = [0.47, 0.74, 1.0, 0.74, 1.0, 0.74, 0.47]

SPRING_STIFFNESS = 0.3
SPRING_DAMPING = 0.7

BREATHING_FREQ = 0.8
BREATHING_AMP = 3.0
BREATHING_PHASES = [0, math.pi / 3, 2 * math.pi / 3, math.pi,
                    4 * math.pi / 3, 5 * math.pi / 3, 2 * math.pi]


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

    def __init__(self, color: QColor = RED, parent=None):
        super().__init__(parent)
        self.setFixedSize(7, 7)
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
    """7 vertical bars with spring physics + bar glow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        bar_area_w = int(BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP)
        self.setFixedSize(bar_area_w + 8, 26)  # extra padding for glow

        self._bar_heights = [BAR_MIN_H] * BAR_COUNT
        self._bar_velocities = [0.0] * BAR_COUNT
        self._bar_targets = [BAR_MIN_H] * BAR_COUNT
        self._rms = 0.0
        self._breathing = True
        self._time_start = time.time()

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_rms(self, value: float):
        self._rms = max(0.0, min(value, 1.0))
        if self._rms > 0.02:
            self._breathing = False
            for i in range(BAR_COUNT):
                self._bar_targets[i] = max(
                    BAR_MIN_H,
                    self._rms * BAR_MAX_H * BAR_SCALE_FACTORS[i]
                )
        else:
            self._breathing = True

    def start_animation(self):
        self._time_start = time.time()
        self._timer.start()

    def stop_animation(self):
        self._timer.stop()

    def reset(self):
        self._bar_heights = [BAR_MIN_H] * BAR_COUNT
        self._bar_velocities = [0.0] * BAR_COUNT
        self._bar_targets = [BAR_MIN_H] * BAR_COUNT
        self._rms = 0.0
        self._breathing = True
        self.update()

    def _tick(self):
        elapsed = time.time() - self._time_start
        if self._breathing:
            for i in range(BAR_COUNT):
                self._bar_targets[i] = (
                    BAR_MIN_H + BREATHING_AMP
                    + math.sin(elapsed * BREATHING_FREQ * 2 * math.pi
                               + BREATHING_PHASES[i]) * BREATHING_AMP
                )

        for i in range(BAR_COUNT):
            displacement = self._bar_targets[i] - self._bar_heights[i]
            self._bar_velocities[i] += displacement * SPRING_STIFFNESS
            self._bar_velocities[i] *= SPRING_DAMPING
            self._bar_heights[i] += self._bar_velocities[i]
            self._bar_heights[i] = max(BAR_MIN_H, self._bar_heights[i])

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        total_w = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        start_x = (self.width() - total_w) / 2
        cy = self.height() / 2

        p.setPen(Qt.PenStyle.NoPen)

        for i in range(BAR_COUNT):
            h = self._bar_heights[i]
            x = start_x + i * (BAR_WIDTH + BAR_GAP)
            y = cy - h / 2

            # Soft glow: 3 progressively wider/fainter layers
            for spread, alpha in [(3.0, 18), (2.0, 30), (1.0, 50)]:
                glow = QColor(91, 196, 255, alpha)
                p.setBrush(glow)
                gw = BAR_WIDTH + spread * 2
                gh = h + spread * 2
                gx = x - spread
                gy = y - spread
                glow_path = QPainterPath()
                glow_path.addRoundedRect(gx, gy, gw, gh, gw / 2, gw / 2)
                p.drawPath(glow_path)

            # Solid bar
            p.setBrush(BLUE)
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
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BORDER_HI)
        p.drawRect(0, 0, 1, 14)
        p.end()


# ════════════════════════════════════════════════════════════
#  BLINKING CURSOR
# ════════════════════════════════════════════════════════════

class BlinkingCursor(QWidget):
    """Inline blinking cursor (| character) matching CSS blink animation."""

    def __init__(self, color: QColor = BLUE, parent=None):
        super().__init__(parent)
        self._color = color
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
#  PARTICLE STREAM — connector animation
# ════════════════════════════════════════════════════════════

STREAM_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?-"
STREAM_WIDTH = 160
STREAM_PARTICLE_COUNT = 14


class _StreamParticle:
    """Single glyph that falls from pill to notepad."""

    def __init__(self, canvas_h: float, initial: bool = True):
        self.canvas_h = canvas_h
        self.reset(initial)

    def reset(self, initial: bool = False):
        self.x = STREAM_WIDTH / 2 + (random.random() - 0.5) * 28
        self.y = random.random() * self.canvas_h if initial else -4.0
        self.vy = 3.0 + random.random() * 3.5
        self.alpha = 0.0
        self.target_alpha = 0.4 + random.random() * 0.55
        self.size = 8 + random.random() * 5
        self.glyph = random.choice(STREAM_GLYPHS)
        self.glyph_timer = 0
        self.glyph_interval = 4 + random.randint(0, 7)
        self.trail: list[tuple[float, float, float]] = []
        self.trail_length = 3 + random.randint(0, 2)
        bright = random.random() > 0.8
        self.color = QColor(255, 255, 255) if bright else QColor(91, 196, 255)
        self.glow_color = (QColor(180, 230, 255, 204) if bright
                           else QColor(91, 196, 255, 179))
        self.life = 0
        self.max_life = (self.canvas_h / self.vy) * (0.8 + random.random() * 0.4)

    def update(self):
        self.trail.insert(0, (self.x, self.y, self.alpha))
        if len(self.trail) > self.trail_length:
            self.trail.pop()

        self.y += self.vy
        self.x += (random.random() - 0.5) * 0.4
        self.life += 1

        progress = self.life / max(self.max_life, 1)
        if progress < 0.15:
            self.alpha = (progress / 0.15) * self.target_alpha
        elif progress > 0.75:
            self.alpha = ((1 - progress) / 0.25) * self.target_alpha
        else:
            self.alpha = self.target_alpha

        self.glyph_timer += 1
        if self.glyph_timer >= self.glyph_interval:
            self.glyph = random.choice(STREAM_GLYPHS)
            self.glyph_timer = 0

        if self.y > self.canvas_h + 10 or self.life >= self.max_life:
            self.reset()


class _BurstPacket:
    """Bright dot that shoots down the connector."""

    def __init__(self, canvas_h: float):
        self.canvas_h = canvas_h
        self.x = STREAM_WIDTH / 2 + (random.random() - 0.5) * 10
        self.y = 0.0
        self.vy = 5.5 + random.random() * 4.0
        self.radius = 2 + random.random() * 1.5
        self.alpha = 0.9
        self.done = False

    def update(self):
        self.y += self.vy
        self.alpha -= 0.025
        if self.y > self.canvas_h or self.alpha <= 0:
            self.done = True


class ParticleStreamWidget(QWidget):
    """Canvas-like widget that renders streaming glyphs from pill to notepad.
    Matches the HTML prototype's particle stream animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(STREAM_WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()  # Never visible — rendered by parent's paintEvent
        self._particles: list[_StreamParticle] = []
        self._bursts: list[_BurstPacket] = []
        self._burst_timer = 0
        self._active = False
        self._opacity = 0.0
        self._target_opacity = 0.0
        self._canvas_h = CONNECTOR_HEIGHT + 40

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)  # ~60fps
        self._tick_timer.timeout.connect(self._tick)

    # Animatable opacity
    def _get_stream_opacity(self) -> float:
        return self._opacity

    def _set_stream_opacity(self, val: float):
        self._opacity = val
        self.update()

    stream_opacity = pyqtProperty(float, _get_stream_opacity, _set_stream_opacity)

    def start(self):
        if self._active:
            return
        self._active = True
        h = self._canvas_h
        self._particles = [_StreamParticle(h, initial=True)
                           for _ in range(STREAM_PARTICLE_COUNT)]
        self._bursts.clear()
        self._burst_timer = 0
        self._opacity = 0.0
        self._target_opacity = 1.0
        self._tick_timer.start()

        # Fade in
        self._fade_anim = QPropertyAnimation(self, b"stream_opacity")
        self._fade_anim.setDuration(400)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def stop(self):
        if not self._active:
            return
        self._active = False

        # Fade out then hide
        self._fade_anim = QPropertyAnimation(self, b"stream_opacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.finished.connect(self._on_fade_out_done)
        self._fade_anim.start()

    def _on_fade_out_done(self):
        self._tick_timer.stop()
        self._particles.clear()
        self._bursts.clear()

    def _tick(self):
        h = self._canvas_h
        for pt in self._particles:
            pt.canvas_h = h
            pt.update()

        self._burst_timer += 1
        if self._burst_timer % 40 == 0 and self._active:
            self._bursts.append(_BurstPacket(h))
        self._bursts = [b for b in self._bursts if not b.done]
        for b in self._bursts:
            b.update()

        # Trigger parent repaint (particles rendered in parent's paintEvent)
        if self.parent():
            self.parent().update()

    def render(self, p: QPainter, x: float, y: float, w: float, h: float):
        """Paint particles into an external QPainter at the given rect.
        Called from OverlayWindow.paintEvent BEFORE the pill is drawn,
        so particles appear behind the pill and notepad."""
        if self._opacity < 0.01 or not self._particles:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        cx = x + w / 2

        # Center tube glow line
        p.setOpacity(self._opacity)
        line_grad = QLinearGradient(QPointF(cx, y), QPointF(cx, y + h))
        line_grad.setColorAt(0.0, QColor(91, 196, 255, 0))
        line_grad.setColorAt(0.2, QColor(91, 196, 255, 64))
        line_grad.setColorAt(0.8, QColor(91, 196, 255, 64))
        line_grad.setColorAt(1.0, QColor(91, 196, 255, 0))
        p.setPen(QPen(QBrush(line_grad), 1))
        p.drawLine(QPointF(cx, y), QPointF(cx, y + h))

        x_off = x + (w - STREAM_WIDTH) / 2

        # Draw burst packets (stretched vertically for motion blur)
        p.setPen(Qt.PenStyle.NoPen)
        for b in self._bursts:
            bx = x_off + b.x
            streak_len = b.vy * 4
            for step in range(6):
                frac = step / 5.0
                sy = y + b.y - streak_len * frac
                sa = b.alpha * (1.0 - frac) * 0.4
                p.setOpacity(self._opacity * sa)
                p.setBrush(QColor(180, 230, 255))
                p.drawEllipse(QPointF(bx, sy), b.radius * 2, b.radius * 2)
            p.setOpacity(self._opacity * b.alpha)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(bx, y + b.y), b.radius, b.radius)

        # Draw particles with heavy motion blur
        BLUR_STEPS = 8
        BLUR_SPREAD = 28.0  # px of vertical smear above the glyph

        for pt in self._particles:
            gx = x_off + pt.x - pt.size * 0.3
            gy = y + pt.y

            fnt = QFont("Inter")
            fnt.setPixelSize(int(pt.size))
            fnt.setWeight(QFont.Weight.Medium)
            p.setFont(fnt)

            # Motion blur copies (drawn above the glyph, fading out)
            for step in range(BLUR_STEPS, 0, -1):
                frac = step / BLUR_STEPS
                blur_y = gy - BLUR_SPREAD * frac
                blur_alpha = pt.alpha * (1.0 - frac) * 0.18
                p.setOpacity(self._opacity * blur_alpha)
                p.setPen(QPen(pt.glow_color))
                p.drawText(QPointF(gx, blur_y), pt.glyph)

            # Glow halo (offset copies)
            p.setOpacity(self._opacity * pt.alpha * 0.6)
            p.setPen(QPen(pt.glow_color))
            p.drawText(QPointF(gx - 0.5, gy + 0.5), pt.glyph)
            p.drawText(QPointF(gx + 0.5, gy - 0.5), pt.glyph)

            # Core glyph
            p.setOpacity(self._opacity * pt.alpha * 0.8)
            p.setPen(QPen(pt.color))
            p.drawText(QPointF(gx, gy), pt.glyph)

        p.restore()

    def paintEvent(self, event):
        pass  # Rendering handled by parent's paintEvent via render()


# ════════════════════════════════════════════════════════════
#  NOTEPAD WIDGET
# ════════════════════════════════════════════════════════════

class NotepadWidget(QWidget):
    """Glass card notepad that drops below the pill."""

    editClicked = pyqtSignal()
    retryClicked = pyqtSignal()
    copyCloseClicked = pyqtSignal(str)
    closeClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(NOTEPAD_WIDTH)
        self._target_opacity = 0.0
        self._current_opacity = 0.0
        self._text_scale = 1.0
        self._text_translate_y = 0.0
        self._text_opacity = 1.0
        self._prev_text = ""
        self._build_ui()

    # ── Animatable text properties ─────────────────────────

    def _get_text_scale(self) -> float:
        return self._text_scale

    def _set_text_scale(self, val: float):
        self._text_scale = val
        t = self._text_edit.viewport()
        if t:
            t.update()

    text_scale = pyqtProperty(float, _get_text_scale, _set_text_scale)

    def _get_text_translate_y(self) -> float:
        return self._text_translate_y

    def _set_text_translate_y(self, val: float):
        self._text_translate_y = val
        t = self._text_edit.viewport()
        if t:
            t.update()

    text_translate_y = pyqtProperty(float, _get_text_translate_y, _set_text_translate_y)

    def _get_text_opacity(self) -> float:
        return self._text_opacity

    def _set_text_opacity(self, val: float):
        self._text_opacity = val
        # Map opacity to stylesheet alpha
        alpha = max(0.0, min(1.0, val))
        self._text_edit.setStyleSheet(
            "QTextEdit {"
            "  background: transparent; border: none;"
            f"  padding: 14px 16px; color: rgba(255,255,255,{alpha:.2f});"
            "  selection-background-color: rgba(91,196,255,0.25);"
            "}"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

    text_opacity = pyqtProperty(float, _get_text_opacity, _set_text_opacity)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(
            "border-bottom: 1px solid rgba(255,255,255,0.07); background: transparent;"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 12, 14, 10)

        self._header_dot = PulsingDot(BLUE, header)
        self._header_dot.setFixedSize(5, 5)
        h_layout.addWidget(self._header_dot)

        title = QLabel("VOICETYPE")
        title.setFont(font(10, 600))
        title.setStyleSheet(
            "color: rgba(255,255,255,0.28); letter-spacing: 2.2px; border: none;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.07);"
            "  border-radius: 10px; color: rgba(255,255,255,0.28); font-size: 9px;"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.93); }"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.closeClicked.emit)
        h_layout.addWidget(close_btn)
        layout.addWidget(header)

        # Text area
        self._text_edit = QTextEdit()
        self._text_edit.setFont(font(14))
        self._text_edit.setStyleSheet(
            "QTextEdit {"
            "  background: transparent; border: none;"
            "  padding: 14px 16px; color: rgba(255,255,255,0.93);"
            "  selection-background-color: rgba(91,196,255,0.25);"
            "}"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self._text_edit.setMinimumHeight(80)
        self._text_edit.setMaximumHeight(200)
        self._text_edit.setReadOnly(True)
        layout.addWidget(self._text_edit)

        # Footer
        footer = QWidget()
        footer.setStyleSheet(
            "border-top: 1px solid rgba(255,255,255,0.07); background: transparent;"
        )
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(14, 10, 14, 14)
        f_layout.setSpacing(7)

        btn_style = (
            "QPushButton {"
            "  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.07);"
            "  border-radius: 99px; padding: 5px 12px;"
            "  color: rgba(255,255,255,0.55); font-size: 11px; font-weight: 500;"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.93); }"
        )

        btn_edit = QPushButton("\u270f\ufe0f Edit")
        btn_edit.setStyleSheet(btn_style)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self._on_edit)
        f_layout.addWidget(btn_edit)

        btn_retry = QPushButton("\U0001f504 Retry")
        btn_retry.setStyleSheet(btn_style)
        btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retry.clicked.connect(self.retryClicked.emit)
        f_layout.addWidget(btn_retry)

        self._char_count = QLabel("0 chars")
        self._char_count.setFont(font(10))
        self._char_count.setStyleSheet("color: rgba(255,255,255,0.28); border: none;")
        f_layout.addStretch()
        f_layout.addWidget(self._char_count)

        btn_copy = QPushButton("\U0001f4cb Copy & Close")
        btn_copy.setStyleSheet(
            "QPushButton {"
            "  background: #5bc4ff; border: none; border-radius: 99px;"
            "  padding: 5px 12px; color: rgba(0,0,0,0.85);"
            "  font-size: 11px; font-weight: 600;"
            "}"
            "QPushButton:hover { background: #7dd4ff; }"
        )
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._on_copy_close)
        f_layout.addWidget(btn_copy)

        layout.addWidget(footer)

    def _on_edit(self):
        self._text_edit.setReadOnly(False)
        self._text_edit.setFocus()
        self.editClicked.emit()

    def _on_copy_close(self):
        self.copyCloseClicked.emit(self._text_edit.toPlainText())

    def set_text(self, text: str):
        if text == self._prev_text:
            return
        self._prev_text = text
        self._text_edit.setPlainText(text)
        self._text_edit.setReadOnly(True)
        self._char_count.setText(f"{len(text)} chars")
        self._animate_text_popup()

    def append_word(self, word: str):
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        if cursor.position() > 0:
            cursor.insertText(" ")
        cursor.insertText(word)
        count = len(self._text_edit.toPlainText())
        self._char_count.setText(f"{count} chars")

    def clear_text(self):
        self._text_edit.clear()
        self._char_count.setText("0 chars")

    def get_text(self) -> str:
        return self._text_edit.toPlainText()

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
        self._header_dot.start(speed=0.77)

    def stop_dot_pulse(self):
        self._header_dot.stop()
        self._header_dot.set_color(T3)
        self._header_dot.set_static()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(),
                            RADIUS_CARD, RADIUS_CARD)

        # Fill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GLASS2)
        p.drawPath(path)

        # Border
        p.setPen(QPen(BORDER_HI, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Inner inset glow
        inner = QPainterPath()
        inner.addRoundedRect(1, 1, self.width() - 2, self.height() - 2,
                             RADIUS_CARD - 1, RADIUS_CARD - 1)
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.drawPath(inner)

        # Inner blue glow (matches CSS box-shadow inset)
        p.setPen(Qt.PenStyle.NoPen)
        blue_inner = QColor(91, 196, 255, 13)
        p.setBrush(blue_inner)
        p.drawPath(inner)

        # Top sheen (matches .notepad-inner::before)
        sheen = QLinearGradient(QPointF(14, 0), QPointF(self.width() - 14, 0))
        sheen.setColorAt(0.0, QColor(0, 0, 0, 0))
        sheen.setColorAt(0.3, QColor(255, 255, 255, 26))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 41))
        sheen.setColorAt(0.7, QColor(255, 255, 255, 26))
        sheen.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(sheen)
        p.drawRect(14, 0, self.width() - 28, 1)
        p.end()


# ════════════════════════════════════════════════════════════
#  MAIN OVERLAY WINDOW
# ════════════════════════════════════════════════════════════

class OverlayWindow(QWidget):
    """Pill + connector + notepad system. Always bottom-centre of screen."""

    rms_received = pyqtSignal(float)
    transcript_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = OverlayState.IDLE
        self._widget_opacity = 1.0
        self._timer_seconds = 0
        self._live_words: list[str] = []
        self._pill_translate_y = 0.0
        self._pill_scale = 1.0
        self._notepad_translate_y = -8.0
        self._notepad_opacity = 0.0
        self._connector_h = 0.0
        self._animations: list = []  # keep refs alive

        self._setup_window_flags()
        self._build_widgets()
        self._connect_signals()
        self._start_timer_clock()

        # Start in IDLE (visible but dimmed)
        self._enter_idle(None)

    # ── Animatable properties ────────────────────────────────

    def _get_widget_opacity(self) -> float:
        return self._widget_opacity

    def _set_widget_opacity(self, val: float):
        self._widget_opacity = val
        self.update()

    widget_opacity = pyqtProperty(float, _get_widget_opacity, _set_widget_opacity)

    def _get_pill_translate_y(self) -> float:
        return self._pill_translate_y

    def _set_pill_translate_y(self, val: float):
        self._pill_translate_y = val
        self.update()

    pill_translate_y = pyqtProperty(float, _get_pill_translate_y, _set_pill_translate_y)

    def _get_pill_scale(self) -> float:
        return self._pill_scale

    def _set_pill_scale(self, val: float):
        self._pill_scale = val
        self.update()

    pill_scale = pyqtProperty(float, _get_pill_scale, _set_pill_scale)

    def _get_notepad_opacity(self) -> float:
        return self._notepad_opacity

    def _set_notepad_opacity(self, val: float):
        self._notepad_opacity = val
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
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 20, 20, 20)
        self._main_layout.setSpacing(0)
        self._main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ── PILL ──
        self._pill = QWidget(self)
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
        self._idle_dot = PulsingDot(T4, self._idle_container)
        idle_l.addWidget(self._idle_dot)
        self._idle_label = QLabel("Hold Right \u2325 to record")
        self._idle_label.setFont(font(12, 500))
        self._idle_label.setStyleSheet("color: rgba(255,255,255,0.55);")
        idle_l.addWidget(self._idle_label)
        pill_layout.addWidget(self._idle_container)

        # -- Recording state --
        self._rec_container = QWidget()
        rec_l = QHBoxLayout(self._rec_container)
        rec_l.setContentsMargins(0, 0, 0, 0)
        rec_l.setSpacing(10)
        self._rec_dot = PulsingDot(RED, self._rec_container)
        rec_l.addWidget(self._rec_dot)
        self._waveform = WaveformWidget(self._rec_container)
        rec_l.addWidget(self._waveform)
        self._rec_sep = PillSep(self._rec_container)
        rec_l.addWidget(self._rec_sep)
        self._timer_label = QLabel("0:00")
        self._timer_label.setFont(font(11))
        self._timer_label.setStyleSheet("color: rgba(255,255,255,0.28); letter-spacing: 0.2px;")
        rec_l.addWidget(self._timer_label)
        self._rec_container.hide()
        pill_layout.addWidget(self._rec_container)

        # -- Live transcribing state --
        self._live_container = QWidget()
        live_l = QHBoxLayout(self._live_container)
        live_l.setContentsMargins(0, 0, 0, 0)
        live_l.setSpacing(10)
        self._live_dot = PulsingDot(RED, self._live_container)
        live_l.addWidget(self._live_dot)
        self._live_waveform = WaveformWidget(self._live_container)
        live_l.addWidget(self._live_waveform)
        self._live_sep = PillSep(self._live_container)
        live_l.addWidget(self._live_sep)
        self._live_text = QLabel("")
        self._live_text.setFont(font(12))
        self._live_text.setStyleSheet("color: rgba(255,255,255,0.93);")
        self._live_text.setMaximumWidth(260)
        live_l.addWidget(self._live_text)
        self._live_cursor = BlinkingCursor(BLUE, self._live_container)
        live_l.addWidget(self._live_cursor)
        self._live_container.hide()
        pill_layout.addWidget(self._live_container)

        # -- Notepad pill state (blue dot + label) --
        self._np_pill_container = QWidget()
        np_l = QHBoxLayout(self._np_pill_container)
        np_l.setContentsMargins(0, 0, 0, 0)
        np_l.setSpacing(10)
        self._np_dot = PulsingDot(BLUE, self._np_pill_container)
        np_l.addWidget(self._np_dot)
        self._np_label = QLabel("Tap to edit \u00b7 Right \u2325 to record again")
        self._np_label.setFont(font(12, 500))
        self._np_label.setStyleSheet(f"color: {BLUE.name()};")
        np_l.addWidget(self._np_label)
        self._np_pill_container.hide()
        pill_layout.addWidget(self._np_pill_container)

        # -- Success state --
        self._success_container = QWidget()
        suc_l = QHBoxLayout(self._success_container)
        suc_l.setContentsMargins(0, 0, 0, 0)
        suc_l.setSpacing(10)
        self._success_dot = PulsingDot(GREEN, self._success_container)
        suc_l.addWidget(self._success_dot)
        self._success_label = QLabel("Typed into field")
        self._success_label.setFont(font(12, 500))
        self._success_label.setStyleSheet(f"color: {GREEN.name()};")
        suc_l.addWidget(self._success_label)
        self._success_container.hide()
        pill_layout.addWidget(self._success_container)

        # Pill drop shadow (matches CSS box-shadow: 0 8px 32px rgba(0,0,0,0.55))
        self._pill_shadow = QGraphicsDropShadowEffect(self._pill)
        self._pill_shadow.setBlurRadius(32)
        self._pill_shadow.setOffset(0, 8)
        self._pill_shadow.setColor(QColor(0, 0, 0, 140))
        self._pill.setGraphicsEffect(self._pill_shadow)

        self._main_layout.addWidget(self._pill, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── CONNECTOR + PARTICLE STREAM ──
        self._connector = QWidget(self)
        self._connector.setFixedSize(1, 0)
        self._connector.setStyleSheet("background: transparent;")
        self._main_layout.addWidget(self._connector, 0, Qt.AlignmentFlag.AlignHCenter)

        self._particle_stream = ParticleStreamWidget(self)

        # ── NOTEPAD ──
        self._notepad = NotepadWidget(self)
        self._notepad.hide()
        self._main_layout.addWidget(self._notepad, 0, Qt.AlignmentFlag.AlignHCenter)

        self._pill.adjustSize()
        self.adjustSize()

    def _connect_signals(self):
        self.rms_received.connect(
            self._on_rms, Qt.ConnectionType.QueuedConnection
        )
        self.transcript_received.connect(
            self._on_transcript_update, Qt.ConnectionType.QueuedConnection
        )
        self._notepad.copyCloseClicked.connect(self._on_copy_close)
        self._notepad.closeClicked.connect(lambda: self.transition_to(OverlayState.IDLE))

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
        self.move(x, y)

    # ── Pill shadow ───────────────────────────────────────────

    def _set_pill_shadow_idle(self):
        """Idle/success: subtle dark shadow only (CSS: 0 4px 16px rgba(0,0,0,0.40))."""
        self._pill_shadow.setBlurRadius(16)
        self._pill_shadow.setOffset(0, 4)
        self._pill_shadow.setColor(QColor(0, 0, 0, 102))

    def _set_pill_shadow_active(self):
        """Active states: larger shadow + blue glow (CSS: 0 8px 32px ..., 0 0 24px blue)."""
        self._pill_shadow.setBlurRadius(32)
        self._pill_shadow.setOffset(0, 8)
        self._pill_shadow.setColor(QColor(0, 0, 0, 140))

    # ── Particle stream ────────────────────────────────────

    def _update_particle_canvas(self):
        """Update the particle stream's canvas height to match the connector."""
        self._particle_stream._canvas_h = CONNECTOR_HEIGHT + 40

    # ── Animation helpers ───────────────────────────────────

    def _stop_animations(self):
        for anim in self._animations:
            if hasattr(anim, 'stop'):
                anim.stop()
        self._animations.clear()

    def _animate_pill_entrance(self):
        """Matches CSS pillIn: translateY(16px) scale(0.88) → 0 / 1, 450ms."""
        self._pill_translate_y = 16.0
        self._pill_scale = 0.88
        self._widget_opacity = 0.0

        group = QParallelAnimationGroup(self)

        ty_anim = QPropertyAnimation(self, b"pill_translate_y")
        ty_anim.setDuration(450)
        ty_anim.setStartValue(16.0)
        ty_anim.setEndValue(0.0)
        ty_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(ty_anim)

        sc_anim = QPropertyAnimation(self, b"pill_scale")
        sc_anim.setDuration(450)
        sc_anim.setStartValue(0.88)
        sc_anim.setEndValue(1.0)
        sc_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(sc_anim)

        op_anim = QPropertyAnimation(self, b"widget_opacity")
        op_anim.setDuration(320)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(op_anim)

        self._animations.append(group)
        group.start()

    def _animate_notepad_open(self):
        """Matches CSS notepad.open: opacity 0→1, translateY(-8→0).
        Plus connector height 0→56."""
        group = QParallelAnimationGroup(self)

        # Connector height (450ms to match CSS)
        ch_anim = QPropertyAnimation(self, b"connector_h")
        ch_anim.setDuration(450)
        ch_anim.setStartValue(0.0)
        ch_anim.setEndValue(float(CONNECTOR_HEIGHT))
        ch_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(ch_anim)

        # Notepad opacity
        no_anim = QPropertyAnimation(self, b"notepad_opacity")
        no_anim.setDuration(350)
        no_anim.setStartValue(0.0)
        no_anim.setEndValue(1.0)
        no_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(no_anim)

        # Notepad translateY
        nt_anim = QPropertyAnimation(self, b"notepad_translate_y")
        nt_anim.setDuration(400)
        nt_anim.setStartValue(-8.0)
        nt_anim.setEndValue(0.0)
        nt_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(nt_anim)

        self._animations.append(group)
        group.start()

    def _animate_notepad_close(self):
        """Reverse of open — fade out + slide up."""
        self._particle_stream.stop()
        group = QParallelAnimationGroup(self)

        ch_anim = QPropertyAnimation(self, b"connector_h")
        ch_anim.setDuration(ANIM_EXIT)
        ch_anim.setStartValue(self._connector_h)
        ch_anim.setEndValue(0.0)
        ch_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(ch_anim)

        no_anim = QPropertyAnimation(self, b"notepad_opacity")
        no_anim.setDuration(ANIM_EXIT)
        no_anim.setStartValue(self._notepad_opacity)
        no_anim.setEndValue(0.0)
        no_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(no_anim)

        nt_anim = QPropertyAnimation(self, b"notepad_translate_y")
        nt_anim.setDuration(ANIM_EXIT)
        nt_anim.setStartValue(0.0)
        nt_anim.setEndValue(-8.0)
        nt_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(nt_anim)

        group.finished.connect(self._on_notepad_closed)
        self._animations.append(group)
        group.start()

    def _on_notepad_closed(self):
        self._notepad.hide()
        self._connector.setFixedHeight(0)
        self.adjustSize()
        self._reposition()

    def _animate_exit_success(self):
        """Exit: scale 1→0.96, opacity 1→0, translateY +20px, 280ms InCubic."""
        group = QParallelAnimationGroup(self)

        sc_anim = QPropertyAnimation(self, b"pill_scale")
        sc_anim.setDuration(ANIM_EXIT)
        sc_anim.setStartValue(1.0)
        sc_anim.setEndValue(0.96)
        sc_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(sc_anim)

        op_anim = QPropertyAnimation(self, b"widget_opacity")
        op_anim.setDuration(ANIM_EXIT)
        op_anim.setStartValue(1.0)
        op_anim.setEndValue(0.0)
        op_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(op_anim)

        ty_anim = QPropertyAnimation(self, b"pill_translate_y")
        ty_anim.setDuration(ANIM_EXIT)
        ty_anim.setStartValue(0.0)
        ty_anim.setEndValue(20.0)
        ty_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(ty_anim)

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

    def _hide_all_pill_states(self):
        self._idle_container.hide()
        self._rec_container.hide()
        self._live_container.hide()
        self._np_pill_container.hide()
        self._success_container.hide()
        self._waveform.stop_animation()
        self._live_waveform.stop_animation()
        self._rec_dot.stop()
        self._live_dot.stop()
        self._np_dot.stop()
        self._success_dot.stop()
        self._idle_dot.stop()
        self._live_cursor.stop()
        self._clock_timer.stop()

    def _hide_notepad_instant(self):
        self._connector.setFixedHeight(0)
        self._connector_h = 0.0
        self._notepad_opacity = 0.0
        self._notepad_translate_y = -8.0
        self._notepad.hide()
        self._particle_stream.stop()

    def _enter_idle(self, from_state, **kwargs):
        self._stop_animations()
        self._hide_all_pill_states()

        # If coming from a state with notepad, animate it closed
        if from_state in (OverlayState.LIVE_TRANSCRIBING, OverlayState.RESULT_NOTEPAD):
            self._animate_notepad_close()
        else:
            self._hide_notepad_instant()

        self._idle_container.show()
        self._idle_dot.set_color(T4)
        self._idle_dot.set_static()
        self._set_pill_shadow_idle()

        self._pill.adjustSize()
        self.show()
        self._reposition()

        # First show or coming back from success — animate pill in
        if from_state is None or from_state == OverlayState.RESULT_FIELD:
            self._animate_pill_entrance()
        else:
            # Smooth cross-fade for other transitions
            self._pill_translate_y = 0.0
            self._pill_scale = 1.0
            self._widget_opacity = 1.0

    def _enter_recording(self, from_state, **kwargs):
        self._stop_animations()
        self._hide_all_pill_states()
        self._hide_notepad_instant()

        self._rec_container.show()
        self._rec_dot.start(speed=1.1)
        self._waveform.start_animation()
        self._set_pill_shadow_active()
        self._timer_seconds = 0
        self._timer_label.setText("0:00")
        self._clock_timer.start()
        self._live_words = []

        self._pill.adjustSize()
        self.show()
        self._reposition()

        # Entrance animation from idle or first show
        if from_state in (None, OverlayState.IDLE):
            self._animate_pill_entrance()

    def _enter_live_transcribing(self, from_state, **kwargs):
        self._stop_animations()
        self._hide_all_pill_states()

        self._live_container.show()
        self._live_dot.start(speed=1.1)
        self._live_waveform.start_animation()
        self._live_text.setText("")
        self._live_cursor.start()
        self._set_pill_shadow_active()

        # Transfer waveform RMS from recording
        self._live_waveform.set_rms(self._waveform._rms)

        # Keep timer running
        self._clock_timer.start()

        # Show notepad with animation
        self._notepad.show()
        self._notepad.clear_text()
        self._notepad.start_dot_pulse()

        self._pill.adjustSize()
        self.adjustSize()
        self._reposition()

        # Animate notepad dropping down + start particle stream
        self._animate_notepad_open()
        self._update_particle_canvas()
        self._particle_stream.start()

    def _enter_result_field(self, from_state, text: str = "", **kwargs):
        self._stop_animations()
        self._hide_all_pill_states()

        # If coming from live, close notepad
        if from_state in (OverlayState.LIVE_TRANSCRIBING, OverlayState.RESULT_NOTEPAD):
            self._animate_notepad_close()
        else:
            self._hide_notepad_instant()

        self._success_container.show()
        self._success_dot.set_color(GREEN)
        self._success_dot.set_static()
        self._set_pill_shadow_idle()

        self._pill.adjustSize()
        self._reposition()

        # Auto-dismiss: exit animation then back to idle
        def _start_exit():
            if self._state == OverlayState.RESULT_FIELD:
                self._animate_exit_success()
                QTimer.singleShot(ANIM_EXIT + 50, self._finish_success_exit)

        QTimer.singleShot(2200, _start_exit)

    def _finish_success_exit(self):
        if self._state == OverlayState.RESULT_FIELD:
            self.transition_to(OverlayState.IDLE)

    def _enter_result_notepad(self, from_state, text: str = "", **kwargs):
        self._stop_animations()
        self._hide_all_pill_states()

        self._np_pill_container.show()
        self._np_dot.set_color(BLUE)
        self._np_dot.start(speed=0.7)
        self._live_cursor.stop()
        self._set_pill_shadow_active()

        # Stop particle stream (text has arrived)
        self._particle_stream.stop()

        # Show notepad with final text
        self._notepad.set_text(text)
        self._notepad.stop_dot_pulse()
        self._notepad.show()

        # If notepad was already open (from live), just update
        if from_state == OverlayState.LIVE_TRANSCRIBING:
            self._connector_h = float(CONNECTOR_HEIGHT)
            self._connector.setFixedHeight(CONNECTOR_HEIGHT)
            self._notepad_opacity = 1.0
            self._notepad_translate_y = 0.0
        else:
            self._animate_notepad_open()

        self._pill.adjustSize()
        self.adjustSize()
        self._reposition()

    # ── Painting ─────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._widget_opacity)

        # ── Particle stream (painted FIRST so it appears behind pill/notepad) ──
        conn_rect = self._connector.geometry()
        if self._particle_stream._opacity > 0.01 and conn_rect.height() > 0:
            stream_h = conn_rect.height() + 40
            stream_x = (self.width() - STREAM_WIDTH) / 2
            stream_y = conn_rect.y() - 20
            self._particle_stream.render(p, stream_x, stream_y,
                                         float(STREAM_WIDTH), float(stream_h))
            p.setOpacity(self._widget_opacity)  # restore after particle render

        pill_rect = self._pill.geometry()

        # Apply pill transforms
        pill_cx = pill_rect.x() + pill_rect.width() / 2
        pill_cy = pill_rect.y() + pill_rect.height() / 2
        p.save()
        p.translate(pill_cx, pill_cy + self._pill_translate_y)
        p.scale(self._pill_scale, self._pill_scale)
        p.translate(-pill_cx, -pill_cy)

        # Pill fill
        pill_path = QPainterPath()
        pill_path.addRoundedRect(
            float(pill_rect.x()), float(pill_rect.y()),
            float(pill_rect.width()), float(pill_rect.height()),
            RADIUS_PILL, RADIUS_PILL
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(GLASS)
        p.drawPath(pill_path)

        # Pill border (dimmer for idle/success, brighter otherwise)
        is_dim = self._state in (OverlayState.IDLE, OverlayState.RESULT_FIELD)
        border_color = BORDER if is_dim else BORDER_HI
        p.setPen(QPen(border_color, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(pill_path)

        # Inner inset highlight
        inner_path = QPainterPath()
        inner_path.addRoundedRect(
            float(pill_rect.x()) + 1, float(pill_rect.y()) + 1,
            float(pill_rect.width()) - 2, float(pill_rect.height()) - 2,
            RADIUS_PILL, RADIUS_PILL
        )
        p.setPen(QPen(QColor(255, 255, 255, 9), 1))
        p.drawPath(inner_path)

        # Pill top sheen (matches .pill::before)
        p.setPen(Qt.PenStyle.NoPen)
        sheen = QLinearGradient(
            QPointF(pill_rect.x() + 16, pill_rect.y()),
            QPointF(pill_rect.right() - 16, pill_rect.y()),
        )
        sheen.setColorAt(0.0, QColor(0, 0, 0, 0))
        sheen.setColorAt(0.4, QColor(255, 255, 255, 56))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 71))
        sheen.setColorAt(0.6, QColor(255, 255, 255, 56))
        sheen.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(sheen)
        p.drawRect(pill_rect.x() + 16, pill_rect.y(), pill_rect.width() - 32, 1)

        p.restore()

        # Connector gradient line (1px, fades at both ends)
        conn_rect = self._connector.geometry()
        if conn_rect.height() > 0:
            cx = conn_rect.center().x()
            conn_grad = QLinearGradient(
                QPointF(cx, conn_rect.y()),
                QPointF(cx, conn_rect.bottom()),
            )
            conn_grad.setColorAt(0.0, QColor(91, 196, 255, 0))
            conn_grad.setColorAt(0.4, QColor(91, 196, 255, 128))
            conn_grad.setColorAt(0.6, QColor(91, 196, 255, 128))
            conn_grad.setColorAt(1.0, QColor(91, 196, 255, 0))
            p.setPen(QPen(QBrush(conn_grad), 1))
            p.drawLine(QPointF(cx, conn_rect.y()),
                       QPointF(cx, conn_rect.bottom()))

        # Notepad with opacity + translate
        if self._notepad.isVisible() and self._notepad_opacity > 0.01:
            p.setOpacity(self._widget_opacity * self._notepad_opacity)
            # The notepad widget paints itself via its own paintEvent,
            # but we apply the opacity transform here for the fade effect.

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
