# Known issues

This page lists known limitations, behaviours that surprised early users, and things that aren't bugs but are worth being aware of. For an explicit list of features that are intentionally absent, see [§1.2 Scope and non-goals](../1-overview/scope-and-non-goals.md).

## Anchors are not saved automatically

Adding, deleting, or editing anchors in the dock does **not** mark the session dirty in any visible way (no asterisk in the title bar, no prompt before quitting). Closing the window with ++ctrl+q++ or the X button discards unsaved anchors silently. Press ++ctrl+s++ before quitting if you want to keep them.

This is intentional — the app is single-purpose and lightweight, and a save-or-lose prompt was deemed more friction than value. If you find yourself losing work, treat ++ctrl+s++ as a habit after every batch of anchors.

## Closing the anchor dock has no menu-item to reopen

The dock's title bar has a small `[X]` button that hides it. There is currently no **View** menu item or shortcut to bring it back. The workaround is to **restart the app** — every launch re-creates the dock in the right-side area regardless of how the previous session left it.

Window geometry and dock state are deliberately not persisted (see [What does not get persisted](../4-project-files/saving-and-loading.md#what-does-not-get-persisted)).

## Re-opening the same MIDI clears unsaved anchors

`File → Open…` and picking the currently-loaded MIDI again resets the anchor table to empty (the reload calls `_anchor_table.clear()`). If you had unsaved anchors, they are gone.

This is verified by `tests/test_smoke.py::test_opening_midi_clears_existing_anchors`.

## Multi-tempo MIDI files use the first tempo

`MidiAdapter._extract_tempo` collects every `set_tempo` message in every track. If the file has more than one distinct tempo, it returns the **first** one encountered. The `time_resolution` (seconds per tick) and the displayed `Tick` count in the info label are derived from that single tempo, so they will be wrong for sections of the file that use a different tempo.

The note **positions** themselves are correct — `pretty_midi` resolves tempo changes internally when computing each note's start/end time in seconds. Only the tick-conversion display is affected.

In practice Disklavier exports are constant-tempo, so this is a non-issue for the intended use case.

## Only the first track is rendered

The visualizer reads `pretty_midi.instruments[0].notes` and ignores the rest. A multi-track MIDI (e.g. piano + violin) shows only the first track.

This is documented in [§1.1 What it is → How a MIDI file is interpreted](../1-overview/what-it-is.md#how-a-midi-file-is-interpreted) and [§1.2 Scope and non-goals → No multi-track or multi-instrument view](../1-overview/scope-and-non-goals.md#no-multi-track-or-multi-instrument-view).

## Out-of-range pitches are silently dropped

Notes outside the 88-key piano range (MIDI 21 to 108) are skipped at paint time. They count toward the file's note total in the status bar but do not appear on the canvas. This is rare for piano MIDI but possible if the file has been programmatically transposed.

## Velocity 0 notes paint as soft blue

A `note_on` with velocity 0 is sometimes used as a synonym for `note_off`. `pretty_midi` should normally suppress these, but if any leak through they will paint as a thin soft-blue rectangle. There is no special handling.

## The slider can drift one millisecond from the canvas

The canvas keeps `_current_time` as a `float` (sub-millisecond). The slider rounds to the nearest millisecond when updating its thumb. Reading back from the slider would lose precision; instead, the canvas is the source of truth, and the info label shows the float time directly.

This drift is invisible at any normal scrub speed, but if you compare `current_time` (canvas) and `slider.value() / 1000.0` you can see the rounding error.

## Duration mismatch warning is informational

If the loaded MIDI's `length` differs from the value stored in the JSON by more than 0.01 seconds, the load shows a warning but proceeds. The warning is intended to flag "you've edited this MIDI since saving these anchors" — but it cannot tell you which side is right.

Common causes:
- The MIDI was re-recorded from the same session and is mostly the same but ends at a different `end_of_track`.
- The MIDI was edited in a DAW.
- You picked the wrong file at the relocation prompt.

If the timestamps still look right after the warning, the anchors are usable. If they look wrong, abort and check the file.

## OneDrive / cloud-synced folders can lock files

On Windows, OneDrive (and similar tools) sometimes hold open file handles on files in synced folders. Saving anchors over the network into a syncing folder generally works, but if you see `Could not save anchors: [WinError 5] Access is denied`, try:

1. Saving to a local non-synced folder first.
2. Re-saving once OneDrive finishes syncing.

The atomic-write strategy (`tempfile` + `os.replace`) guards against torn writes on this kind of filesystem race.

## Very large MIDI files take a few seconds to parse

`pretty_midi.PrettyMIDI(filepath)` walks the entire file and pre-computes note start/end times in seconds — this is O(notes) and happens on the UI thread. A wait cursor is shown via `QApplication.setOverrideCursor`, but the window will not respond to input until parsing completes. For Disklavier-typical files (tens of thousands of notes, ~5 minutes long) this is well under a second; for synthetic 1M-note files it can be several seconds.

There is no progress bar.
