# Disklavier MIDI Visualizer

A small PyQt5 desktop app for inspecting Disklavier MIDI recordings as a falling-keys piano roll. Pick a `.mid` file, scrub through it, zoom in or out, see notes colored by velocity. Pure visualization — no audio playback, no annotations, no alignment.

## Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For development (tests):

```powershell
pip install -r requirements-dev.txt
```

## Run

```powershell
python -m disklavier_visualizer
```

Then `File > Open...` (or `Ctrl+O`) to pick a `.mid` file.

## Interactions

| Action                     | Effect                                                |
|----------------------------|-------------------------------------------------------|
| Drag canvas (left mouse)   | Scrub the playhead through time                       |
| Scroll wheel on canvas     | Zoom in/out (0.5s–60s viewport)                       |
| Double-click a note        | Jump the playhead to that note's start                |
| Drag the timeline slider   | Scrub like a video player                             |
| Click on the slider trough | Jump to that position                                 |
| `Left` / `Right`           | Step the playhead by ±1 MIDI tick                     |
| `Shift+Left` / `Shift+Right` | Step by ±100 ticks                                  |
| `Ctrl+O`                   | Open a MIDI file                                      |
| `Ctrl+Q`                   | Quit                                                  |

Notes are colored by MIDI velocity:

- Soft (vel ~0–63): blue → green
- Medium (vel ~64–99): green → yellow
- Loud (vel ~100–127): yellow → red

## Limitations

- Reads only the first track (`pretty_midi.instruments[0]`). Disklavier exports are single-track piano, so this is the right default.
- No audio playback. Scrubbing is visual-only.
- No persistence between sessions (no recent-files list, no last-opened memory).
- No annotations, anchors, or alignment features.

## Project layout

```
disklavier_visualizer/
├── app.py             — QApplication bootstrap
├── __main__.py        — `python -m disklavier_visualizer` entry point
├── io/
│   └── midi_adapter.py    — mido + pretty_midi MIDI parser
└── ui/
    ├── main_window.py     — QMainWindow shell, menu, signal wiring
    ├── midi_canvas.py     — falling-keys QPainter visualization
    └── timeline_slider.py — scrubber bar at the bottom
```

The visualization (`midi_canvas.py`) and MIDI parser (`midi_adapter.py`) are adapted from the
`midi_camera_alignment_tool` project.

## Tests

```powershell
pytest
```

Test layout:
- `tests/test_midi_adapter.py` — MIDI parsing, error handling
- `tests/test_note_data.py` — visibility-range logic
- `tests/test_velocity_color.py` — colormap stops and interpolation
- `tests/test_smoke.py` — end-to-end MainWindow wiring (requires `pytest-qt`)

For manual UI verification, see `docs/manual_test.md`.
