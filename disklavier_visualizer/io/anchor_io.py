"""JSON save/load for MIDI anchor files.

Schema v1: a self-contained JSON sidecar bound to one MIDI file by absolute
path. Atomic write via tempfile + os.replace. Anchors are stored sorted by
timestamp so re-saving produces a stable diff.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


@dataclass
class Anchor:
    timestamp_seconds: float
    label: str = ""


@dataclass
class AnchorFile:
    midi_path: str
    midi_duration_seconds: float
    anchors: list[Anchor] = field(default_factory=list)
    saved_at: str | None = None


class AnchorParseError(Exception):
    """Raised when an anchor JSON file cannot be opened or parsed."""


def save_anchors(anchor_file: AnchorFile, json_path: str) -> None:
    """Serialize an AnchorFile to JSON atomically.

    Mutates anchor_file.saved_at to the wall-clock save time. Anchors written
    to disk are sorted by timestamp ascending; the in-memory list is left
    untouched so the UI ordering does not jump under the user's feet.
    """
    anchor_file.saved_at = datetime.now(timezone.utc).isoformat()
    sorted_anchors = sorted(anchor_file.anchors, key=lambda a: a.timestamp_seconds)
    data = {
        "schema_version": SCHEMA_VERSION,
        "saved_at": anchor_file.saved_at,
        "midi_path": anchor_file.midi_path,
        "midi_duration_seconds": anchor_file.midi_duration_seconds,
        "anchors": [
            {"timestamp_seconds": a.timestamp_seconds, "label": a.label}
            for a in sorted_anchors
        ],
    }

    target = Path(json_path)
    target_dir = target.parent if str(target.parent) != "" else Path(".")
    fd, tmp_path = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target_dir),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_anchors(json_path: str) -> AnchorFile:
    """Deserialize an AnchorFile from JSON. Raises AnchorParseError on any failure.

    Does not validate that anchor_file.midi_path actually exists on disk; the
    UI is responsible for relocating the MIDI if it has moved.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise AnchorParseError(f"Invalid anchor file: JSON decode error: {e}") from e
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise AnchorParseError(f"Cannot read anchor file: {e}") from e

    if not isinstance(data, dict):
        raise AnchorParseError("Invalid anchor file: top-level value is not an object")

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise AnchorParseError(
            f"Unsupported schema version: {version!r} (expected {SCHEMA_VERSION})"
        )

    try:
        midi_path = data["midi_path"]
        midi_duration = float(data["midi_duration_seconds"])
        raw_anchors = data["anchors"]
    except (KeyError, TypeError, ValueError) as e:
        raise AnchorParseError(f"Invalid anchor file: missing/invalid field: {e}") from e

    if not isinstance(midi_path, str):
        raise AnchorParseError("Invalid anchor file: midi_path is not a string")
    if not math.isfinite(midi_duration):
        raise AnchorParseError(
            f"Invalid anchor file: midi_duration_seconds is {midi_duration!r}"
        )
    if not isinstance(raw_anchors, list):
        raise AnchorParseError("Invalid anchor file: anchors is not an array")

    anchors: list[Anchor] = []
    for i, raw in enumerate(raw_anchors):
        if not isinstance(raw, dict):
            raise AnchorParseError(f"Invalid anchor file: anchors[{i}] is not an object")
        try:
            ts = float(raw["timestamp_seconds"])
        except (KeyError, TypeError, ValueError) as e:
            raise AnchorParseError(
                f"Invalid anchor file: anchors[{i}].timestamp_seconds: {e}"
            ) from e
        if not math.isfinite(ts):
            raise AnchorParseError(
                f"Invalid anchor file: anchors[{i}].timestamp_seconds is {ts!r}"
            )
        label = raw.get("label", "")
        if not isinstance(label, str):
            raise AnchorParseError(
                f"Invalid anchor file: anchors[{i}].label is not a string"
            )
        anchors.append(Anchor(timestamp_seconds=ts, label=label))

    return AnchorFile(
        midi_path=midi_path,
        midi_duration_seconds=midi_duration,
        anchors=anchors,
        saved_at=data.get("saved_at"),
    )
