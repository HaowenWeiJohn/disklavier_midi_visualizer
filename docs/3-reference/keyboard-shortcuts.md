# Keyboard shortcuts

A single cheat sheet for every key binding in the app.

## Menu shortcuts (global)

These work regardless of which child widget has focus. Registered through `QAction.setShortcut` on the **File** menu items.

| Key | Action |
|---|---|
| ++ctrl+o++ | Open… (`*.mid`, `*.MID`, `*.json` — the `.json` path loads anchors and their referenced MIDI) |
| ++ctrl+s++ | Save Anchors… (disabled until a MIDI is loaded) |
| ++ctrl+q++ | Quit (no "save first" prompt — unsaved anchors are discarded) |

## Window shortcuts

Registered with `Qt.WindowShortcut` scope on the main window. They fire regardless of which child widget has focus, **except** when an editable widget (the anchor table's label editor) is intercepting key events — see the note at the bottom.

| Key | Action |
|---|---|
| ++left++ | Step playhead by `-1` MIDI tick |
| ++right++ | Step playhead by `+1` MIDI tick |
| ++shift+left++ | Step playhead by `-100` ticks |
| ++shift+right++ | Step playhead by `+100` ticks |
| ++a++ | Add anchor at current playhead time |

A "tick" is `1 / sample_rate` seconds, derived from the MIDI file's tempo and ticks-per-beat. Typical values:

- 120 BPM, 480 ticks/beat → ≈ 1.04 ms per tick
- 120 BPM, 1920 ticks/beat (Disklavier) → ≈ 0.26 ms per tick

At those resolutions, single-tick stepping is only visible at the highest zoom levels (≤ 1 s per viewport).

## Anchor table shortcuts

Scoped to the anchor table widget (`Qt.WidgetShortcut`) — they only fire when the table has keyboard focus.

| Key | Action |
|---|---|
| ++delete++ | Delete the currently-selected anchor |
| ++f2++ | Open the inline editor on the selected row's Label cell |
| ++enter++ | Commit a label edit |
| ++esc++ | Cancel a label edit |

++f2++ is the standard Qt edit-key for `EditKeyPressed`. Single-clicking a Label cell to select it, then pressing ++f2++, opens the editor without needing a double-click.

## Mouse interactions

Mouse details live on each widget's reference page:

- **[MIDI canvas](midi-canvas.md)** — drag to scrub (vertical), wheel to zoom, double-click a note to snap, hover for white outline.
- **[Timeline slider](timeline-slider.md)** — drag the thumb, click the trough to jump directly.
- **[Anchor table](anchor-table.md)** — double-click `Time (s)` to jump the playhead, double-click `Label` to edit, click any cell to select the row.

## Behaviour during a label edit

When the **Label** cell of the anchor table is being edited (its inline editor is focused), some letter keys are absorbed by the editor before reaching the main window:

- ++a++ does **not** add an anchor — it types an "a" into the label.
- Arrow keys move the cursor inside the editor — they do **not** step the playhead.

Press ++enter++ (commit) or ++esc++ (cancel), or click outside the cell, to release the editor focus and re-enable the window shortcuts.

The menu shortcuts (++ctrl+o++, ++ctrl+s++, ++ctrl+q++) are not affected by this — they fire regardless of edit state because Qt routes them at the action level rather than as raw key events.

## What is not bound

There is no shortcut for:

- Reset zoom (use ++ctrl+o++ to re-open the file — that resets viewport to 5 s).
- Jump to start / jump to end (use the timeline slider's trough click, or drag the slider thumb to either end).
- Undo / redo. The anchor table has no undo stack; deletion is immediate.
- Open Recent / re-open last file. The app keeps no recent-files list.
- Toggle the anchor dock. Use the dock's `[X]` button to close it, but note there is no menu item to reopen it once closed — restart the app.
