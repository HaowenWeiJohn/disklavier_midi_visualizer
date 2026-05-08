# What it is

The Disklavier MIDI Visualizer is a **single-window PyQt5 application** that draws a `.mid` file as a falling-keys piano roll and lets you mark moments in it as labeled anchors. It is intentionally narrow in scope — one file open at a time, one track displayed, no audio.

## The three things on screen

When a MIDI file is loaded, the window has exactly three regions:

1. **Falling-keys canvas** (centre, the bulk of the window). Notes scroll from top (future) to bottom (past), past a horizontal red playhead near the bottom. An 88-key piano strip is drawn underneath for orientation. Notes are coloured by velocity, hovered notes get a white outline.
2. **Timeline slider** (full-width strip below the canvas). A horizontal scrubber with `MM:SS.mmm / MM:SS.mmm` digital readout on the right. Two-way bound to the canvas — moving one moves the other.
3. **Anchor dock** (right side, dockable). A table of `(#, Time(s), Label)` rows with **Add Anchor** and **Delete Selected** buttons, plus the **A** keyboard shortcut for adding at the current playhead.

Below all three is a status bar that shows the loaded filename, note count, duration, anchor count, and a help-hint string.

## What you can do with it

| Goal | How |
|---|---|
| Open a file | **File → Open…** (++ctrl+o++); accepts `.mid`, `.MID`, or a saved `.json` anchor file |
| Scrub through the file | Drag the canvas vertically, drag the slider, or click the slider trough |
| Zoom in or out | Mouse wheel over the canvas (clamped to 0.5 s – 60 s viewport) |
| Step a single MIDI tick | ++left++ / ++right++ (typically ~0.5 ms at 480 ticks/beat, 120 BPM) |
| Step coarsely | ++shift+left++ / ++shift+right++ (100 ticks at a time) |
| Snap to a note | Double-click on it |
| Mark the current time | Press ++a++ or click **Add Anchor** in the dock |
| Jump to an anchor | Double-click its **Time (s)** cell in the table |
| Edit a label | Double-click the **Label** cell, type, press ++enter++ |
| Save anchors | **File → Save Anchors…** (++ctrl+s++); writes a `*.anchors.json` sidecar |
| Restore a session | **File → Open…** the `.json` file; the visualizer re-loads the referenced MIDI |
| Quit | ++ctrl+q++ |

## How a MIDI file is interpreted

The visualizer reads two views of the same file in parallel:

- **`mido.MidiFile`** — for tempo extraction, ticks-per-beat, and the trailing-silence-aware `length` (used as the file's duration so `end_of_track` time after the last note is preserved; Disklavier writes `end_of_track` when STOP is pressed).
- **`pretty_midi.PrettyMIDI`** — for the note list. Only `instruments[0]` is consulted; Disklavier exports are single-track piano, so this is the right default.

If either parse fails, the UI shows a warning dialog and the previously loaded file (if any) stays on screen. Tempo extraction picks the **first `set_tempo`** message encountered, falling back to 120 BPM (`500_000` µs/beat) when the file has no tempo events at all.

See the [MidiAdapter source](https://github.com/HaowenWeiJohn/disklavier_midi_visualizer/blob/main/disklavier_visualizer/io/midi_adapter.py) (`disklavier_visualizer/io/midi_adapter.py`) for the full extraction logic.

## How an anchor file is interpreted

An anchor file is a self-contained UTF-8 JSON document with `schema_version == 1`. It binds to one MIDI file by **absolute path** and stores its duration so the visualizer can warn when a file has been edited since the anchors were saved. The anchor list itself is just a sorted array of `(timestamp_seconds, label)` pairs.

For the full schema and validation rules, see [§4.2 JSON schema (v1)](../4-project-files/json-schema.md).

## What's deliberately not here

This is a visualizer, not an editor. See [Scope and non-goals](scope-and-non-goals.md) for the explicit list of features that won't be added without a clear motivating use case.
