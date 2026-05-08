# Timeline slider

The timeline slider is the horizontal scrubber strip below the canvas. It is implemented as `TimelineSliderWidget` in `disklavier_visualizer/ui/timeline_slider.py:57`, with a custom `_ClickJumpSlider` subclass (`timeline_slider.py:30`) for click-to-jump behaviour.

## Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━  03:12.847 / 04:21.500 │
└────────────────────────────────────────────────────────────────────────┘
   ↑ slider (stretch=1)                              ↑ MM:SS.mmm label
```

A `QHBoxLayout` with 8 px horizontal margins and 4 px vertical margins. The slider takes all the horizontal space; the label is fixed at a minimum width of **160 px** so its monospace text doesn't shift the slider as digits change.

## Internal units

The slider uses **integer milliseconds** internally:

| Value | Meaning |
|---|---|
| `setRange(0, 0)` | Initial state — disabled, no MIDI |
| `setRange(0, int(round(duration * 1000)))` | After `set_duration` |
| `setSingleStep(10)` | One arrow-key press = 10 ms |
| `setPageStep(1000)` | Page-up / page-down = 1000 ms |
| `setTracking(True)` | `valueChanged` fires continuously while dragging |

The `position_changed(float)` signal exposed externally is in **seconds** (`ms / 1000.0`), so external code never has to know about the millisecond granularity.

## Time format

The label uses `_format_mmss`:

```python
def _format_mmss(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:06.3f}"
```

Examples:

| Seconds | Formatted |
|---|---|
| `0.0` | `00:00.000` |
| `3.5` | `00:03.500` |
| `192.847` | `03:12.847` |
| `261.5` | `04:21.500` |

The label always shows `current / total`. Both halves use the same format.

The font family is set to `monospace` after construction so the digits stay aligned as they update; otherwise on most systems Qt's default proportional font would jitter the layout horizontally as digits widen and narrow.

## Interactions

### Drag the thumb

Standard `QSlider` drag — press and hold the thumb, drag horizontally. With `setTracking(True)`, `valueChanged(int ms)` fires on every mouse-move tick, so the canvas updates in real time, not just on release.

### Click the trough

Vanilla `QSlider` only **page-steps** when you click the trough (a click jumps the thumb by one page step toward the click, not directly to the click). The custom `_ClickJumpSlider` overrides `mousePressEvent` to convert a trough click directly into a thumb position:

```python
if event.button() == Qt.LeftButton:
    handle = subControlRect(SC_SliderHandle)
    if not handle.contains(event.pos()):
        groove = subControlRect(SC_SliderGroove)
        pos = event.pos().x() - groove.x()
        span = groove.width()
        value = QStyle.sliderValueFromPosition(min, max, pos, span, opt.upsideDown)
        self.setValue(value)
super().mousePressEvent(event)
```

After the override sets the value, the parent `mousePressEvent` is still called, so the user can immediately drag from the new position without releasing the button.

### Disabled state

The slider is disabled (`setEnabled(False)`) when `duration == 0` (no MIDI loaded). Clicking or dragging in that state has no effect; the trough renders greyed-out.

`set_duration` is called by the main window from `_open_midi` after a successful parse:

```python
self._slider.set_duration(adapter.duration)
```

This expands the range to `[0, duration_ms]` and enables the slider.

## Two-way bind without echo

The slider is wired bidirectionally with the canvas:

```
canvas.position_changed → slider.set_position
slider.position_changed → canvas.set_position
```

If both `set_position`s emitted `position_changed`, a single user action would bounce forever. The slider breaks the loop with `blockSignals` around the internal `setValue`:

```python
def set_position(self, seconds: float):
    self._position = max(0.0, min(float(seconds), self._duration))
    ms = int(round(self._position * 1000))
    self._slider.blockSignals(True)
    self._slider.setValue(ms)
    self._slider.blockSignals(False)
    self._update_label()
```

`set_position` is the **programmatic** path — it never emits `position_changed`.

`_on_slider_value_changed`, on the other hand, **does** emit:

```python
def _on_slider_value_changed(self, ms: int):
    self._position = ms / 1000.0
    self._update_label()
    self.position_changed.emit(self._position)
```

This is wired to the slider's `valueChanged` signal, which only fires for genuine user input (because programmatic `setValue` calls happen with signals blocked).

The canvas uses a different but equivalent pattern: an early-return when the new position equals the current. Either way, a single user action settles in one event-loop tick.

## set_duration: rounding and clamping

```python
def set_duration(self, seconds: float):
    self._duration = max(0.0, float(seconds))
    max_ms = int(round(self._duration * 1000))
    self._slider.blockSignals(True)
    self._slider.setRange(0, max_ms)
    self._slider.setEnabled(self._duration > 0)
    self._position = min(self._position, self._duration)
    self._slider.setValue(int(round(self._position * 1000)))
    self._slider.blockSignals(False)
    self._update_label()
```

Note the explicit:

- `max(0.0, ...)` — negative durations are coerced to 0.
- `min(self._position, self._duration)` — if a previous file had a longer duration, the position is clamped into the new range so the slider thumb doesn't disappear off the right edge.
- `blockSignals(True/False)` around both `setRange` and `setValue` to avoid an echo through `valueChanged`.

## Public API

### Signals

| Signal | When |
|---|---|
| `position_changed(float)` | User-driven slider drag or trough click. **Not** emitted on programmatic `set_position` or `set_duration`. Emits seconds, not milliseconds. |

### Methods

| Method | Purpose |
|---|---|
| `set_duration(seconds: float)` | Set the maximum scrubbable time. Enables/disables the slider. Clamps current position. |
| `set_position(seconds: float)` | Set the thumb position without re-emitting. Used by the canvas → slider bind. |

There are **no** read-only properties for current position or duration — the main window doesn't need them (it tracks the playhead via the canvas, which is the source of truth).

## Edge cases

- **Sub-millisecond precision is lost.** The slider rounds to the nearest millisecond, so a canvas tick step of 0.5 ms might quantize to a 1 ms or 0 ms slider movement. This is invisible at the slider's pixel resolution but is the reason the canvas keeps its own float `_current_time` rather than reading back from the slider.
- **Files longer than ~24 days overflow `int32`.** `setRange` accepts `int`, and Qt internally uses `int32` for slider values. A 24-day MIDI file (≈ 2.1 billion ms) is well past Qt's slider range. Disklavier recordings are minutes long, so this is purely theoretical, but worth noting if you ever try to visualize a multi-day stitched MIDI.
- **Duration changes while the user is dragging.** Not possible in the current UI: `set_duration` is only called on file load, and the user can't drag the slider while a file dialog is open.
