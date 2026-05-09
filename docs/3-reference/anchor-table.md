# Anchor table

The anchor table is the dockable list of timestamped labels for the currently-loaded MIDI file. It lives on the right side of the main window in a `QDockWidget` and may be moved to either side or undocked into a floating window.

It is implemented as `AnchorTableWidget` in `disklavier_visualizer/ui/anchor_table.py:34`. The widget owns its own `list[Anchor]` and emits signals on every user-driven mutation; the main window catches `jump_requested` and `add_requested` to keep the canvas in sync.

## Layout

```
┌──────────────────────────────────────────────────────────┐
│ Anchors          [ Add Anchor ]   [ Delete Selected ]    │ ← header row
├────┬───────────┬────────────────────────────────────────┤
│ #  │ Time (s)  │ Label                                  │
├────┼───────────┼────────────────────────────────────────┤
│ 1  │ 174.417   │ first cord d                           │
│ 2  │ 184.187   │ second cord d                          │
│ 3  │ 192.847   │ third cord d                           │
└────┴───────────┴────────────────────────────────────────┘
```

The header row has the **Anchors** label on the left, **Add Anchor** and **Delete Selected** buttons on the right. Below it sits a `QTableWidget` with three columns. The `#` and `Time (s)` columns resize to fit their contents; the `Label` column stretches to fill the remaining width.

## Columns

| # | Column | Source field | Format | Editable |
|---|---|---|---|---|
| 0 | `#` | row index + 1 | int, centred | No |
| 1 | `Time (s)` | `anchor.timestamp_seconds` | `f"{t:.3f}"`, right-aligned | No |
| 2 | `Label` | `anchor.label` | free string | **Yes** (in place) |

Editability is enforced both at the table level (`setEditTriggers(DoubleClicked | EditKeyPressed)`) and per-item via `Qt.ItemIsEditable` flag on the label items. The `#` and `Time (s)` items have that flag explicitly cleared.

## Header buttons

### Add Anchor

- **Tooltip**: `Add an anchor at the current playhead time (A)`
- **Disabled** until a MIDI is loaded. The main window calls `set_enabled_for_midi(True)` from `_open_midi` after a successful parse.
- **Clicking** emits `add_requested()`. The widget does **not** know the playhead time itself — the main window catches the signal, reads the time from the canvas, and calls `add_anchor_at(time)` back on the table.

The same effect can be achieved via the ++a++ keyboard shortcut on the main window.

### Delete Selected

- **Disabled** unless at least one row is selected (single-selection only).
- **Clicking** removes the selected row from the in-memory list, refreshes the table, and emits `anchors_changed`.
- The keyboard equivalent is the ++delete++ key, scoped to the table widget itself via a `QShortcut` with `Qt.WidgetShortcut` context — it only fires when the table has focus.

## Adding an anchor

The `add_anchor_at(timestamp_seconds)` method:

1. Constructs a new `Anchor(timestamp_seconds, label="")`.
2. Appends to the in-memory list and re-sorts by `timestamp_seconds`.
3. Calls `_refresh()` to rebuild the table rows.
4. Selects the new row (now at its sorted position).
5. **Opens the inline editor on the new row's Label cell** so you can type immediately.
6. Emits `anchors_changed`.

So in the typical flow — press ++a++, type a label, press ++enter++ — the steps are: shortcut fires → main window calls `add_anchor_at(playhead_time)` → table inserts and starts editing → user types → ++enter++ commits the label.

## Editing a label

The Label column is the only editable cell. To edit:

1. **Double-click** the Label cell. An inline editor opens over the cell.
2. Type the new label.
3. Press ++enter++ to commit, or ++esc++ to cancel.

Committing routes through `_on_item_changed`, which:

- Ignores edits while `_populating` is true (during `_refresh`).
- Ignores edits to non-Label columns (defensive — they're flagged read-only anyway).
- Compares the new text to the stored label; **emits `anchors_changed` only if it actually changed.**
- Writes the new text to `self._anchors[row].label`.

Setting the cell text to its current value is therefore a no-op — no signal, no spurious dirty marker.

!!! note "Letter shortcuts during edit"
    While the inline editor is focused, single-key shortcuts on the main window (specifically ++a++) are absorbed by the editor, not delivered to the main window. To press ++a++ for "add anchor" again, click outside the cell or press ++enter++ / ++esc++ first to release the editor focus.

## Deleting an anchor

Either click **Delete Selected** or press ++delete++ with the table focused. The selected row is removed from the in-memory list, the table is refreshed (renumbering subsequent rows), and `anchors_changed` is emitted.

There is **no multi-select**: `setSelectionMode(QAbstractItemView.SingleSelection)` is set in `__init__`. Even if you ++ctrl++-click a second row, only one row is selected and only that one will be deleted.

There is no undo. Deletion is immediate and unrecoverable within the session — but the on-disk JSON is unchanged until you press ++ctrl+s++ again, so you can reload the saved file to restore.

## Jumping to an anchor

**Double-click the Time (s) cell** to jump the playhead. Internally:

```python
def _on_cell_double_clicked(self, row: int, col: int):
    if col != TIME_COL:
        return
    if not (0 <= row < len(self._anchors)):
        return
    self.jump_requested.emit(self._anchors[row].timestamp_seconds)
```

Double-clicking the `#` column or `Label` column does **not** jump — the latter opens the label editor instead. Single-clicks anywhere just select the row.

The main window connects `jump_requested` to `panel.set_position`, which moves the playhead and updates both the canvas and the slider through the two-way bind.

## Bulk replace (for JSON load)

`set_anchors(anchors: list[Anchor])` replaces the entire list:

1. Copies each input anchor into a new `Anchor` instance (defensive copy — the input list and the input anchors are not retained).
2. Sorts by timestamp.
3. Refreshes the table.
4. Emits `anchors_changed`.

This is the path used by `_open_anchors` in the main window after JSON load, with the timestamps already clamped to the file's duration.

## Clearing the table

`clear()` empties the list and refreshes. It only emits `anchors_changed` if the list was non-empty before — clearing an already-empty table is silent.

The main window calls `clear()` at the start of every `_open_midi`, so opening a new MIDI always starts with an empty anchor table even if the previous session had unsaved anchors.

## Defensive copies in the public API

`get_anchors()` returns a deep copy:

```python
return [
    Anchor(timestamp_seconds=a.timestamp_seconds, label=a.label)
    for a in sorted(self._anchors, key=lambda a: a.timestamp_seconds)
]
```

Callers can mutate the returned list and the contained `Anchor` instances without affecting the widget's internal state. This is verified by `tests/test_anchor_table.py:128-136`.

`set_anchors(...)` likewise copies its input rather than retaining references. The result: there is no aliasing between the widget's state and any external list.

## Public API

### Signals

| Signal | When |
|---|---|
| `add_requested()` | **Add Anchor** button clicked. The host (main window) reads the current playhead and calls `add_anchor_at`. |
| `jump_requested(float)` | Time cell double-clicked. The host moves the playhead to that time. |
| `anchors_changed()` | Anchor list mutated (add, delete, label edit, `set_anchors`, `clear`). The main window connects this to `_on_anchors_changed`, which sets `_dirty=True` and refreshes the title — see [Main window → Unsaved changes guard](main-window.md#unsaved-changes-guard). |

### Methods

| Method | Purpose |
|---|---|
| `set_enabled_for_midi(enabled: bool)` | Enable/disable the **Add Anchor** button. Called from the main window on file load. |
| `add_anchor_at(timestamp_seconds: float)` | Insert at the given time, re-sort, select the new row, open the label editor. |
| `set_anchors(anchors: list[Anchor])` | Replace the entire list. Used after JSON load. |
| `get_anchors() -> list[Anchor]` | Return a sorted deep copy. Used when saving. |
| `clear()` | Empty the list. Called at the start of every MIDI load. |

## What the table does not do

- **No multi-select, no bulk delete, no copy-paste.** One row at a time.
- **Time and `#` cells are read-only.** To "edit" an anchor's time, delete it and add a new one at the new time. (You could edit the JSON by hand and re-load; see [§4.2 JSON schema](../4-project-files/json-schema.md).)
- **No drag-to-reorder.** Order is always sorted by timestamp; manual reordering would conflict with that invariant.
- **No filter / search.** The table is intended for tens of anchors per file, not thousands.
- **No row colour or category.** All rows look identical except for the `#`. Colour-coding by label or grouping by category is not implemented.
