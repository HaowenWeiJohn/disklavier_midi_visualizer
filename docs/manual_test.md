# Manual Test Checklist

Run after any non-trivial change. Launch the app:

```powershell
python -m disklavier_visualizer
```

Then walk through the following checklist with the bundled sample
(`data/20250814_140328_pia02_s044_002_slow_reaching.mid`):

1. App launches; window shows empty canvas + a disabled timeline slider at the bottom.
2. `Ctrl+O` → pick the bundled `.mid` file → notes appear, the slider becomes active, the title bar updates to include the filename, the status bar shows note count and duration.
3. Notes are colored according to velocity: a quiet passage looks blue/green; a loud chord has yellow/red rectangles.
4. Drag the canvas downward → playhead advances, notes scroll past. The slider thumb moves with the canvas.
5. Drag the slider thumb → playhead position updates and the canvas repaints to match.
6. Click on the slider trough (not the thumb) → thumb jumps to that location and the canvas matches.
7. Scroll up over the canvas → notes appear larger (zoom in). Scroll down → smaller (zoom out). The slider is unaffected by zooming.
8. Double-click on a visible note → playhead snaps to that note's start time.
9. Hover over a note → the note shows a white outline. Move off → outline goes away.
10. Press `Right` arrow → playhead nudges by 1 tick (visible only at high zoom). `Shift+Right` → 100 ticks. `Left` and `Shift+Left` move backward.
11. The 88-key piano keyboard at the bottom: white keys span the full width, black keys are narrower (≈70% width). C-note labels (`C1` through `C8`) are readable at the bottom of each C key.
12. Open a different `.mid` file via `Ctrl+O` → the previous file is fully replaced (canvas, slider range, title, status bar).
13. Try opening a non-MIDI file (e.g. `README.md` after changing the dialog filter) → a warning dialog appears; the previously loaded file remains visible.
14. Close the window → process exits cleanly.

If any step fails, capture which step it was and a screenshot before reporting.
