# Installation

The Disklavier MIDI Visualizer is a standalone Python/PyQt5 application. It runs on Windows, macOS, and Linux. The reference development environment is Windows 11 with Python 3.12.

## Prerequisites

- **Python 3.9 or newer.** `from __future__ import annotations` is used throughout, so Python 3.8 and earlier are not supported. The project's `.venv` was created against Python 3.12; that's the recommended baseline.
- **A Qt-capable display.** PyQt5 needs a windowing environment — there is no headless mode.

## Get the code

Clone the repository:

```bash
git clone https://github.com/HaowenWeiJohn/disklavier_midi_visualizer.git
cd disklavier_midi_visualizer
```

There is no installable package — the app runs directly from the source checkout as a module (see [First launch](first-launch.md)).

## Install dependencies

Pick the recipe that matches how you manage Python environments. Both produce equivalent runtime environments.

=== "pip"

    Runtime dependencies are pinned in `requirements.txt`:

    ```powershell
    python -m venv .venv
    .venv\Scripts\activate
    python -m pip install -r requirements.txt
    ```

    To run the test suite as well, install dev dependencies:

    ```powershell
    python -m pip install -r requirements-dev.txt
    ```

    `requirements-dev.txt` includes `requirements.txt` plus `pytest` and `pytest-qt`.

=== "conda"

    All three runtime dependencies are available on `conda-forge`. The `pyqt=5` pin avoids picking up PyQt6, which the app does not support.

    ```bash
    conda create -n disklavier-vis -c conda-forge python=3.12 "pyqt=5" mido pretty_midi
    conda activate disklavier-vis
    ```

    For tests, add `pytest` and `pytest-qt`:

    ```bash
    conda install -c conda-forge pytest pytest-qt
    ```

    !!! note "Package names on conda-forge"
        `pyqt` (with `=5` pin) provides **PyQt5**. `mido` and `pretty_midi` use the same names as on PyPI. The exact pinned versions live in `requirements.txt` (PyPI names) — match those if you want a reproducible environment.

## Runtime dependencies

The full pinned list (`requirements.txt`):

| Package | Pin | Why |
|---|---|---|
| `PyQt5` | `5.15.11` | Window system, widgets, painter — the entire UI layer |
| `mido` | `1.3.3` | Tempo extraction, ticks-per-beat, `MidiFile.length` (duration including trailing silence) |
| `pretty_midi` | `0.2.11` | Note list (`instruments[0].notes`) — pre-computed start/end times in seconds |

The dev-only additions (`requirements-dev.txt`):

| Package | Pin | Why |
|---|---|---|
| `pytest` | `>=7.0` | Test runner |
| `pytest-qt` | `>=4.2` | `qtbot` fixture for the smoke test (`tests/test_smoke.py`) |

## Verify the install

```bash
python -c "import PyQt5, mido, pretty_midi; print('OK')"
```

If that prints `OK`, you are ready to [launch the app](first-launch.md).

## Run the tests (optional)

From the repo root with the dev deps installed:

```bash
pytest
```

The suite covers the MIDI parser, anchor I/O round-trips and schema validation, the anchor table widget, the velocity colormap, visibility-range logic, and an end-to-end smoke test of the main window. The smoke test requires `pytest-qt`; if it is missing, those tests are skipped (not failed).
