"""Tests for AnchorTableWidget — add, sort, delete, jump, label edit, signals."""
from __future__ import annotations

import pytest

pytest.importorskip("pytestqt")

from PyQt5.QtCore import Qt

from disklavier_visualizer.io.anchor_io import Anchor
from disklavier_visualizer.ui.anchor_table import (
    LABEL_COL,
    TIME_COL,
    AnchorTableWidget,
)


@pytest.fixture
def widget(qtbot):
    w = AnchorTableWidget()
    qtbot.addWidget(w)
    return w


def test_add_anchor_inserts_row(widget: AnchorTableWidget):
    widget.add_anchor_at(5.0)
    anchors = widget.get_anchors()
    assert len(anchors) == 1
    assert anchors[0].timestamp_seconds == pytest.approx(5.0)
    assert anchors[0].label == ""


def test_add_anchor_keeps_list_sorted(widget: AnchorTableWidget):
    widget.add_anchor_at(20.0)
    widget.add_anchor_at(5.0)
    widget.add_anchor_at(12.0)
    times = [a.timestamp_seconds for a in widget.get_anchors()]
    assert times == [5.0, 12.0, 20.0]


def test_add_anchor_emits_anchors_changed(widget: AnchorTableWidget, qtbot):
    with qtbot.waitSignal(widget.anchors_changed, timeout=500):
        widget.add_anchor_at(3.0)


def test_set_anchors_replaces_existing(widget: AnchorTableWidget):
    widget.add_anchor_at(1.0)
    widget.add_anchor_at(2.0)
    widget.set_anchors([
        Anchor(timestamp_seconds=10.0, label="a"),
        Anchor(timestamp_seconds=5.0, label="b"),
    ])
    anchors = widget.get_anchors()
    assert [a.timestamp_seconds for a in anchors] == [5.0, 10.0]
    assert [a.label for a in anchors] == ["b", "a"]


def test_label_edit_updates_anchor_and_emits(widget: AnchorTableWidget, qtbot):
    widget.add_anchor_at(5.0)
    table = widget._table  # noqa: SLF001 — test reaching in
    label_item = table.item(0, LABEL_COL)
    assert label_item is not None

    with qtbot.waitSignal(widget.anchors_changed, timeout=500):
        label_item.setText("verse")

    assert widget.get_anchors()[0].label == "verse"


def test_label_edit_to_same_text_is_silent(widget: AnchorTableWidget, qtbot):
    widget.add_anchor_at(5.0)
    table = widget._table
    table.item(0, LABEL_COL).setText("verse")
    # Setting to the same text shouldn't emit.
    received = []
    widget.anchors_changed.connect(lambda: received.append(True))
    table.item(0, LABEL_COL).setText("verse")
    qtbot.wait(20)
    assert received == []


def test_double_click_time_emits_jump(widget: AnchorTableWidget, qtbot):
    widget.add_anchor_at(7.5)
    table = widget._table
    with qtbot.waitSignal(widget.jump_requested, timeout=500) as blocker:
        # Simulate the cellDoubleClicked signal directly — clicking pixels in
        # a table widget is brittle and not what we're verifying here.
        table.cellDoubleClicked.emit(0, TIME_COL)
    assert blocker.args == [pytest.approx(7.5)]


def test_double_click_label_does_not_emit_jump(widget: AnchorTableWidget, qtbot):
    widget.add_anchor_at(7.5)
    received = []
    widget.jump_requested.connect(lambda t: received.append(t))
    widget._table.cellDoubleClicked.emit(0, LABEL_COL)
    qtbot.wait(20)
    assert received == []


def test_delete_removes_selected_row(widget: AnchorTableWidget, qtbot):
    widget.add_anchor_at(1.0)
    widget.add_anchor_at(2.0)
    widget.add_anchor_at(3.0)
    widget._table.selectRow(1)
    with qtbot.waitSignal(widget.anchors_changed, timeout=500):
        widget._on_delete()
    times = [a.timestamp_seconds for a in widget.get_anchors()]
    assert times == [1.0, 3.0]


def test_set_enabled_for_midi_toggles_add_button(widget: AnchorTableWidget):
    assert not widget._add_btn.isEnabled()
    widget.set_enabled_for_midi(True)
    assert widget._add_btn.isEnabled()
    widget.set_enabled_for_midi(False)
    assert not widget._add_btn.isEnabled()


def test_clear_empties_table(widget: AnchorTableWidget):
    widget.add_anchor_at(1.0)
    widget.add_anchor_at(2.0)
    widget.clear()
    assert widget.get_anchors() == []
    assert widget._table.rowCount() == 0


def test_get_anchors_returns_copies(widget: AnchorTableWidget):
    """Mutating the returned list must not affect the widget's state."""
    widget.add_anchor_at(5.0)
    out = widget.get_anchors()
    out[0].label = "mutated"
    out.append(Anchor(timestamp_seconds=99.0, label="x"))
    again = widget.get_anchors()
    assert len(again) == 1
    assert again[0].label == ""


def test_add_button_emits_add_requested(widget: AnchorTableWidget, qtbot):
    widget.set_enabled_for_midi(True)
    with qtbot.waitSignal(widget.add_requested, timeout=500):
        widget._add_btn.click()


def test_row_numbers_are_one_based(widget: AnchorTableWidget):
    widget.add_anchor_at(1.0)
    widget.add_anchor_at(2.0)
    table = widget._table
    assert table.item(0, 0).text() == "1"
    assert table.item(1, 0).text() == "2"


def test_time_column_is_three_decimals(widget: AnchorTableWidget):
    widget.add_anchor_at(12.5)
    assert widget._table.item(0, TIME_COL).text() == "12.500"
