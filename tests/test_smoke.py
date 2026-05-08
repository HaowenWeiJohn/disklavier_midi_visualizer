"""End-to-end smoke test for MainWindow wiring (pytest-qt)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pytestqt")

from disklavier_visualizer.io.anchor_io import Anchor, AnchorFile, save_anchors
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
    """Programmatically reproduce _open_midi for the sample file."""
    window._open_midi(str(SAMPLE_MIDI))


def test_loads_sample_file(window: MainWindow):
    _load_sample(window)
    assert window._panel.canvas.adapter is not None
    # Auto-seek puts the playhead at the first note's start, which is non-zero
    assert window._panel.current_time > 0


def test_canvas_drives_slider(window: MainWindow, qtbot):
    _load_sample(window)
    window._panel.set_position(5.0)
    qtbot.wait(10)
    assert window._slider._slider.value() == 5000


def test_slider_drives_canvas(window: MainWindow, qtbot):
    _load_sample(window)
    window._slider._slider.setValue(10000)
    qtbot.wait(10)
    assert window._panel.current_time == pytest.approx(10.0, abs=0.001)


def test_two_way_bind_does_not_recurse(window: MainWindow, qtbot):
    """Verify the bind settles in one event-loop tick without RecursionError."""
    _load_sample(window)
    for t in [1.0, 2.5, 7.3, 0.0, 15.0]:
        window._panel.set_position(t)
        qtbot.wait(5)
    assert True


# ---- anchor wiring ----


def test_anchor_dock_present_and_disabled_before_load(window: MainWindow):
    assert window._anchor_dock is not None
    # Before any MIDI is loaded the Add button should be disabled and Save
    # action greyed out.
    assert not window._anchor_table._add_btn.isEnabled()
    assert not window._save_action.isEnabled()


def test_loading_midi_enables_anchor_features(window: MainWindow):
    _load_sample(window)
    assert window._anchor_table._add_btn.isEnabled()
    assert window._save_action.isEnabled()


def test_opening_midi_clears_existing_anchors(window: MainWindow, qtbot):
    """Flow 1: opening a MIDI must reset the anchor table to empty."""
    _load_sample(window)
    window._anchor_table.set_anchors([
        Anchor(timestamp_seconds=1.0, label="x"),
        Anchor(timestamp_seconds=2.0, label="y"),
    ])
    assert len(window._anchor_table.get_anchors()) == 2
    # Re-open the same MIDI; anchors should be wiped, MIDI re-loaded.
    window._open_midi(str(SAMPLE_MIDI))
    qtbot.wait(5)
    assert window._anchor_table.get_anchors() == []
    assert window._panel.canvas.adapter is not None
    assert window._anchor_table._add_btn.isEnabled()


def test_add_anchor_at_playhead(window: MainWindow, qtbot):
    _load_sample(window)
    window._panel.set_position(5.0)
    qtbot.wait(5)
    window._on_add_anchor()
    anchors = window._anchor_table.get_anchors()
    assert len(anchors) == 1
    assert anchors[0].timestamp_seconds == pytest.approx(window._panel.current_time, abs=1e-6)


def test_anchor_jump_drives_canvas(window: MainWindow, qtbot):
    _load_sample(window)
    window._anchor_table.add_anchor_at(7.5)
    # Simulate a double-click jump on the time cell.
    window._anchor_table._table.cellDoubleClicked.emit(0, 1)
    qtbot.wait(10)
    assert window._panel.current_time == pytest.approx(7.5, abs=0.001)


def test_save_then_open_round_trip(window: MainWindow, qtbot, tmp_path):
    _load_sample(window)
    window._anchor_table.set_anchors([
        Anchor(timestamp_seconds=2.0, label="alpha"),
        Anchor(timestamp_seconds=8.0, label="beta"),
    ])
    json_path = tmp_path / "out.json"
    # Persist directly via the io layer (bypass the file dialog).
    save_anchors(
        AnchorFile(
            midi_path=str(SAMPLE_MIDI),
            midi_duration_seconds=window._panel.canvas.adapter.duration,
            anchors=window._anchor_table.get_anchors(),
        ),
        str(json_path),
    )
    # Now wipe state and re-open via the JSON path.
    window._anchor_table.clear()
    window._open_anchors(str(json_path))
    qtbot.wait(10)
    anchors = window._anchor_table.get_anchors()
    assert [(a.timestamp_seconds, a.label) for a in anchors] == [
        (pytest.approx(2.0), "alpha"),
        (pytest.approx(8.0), "beta"),
    ]
    assert window._panel.canvas.adapter is not None


def test_open_anchors_with_missing_midi_uses_picker(
    window: MainWindow, qtbot, tmp_path, monkeypatch
):
    """If midi_path doesn't exist, the user picker provides the real file."""
    json_path = tmp_path / "out.json"
    save_anchors(
        AnchorFile(
            midi_path=str(tmp_path / "does_not_exist.mid"),
            midi_duration_seconds=87.342,
            anchors=[Anchor(timestamp_seconds=1.0, label="x")],
        ),
        str(json_path),
    )

    # Stub out the warning and the file picker.
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(SAMPLE_MIDI), ""),
    )

    window._open_anchors(str(json_path))
    qtbot.wait(10)
    assert window._panel.canvas.adapter is not None
    assert window._panel.canvas.adapter.filename == SAMPLE_MIDI.name
    anchors = window._anchor_table.get_anchors()
    assert len(anchors) == 1
    assert anchors[0].label == "x"


def test_open_anchors_user_cancels_picker(
    window: MainWindow, qtbot, tmp_path, monkeypatch
):
    """If the user cancels the relocation picker, state is preserved."""
    _load_sample(window)
    window._anchor_table.add_anchor_at(3.0)
    pre_anchors = window._anchor_table.get_anchors()

    json_path = tmp_path / "out.json"
    save_anchors(
        AnchorFile(
            midi_path=str(tmp_path / "missing.mid"),
            midi_duration_seconds=10.0,
            anchors=[Anchor(timestamp_seconds=1.0, label="other")],
        ),
        str(json_path),
    )

    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))

    window._open_anchors(str(json_path))
    qtbot.wait(10)
    # Existing MIDI + anchors preserved.
    assert window._panel.canvas.adapter is not None
    assert [(a.timestamp_seconds, a.label) for a in window._anchor_table.get_anchors()] == \
        [(a.timestamp_seconds, a.label) for a in pre_anchors]
