# Scope and non-goals

This page is the explicit list of things the Disklavier MIDI Visualizer **does not** do, and why. If you are evaluating whether the tool fits your workflow, this is the page that will tell you fastest.

## What's in scope

- Opening a single `.mid` file and displaying its first track as a falling-keys piano roll.
- Scrubbing the playhead via canvas drag, slider drag, slider trough click, arrow-key tick stepping, and double-click on a note.
- Wheel-zooming the time axis (0.5 s – 60 s viewport), reset to 5 s on each new file load.
- Marking timestamps as named **anchors** and saving the list as a JSON sidecar bound to the loaded MIDI by absolute path.
- Re-loading a session by opening the saved `.json` — the visualizer locates the referenced MIDI (or prompts you to relocate it), restores the anchors, and warns if the MIDI's duration has drifted since save.

## What's deliberately not in scope

### No audio playback

There is no MIDI synthesis, no audio file output, no master clock, no transport (play/pause/stop) buttons. Scrubbing is **visual-only**. If you need audio, route the `.mid` through a DAW or a synth (FluidSynth, etc.) — the visualizer is purely an inspection tool.

### No MIDI editing

You cannot move, resize, delete, or insert notes. You cannot transpose, change velocities, or edit tempo. The `.mid` file is opened read-only and never written back. Anchors are the only persistent output, and they go in a separate `*.anchors.json` file.

### No multi-track or multi-instrument view

The visualizer reads `pretty_midi.instruments[0]` and ignores the rest. Disklavier exports are single-track piano so this is correct for the intended use case, but it does mean a MIDI file with multiple instruments will only show the first one.

### No camera, no video, no alignment

The sibling [`midi_camera_alignment_tool`](https://github.com/HaowenWeiJohn/midi_camera_alignment_tool) project pairs MIDI with overhead camera video and provides a two-phase alignment workflow (global shift + per-clip anchors). **None** of that is here. This visualizer's anchors are MIDI-only timestamps with optional labels — they do not encode any external time reference.

### No persistence between sessions (besides anchor files)

The app does not remember:

- The last folder you opened from.
- A recent-files list.
- Window geometry or dock position.
- Zoom level or playhead position from a previous run.

Every launch starts at a blank canvas. The only state that survives is the explicit `.anchors.json` you save.

### No multi-anchor selection or bulk operations

The anchor table supports single-row selection only. There is no multi-select, no "delete all", no copy/paste between tables, no import/export beyond the dedicated save/load. Each operation is one row at a time.

### No automation, no command-line interface

The app is launched as `python -m disklavier_visualizer` and that's it. There are no flags, no headless mode, no scripting hooks. If you need to batch-process anchor files, the `disklavier_visualizer.io.anchor_io` module's `load_anchors` / `save_anchors` functions are pure-Python and importable, but the UI itself is not driveable from the command line.

### No annotation types beyond timestamped labels

An anchor is `(timestamp_seconds: float, label: str)`. There are no:

- Region anchors (start + end).
- Per-note tags.
- Categories or colours.
- Linked anchors across files.

If a richer annotation model is needed, that is a feature request — open an issue with the use case.

## Why this scope

Two reasons:

1. **Single-purpose tools are easier to maintain.** Every feature listed in "in scope" has a corresponding test in `tests/` and a path on the [§3 Reference](../3-reference/main-window.md) pages. Features outside that perimeter would expand the surface area without clear benefit for the intended workflow.
2. **The sibling project already exists.** If you need camera-paired alignment, intensity probes, or per-clip workflows, use [`midi_camera_alignment_tool`](https://github.com/HaowenWeiJohn/midi_camera_alignment_tool). This visualizer is the trimmed, MIDI-only subset of that tool.
