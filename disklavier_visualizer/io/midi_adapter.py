"""Lightweight MIDI file adapter.

Adapted from midi_camera_alignment_tool's MidiAdapter, trimmed for a
standalone visualizer:
- No mtime-based wall-clock derivation (no alignment to other media)
- No MidiFileInfo builder (downstream consumes the adapter directly)
- Adds MidiParseError so the UI layer has a single exception to catch
"""
from __future__ import annotations

import os

import mido
import pretty_midi


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MIDI_TO_NOTE = {
    pitch: f"{NOTE_NAMES[pitch % 12]}{(pitch // 12) - 1}"
    for pitch in range(21, 109)
}


class MidiParseError(Exception):
    """Raised when a MIDI file cannot be opened or parsed."""


def _ticks_to_seconds(ticks: int, tempo: float, ticks_per_beat: int) -> float:
    seconds_per_beat = tempo / 1_000_000
    return (ticks / ticks_per_beat) * seconds_per_beat


class MidiAdapter:
    """Wraps a MIDI file for visualization."""

    def __init__(self, filepath: str):
        self._filepath = filepath
        try:
            self._mido = mido.MidiFile(filepath)
        except (FileNotFoundError, PermissionError) as e:
            raise MidiParseError(f"Cannot read file: {e}") from e
        except Exception as e:
            raise MidiParseError(f"Not a valid MIDI file: {e}") from e

        try:
            self._pm = pretty_midi.PrettyMIDI(filepath)
        except Exception as e:
            raise MidiParseError(f"Not a valid MIDI file: {e}") from e

        self._tempo = self._extract_tempo()

    def _extract_tempo(self) -> float:
        """Extract tempo in microseconds per beat.

        For constant-tempo files, returns the single tempo.
        For multi-tempo files, returns the first tempo encountered.
        """
        default_tempo = 500_000  # 120 BPM
        tempos = set()
        for track in self._mido.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    tempos.add(msg.tempo)
        if not tempos:
            return default_tempo
        if len(tempos) == 1:
            return tempos.pop()
        for track in self._mido.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    return msg.tempo
        return default_tempo

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def filename(self) -> str:
        return os.path.basename(self._filepath)

    @property
    def ticks_per_beat(self) -> int:
        return self._mido.ticks_per_beat

    @property
    def tempo(self) -> float:
        return self._tempo

    @property
    def time_resolution(self) -> float:
        """Seconds per tick."""
        return _ticks_to_seconds(1, self._tempo, self._mido.ticks_per_beat)

    @property
    def sample_rate(self) -> float:
        """Ticks per second."""
        return 1.0 / self.time_resolution

    @property
    def duration(self) -> float:
        """Recording duration in seconds, end_of_track inclusive.

        Uses mido.MidiFile.length so trailing silence between the last note
        and end_of_track is preserved (Disklavier writes end_of_track when
        STOP is pressed, which is significant for timing).
        """
        return self._mido.length

    @property
    def notes(self) -> list:
        """PrettyMIDI note list from the first instrument, or [] if none."""
        if self._pm.instruments:
            return self._pm.instruments[0].notes
        return []
