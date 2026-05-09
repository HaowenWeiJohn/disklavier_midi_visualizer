# First launch

This page walks you from a fresh install to a loaded MIDI with anchors saved, in well under five minutes.

## Start the app

From the repo root with your virtual environment activated:

```powershell
python -m disklavier_visualizer
```

The main window opens at **1400 × 700** with the title bar reading **Disklavier MIDI Visualizer** and an empty canvas:

```
No MIDI loaded
```

The timeline slider at the bottom is greyed out and inert. The status bar reads:

```
Drag canvas to scrub  |  Scroll to zoom  |  Arrows to step  |  Double-click a note to seek  |  A to add anchor
```

The anchor dock on the right is visible but its **Add Anchor** button is disabled until a MIDI file is loaded.

## Open a MIDI file

1. **File → Open…** (or press ++ctrl+o++).
2. The file dialog filters to `*.mid`, `*.MID`, and `*.json` by default. Pick a `.mid` file.
3. The app parses the file (a wait cursor is shown for large files) and switches to the loaded state.

If parsing succeeds:

- The canvas redraws with notes coloured by velocity. The playhead **auto-seeks to the first note's start time** (matching the reference project's behaviour) so you don't see a wall of empty space at the top of the file.
- The timeline slider activates, its range becomes `0 .. duration_ms`, and its thumb sits at the playhead time.
- The title bar updates to `{filename} — Disklavier MIDI Visualizer`.
- The status bar shows the load summary, e.g.:

    ```
    Loaded trial_001.mid  |  4321 notes  |  187.40s   —   Drag canvas to scrub  | …
    ```

- The bundled sample (`data/20250814_140328_pia02_s044_002_slow_reaching.mid`) is a good first-test file if you have nothing handy.

If parsing fails (the file is missing, unreadable, or not actually MIDI), a warning dialog appears with the underlying error message and the previously loaded file (if any) stays on screen.

## Get oriented

- **Drag the canvas down** with the left mouse button — notes scroll past, the playhead time advances, the slider thumb follows.
- **Scroll the wheel** over the canvas — the time axis zooms (in to 0.5 s, out to 60 s). The slider is unaffected by zoom.
- **Press ++right++** — the playhead nudges by one MIDI tick (typically half a millisecond, only visible at high zoom). ++shift+right++ steps 100 ticks.
- **Double-click a note** — the playhead snaps to that note's start time.

## Add some anchors

1. Scrub or zoom to a moment of interest.
2. Press ++a++ (or click **Add Anchor** in the dock). A new row appears in the anchor table with the current time and an empty label cell focused for immediate typing.
3. Type a label, press ++enter++. The label commits.
4. Add a few more anchors at different times — note that the table re-sorts by timestamp automatically.

To jump the playhead back to an anchor's time, **double-click its `Time (s)` cell**. To delete an anchor, select its row and click **Delete Selected** (or press ++delete++ with the table focused).

## Save the anchors

1. **File → Save Anchors…** (++ctrl+s++).
2. The save dialog defaults to the same folder as the MIDI file, with a name like `{midi-stem}.anchors.json`.
3. Confirm. The status bar shows:

    ```
    Saved 3 anchors to trial_001.anchors.json
    ```

The file is a UTF-8 JSON document; you can open it in any text editor. See [§4.2 JSON schema (v1)](../4-project-files/json-schema.md) for the full layout.

## Reload the session later

To resume work later:

1. **File → Open…** and pick the `.json` you saved (the dialog filter includes both `.mid` and `.json`).
2. The app loads the MIDI file referenced inside the JSON, then populates the anchor table.

If the referenced MIDI has been moved or renamed, a warning appears and a second file dialog opens so you can locate the file. Cancelling that dialog aborts the load and leaves the previous session (if any) intact.

If the loaded MIDI's duration differs from the value stored at save time by more than 0.01 seconds, a warning notes the mismatch. Anchors whose timestamps fall outside the new duration range are clamped, and the status bar reports the clamp count.

## Quit

++ctrl+q++ (or the window's **X** button) closes the window. If you have unsaved anchor edits — the title bar shows a `*` marker — a **Save / Discard / Cancel** prompt appears first:

- **Save** opens the save dialog; succeeding closes the window, cancelling the dialog keeps it open.
- **Discard** closes the window and loses the edits.
- **Cancel** keeps the window open with edits intact.

If there are no unsaved edits, the window closes immediately. See [§3.1 Main window → Unsaved changes guard](../3-reference/main-window.md#unsaved-changes-guard) for the full flow.

## Where to next

- For a full walkthrough of every UI element and signal, head to [§3 Reference → Main window](../3-reference/main-window.md).
- For the keyboard cheat sheet, [§3.5 Keyboard shortcuts](../3-reference/keyboard-shortcuts.md).
- For the on-disk anchor format, [§4.2 JSON schema (v1)](../4-project-files/json-schema.md).
