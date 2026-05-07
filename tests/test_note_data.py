"""Tests for NoteData visibility logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pytest

from disklavier_visualizer.ui.midi_canvas import NoteData


@dataclass
class _FakeNote:
    """Minimal stand-in for pretty_midi.Note."""
    start: float
    end: float
    pitch: int
    velocity: int


@dataclass
class _FakeAdapter:
    notes: List[_FakeNote]


def _build(notes: List[_FakeNote]) -> NoteData:
    nd = NoteData()
    nd.load_from_adapter(_FakeAdapter(notes=notes))
    return nd


def test_empty():
    nd = _build([])
    assert list(nd.visible_range(0, 10)) == []


def test_window_before_all_notes():
    notes = [_FakeNote(start=5.0, end=6.0, pitch=60, velocity=80)]
    nd = _build(notes)
    assert list(nd.visible_range(0.0, 1.0)) == []


def test_window_after_all_notes():
    notes = [_FakeNote(start=0.0, end=1.0, pitch=60, velocity=80)]
    nd = _build(notes)
    assert list(nd.visible_range(5.0, 10.0)) == []


def test_window_inside_dense_cluster():
    notes = [
        _FakeNote(start=0.0, end=0.1, pitch=60, velocity=80),
        _FakeNote(start=0.2, end=0.3, pitch=62, velocity=80),
        _FakeNote(start=0.4, end=0.5, pitch=64, velocity=80),
        _FakeNote(start=0.6, end=0.7, pitch=65, velocity=80),
    ]
    nd = _build(notes)
    visible = list(nd.visible_range(0.15, 0.45))
    # Notes 1 (0.2-0.3) and 2 (0.4-0.5) should be in range
    assert 1 in visible
    assert 2 in visible


def test_sustained_note_starting_before_window():
    """A long note that starts before t_min but ends inside the window must be reported."""
    notes = [
        _FakeNote(start=0.0, end=10.0, pitch=60, velocity=80),  # long sustain
        _FakeNote(start=5.5, end=6.0, pitch=62, velocity=80),
    ]
    nd = _build(notes)
    visible = list(nd.visible_range(5.0, 6.5))
    # The sustained note (index 0) starts before t_min=5.0 but extends past it
    assert 0 in visible
    assert 1 in visible


def test_window_exactly_at_note_boundary():
    notes = [
        _FakeNote(start=0.0, end=1.0, pitch=60, velocity=80),
        _FakeNote(start=1.0, end=2.0, pitch=62, velocity=80),
    ]
    nd = _build(notes)
    # Window starting exactly where the second note starts
    visible = list(nd.visible_range(1.0, 1.5))
    assert 1 in visible


def test_starts_are_sorted():
    """load_from_adapter must sort by start time so bisect is valid."""
    notes = [
        _FakeNote(start=2.0, end=2.5, pitch=60, velocity=80),
        _FakeNote(start=0.0, end=0.5, pitch=62, velocity=80),
        _FakeNote(start=1.0, end=1.5, pitch=64, velocity=80),
    ]
    nd = _build(notes)
    assert nd.starts == sorted(nd.starts)
