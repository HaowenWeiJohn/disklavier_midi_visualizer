"""Timeline scrubber widget for the visualizer.

A horizontal QSlider plus a label. Two-way binds with the canvas:
- User drag/click → emits position_changed
- Programmatic set_position → updates value with signals blocked, no echo
"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QWidget,
)


def _format_mmss(seconds: float) -> str:
    """Format seconds as MM:SS.mmm."""
    if seconds < 0:
        seconds = 0.0
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:06.3f}"


class _ClickJumpSlider(QSlider):
    """QSlider variant where clicking the trough jumps the thumb directly."""

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            handle = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self
            )
            if not handle.contains(event.pos()):
                groove = self.style().subControlRect(
                    QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
                )
                if self.orientation() == Qt.Horizontal:
                    pos = event.pos().x() - groove.x()
                    span = groove.width()
                else:
                    pos = event.pos().y() - groove.y()
                    span = groove.height()
                value = QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(), pos, span, opt.upsideDown
                )
                self.setValue(value)
        super().mousePressEvent(event)


class TimelineSliderWidget(QWidget):
    """Horizontal scrubber that emits position_changed on user input only.

    Internally the slider uses integer milliseconds. set_position is the
    programmatic setter and uses blockSignals(True) so it does not echo back
    through valueChanged.
    """

    position_changed = pyqtSignal(float)  # seconds; emitted only for user input

    def __init__(self, parent=None):
        super().__init__(parent)

        self._duration = 0.0
        self._position = 0.0

        self._slider = _ClickJumpSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setSingleStep(10)
        self._slider.setPageStep(1000)
        self._slider.setTracking(True)
        self._slider.setEnabled(False)
        self._slider.valueChanged.connect(self._on_slider_value_changed)

        self._label = QLabel(_format_mmss(0) + " / " + _format_mmss(0))
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        # Fixed-width font keeps the label from jittering as digits change
        font = self._label.font()
        font.setFamily("monospace")
        self._label.setFont(font)
        self._label.setMinimumWidth(160)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self._slider, stretch=1)
        layout.addWidget(self._label)

    def set_duration(self, seconds: float):
        self._duration = max(0.0, float(seconds))
        max_ms = int(round(self._duration * 1000))
        self._slider.blockSignals(True)
        self._slider.setRange(0, max_ms)
        self._slider.setEnabled(self._duration > 0)
        # Clamp current position into the new range
        self._position = min(self._position, self._duration)
        self._slider.setValue(int(round(self._position * 1000)))
        self._slider.blockSignals(False)
        self._update_label()

    def set_position(self, seconds: float):
        """Programmatic position update; suppresses valueChanged echo."""
        self._position = max(0.0, min(float(seconds), self._duration))
        ms = int(round(self._position * 1000))
        self._slider.blockSignals(True)
        self._slider.setValue(ms)
        self._slider.blockSignals(False)
        self._update_label()

    def _on_slider_value_changed(self, ms: int):
        self._position = ms / 1000.0
        self._update_label()
        self.position_changed.emit(self._position)

    def _update_label(self):
        self._label.setText(
            f"{_format_mmss(self._position)} / {_format_mmss(self._duration)}"
        )
