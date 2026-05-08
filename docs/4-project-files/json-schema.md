# JSON schema (v1)

The anchor save file is a single UTF-8 JSON document with `indent=2`, strict finite-number policy (`allow_nan=False`), and **`schema_version == 1`**. This page documents every field with types and validation rules.

The reference implementation lives in `disklavier_visualizer/io/anchor_io.py`. Tests in `tests/test_anchor_io.py` exercise round-trips, sort-on-save, and every rejection rule.

## Example

```json
{
  "schema_version": 1,
  "saved_at": "2026-05-08T15:42:08.317491+00:00",
  "midi_path": "C:\\Users\\me\\study\\trial_001.mid",
  "midi_duration_seconds": 187.402,
  "anchors": [
    {
      "timestamp_seconds": 12.456,
      "label": "phrase 1 opening"
    },
    {
      "timestamp_seconds": 47.802,
      "label": ""
    },
    {
      "timestamp_seconds": 174.417,
      "label": "first cord d"
    }
  ]
}
```

## Top level

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | int | Yes | Must equal `1`. Any other value raises `AnchorParseError("Unsupported schema version: …")`. |
| `saved_at` | string or null | No | ISO 8601 timestamp in UTC, written by `save_anchors`. Optional on load — if missing, becomes `None` in the runtime `AnchorFile`. Not validated as a date format. |
| `midi_path` | string | Yes | **Absolute** path to the MIDI file at save time. Not normalized on load. |
| `midi_duration_seconds` | float | Yes | Duration of the bound MIDI in seconds. Must be finite (NaN / Infinity rejected). Used at load time to detect drift. |
| `anchors` | array of Anchor | Yes | May be empty. |

## Anchor

| Field | Type | Required | Notes |
|---|---|---|---|
| `timestamp_seconds` | float | Yes | Seconds from the start of the MIDI file. Must be finite. Out-of-range values (`< 0` or `> midi_duration_seconds`) are clamped on UI load with a warning, but the JSON itself is not rejected. |
| `label` | string | No | Optional (defaults to `""` on load if missing). Free text — UTF-8, no length limit, may contain whitespace. |

## Validation rules

`load_anchors` enforces these checks. Any failure raises `AnchorParseError` with a specific reason:

- The file exists and can be opened.
- The content is valid JSON.
- The top-level value is an object (not an array, string, etc.).
- `schema_version` equals `1`.
- `midi_path` is a string.
- `midi_duration_seconds` is convertible to a finite `float`.
- `anchors` is a list.
- For every anchor:
    - The element is an object.
    - `timestamp_seconds` is convertible to a finite `float`.
    - `label`, if present, is a string.

The validation is **strict and non-recoverable** — if any check fails, the load aborts and the previous in-memory anchors (if any) are preserved.

What is **not** checked at load time:

- That `midi_path` exists on disk. The UI checks separately and prompts to relocate.
- That `midi_duration_seconds > 0`. The on-disk format allows zero or negative durations; in practice they would never be saved.
- That timestamps are within `[0, midi_duration_seconds]`. The UI clamps on load with a status-bar warning rather than rejecting the file.
- That timestamps are sorted. They are sorted on save, but the loader accepts any order (the UI re-sorts in `set_anchors`).

## Sort-on-save

`save_anchors` sorts the anchors by `timestamp_seconds` ascending **for the on-disk copy only**. The in-memory `AnchorFile.anchors` list is not reordered. The reason: re-saving the same session produces a stable diff (no spurious reordering of identical entries), but the UI ordering is not disturbed.

The runtime `AnchorTableWidget` keeps its anchors sorted independently anyway, so in normal UI flow the on-disk order matches the in-memory order.

## Numeric encoding

- `allow_nan=False` is passed to `json.dump`. If a serializer attempts to write `NaN`, `Infinity`, or `-Infinity`, it raises `ValueError` at save time. This surfaces in the UI as `Could not save anchors`.
- The loader uses Python's standard `json.load`, which by default accepts `NaN` / `Infinity` (these are non-standard JSON extensions). `load_anchors` then explicitly checks `math.isfinite(...)` on every numeric field — non-finite values are rejected with `AnchorParseError`.

So a hand-edited file with `Infinity` in it is rejected at load time, not silently accepted.

## Path encoding on Windows

JSON requires backslashes inside strings to be escaped as `\\`. Python's `json.dumps` does this automatically:

```
"C:\Users\me\study\trial_001.mid"   ← what a user might type
"C:\\Users\\me\\study\\trial_001.mid"  ← what JSON requires
```

`save_anchors` always produces correctly-escaped output. When hand-editing on Windows, double-check that backslashes are doubled.

A test in `test_anchor_io.py:88-94` verifies that Windows-style absolute paths round-trip with backslashes intact.

## Editing the JSON by hand

Hand-editing is supported. The schema is intentionally flat — no hashes, no signatures, no checksums. The rules:

1. Keep `schema_version == 1`.
2. Keep every numeric field finite (no `NaN`, `Infinity`, `-Infinity`).
3. Keep `midi_path` as a string. It can be an empty string, but the UI's path-existence check will then fail and prompt to relocate.
4. Keep every `anchor.timestamp_seconds` finite. Out-of-range values are clamped on UI load.
5. Keep `anchor.label` as a string (or omit it entirely — it defaults to `""`).

If you break a structural rule, loading the file raises `AnchorParseError` with a descriptive message, and your in-memory state is preserved.

## What's deliberately not in the schema

- **No anchor IDs.** Anchors are identified by their position in the array (and that position changes when you add/remove others). This is fine because the schema does not support cross-references.
- **No region anchors.** Each anchor is a single timestamp. Region annotations (start + end) would need a v2 schema.
- **No categories or colours.** Labels are free text.
- **No app version, no Python version, no machine ID.** Only the data needed to reload the session is stored. The minimum delta between saves is the timestamp set + `saved_at`.

## Future schema versions

If the schema ever changes (e.g. adding region anchors), the version bump strategy is:

1. Bump `SCHEMA_VERSION` in `anchor_io.py`.
2. Add a load-time migration path for `schema_version == 1` files (read the v1 fields, populate sensible defaults for the new fields, return a v2-shaped `AnchorFile`).
3. Always save in the latest version.

Currently there is only `v1`, so the loader rejects anything else outright. Any v2 release would need to relax that check before accepting old files.
