# FAQ

A grab-bag of questions that come up around the visualizer. For an explicit list of features that aren't there, see [§1.2 Scope and non-goals](../1-overview/scope-and-non-goals.md). For warnings on edge-case behaviours, see [§5.1 Known issues](known-issues.md).

## Can it play audio?

No. The app does not synthesize MIDI to audio and does not have a transport (play / pause / stop). Scrubbing is **visual-only**.

If you want to hear the file, route it through a DAW or a synth (FluidSynth, etc.) — or open it in a media player that handles `.mid` directly. The visualizer is purely an inspection tool.

## Can it open multiple files at once?

No. The window holds one MIDI at a time. Opening a new one replaces the previous one (and clears the anchor table). If you need to compare files, run two instances of the app side by side.

## Can it edit notes?

No. The `.mid` file is opened read-only and never written back. The only thing that gets persisted is your anchor list, in a separate `*.anchors.json` file next to the MIDI.

## Why are some notes missing?

Three possibilities:

1. **They're outside the 88-key piano range** (MIDI 21–108). Out-of-range notes are silently dropped at paint time. See [Known issues](known-issues.md#out-of-range-pitches-are-silently-dropped).
2. **They're on a different track.** Only `instruments[0]` from `pretty_midi` is rendered. A multi-track file shows only the first track.
3. **They have velocity 0.** Some MIDI exporters use `note_on velocity=0` instead of `note_off`. `pretty_midi` normally folds these into proper note durations, but stray zero-velocity events can fall through.

## Why does the playhead start mid-file when I open something?

The canvas auto-seeks to the **first note's start time** on load. This matches the reference project's behaviour and prevents staring at a wall of empty space when the file has leading silence (e.g. a 30-second pre-roll).

To start at zero anyway, drag the slider thumb to the left edge or click the leftmost part of the slider trough.

## Why does my zoom reset every time I open a file?

By design — `load_midi` resets `_seconds_per_viewport` to 5.0 on every load. The thinking is that "5 seconds visible" is a reasonable default for spotting note shapes, and if you had previously zoomed in for the prior file, that zoom level isn't necessarily appropriate for the new one.

## What does the `*` in the title bar mean?

It marks **unsaved anchor edits**. The title shows `{filename}* — Disklavier MIDI Visualizer` as soon as you add, delete, or rename an anchor, and reverts to `{filename} — Disklavier MIDI Visualizer` (no star) after a successful ++ctrl+s++ save or any fresh load. See [§3.1 Main window → Unsaved changes guard](../3-reference/main-window.md#unsaved-changes-guard).

## What happens if I close the window with unsaved anchors?

If the title shows the `*` marker, closing the window (++ctrl+q++ or the X button) pops a **Save / Discard / Cancel** prompt:

- **Save** opens the save dialog. A successful save closes the window; cancelling the dialog or hitting a write error keeps the window open with edits intact.
- **Discard** closes the window and loses the edits.
- **Cancel** keeps the window open.

If there is no `*`, the window closes immediately. The same prompt appears before `File → Open…` swaps in another file.

## Can I move an anchor to a different time?

Not directly. The Time (s) cell is read-only. To "move" an anchor:

- **Easiest:** delete the existing anchor (++delete++ on the table), then add a new one at the new time (++a++).
- **Alternative:** edit the JSON file by hand, change `timestamp_seconds`, then File → Open… the JSON to re-load.

There is intentionally no in-place time edit because precise sub-millisecond placement via a text field is unergonomic compared to the canvas + ++a++ flow.

## My JSON loads but the timestamps are clamped — what happened?

The status bar reports something like `Loaded foo.mid + 5 anchors from foo.anchors.json (2 timestamp(s) clamped to file range)`. This means two of your anchors had `timestamp_seconds` outside `[0, midi_duration]`. The most likely causes:

- You edited the JSON by hand and entered a typo.
- The MIDI file was edited (truncated or extended) since the anchors were saved. The duration mismatch warning probably also fired.

The clamped values are at exactly `0.0` or exactly `duration`. To restore the original timestamps, fix the underlying issue (edit the JSON or restore the MIDI) before saving over the file.

## What's the difference between this and `midi_camera_alignment_tool`?

The sibling [`midi_camera_alignment_tool`](https://github.com/HaowenWeiJohn/midi_camera_alignment_tool) project adds:

- An overhead camera viewer paired with the MIDI.
- A two-phase alignment workflow (global shift + per-clip anchors).
- A pixel-intensity probe for finding key strikes from video.
- A multi-clip Gantt-timeline overview (Level 1).
- An `AlignmentService` that owns the alignment math and emits state changes.

The Disklavier MIDI Visualizer is the **MIDI-only subset** of that tool. The MIDI parser, falling-keys canvas, and anchor table were copied across and trimmed (e.g. no `AlignmentService` indirection, no camera/probe columns in the table, no active-anchor toggle). If a fix lands on the alignment tool's MIDI side, it likely needs to be ported here too.

## Can I run it headless? CI? On a server?

PyQt5 needs a display. There is no headless mode. For CI:

- The pure-Python pieces (`anchor_io.py`, `MidiAdapter`, `NoteData.visible_range`, `_velocity_color`) are fully tested without `pytest-qt` and run anywhere Python runs.
- The Qt-dependent tests (`test_anchor_table.py`, `test_smoke.py`) need `pytest-qt` and a display. On Linux CI, `xvfb-run pytest` typically works.

There are no tests of the painter output (no pixel comparisons) — visual verification is via `docs/manual_test.md` (a 14-step manual checklist).

## Can I use this with non-Disklavier MIDI files?

Yes. The "Disklavier" name reflects the intended use case (single-track Yamaha Disklavier exports), but the parser handles any standard MIDI file. The single-track limitation (only `instruments[0]` is rendered) is the main caveat — multi-track files will display only the first track.

## How do I customise the velocity colours?

The colour stops are hard-coded as `VEL_COLORS` at the top of `disklavier_visualizer/ui/midi_canvas.py`. To customise, edit the tuples:

```python
VEL_COLORS = [
    (0, QColor(60, 100, 200)),    # soft: blue
    (64, QColor(60, 200, 100)),   # medium: green
    (100, QColor(255, 200, 50)),  # loud-ish: yellow
    (127, QColor(255, 60, 60)),   # loud: red
]
```

Each entry is `(velocity_threshold, QColor)`. The `_velocity_color` function does piecewise-linear RGB interpolation between adjacent stops. There is no settings file or dialog — re-edit the source to change colours.

## How do I report a bug?

Open an issue on [github.com/HaowenWeiJohn/disklavier_midi_visualizer](https://github.com/HaowenWeiJohn/disklavier_midi_visualizer/issues) with:

- The exact steps to reproduce.
- The MIDI file (or a small repro file) if relevant.
- The Python version and OS.
- The full traceback if there is one.

For UI issues, a short screen recording or screenshot saves a lot of back-and-forth.
