"""Tests for anchor_io: round-trip, sort-on-save, schema rejection."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from disklavier_visualizer.io.anchor_io import (
    Anchor,
    AnchorFile,
    AnchorParseError,
    SCHEMA_VERSION,
    load_anchors,
    save_anchors,
)


def _make(anchors=None, midi_path=r"C:\some\path\song.mid", duration=60.0):
    return AnchorFile(
        midi_path=midi_path,
        midi_duration_seconds=duration,
        anchors=list(anchors or []),
    )


def test_round_trip_preserves_fields(tmp_path: Path):
    src = _make(
        anchors=[
            Anchor(timestamp_seconds=1.234, label="intro"),
            Anchor(timestamp_seconds=12.5, label="verse"),
            Anchor(timestamp_seconds=47.881, label=""),
        ],
        midi_path=r"C:\Users\me\song.mid",
        duration=87.342,
    )
    dest = tmp_path / "out.json"
    save_anchors(src, str(dest))

    loaded = load_anchors(str(dest))
    assert loaded.midi_path == src.midi_path
    assert loaded.midi_duration_seconds == pytest.approx(src.midi_duration_seconds)
    assert len(loaded.anchors) == 3
    for got, want in zip(loaded.anchors, src.anchors):
        assert got.timestamp_seconds == pytest.approx(want.timestamp_seconds)
        assert got.label == want.label
    assert loaded.saved_at is not None and loaded.saved_at != ""


def test_save_sorts_unsorted_input(tmp_path: Path):
    src = _make(
        anchors=[
            Anchor(timestamp_seconds=20.0, label="b"),
            Anchor(timestamp_seconds=5.0, label="a"),
            Anchor(timestamp_seconds=30.0, label="c"),
        ],
    )
    dest = tmp_path / "out.json"
    save_anchors(src, str(dest))

    with open(dest, "r", encoding="utf-8") as f:
        raw = json.load(f)
    times = [a["timestamp_seconds"] for a in raw["anchors"]]
    assert times == sorted(times)


def test_save_does_not_mutate_input_order(tmp_path: Path):
    """Save sorts the on-disk anchors but must not reorder the in-memory list."""
    anchors = [
        Anchor(timestamp_seconds=20.0, label="b"),
        Anchor(timestamp_seconds=5.0, label="a"),
    ]
    src = _make(anchors=anchors)
    save_anchors(src, str(tmp_path / "out.json"))
    # The in-memory list is still in insertion order.
    assert [a.timestamp_seconds for a in src.anchors] == [20.0, 5.0]


def test_save_emits_correct_schema_version(tmp_path: Path):
    dest = tmp_path / "out.json"
    save_anchors(_make(), str(dest))
    with open(dest, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert raw["schema_version"] == SCHEMA_VERSION


def test_save_writes_absolute_path_verbatim(tmp_path: Path):
    """Windows-style absolute path must round-trip with backslashes intact."""
    src = _make(midi_path=r"C:\Users\me\Disklavier\song.mid")
    dest = tmp_path / "out.json"
    save_anchors(src, str(dest))
    loaded = load_anchors(str(dest))
    assert loaded.midi_path == r"C:\Users\me\Disklavier\song.mid"


def test_load_rejects_missing_file(tmp_path: Path):
    with pytest.raises(AnchorParseError):
        load_anchors(str(tmp_path / "does_not_exist.json"))


def test_load_rejects_malformed_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("not even json {{", encoding="utf-8")
    with pytest.raises(AnchorParseError):
        load_anchors(str(bad))


def test_load_rejects_wrong_schema_version(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({
            "schema_version": 99,
            "midi_path": "x.mid",
            "midi_duration_seconds": 1.0,
            "anchors": [],
        }),
        encoding="utf-8",
    )
    with pytest.raises(AnchorParseError, match="schema"):
        load_anchors(str(bad))


def test_load_rejects_missing_anchors_key(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({
            "schema_version": SCHEMA_VERSION,
            "midi_path": "x.mid",
            "midi_duration_seconds": 1.0,
        }),
        encoding="utf-8",
    )
    with pytest.raises(AnchorParseError):
        load_anchors(str(bad))


def test_load_rejects_non_finite_timestamp(tmp_path: Path):
    bad = tmp_path / "bad.json"
    # NaN/Infinity isn't valid strict JSON, but we can hand-craft one with
    # the standard library's allow_nan emit and then reload it.
    bad.write_text(
        '{"schema_version": 1, "midi_path": "x.mid", '
        '"midi_duration_seconds": 1.0, '
        '"anchors": [{"timestamp_seconds": Infinity, "label": ""}]}',
        encoding="utf-8",
    )
    with pytest.raises(AnchorParseError):
        load_anchors(str(bad))


def test_load_rejects_anchors_not_a_list(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({
            "schema_version": SCHEMA_VERSION,
            "midi_path": "x.mid",
            "midi_duration_seconds": 1.0,
            "anchors": "nope",
        }),
        encoding="utf-8",
    )
    with pytest.raises(AnchorParseError):
        load_anchors(str(bad))


def test_load_accepts_empty_anchors(tmp_path: Path):
    src = _make(anchors=[])
    dest = tmp_path / "out.json"
    save_anchors(src, str(dest))
    loaded = load_anchors(str(dest))
    assert loaded.anchors == []
