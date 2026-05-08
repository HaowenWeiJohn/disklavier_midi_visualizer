# MIDI canvas

The MIDI canvas is the falling-keys piano roll at the centre of the main window. Notes scroll from the top of the canvas (future) toward a horizontal red playhead near the bottom (now), and a fixed 88-key piano keyboard is drawn below the falling notes.

The canvas is implemented as `MidiCanvasWidget` in `disklavier_visualizer/ui/midi_canvas.py:87`, wrapped by a thin container `MidiPanelWidget` (`midi_canvas.py:356`) that adds an info label below the canvas. The main window holds the `MidiPanelWidget`; the canvas itself is exposed via the `panel.canvas` property.

## Coverage

- Pitch range: **MIDI 21 (A0) to 108 (C8)** — the full 88-key piano (`MIN_PITCH = 21`, `MAX_PITCH = 108`).
- Notes outside that range are silently skipped during paint.
- Keyboard strip: **40 px tall** at the bottom of the canvas (`PIANO_HEIGHT = 40`).
- Playhead line sits at **97 %** of the canvas height (just above the keyboard, `_playhead_frac = 0.97`).
- Source: only `pretty_midi.PrettyMIDI(filepath).instruments[0].notes` (the first track). Other tracks are ignored.

## Note colouring (velocity colormap)

Notes are coloured by their MIDI velocity, interpolated linearly across four anchor stops:

| Velocity | Colour | RGB |
|---|---|---|
| 0 | soft blue | `(60, 100, 200)` |
| 64 | green | `(60, 200, 100)` |
| 100 | yellow | `(255, 200, 50)` |
| 127 | loud red | `(255, 60, 60)` |

The interpolation is piecewise-linear in RGB space (`_velocity_color` in `midi_canvas.py:42`). A velocity of `82` falls in the `64 → 100` segment and gets `(t = 18/36 = 0.5)` between green and yellow.

The note is drawn as a filled rectangle with a slightly darker outline (`color.darker(130)`). When a note is **hovered**, the outline switches to a 2 px white border instead.

## Time axis

- Notes fall from top (future) to bottom (past); the playhead is at `97 %` from the top.
- **Grid lines** are drawn every **0.5 s** by default. At wider zooms the interval widens:

    | Viewport (`_seconds_per_viewport`) | Grid interval |
    |---|---|
    | ≤ 10 s | 0.5 s |
    | 10–20 s | 1 s |
    | > 20 s | 2 s |

- Tick labels (e.g. `12.5s`) are drawn 2 px in from the left edge of each grid line, rendered in 7-pt monospace.

The math behind the y-axis (`_time_to_y`):

```
canvas_height = self.height() - PIANO_HEIGHT
playhead_y    = canvas_height * 0.97
pixels_per_s  = canvas_height / seconds_per_viewport
y(t)          = playhead_y - (t - current_time) * pixels_per_s
```

A note at the playhead time has its bottom at `playhead_y`; future notes are higher up; past notes have already scrolled off below the playhead.

## Pitch axis

Each pitch occupies a fixed-width vertical column:

```
key_width = canvas_width / 88
x(pitch)  = (pitch - MIN_PITCH) * key_width
```

Octave separators (vertical lines at every C, faint colour `(50, 50, 55)`) are drawn full-height of the falling-notes area for easier orientation.

## Auto-seek on load

When `load_midi(adapter)` is called:

1. The note list is rebuilt from `adapter.notes`, sorted by start time, into four parallel arrays (`starts`, `ends`, `pitches`, `velocities`) inside a `NoteData` helper.
2. The viewport is reset to **5 s** regardless of any prior zoom.
3. The playhead **auto-seeks to the first note's start time** (or 0.0 if the file has no notes). This matches the reference project's behaviour and prevents staring at empty space at the top of files with leading silence.
4. `position_changed` is emitted so the slider sees the new position.

## Visibility window

For each repaint the canvas computes `[t_bottom, t_top]` (the time range visible on screen) and asks `NoteData.visible_range` for the index range of notes intersecting that window. The implementation uses `bisect` on the sorted `starts` array, then walks back to catch notes that started before `t_bottom` but extend into the window:

```python
i_start = bisect.bisect_left(self.starts, t_min)
while i_start > 0 and self.ends[i_start - 1] > t_min:
    i_start -= 1
i_end = bisect.bisect_right(self.starts, t_max)
return range(i_start, i_end)
```

This means **rendering cost scales with the visible note count, not the total file size** — even very long Disklavier recordings repaint instantly.

## Interactions

### Drag (scrub)

Left-mouse press on the canvas captures a drag-start `(y, current_time)` snapshot. Subsequent `mouseMoveEvent`s while held update the playhead by `dt = dy / pixels_per_second`, where `dy` is the delta from the press position.

- Dragging **down** moves forward in time (notes fall, playhead advances).
- Dragging **up** moves backward.
- Drag speed scales naturally with zoom because `pixels_per_second` is recomputed every move.

The press emits `user_interacted`; the move emits `position_changed` via `set_position`.

### Wheel (zoom)

`wheelEvent` reads `event.angleDelta().y()`:

- Wheel up (positive delta) → factor `0.8` (zoom in — fewer seconds visible).
- Wheel down (negative delta) → factor `1.25` (zoom out — more seconds visible).
- Clamped to **`[0.5, 60.0]`** seconds-per-viewport.

Zooming emits `user_interacted` but **not** `position_changed` — the playhead time doesn't change, only the visible window around it.

The slider is unaffected by zoom; its range stays at `0 .. duration_ms` regardless of the canvas's current viewport.

### Double-click a note

Left-double-click on a visible note snaps the playhead to that note's **start** time. The implementation cancels any in-progress drag from the preceding press first (`self._dragging = False`) so a tiny pixel jitter between press and double-click can't yank the playhead back via `mouseMoveEvent`.

Double-click on empty space (no note under the cursor) is a no-op — the event passes through to `super().mouseDoubleClickEvent`.

The hit-test (`_note_index_at`) iterates `visible_range` in reverse so the **topmost** visible note at the click point wins (matching what's drawn on top).

### Hover

Mouse motion over a note (with no button held) updates `_hover_index` and triggers a repaint so the hovered note gets its 2 px white outline. Moving off the canvas (`leaveEvent`) clears the hover.

Hover is purely visual feedback — there is no tooltip with note metadata.

## Arrow-key stepping

The canvas does not register the arrow-key shortcuts itself; the **main window** does (see [Main window → Keyboard shortcuts](main-window.md#keyboard-shortcuts)). When fired, they call `MidiPanelWidget.step_ticks(±1)` or `step_ticks(±100)`, which delegates to `self._canvas.step_ticks`:

```python
def step_ticks(self, ticks: int):
    self.set_position(self._current_time + ticks * self._time_resolution)
```

`time_resolution` is `seconds_per_tick` derived from the file's tempo and ticks-per-beat. For a 120 BPM file at 480 ticks/beat, one tick is `60/120/480 ≈ 1.04 ms`. For Disklavier-typical 1920 ticks/beat, ticks are quarter-millisecond — only visible at very high zoom.

`set_position` clamps to `[0, duration]`, so the arrow keys don't drag past the file boundaries.

## Keyboard strip

Drawn by `_draw_piano(painter, y_offset)`:

- White keys first, as full-height (`PIANO_HEIGHT = 40`) light rectangles with faint grey outlines.
- Black keys on top, narrower (70 % of `key_width`) and shorter (65 % of `PIANO_HEIGHT`), in a near-black fill with no outline.
- C-octave labels (`C1`, `C2`, …, `C8`) drawn in 6-pt sans-serif at each C key in the lower-right area of the keyboard strip.

The keyboard is purely **informational** — clicking on it does nothing (there is no `mousePressEvent` distinction between the falling-notes area and the keyboard strip; clicks below the playhead simply have a different y-to-time mapping).

## Empty-state

Before any MIDI is loaded (`self._adapter is None`):

- The whole canvas is filled with the background colour (`(30, 30, 35)`).
- Centred white text reads `No MIDI loaded`.
- The info label below reads `No MIDI loaded`.

## Info label (panel container)

The `MidiPanelWidget` adds a centred `QLabel` below the canvas that updates every time the playhead moves:

```
Time: 192.847s / 261.5s  |  Tick: 370266
```

- `Time` is the current playhead in seconds, then the file duration in seconds.
- `Tick` is the current playhead expressed in MIDI ticks (`int(current_time * sample_rate)`), where `sample_rate = 1 / time_resolution`.

When no MIDI is loaded, the label reads `No MIDI loaded`.

## Public API (signals)

Both the panel and the canvas expose the same signals — the panel just forwards.

| Signal | When |
|---|---|
| `position_changed(float)` | Whenever the playhead moves (drag, arrow keys, double-click, programmatic `set_position`). |
| `user_interacted()` | Direct user input only — left-mouse press or wheel. **Not** emitted on programmatic updates from the slider or anchor table. |

## Public API (methods)

| Method | Purpose |
|---|---|
| `load_midi(adapter: MidiAdapter)` | Replace the displayed MIDI. Resets viewport to 5 s and auto-seeks to the first note. |
| `set_position(time_seconds: float)` | Move the playhead. Clamps to `[0, duration]`. Suppresses re-emit if the time is unchanged. |
| `step_ticks(ticks: int)` | Step by `ticks * time_resolution` seconds. |
| `current_time` (property, panel) | Read-only float, current playhead in seconds. |
| `canvas` (property, panel) | The underlying `MidiCanvasWidget`. |
| `canvas.adapter` (property) | The current `MidiAdapter` or `None`. Used by the main window to gate "save anchors" / "add anchor" actions. |
