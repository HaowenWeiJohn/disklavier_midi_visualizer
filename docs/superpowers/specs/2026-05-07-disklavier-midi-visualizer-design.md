# Disklavier MIDI Visualizer — Design

**Date:** 2026-05-07
**Status:** Approved (pending implementation plan)
**Reference project:** `C:\Users\haowe\OneDrive\Desktop\MIT\midi_camera_alignment_tool`

## 1. Goal

A small desktop application that lets the user pick a single Disklavier MIDI file (`.mid`) and inspect it visually with a falling-keys piano-roll renderer. Notes are colored by velocity. The user can scrub through the file by dragging the canvas, dragging a timeline slider at the bottom, or pressing arrow keys; they can zoom by scrolling. No annotation, no audio playback, no camera, no alignment — pure visualization.

The visualization view, drag/zoom interactions, keyboard rendering, and velocity colormap should match the MIDI panel in the reference `midi_camera_alignment_tool` exactly. The new addition relative to the reference is a horizontal timeline slider at the bottom of the window that two-way-binds with the canvas playhead.

## 2. Non-goals

- No annotations of any kind (no markers, anchors, labels, tags).
- No audio synthesis or MIDI playback (no time auto-advance, no play/pause).
- No camera or video integration.
- No alignment, sync, or anchor workflows.
- No multi-file workflow — one file at a time, picked via `File > Open`.
- No persistence across sessions (no recent-files list, no last-opened, no window geometry restore).
- No undo/redo, no save, no export.
- No web/browser version.

## 3. Tech stack

- Python 3.10+
- PyQt5 5.15.x — match the reference exactly so copied code runs unchanged
- `mido` 1.3.x — duration extraction (includes trailing silence to `end_of_track`)
- `pretty_midi` 0.2.x — note list (pitch, start, end, velocity)

No NumPy, no OpenCV, no audio library, no QSettings.

## 4. Project structure

```
disklavier_midi_visualizer/
├── disklavier_visualizer/
│   ├── __init__.py
│   ├── __main__.py                # `python -m disklavier_visualizer`
│   ├── app.py                     # QApplication bootstrap
│   ├── io/
│   │   ├── __init__.py
│   │   └── midi_adapter.py        # Copied near-verbatim from reference, trimmed
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py         # NEW: QMainWindow with menu, central layout, wiring
│       ├── midi_canvas.py         # Copied from reference's level2_midi_panel.py, trimmed
│       └── timeline_slider.py     # NEW: scrubber widget that two-way-binds to canvas
├── data/                          # User's .mid files (gitignored, already exists)
│   └── 20250814_140328_pia02_s044_002_slow_reaching.mid
├── docs/
│   └── superpowers/specs/
│       └── 2026-05-07-disklavier-midi-visualizer-design.md   # this file
├── tests/
│   ├── test_midi_adapter.py
│   ├── test_note_data.py
│   ├── test_velocity_color.py
│   └── test_smoke.py
├── requirements.txt               # PyQt5, mido, pretty_midi
└── README.md
```

The reference's `core/` and `services/` layers are intentionally dropped: with no alignment state, no anchors, and no multi-file state machine, those layers would be ceremony with no callers.

## 5. Layer responsibilities

Single-direction dependency: `ui → io`. UI layer imports from IO layer; IO layer has no Qt imports.

- **`io/midi_adapter.py`** — pure MIDI parsing. Returns notes and duration metadata. Raises `MidiParseError` on bad input.
- **`ui/midi_canvas.py`** — owns `MidiCanvasWidget` (the falling-keys QPainter canvas) and `MidiPanelWidget` (canvas + info label container). No file I/O.
- **`ui/timeline_slider.py`** — `TimelineSliderWidget`, a `QSlider`-based scrubber. Knows nothing about MIDI internals; speaks only in seconds.
- **`ui/main_window.py`** — the only file that wires everything: handles file-open, instantiates `MidiAdapter`, feeds it to the canvas, syncs canvas ↔ slider via signals.

## 6. Components

### 6.1 `MidiAdapter` (`io/midi_adapter.py`)

Copied from `midi_camera_alignment_tool/alignment_tool/io/midi_adapter.py` with two trims:
1. Drop the `unix_start`/`unix_end` mtime-based wall-clock derivation — not needed.
2. Drop `to_file_info()` and the `MidiFileInfo` builder — not needed; downstream code consumes the adapter directly.

Public surface:
```python
class MidiAdapter:
    def __init__(self, file_path: str) -> None: ...
    @property
    def notes(self) -> list[pretty_midi.Note]: ...   # pitch, start, end, velocity
    @property
    def duration(self) -> float: ...                  # seconds, from mido (trailing silence included)
    @property
    def time_resolution(self) -> float: ...           # seconds per tick
    @property
    def sample_rate(self) -> float: ...               # ticks per second
    @property
    def ticks_per_beat(self) -> int: ...
    @property
    def tempo(self) -> float: ...                     # microseconds per beat
    @property
    def filename(self) -> str: ...
```

Behavior:
- Uses `mido.MidiFile(path)` for `ticks_per_beat`, `length` (duration), tempo extraction.
- Uses `pretty_midi.PrettyMIDI(path)` for notes (`instruments[0].notes`).
- If `instruments` is empty → `notes = []`, no error.
- All mutation happens in `__init__`; the object is otherwise immutable.

`MidiParseError` is a single exception type defined inline in this module. No separate `errors.py`.

Failure handling:
- `FileNotFoundError`/`PermissionError` from `mido.MidiFile` → re-raised as `MidiParseError(f"Cannot read file: {e}")`.
- Any `mido`/`pretty_midi` parse exception → re-raised as `MidiParseError(f"Not a valid MIDI file: {e}")`.

### 6.2 `MidiCanvasWidget` + `MidiPanelWidget` (`ui/midi_canvas.py`)

Copied from `midi_camera_alignment_tool/alignment_tool/ui/level2_midi_panel.py` with three trims:
1. Drop `from alignment_tool.io.midi_adapter import MidiAdapter, MIDI_TO_NOTE` → import from local `..io.midi_adapter`. Drop `MIDI_TO_NOTE` (unused leftover in the reference).
2. Drop the `MidiFileInfo` parameter from `load_midi`. New signature: `load_midi(self, adapter: MidiAdapter) -> None`. The two values previously read from `MidiFileInfo` (duration for clamping, sample_rate for the info label) come from `adapter.duration` and `adapter.sample_rate`.
3. Drop the `M`-key flash side effect in the info-label update path — there are no markers in this app.

Public surface (extended from the reference: `load_midi` signature changes, and `current_time` is promoted from a private attribute to a property so `MainWindow` can read it without poking at `_current_time`):
- `load_midi(adapter: MidiAdapter) -> None`
- `set_position(t: float) -> None` — clamps to `[0, duration]`, schedules a repaint, emits `position_changed`
- `step_ticks(n: int) -> None` — moves by `n * time_resolution`
- `current_time` property (read-only) — returns the playhead's current time in seconds
- Signals: `position_changed(float)`, `user_interacted()`

Behavior preserved verbatim from the reference:
- 88-key falling-keys canvas, MIN_PITCH = 21 (A0), MAX_PITCH = 108 (C8), PIANO_HEIGHT = 40px
- Playhead at 97% from top of canvas; default 5s viewport
- Velocity colormap (4-stop linear RGB):
  - velocity 0   → `QColor(60, 100, 200)`  (blue)
  - velocity 64  → `QColor(60, 200, 100)`  (green)
  - velocity 100 → `QColor(255, 200, 50)`  (yellow)
  - velocity 127 → `QColor(255, 60, 60)`   (red)
- Scroll-wheel zoom, factor 0.8 (zoom in) / 1.25 (zoom out), clamped `[0.5s, 60s]`
- Left-drag scrub: drag down = forward in time, drag up = backward
- Double-click on a note seeks to its start time
- Hover a note → white 2px outline
- Adaptive horizontal grid (0.5s / 1s / 2s intervals based on zoom)
- Vertical octave-separator lines and "C1"…"C8" labels at the bottom of each C key
- Antialiasing explicitly off for crisp pixel-aligned note rectangles
- 88-key piano keyboard drawn in the same `paintEvent` (white keys first pass, black keys at 70% width second pass) — alignment with notes is guaranteed by both using the same `_pitch_to_x` helper.

`MidiCanvasWidget.load_midi` initializes `_current_time` to the first note's start (or 0.0 if no notes). This matches reference behavior.

### 6.3 `TimelineSliderWidget` (`ui/timeline_slider.py`) — NEW

A horizontal `QSlider` in continuous mode, plus a `QLabel` to its right showing `MM:SS.mmm / MM:SS.mmm`.

Internal representation: integer slider ticks at 1ms resolution. `range = [0, int(duration * 1000)]`. `QSlider` is integer-only; millisecond resolution is ample for human scrubbing.

Public surface:
```python
class TimelineSliderWidget(QWidget):
    position_changed = pyqtSignal(float)   # emitted only on user-driven changes (drag/click)
    def set_duration(self, seconds: float) -> None: ...
    def set_position(self, seconds: float) -> None: ...   # programmatic, no signal echo
```

Two-way binding rule:
- When the slider's `valueChanged` fires because the user moved the thumb, `TimelineSliderWidget` emits `position_changed`.
- When `set_position` is called programmatically (e.g. canvas drag updated playhead), the slider value is set with `blockSignals(True)` so no `position_changed` echo.

Click-anywhere-to-jump: on left mouse press anywhere in the slider trough, compute `style().sliderValueFromPosition(...)` and set the value directly. The default Qt behavior pages-step toward the click, which is annoying for scrubbing.

If `set_duration(0)` is called (degenerate file), the slider is disabled (`setEnabled(False)`); re-enable when next set to non-zero.

### 6.4 `MainWindow` (`ui/main_window.py`) — NEW

A `QMainWindow` containing:
- **Menu bar:** `File > Open... (Ctrl+O)`, `File > Quit (Ctrl+Q)`
- **Central widget:** `QWidget` with a `QVBoxLayout`:
  - `MidiPanelWidget` with `stretch=1`
  - `TimelineSliderWidget` at fixed height (~32px)
- **Status bar:** filename + brief help hint (`"Drag canvas to scrub | Scroll to zoom | Arrows to step"`)
- **Window title:** `"<filename> — Disklavier MIDI Visualizer"` after a load; `"Disklavier MIDI Visualizer"` before
- Default size 1200×700, no persistence

Keyboard shortcuts:
- `Left` / `Right` — `canvas.step_ticks(±1)`
- `Shift+Left` / `Shift+Right` — `canvas.step_ticks(±100)`

All other shortcuts from the reference (`M`, `C`, `A`, `R`, `L`, `O`, `Tab`, `Escape`) are dropped.

Wiring (the entire app's wiring lives in `MainWindow.__init__`):
- `canvas.position_changed.connect(slider.set_position)`
- `slider.position_changed.connect(canvas.set_position)`
- `file_open_action.triggered.connect(self._on_open_file)`

`_on_open_file` flow:
1. `path, _ = QFileDialog.getOpenFileName(self, "Open MIDI", "", "MIDI Files (*.mid *.MID)")`
2. If `path` is empty (cancelled): return.
3. `QApplication.setOverrideCursor(Qt.WaitCursor)`
4. `try: adapter = MidiAdapter(path)` — `except MidiParseError as e:` → restore cursor, `QMessageBox.warning(self, "Could not open MIDI", str(e))`, return.
5. Restore cursor.
6. `self._canvas.load_midi(adapter)` — replaces any prior file.
7. `self._slider.set_duration(adapter.duration)`.
8. `self._slider.set_position(self._canvas.current_time)` (programmatic, no echo).
9. Update window title and status bar.

## 7. Data flow

### 7.1 Startup

```
python -m disklavier_visualizer
   → __main__.py imports app.main()
   → app.main(): QApplication, MainWindow, .show()
   → MainWindow.__init__: builds menu, MidiPanelWidget, TimelineSliderWidget, status bar
   → No file loaded; canvas paints empty background; slider disabled
```

### 7.2 File-open flow

See section 6.4's `_on_open_file` flow. After step 6, the canvas internally:
- Builds `NoteData` (sorts notes by start time, parallel arrays for binary-search visibility queries).
- Resets `_current_time` to first note's start (or 0.0 if no notes).
- Calls `self.update()` → repaint.
- Emits `position_changed(_current_time)` → slider updates via the wired signal (with `blockSignals` on the slider's internal `setValue`).

### 7.3 Scrub via canvas drag

```
User left-presses on canvas, drags down 50px
   → MidiCanvasWidget.mousePressEvent: _dragging=True, capture _drag_start_y, _drag_start_time
   → mouseMoveEvent: dy=50, dt = dy / pps, set_position(_drag_start_time + dt)
        → clamp to [0, duration]
        → update _current_time, repaint
        → emit position_changed(_current_time)
   → wired: canvas.position_changed → slider.set_position
        → slider sets value via blockSignals(True), no echo back
```

### 7.4 Scrub via slider drag/click

```
User drags slider thumb to 45.231s (or clicks the trough at that position)
   → QSlider valueChanged(45231)
   → TimelineSliderWidget converts ms → seconds, emits position_changed(45.231)
   → wired: slider.position_changed → canvas.set_position
        → canvas updates _current_time, repaints, emits position_changed(45.231)
        → slider receives, setValue via blockSignals(True), no loop
```

The two-way binding terminates because both `set_position` setters use `blockSignals(True)` to suppress the echo. Both sides converge in a single Qt event-loop tick.

### 7.5 Zoom via scroll wheel

```
User scrolls up over canvas
   → MidiCanvasWidget.wheelEvent: _seconds_per_viewport *= 0.8, clamped [0.5, 60]
   → repaint with denser time axis
   → Slider unaffected (zoom changes scale, not position)
```

### 7.6 Step by tick (arrow keys)

```
User presses Right arrow
   → QShortcut on MainWindow → canvas.step_ticks(+1)
        → set_position(_current_time + adapter.time_resolution)
        → repaint, emit position_changed
   → slider syncs (blocked).
```

`Shift+Right` is the same with `+100` ticks. `Left` / `Shift+Left` are the negative variants.

### 7.7 Open a different file (replace current)

Same as 7.2. `load_midi` overwrites `_note_data`, resets `_current_time` to the new file's first note, slider's range and position update accordingly.

## 8. Error handling

The whole app has only two real failure modes — file I/O and MIDI parsing — and a handful of edge cases.

### 8.1 Errors at the boundary (file load)

The only place errors can enter is `MainWindow._on_open_file`, when constructing `MidiAdapter(path)`.

| Failure mode | Where it surfaces | Handling |
|---|---|---|
| File doesn't exist / unreadable | `mido.MidiFile(path)` raises `FileNotFoundError`/`PermissionError` | Caught in `MidiAdapter.__init__`, re-raised as `MidiParseError("Cannot read file: ...")` |
| Not a valid MIDI file | `mido` or `pretty_midi` raises | Caught in `MidiAdapter.__init__`, re-raised as `MidiParseError("Not a valid MIDI file: ...")` |
| Parses but has no instruments | `pretty_midi.instruments[0]` would `IndexError` | Detected explicitly; `notes = []`, treated as a successful load (empty MIDI is valid) |

### 8.2 What the user sees on failure

`MainWindow._on_open_file` wraps construction in `try`/`except MidiParseError`. On catch:
- Restore cursor.
- `QMessageBox.warning(self, "Could not open MIDI", str(e))` — modal, single OK.
- Method returns. Existing canvas state (if any) is untouched; previous file remains visible.

No retry loop, no log file, no partial-load.

### 8.3 Edge cases handled silently

- **Empty MIDI (zero notes):** canvas paints background + grid + keyboard, no notes. `set_position(0)`. Slider remains active for the trailing silence period. Status bar reads `"Loaded foo.mid | 0 notes | 12.34s"`.
- **Duration is zero:** slider is disabled via `setEnabled(False)`. Canvas still paints. No error.
- **Notes outside MIN_PITCH..MAX_PITCH (pitch <21 or >108):** clipped at render time by `_pitch_to_x` returning out-of-bounds X — Qt's painter clipping handles it. No filter step.
- **Pitch bend, sustain pedal, multi-track:** ignored. Only `instruments[0].notes` is read. Disklavier exports are single-track piano, so this is the right default. Documented in README.

### 8.4 Not defended against

- No type-checking inside the canvas — `MainWindow` is the only caller of `load_midi` and just constructed the adapter.
- No drift checks on the two-way bind — `blockSignals` makes it correct by construction.
- No concurrent-load race — file dialog is modal.
- No OOM defense for huge files — `MidiParseError` surfaces whatever `pretty_midi` raises.

### 8.5 Logging

None. Uncaught exceptions propagate to Qt's default handler (stderr).

## 9. Testing

### 9.1 Unit tests (pytest, no Qt event loop)

**`tests/test_midi_adapter.py`**
- Loads `data/20250814_140328_pia02_s044_002_slow_reaching.mid` and asserts: `len(notes) > 0`, `duration > 0`, `time_resolution > 0`, `sample_rate ~= 1/time_resolution`, all notes have valid `pitch`/`velocity` (0–127).
- Bad path → `MidiParseError`.
- Non-MIDI file (e.g. point at README) → `MidiParseError`.
- Round-trip: re-loading the same file produces equal note counts and equal `duration`.

**`tests/test_note_data.py`**
- Build `NoteData` from a hand-crafted small list of notes; assert `visible_range(t_min, t_max)` returns correct indices for:
  - Window entirely before any notes → empty
  - Window entirely after all notes → empty
  - Window straddling a sustained note that started before `t_min` (backward-walk path)
  - Window inside a dense cluster

**`tests/test_velocity_color.py`**
- Test the colormap at velocity = 0, 32, 64, 96, 100, 127; assert RGB values match the documented stops and linear interpolations.

### 9.2 Smoke test (pytest-qt)

**`tests/test_smoke.py`**
- Boot `QApplication`, instantiate `MainWindow`, programmatically load the bundled `.mid`. Assert:
  - Window title updated.
  - Canvas `_current_time` is non-zero (auto-seek to first note).
  - Slider range and value are set correctly.
- Drive `canvas.set_position(5.0)` → assert `slider.value() == 5000`.
- Drive `slider.setValue(10000)` → assert `canvas._current_time == 10.0`.
- Verify no `RecursionError` from the two-way bind.

### 9.3 Not automated

- Pixel-level paint correctness — manual visual check only. Snapshot tests of `QPainter` are brittle (font hinting, OS theme).
- Drag/scroll/double-click event handlers — math is trivial; manual check is faster than synthesizing `QMouseEvent`s.
- File dialog — Qt internal.

### 9.4 Manual check (`docs/manual_test.md`)

Run `python -m disklavier_visualizer` and verify:

1. App launches; empty canvas + disabled slider visible.
2. `Ctrl+O` → pick the bundled `.mid` → notes appear, slider activates, title and status bar update.
3. Notes show velocity coloring (blue → green → yellow → red).
4. Drag canvas down → playhead advances, notes scroll, slider thumb moves with it.
5. Drag slider thumb → playhead moves, canvas matches.
6. Click on slider trough → thumb jumps there, canvas matches.
7. Scroll up → zoom in; scroll down → zoom out. Slider unaffected.
8. Double-click a note → playhead snaps to its start.
9. Hover a note → white outline.
10. `Right`/`Left` → ±1 tick (visible at high zoom). `Shift+Arrow` → ±100 ticks.
11. 88-key keyboard at bottom: white keys span full width, black keys narrower at 70%, C-note labels readable.
12. Open a second MIDI file → previous fully replaced.
13. Try opening README → `QMessageBox` warning, previous file still loaded.
14. Close window → process exits cleanly.

### 9.5 CI

None for now. Single-developer desktop tool. If it grows, add a GitHub Actions job running pytest on Linux with `xvfb-run` for the pytest-qt smoke test.

## 10. Out-of-scope items (deferred)

If anyone asks for these later, they're explicit deferrals — not part of this design:
- Audio playback (would require fluidsynth or pygame.midi + a soundfont).
- Recent-files menu / last-opened persistence (needs QSettings).
- Multi-file dropdown / folder mode.
- Pitch-bend or sustain pedal visualization.
- Multi-track rendering with track selector.
- Export to PNG/SVG.
- Pixel-snapshot regression testing.

## 11. References

- Reference project: `C:\Users\haowe\OneDrive\Desktop\MIT\midi_camera_alignment_tool`
  - `alignment_tool/ui/level2_midi_panel.py` — the canvas to copy
  - `alignment_tool/io/midi_adapter.py` — the adapter to copy
- Bundled sample: `data/20250814_140328_pia02_s044_002_slow_reaching.mid`
