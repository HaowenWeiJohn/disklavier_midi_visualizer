# Saving and loading anchors

Anchors are the only persistent state the app produces. They are stored as a UTF-8 JSON sidecar — typically `{midi-stem}.anchors.json` next to the `.mid` file — and the format is designed to be hand-editable, diff-friendly, and bound to a specific MIDI by absolute path.

This page describes the workflow. For the on-disk schema, see [JSON schema (v1)](json-schema.md).

## Saving anchors

### Trigger

- Menu: **File → Save Anchors…**
- Shortcut: ++ctrl+s++
- Disabled until a MIDI is loaded.

### Default save location

The save dialog defaults to:

```
{midi-folder}/{midi-stem}.anchors.json
```

For example, opening `C:\study\trial_001.mid` and pressing ++ctrl+s++ defaults to `C:\study\trial_001.anchors.json`. You can pick any other path or filename, but `.anchors.json` is the conventional suffix.

### What gets written

The save flow (`MainWindow._on_save_anchors` in `disklavier_visualizer/ui/main_window.py:298`):

1. Read the current MIDI's adapter from the canvas.
2. Build an `AnchorFile`:
    - `midi_path = os.path.abspath(self._current_midi_path)` — the **absolute path** to the MIDI at save time.
    - `midi_duration_seconds = adapter.duration` — used as a sanity check on reload.
    - `anchors = self._anchor_table.get_anchors()` — a defensive copy of the in-memory list.
3. Call `save_anchors(anchor_file, path)`.

`_on_save_anchors` returns `bool` — `True` if the file was written, `False` if the user cancelled the save dialog or the write raised `OSError`. The [unsaved-changes guard](../3-reference/main-window.md#unsaved-changes-guard) uses this return value to decide whether the action that triggered the save (a file open, a window close) may proceed.

`save_anchors` (`disklavier_visualizer/io/anchor_io.py:38`):

1. Sets `anchor_file.saved_at` to the current UTC time in ISO 8601 format.
2. Sorts the anchors by timestamp (the **on-disk** copy, not the in-memory one — the UI ordering is not disturbed).
3. Serializes the dict with `indent=2`, `ensure_ascii=False`, `allow_nan=False`.
4. **Atomic write**: opens a `NamedTemporaryFile` in the same directory, writes there, then `os.replace` to the target path. On any error, the temp file is removed.

`allow_nan=False` means a `NaN` or `Infinity` timestamp would raise a `ValueError` at serialize time, surfacing as the **Could not save anchors** dialog. In practice this never triggers — the timestamps come from the canvas, which clamps them to the file's duration.

### Atomic write semantics

The `tempfile.mkstemp` + `os.replace` pattern guarantees that:

- If the write succeeds, readers see the complete new file.
- If the write fails midway (disk full, power loss, killed process), the original file (if any) is intact — the new content was in a temp file that gets cleaned up on the next launch by the OS.
- A reader observing the file path during the save sees either the old content or the new content, never a partial write.

### Mutation of `saved_at`

`save_anchors` mutates the `AnchorFile.saved_at` field in place. The main window currently throws the `AnchorFile` away after save, so this is invisible — but if you call `save_anchors` from your own code, be aware that the input dataclass is modified.

## Loading anchors

### Trigger

- Menu: **File → Open…**
- Shortcut: ++ctrl+o++
- The dialog filter shows `*.mid`, `*.MID`, and `*.json`. Picking a `.json` dispatches to `_open_anchors`; anything else dispatches to `_open_midi`.

There is no separate "Open Anchors" menu item. The same picker handles both.

### What gets read

The load flow (`MainWindow._open_anchors` in `disklavier_visualizer/ui/main_window.py:166`):

1. Call `load_anchors(json_path)`.
2. Take `anchor_file.midi_path` (the absolute path stored at save time).
3. **Check the MIDI exists.** If not → warning dialog → file picker to relocate the MIDI → if the user cancels, abort the load.
4. Open the (possibly relocated) MIDI via `_open_midi`. If that fails, abort.
5. **Compare durations.** If `|adapter.duration - anchor_file.midi_duration_seconds| > 0.01`, show a warning. The load proceeds.
6. **Clamp timestamps.** Any anchor with `timestamp < 0` or `timestamp > adapter.duration` is clamped into the valid range. The clamped count is reported in the status bar.
7. Replace the anchor table with the clamped anchors.

### Failure modes

| Failure | What happens |
|---|---|
| JSON file missing or unreadable | `AnchorParseError` → warning dialog `Could not open anchor file`, abort. |
| JSON malformed | Same as above. |
| `schema_version != 1` | `AnchorParseError` with `Unsupported schema version: ...` → same dialog. |
| Required field missing or wrong type | Same. |
| Non-finite timestamp in the JSON | Same. |
| Referenced MIDI missing on disk | Warning dialog + relocation file picker. Cancelling aborts. |
| User picks a wrong MIDI in the relocation step | Loads anyway. Duration mismatch warning will fire if applicable. |
| MIDI duration disagrees with the JSON's stored duration | Warning dialog (proceeds). Check that you picked the right file. |

### Why the absolute path

The `midi_path` is stored as an **absolute path** rather than a path relative to the JSON for one reason: anchor JSONs are typically saved in the same folder as the MIDI, but nothing enforces that. Storing absolute makes the file work regardless of where you save the JSON.

The trade-off: moving the MIDI invalidates the path. The relocation flow (warn → re-pick) handles this gracefully without requiring you to edit the JSON.

If you want a relocatable session (move the whole folder to another machine), the easiest path is to load the JSON, accept the relocation prompt, then re-save — the new save records the new absolute path.

## What does not get persisted

- Window geometry (position, size, dock side).
- Zoom level (always reset to 5 s on file load).
- Playhead time at save (the loaded session auto-seeks to the first note).
- Selected anchor row.
- Recent files list.

The anchor JSON contains anchors and a MIDI binding — and nothing else. Everything else is recomputed on each launch.

## Hand-editing the JSON

The schema is intentionally flat and human-readable. You can edit the file in any text editor:

- Add or remove anchors.
- Change a label.
- Adjust a timestamp.

The constraints are documented in [JSON schema (v1)](json-schema.md). The most important ones:

1. Keep `schema_version == 1`.
2. Keep every numeric field finite (no `NaN`, `Infinity`).
3. Keep `timestamp_seconds` in the file's range — out-of-range values get clamped on load (with a status-bar warning).

If you break a structural rule (missing field, wrong type, wrong schema version), the next load aborts with `AnchorParseError` and a descriptive message. Your old anchors stay in memory unchanged.

## Programmatic use

`anchor_io.py` is a pure-Python module with no Qt dependency. You can import it in scripts:

```python
from disklavier_visualizer.io.anchor_io import (
    Anchor, AnchorFile, load_anchors, save_anchors,
)

af = load_anchors("trial_001.anchors.json")
print(af.midi_path, len(af.anchors))

af.anchors.append(Anchor(timestamp_seconds=120.0, label="added by script"))
save_anchors(af, "trial_001.anchors.json")
```

The `save_anchors` call sorts on disk and updates `saved_at`, so two scripts writing to the same file produce diffs that contain only the changed lines.
