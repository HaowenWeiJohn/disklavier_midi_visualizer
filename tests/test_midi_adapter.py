"""Tests for MidiAdapter."""
from __future__ import annotations

from pathlib import Path

import pytest

from disklavier_visualizer.io.midi_adapter import MidiAdapter, MidiParseError

PROJECT_ROOT = Path(__file__).parent.parent
SAMPLE_MIDI = PROJECT_ROOT / "data" / "20250814_140328_pia02_s044_002_slow_reaching.mid"


@pytest.fixture(scope="module")
def adapter() -> MidiAdapter:
    if not SAMPLE_MIDI.exists():
        pytest.skip(f"Sample MIDI not present at {SAMPLE_MIDI}")
    return MidiAdapter(str(SAMPLE_MIDI))


def test_loads_sample(adapter: MidiAdapter):
    assert len(adapter.notes) > 0
    assert adapter.duration > 0
    assert adapter.time_resolution > 0
    # sample_rate is the inverse of time_resolution by construction
    assert adapter.sample_rate == pytest.approx(1.0 / adapter.time_resolution)
    assert adapter.ticks_per_beat > 0
    assert adapter.tempo > 0


def test_notes_are_in_valid_midi_range(adapter: MidiAdapter):
    for note in adapter.notes:
        assert 0 <= note.pitch <= 127
        assert 0 <= note.velocity <= 127
        assert note.end >= note.start


def test_filename_property(adapter: MidiAdapter):
    assert adapter.filename == "20250814_140328_pia02_s044_002_slow_reaching.mid"


def test_round_trip_equivalence():
    if not SAMPLE_MIDI.exists():
        pytest.skip(f"Sample MIDI not present at {SAMPLE_MIDI}")
    a1 = MidiAdapter(str(SAMPLE_MIDI))
    a2 = MidiAdapter(str(SAMPLE_MIDI))
    assert len(a1.notes) == len(a2.notes)
    assert a1.duration == a2.duration
    assert a1.tempo == a2.tempo


def test_bad_path_raises():
    with pytest.raises(MidiParseError):
        MidiAdapter("/path/that/does/not/exist.mid")


def test_non_midi_file_raises(tmp_path):
    fake = tmp_path / "not_a_midi.mid"
    fake.write_text("this is just a text file, not MIDI")
    with pytest.raises(MidiParseError):
        MidiAdapter(str(fake))
