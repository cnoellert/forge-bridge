"""Tests for v1.0.1 timeline.rename_shots gap-fill fix.

The previous canonical rename_shots would silently skip T0 gaps: when the
background track had a gap-segment at a record range, no shot name was
assigned and subsequent shots renumbered. The fix scans upward tracks
(T1, T2, ...) to find a real segment covering the gap range and uses it
as the shot's source of truth.

The algorithm lives inside a Python-string that is shipped to Flame via
bridge.execute_json — so these tests verify the code template itself
contains the required markers (gap_fills set, upward track loop,
id(fill_seg) tracking) and that the rename_shots signature is unchanged.

End-to-end verification of the gap-fill behavior against a real Flame
instance is out-of-scope for the unit test suite (requires Flame runtime);
projekt-forge's staging verification exercises the code path against
a live sequence.
"""

from __future__ import annotations

import inspect
import json
import re

from forge_bridge.tools import timeline


# ── Public signature preserved ─────────────────────────────────────────


def test_rename_shots_is_coroutine():
    assert inspect.iscoroutinefunction(timeline.rename_shots)


def test_rename_shots_accepts_RenameInput():
    sig = inspect.signature(timeline.rename_shots)
    params = list(sig.parameters)
    assert params == ["params"]
    # Annotation resolves to RenameInput (string form acceptable under
    # `from __future__ import annotations`)
    ann = sig.parameters["params"].annotation
    assert ann is timeline.RenameInput or ann == "RenameInput"


# ── Gap-fill algorithm markers in generated code ──────────────────────


def _source_of(fn) -> str:
    """Return the source text of rename_shots so we can assert on the
    inline Flame-side Python string it builds."""
    return inspect.getsource(fn)


def test_gap_fills_set_present_in_rename_shots_code():
    """The gap_fills set is the core of the fix — ensures an upper-track
    segment used as a T0 gap fill is not re-renamed during Pass 2."""
    src = _source_of(timeline.rename_shots)
    assert "gap_fills" in src


def test_gap_fills_tracks_segments_by_id():
    """The set stores id(seg) (not the segment itself) because Flame
    PySegment objects are not hashable by identity semantics we want."""
    src = _source_of(timeline.rename_shots)
    # gap_fills.add(id(fill_seg)) or similar pattern
    assert re.search(r"gap_fills\.add\(\s*id\(", src), (
        "Expected gap_fills.add(id(...)) pattern in rename_shots code"
    )


def test_rename_shots_has_upward_track_scan_for_gap_fill():
    """When T0 is a gap, the algorithm must iterate upper tracks to find
    a real segment covering the gap range."""
    src = _source_of(timeline.rename_shots)
    # The upward scan iterates track indices starting from 1
    assert re.search(r"for\s+\w+\s+in\s+range\(\s*1\s*,\s*len\(tracks\)", src), (
        "Expected 'for <idx> in range(1, len(tracks))' upward scan in rename_shots"
    )


def test_pass2_skips_segments_already_used_as_gap_fills():
    """Pass 2 propagation must skip any segment id() already recorded in
    gap_fills — otherwise the fill segment gets a second shot name."""
    src = _source_of(timeline.rename_shots)
    assert "id(seg) in gap_fills" in src, (
        "Expected 'id(seg) in gap_fills' guard in Pass 2 propagation"
    )


# ── Pure-gap column (no upper-track fill) branch ───────────────────────


def test_rename_shots_handles_pure_gap_column():
    """When T0 is a gap AND no upper track has a real segment at that
    range, the algorithm must still append a (None, ...) entry to bg_map
    so record-range bookkeeping stays consistent for later propagation."""
    src = _source_of(timeline.rename_shots)
    # The pure-gap branch appends (None, gap_in, gap_out) to bg_map
    assert re.search(r"bg_map\.append\(\s*\(\s*None\s*,", src), (
        "Expected bg_map.append((None, ...)) for pure-gap columns"
    )


# ── Sanity: existing shots_assigned counter still incremented ─────────


def test_shots_assigned_counter_incremented_on_fill():
    """When an upper-track segment fills a T0 gap, shots_assigned must
    increment — otherwise the rename shot numbering skips."""
    src = _source_of(timeline.rename_shots)
    # Find a block of code around the gap-fill branch that increments
    # shots_assigned. Check that shots_assigned is incremented more than
    # once in the function (once in the fill branch, once in the normal
    # non-gap branch).
    assert src.count("shots_assigned") >= 3, (
        "Expected multiple shots_assigned references (init, fill, non-gap)"
    )


def test_rename_shots_uses_worker_bridge_for_inner_idle_event(monkeypatch):
    """The generated Flame code schedules its own idle callback and waits.

    Sending that wrapper through bridge main_thread=True would put the wait
    itself on Flame's main thread, preventing the scheduled callback from
    running until the wait releases.
    """
    captured: dict = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        captured["main_thread"] = main_thread
        return {"renamed": 0}

    monkeypatch.setattr(timeline.bridge, "execute_json", _fake_execute_json)

    import asyncio

    out = asyncio.run(
        timeline.rename_shots(
            timeline.RenameInput(
                sequence_name="30sec_21",
                prefix="genesis",
                padding=4,
                increment=10,
                start=10,
            ),
        ),
    )

    assert json.loads(out)["renamed"] == 0
    assert "flame.schedule_idle_event(_do)" in captured["code"]
    assert captured["main_thread"] is False


def test_rename_shots_numbers_from_start_by_increment():
    src = _source_of(timeline.rename_shots)

    assert "num_str   = str(shot_num).zfill(padding)" in src
    assert "shot_num += increment" in src
    assert "shot_num * increment" not in src


def test_rename_defaults_start_at_first_ten():
    assert timeline.RenameInput(
        sequence_name="30sec_21",
        prefix="genesis",
    ).start == 10
    assert timeline.PreviewRenameInput(
        sequence_name="30sec_21",
        prefix="genesis",
    ).start == 10


def test_phase25_mutation_inputs_expose_dry_run_port():
    assert timeline.RenameInput(
        sequence_name="30sec_21",
        prefix="genesis",
    ).dry_run is False
    assert timeline.SetStartFramesInput(sequence_name="30sec_21").dry_run is False
    assert timeline.SetSegmentInput(
        sequence_name="30sec_21",
        segment_name="seg01",
        attribute="comment",
        value="ok",
    ).dry_run is False
    assert timeline.AssignRolesInput(
        sequence_names=["30sec_21"],
        assignments={"seg01": "comp"},
    ).dry_run is False


def test_rename_shots_dry_run_template_does_not_write_names():
    src = _source_of(timeline.rename_shots)

    assert "dry_run" in src
    assert "'proposed_changes': result.get('changes', [])" in src
    assert re.search(r"if dry_run:.*?else:\s+seg\.name\.set_value", src, re.S)
    assert re.search(r"if not dry_run:\s+seg\.shot_name\.set_value", src)


def test_legacy_preview_rename_delegates_to_dry_run_rename(monkeypatch):
    captured = {}

    async def _fake_rename(params):
        captured["params"] = params
        return json.dumps({"dry_run": True})

    monkeypatch.setattr(timeline, "rename_shots", _fake_rename)

    import asyncio

    out = asyncio.run(
        timeline.preview_rename(
            timeline.PreviewRenameInput(
                sequence_name="30sec_21",
                prefix="genesis",
            ),
        ),
    )

    assert json.loads(out) == {"dry_run": True}
    assert captured["params"].dry_run is True
    assert captured["params"].sequence_name == "30sec_21"
    assert captured["params"].prefix == "genesis"


def test_legacy_preview_start_frames_delegates_to_dry_run_set_start(monkeypatch):
    captured = {}

    async def _fake_set_start_frames(params):
        captured["params"] = params
        return json.dumps({"dry_run": True})

    monkeypatch.setattr(timeline, "set_start_frames", _fake_set_start_frames)

    import asyncio

    out = asyncio.run(
        timeline.preview_start_frames(
            timeline.PreviewStartFramesInput(sequence_name="30sec_21"),
        ),
    )

    assert json.loads(out) == {"dry_run": True}
    assert captured["params"].dry_run is True
    assert captured["params"].sequence_name == "30sec_21"


def test_rename_shots_infers_padding_from_existing_shot_names():
    src = _source_of(timeline.rename_shots)

    assert "existing_padding_widths = []" in src
    assert r"_(\\d+)(?:_|$)" in src
    assert "existing_padding_widths.append(len(m.group(1)))" in src
    assert "len(set(existing_padding_widths)) == 1" in src
    assert "padding = existing_padding_widths[0]" in src


def test_rename_shots_preview_preserves_existing_padding(monkeypatch):
    captured: dict = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        captured["main_thread"] = main_thread
        return {
            "dry_run": True,
            "proposed_changes": [
                {
                    "index": 0,
                    "current": "genesis_0010_source_L01",
                    "proposed": "nova_0010_source_L01",
                    "type": "shot_name",
                },
            ],
            "count": 1,
        }

    monkeypatch.setattr(timeline.bridge, "execute_json", _fake_execute_json)

    import asyncio

    out = asyncio.run(
        timeline.rename_shots(
            timeline.RenameInput(
                sequence_name="30sec_21",
                prefix="nova",
                dry_run=True,
            ),
        ),
    )

    assert json.loads(out)["proposed_changes"][0]["proposed"] == (
        "nova_0010_source_L01"
    )
    assert "padding = existing_padding_widths[0]" in captured["code"]
    assert captured["main_thread"] is False


def test_rename_shots_uses_provided_padding_when_no_existing_pattern(monkeypatch):
    captured: dict = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        return {"dry_run": True, "proposed_changes": [], "count": 0}

    monkeypatch.setattr(timeline.bridge, "execute_json", _fake_execute_json)

    import asyncio

    asyncio.run(
        timeline.rename_shots(
            timeline.RenameInput(
                sequence_name="30sec_21",
                prefix="nova",
                padding=5,
                dry_run=True,
            ),
        ),
    )

    assert "padding             = 5" in captured["code"]
    assert "if existing_padding_widths and len(set(existing_padding_widths)) == 1" in (
        captured["code"]
    )
