# Main window

The main window is the top-level container — a `QMainWindow` (`disklavier_visualizer/ui/main_window.py:39`) that owns three child widgets, a menu bar, a status bar, a single dock, and a small set of keyboard shortcuts.

The window opens at **1400 × 700** by default and is fully resizable.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ File                                                              [_][□][X] │ ← menu + native title bar
├────────────────────────────────────────────────────┬─────────────────────┤
│                                                    │ Anchors  [□][X]    │
│                                                    │ ┌───────────────┐  │
│              MidiPanelWidget (canvas)              │ │ Anchors       │  │
│                                                    │ │ Add Anchor    │  │
│                                                    │ │ Delete Sel.   │  │
│                                                    │ ├──┬───────┬─────┤  │ ← anchor dock
│                                                    │ │# │Time(s)│Label│  │
│                                                    │ ├──┼───────┼─────┤  │
│                                                    │ │ 1│174.417│ ... │  │
│                                                    │ ├──┼───────┼─────┤  │
│                                                    │ ...                │
│                                                    │                     │
│        Time: 192.847s / 261.5s  |  Tick: 370266    │                     │ ← info label (canvas footer)
├────────────────────────────────────────────────────┤                     │
│ ━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━  03:12.847 / 04:21.500              │ ← timeline slider
├──────────────────────────────────────────────────────────────────────────┤
│ Loaded {file} | 3 anchors from {file}.anchors.json — Drag canvas… A to add anchor │ ← status bar
└──────────────────────────────────────────────────────────────────────────┘
```

The central widget is a `QVBoxLayout` containing the `MidiPanelWidget` (stretch=1) on top and the `TimelineSliderWidget` below. The anchor dock is a `QDockWidget` floated to `Qt.RightDockWidgetArea` and may be moved to either side or undocked entirely.

## Title bar

Three states:

| Title | Meaning |
|---|---|
| `Disklavier MIDI Visualizer` | No MIDI loaded |
| `{filename} — Disklavier MIDI Visualizer` | MIDI loaded; no unsaved anchor edits |
| `{filename}* — Disklavier MIDI Visualizer` | MIDI loaded; anchors edited since the last save / load |

The trailing `*` is the **dirty marker**. See [Unsaved changes guard](#unsaved-changes-guard) for what triggers it and what protections it enables.

## Status bar

Always shows a help-hint string after `—`:

```
Drag canvas to scrub  |  Scroll to zoom  |  Arrows to step  |  Double-click a note to seek  |  A to add anchor
```

What appears before the `—` depends on state:

| State | Status text |
|---|---|
| App just started | (just the help hint) |
| MIDI loaded | `Loaded {filename}  |  {N} notes  |  {duration:.2f}s` |
| Anchor JSON loaded | `Loaded {filename}  +  {N} anchors from {basename}` |
| Anchor JSON loaded with clamping | `…  ({K} timestamp(s) clamped to file range)` |
| Just saved anchors | `Saved {N} anchors to {basename}` |

The hint is appended to load messages but **replaced** for "Saved" (which has no hint suffix).

## File menu

Single top-level menu, no toolbar.

| Item | Shortcut | Behaviour |
|---|---|---|
| **Open…** | ++ctrl+o++ | File picker for `*.mid`, `*.MID`, or `*.json`. Dispatch by extension: `.json` → [load anchors](../4-project-files/saving-and-loading.md#loading-anchors); anything else → load MIDI. |
| **Save Anchors…** | ++ctrl+s++ | File picker for `*.json`. Disabled until a MIDI is loaded. Default name is `{midi-stem}.anchors.json` in the MIDI's folder. Atomic write via tempfile + `os.replace`. |
| **Quit** | ++ctrl+q++ | Closes the window. If there are unsaved anchor edits, prompts **Save / Discard / Cancel** first — see [Unsaved changes guard](#unsaved-changes-guard). |

## File dispatch

`File → Open…` calls a single dialog with a multi-extension filter:

```
MIDI or Anchors (*.mid *.MID *.json);;MIDI Files (*.mid *.MID);;Anchor Files (*.json);;All Files (*)
```

The chosen filename's extension drives the next step:

- Ends with `.json` (case-insensitive) → `_open_anchors(path)`.
- Anything else → `_open_midi(path)`.

So you can drop a `.json` into the same picker that you use for `.mid` files. There is no separate "Open Anchors" menu item.

## Anchor JSON load flow

When the picked file is a `.json`, `_open_anchors` runs (`disklavier_visualizer/ui/main_window.py:166`):

1. Parse the JSON via `load_anchors`. Any failure → warning dialog, abort.
2. Check that `midi_path` (stored as an absolute path inside the JSON) exists on disk. If not → warning dialog, then a second file dialog asking the user to **locate the MIDI**. Cancelling the relocation aborts the load.
3. Open the (possibly relocated) MIDI via `_open_midi`. If that fails, abort.
4. Compare the loaded MIDI's `duration` against `midi_duration_seconds` from the JSON. If they differ by more than **0.01 s**, show a warning (proceeds anyway).
5. Clamp every anchor's `timestamp_seconds` into `[0, duration]`. Anchors that needed clamping are counted and reported.
6. Replace the table contents with the clamped anchors and update the status bar.

See [§4.1 Saving and loading anchors](../4-project-files/saving-and-loading.md) for the full workflow including edge cases.

## Unsaved changes guard

The main window tracks whether the in-memory anchor list differs from the last save (or last fresh load) via a `_dirty` boolean (`disklavier_visualizer/ui/main_window.py:68`). The flag is the source of truth for both the title-bar `*` marker and a confirmation prompt that fires before any action that would lose the edits.

### When the flag flips

| Event | New `_dirty` | Where |
|---|---|---|
| Add anchor (++a++ or **Add Anchor**) | `True` | `_on_anchors_changed` ← `AnchorTableWidget.anchors_changed` |
| Delete anchor | `True` | same signal |
| Edit a label to a new value | `True` | same signal |
| ++ctrl+s++ save succeeds | `False` | `_mark_clean()` at the end of `_on_save_anchors` |
| `File → Open…` loads a MIDI | `False` | `_mark_clean()` at the end of `_open_midi` |
| `File → Open…` loads an anchor JSON | `False` | `_mark_clean()` at the end of `_open_anchors` |

Loads call `_anchor_table.clear()` / `set_anchors(...)` first, both of which themselves emit `anchors_changed` (and would set `_dirty=True`). The `_mark_clean()` call deliberately runs *after* the mutation to settle the flag back to `False`.

### Save / Discard / Cancel prompt

`_maybe_confirm_discard()` (`disklavier_visualizer/ui/main_window.py:145`) is invoked from two call sites that would otherwise lose anchors:

- `_on_open_file` — before showing the file picker. Cancelling aborts the open.
- `closeEvent` — before accepting the close. Cancelling keeps the window alive.

When `_dirty` is `True`, a `QMessageBox.question` with three buttons appears:

- **Save** — chains into `_on_save_anchors`. The save dialog appears; if the user picks a path and the write succeeds, the original action proceeds. If the user cancels the save dialog or the write raises `OSError`, the original action is **aborted** (treated as Cancel) — anchors are preserved rather than silently discarded.
- **Discard** — proceed without saving. The unsaved edits are lost.
- **Cancel** — abort. The window stays open / the file picker never appears.

If `_dirty` is `False`, the prompt is skipped and the action proceeds immediately.

## Two-way bind: canvas ↔ slider

The canvas (`MidiPanelWidget`) and the slider (`TimelineSliderWidget`) both expose:

- `position_changed(float)` — Qt signal emitted on user input or programmatic update.
- `set_position(float)` — slot; updates the widget's position and re-emits the signal.

The main window wires:

```python
self._panel.position_changed.connect(self._slider.set_position)
self._slider.position_changed.connect(self._panel.set_position)
```

Both `set_position` implementations internally suppress signal echo (the slider via `QSignalBlocker`-style `blockSignals(True)`, the canvas via an early-return when the new value equals the current) so a single user action settles in one event-loop tick without recursing.

## Anchor wiring

The anchor table emits two signals the main window cares about:

| Signal | Wired to | Effect |
|---|---|---|
| `jump_requested(float)` | `self._panel.set_position` | Double-clicking a `Time (s)` cell jumps the playhead |
| `add_requested()` | `self._on_add_anchor` | Clicking **Add Anchor** asks the host for the playhead time |

The ++a++ keyboard shortcut bypasses the table and calls `_on_add_anchor` directly (the table's button is the other path to the same function).

`_on_add_anchor` reads the canvas's current playhead time and calls `AnchorTableWidget.add_anchor_at(t)`. It is a no-op if no MIDI is loaded.

## Keyboard shortcuts

Registered in `_build_shortcuts` with `Qt.WindowShortcut` scope, so they fire regardless of which child widget has focus (with one exception — see below).

| Key | Action |
|---|---|
| ++left++ | Step playhead by `-1` MIDI tick |
| ++right++ | Step playhead by `+1` MIDI tick |
| ++shift+left++ | Step playhead by `-100` ticks |
| ++shift+right++ | Step playhead by `+100` ticks |
| ++a++ | Add anchor at current playhead |

Plus the menu shortcuts (++ctrl+o++, ++ctrl+s++, ++ctrl+q++) registered through `QAction.setShortcut`.

!!! note "Anchor table label-edit consumes letters"
    When the **Label** cell of the anchor table is being edited (its inline editor is focused), the ++a++ shortcut is absorbed by the editor, not delivered to the main window. Press ++enter++ or ++esc++ to release the editor before pressing ++a++ again.

## Window state and the dock

The dock has `objectName = "anchorsDock"` so its position could be persisted via `QMainWindow.saveState` / `restoreState`. The current implementation does **not** call either — every launch starts with the dock on the right side, expanded.

The dock is allowed in `Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea` only; top and bottom areas are disallowed via `setAllowedAreas`. It can be undocked into a floating window or closed entirely (use the small **X** in its title bar — there is no menu item to reopen it once closed; restart the app).

## Error dialogs

All error dialogs are `QMessageBox.warning`:

| Trigger | Title | Body |
|---|---|---|
| `MidiParseError` | `Could not open MIDI` | The exception message |
| `AnchorParseError` | `Could not open anchor file` | The exception message |
| Anchor JSON points to a missing MIDI | `MIDI file not found` | The path, plus a "Please locate" hint; followed by the relocation file dialog |
| Loaded MIDI's duration disagrees with anchor JSON | `MIDI duration mismatch` | Both durations side-by-side; the load proceeds |
| `OSError` during anchor save | `Could not save anchors` | The exception message |

There is no exhaustive error-router class — errors are caught and surfaced at each call site directly.
