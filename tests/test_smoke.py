"""End-to-end smoke test for MainWindow wiring (pytest-qt)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pytestqt")

from disklavier_visualizer.io.midi_adapter import MidiAdapter
from disklavier_visualizer.ui.main_window import MainWindow

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_MIDI = PROJECT_ROOT / "data" / "20250814_140328_pia02_s044_002_slow_reaching.mid"


@pytest.fixture
def window(qtbot):
    if not SAMPLE_MIDI.exists():
        pytest.skip(f"Sample MIDI not present at {SAMPLE_MIDI}")
    w = MainWindow()
    qtbot.addWidget(w)
    return w


def _load_sample(window: MainWindow):
    """Programmatically reproduce _on_open_file for the sample file."""
    adapter = MidiAdapter(str(SAMPLE_MIDI))
    window._slider.set_duration(adapter.duration)
    window._panel.load_midi(adapter)
    window._slider.set_position(window._panel.current_time)


def test_loads_sample_file(window: MainWindow):
    _load_sample(window)
    assert window._panel.canvas.adapter is not None
    # Auto-seek puts the playhead at the first note's start, which is non-zero
    assert window._panel.current_time > 0


def test_canvas_drives_slider(window: MainWindow, qtbot):
    _load_sample(window)
    window._panel.set_position(5.0)
    # set_position emits position_changed; the wired slider receives it
    qtbot.wait(10)
    assert window._slider._slider.value() == 5000


def test_slider_drives_canvas(window: MainWindow, qtbot):
    _load_sample(window)
    # Drive the inner QSlider directly so valueChanged fires (simulates user input)
    window._slider._slider.setValue(10000)
    qtbot.wait(10)
    assert window._panel.current_time == pytest.approx(10.0, abs=0.001)


def test_two_way_bind_does_not_recurse(window: MainWindow, qtbot):
    """Verify the bind settles in one event-loop tick without RecursionError."""
    _load_sample(window)
    for t in [1.0, 2.5, 7.3, 0.0, 15.0]:
        window._panel.set_position(t)
        qtbot.wait(5)
    # If we got here without RecursionError, the bind is correct
    assert True
