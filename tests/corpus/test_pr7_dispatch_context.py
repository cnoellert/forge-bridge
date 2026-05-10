"""tests.corpus.test_pr7_dispatch_context — PR 7 Step 3+ tests.

Dispatch-provenance substrate (Step 3), scope surface (Step 4),
and resolution path (Step 6) tests for the contextvar layer
introduced in ``forge_bridge/corpus/_capture.py``.

See ``forge_bridge/corpus/_sources.py`` module docstring for the
14 inherited carriers + binding framing clarification (verbatim).
The §4.2 inert-parameter binding pair (verbatim, scope-local to
``_capture.py``) is documented at the production module; this
test module enforces the pair mechanically via
``test_call_site_source_value_is_inert`` (lands at Step 6).

Step-by-step test landings (per ``A.5.3.2-PR7-SPEC.md`` §6):

- Step 3: ``test_dispatch_context_dataclass_is_frozen``.
- Step 4: ``test_scope_resets_on_exception``,
  ``test_nested_scope_inner_overrides``.
- Step 6: ``test_scope_inactive_persists_runtime``,
  ``test_scope_active_persists_seed_and_fixture_id``,
  ``test_call_site_source_value_is_inert``.

Total at PR 7 close: 6 tests in this file.

Step 6 (resolution-path) reorder: the three persistence-shaped
tests below were originally drafted as Step 5 in the spec; the
§4.3 amendment reordered Step 5↔Step 6 so the schema validator
landing (now Step 5) precedes the resolution path emitting
``source="seed"`` records (now Step 6). The tests' substance is
unchanged; only the step number moved.
"""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from forge_bridge.corpus import emit_divergence_capture
from forge_bridge.corpus._capture import (
    _DispatchContext,
    _dispatch_context,
    seed_dispatch_scope,
)

from tests.corpus._pr3_helpers import base_writer_args


# ── Step 6 helpers (mechanical duplication from test_pr3_writer.py) ────────
#
# Duplicated rather than promoted to ``_pr3_helpers.py`` to keep Step 6
# minimal-touch. The two helpers are trivial path/IO utilities, not
# carrier-bearing. Future consolidation (if any) lives at a refactor
# step explicitly authorized by spec — not smuggled into Step 6's
# resolution-path scope.


def _today_capture_path(corpus_dir: Path) -> Path:
    """Locate the ``capture-YYYY-MM-DD.jsonl`` file in ``corpus_dir``.

    Returns the unique match; fails if zero or more than one file
    exists. Used by tests that emit one or more records and then
    assert on the resulting file.
    """
    matches = list(corpus_dir.glob("capture-*.jsonl"))
    assert len(matches) == 1, (
        f"expected exactly one capture file in {corpus_dir}, "
        f"found {len(matches)}: {matches}"
    )
    return matches[0]


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_dispatch_context_dataclass_is_frozen() -> None:
    """Step 3. Asserts ``_DispatchContext`` is structurally frozen.

    The frozen-dataclass contract is load-bearing per
    ``A.5.3.2-PR7-SPEC.md`` §4.2.2: the dispatch context is
    constructed at exactly one site (the scope helper, Step 4) and
    must not be mutated across the yield point of the context
    manager. ``frozen=True`` is the structural guarantee — Python
    raises ``FrozenInstanceError`` on attribute assignment.

    Failing this test means a future PR removed ``frozen=True``
    from the dataclass declaration. Reject at CI; review surfaces
    the framing-level decision (the bounded-surface property in
    spec §4.1: dispatch state constructed at one site, persisted at
    one site, inspected at one site).
    """
    ctx = _DispatchContext(source="seed", fixture_id="fix-001")

    with pytest.raises(FrozenInstanceError):
        ctx.source = "runtime"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        ctx.fixture_id = "fix-002"  # type: ignore[misc]


def test_scope_resets_on_exception() -> None:
    """Step 4. Asserts the contextvar resets even when the body raises.

    The scope helper's ``finally`` block must call
    ``_dispatch_context.reset(token)`` regardless of whether the
    ``with`` body completed normally or raised. Without this
    guarantee, an exception inside a seed dispatch would leak
    ``source="seed"`` provenance into subsequent runtime emissions
    — a silent provenance corruption mode the test guards against.

    Risk #1 (per ``A.5.3.2-PR7-SPEC.md`` §3): "Contextvar leaks
    across scope boundary." This test fires when the leak occurs.
    """
    sentinel = RuntimeError("intentional probe failure")

    assert _dispatch_context.get() is None

    with pytest.raises(RuntimeError) as excinfo:
        with seed_dispatch_scope(fixture_id="fix-leak"):
            assert _dispatch_context.get() is not None
            raise sentinel

    assert excinfo.value is sentinel
    assert _dispatch_context.get() is None


def test_nested_scope_inner_overrides() -> None:
    """Step 4. Asserts nested scopes follow ContextVar stack semantics.

    Inside an outer scope with ``fixture_id="outer"``, opening a
    nested scope with ``fixture_id="inner"`` must shift the
    contextvar to the inner payload. After the inner scope exits,
    the contextvar must restore to the outer payload — not collapse
    to ``None``. Locks ``ContextVar.set/reset``'s stack discipline
    structurally so future contributors do not assume the scope
    helper is single-shot.

    The test exercises the dispatch-context's value transitions
    only; persistence behavior (which depends on the resolution
    path inside ``emit_divergence_capture``) lands at Step 6.
    """
    assert _dispatch_context.get() is None

    with seed_dispatch_scope(fixture_id="outer"):
        outer_ctx = _dispatch_context.get()
        assert outer_ctx is not None
        assert outer_ctx.source == "seed"
        assert outer_ctx.fixture_id == "outer"

        with seed_dispatch_scope(fixture_id="inner"):
            inner_ctx = _dispatch_context.get()
            assert inner_ctx is not None
            assert inner_ctx.source == "seed"
            assert inner_ctx.fixture_id == "inner"

        # Inner scope exited; outer payload restored.
        restored_ctx = _dispatch_context.get()
        assert restored_ctx is not None
        assert restored_ctx.fixture_id == "outer"

    # Outer scope exited; contextvar back to None.
    assert _dispatch_context.get() is None


# ── Step 6: resolution-path persistence tests ──────────────────────────────


def test_scope_inactive_persists_runtime(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Step 6. Without an active scope, persisted records carry
    ``source="runtime"`` and ``fixture_id`` is ``None``.

    This test fires the inactive branch of the resolution path inside
    ``emit_divergence_capture`` (spec §4.2.5): the contextvar default
    (``None``) yields ``resolved_source = "runtime"`` and
    ``resolved_fixture_id = None``, which the builder then emits
    explicitly into the persisted record.

    Failing this test means the resolution path's inactive branch is
    broken — either the contextvar default isn't ``None`` (which
    would mean Step 3 regressed) or the builder's record dict no
    longer always includes ``"fixture_id"`` (which would mean the
    Q3 cleanup-pressure-resistance property has been violated).
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args(prompt="step6-inactive"))

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)
    # 1 header + 1 record
    assert len(lines) == 2
    record = json.loads(lines[1])

    assert record["source"] == "runtime"
    assert record["fixture_id"] is None


def test_scope_active_persists_seed_and_fixture_id(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Step 6. Inside ``seed_dispatch_scope``, persisted records
    carry ``source="seed"`` and the supplied ``fixture_id``.

    This test fires the active branch of the resolution path: the
    contextvar payload yields ``resolved_source = ctx.source`` (i.e.
    ``"seed"``) and ``resolved_fixture_id = ctx.fixture_id``, both
    emitted into the persisted record verbatim.

    Failing this test means either the scope helper isn't setting
    the contextvar (Step 4 regression) or the resolution path inside
    ``emit_divergence_capture`` isn't consulting it (Step 6
    regression).
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    fixture_id = "fix-pr7-step6"
    with seed_dispatch_scope(fixture_id=fixture_id):
        emit_divergence_capture(**base_writer_args(prompt="step6-active"))

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)
    assert len(lines) == 2
    record = json.loads(lines[1])

    assert record["source"] == "seed"
    assert record["fixture_id"] == fixture_id


def test_call_site_source_value_is_inert(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Step 6. The call-site ``source`` parameter does not influence
    the persisted ``source`` field.

    This is the mechanical assertion for the §4.2 inert-parameter
    binding pair (verbatim in ``_capture.py`` module + helper
    docstrings). The pair states the call-site ``source`` literal
    is structurally authoritative (Property C) and operationally
    inert (no participation in persisted-provenance resolution).

    The test passes deliberately invalid call-site source values
    (``"this-is-garbage"``, ``"another-garbage"``) — values that
    would fail schema validation if they leaked through. Two
    emissions: one without scope (expect persisted
    ``source="runtime"``), one inside scope (expect persisted
    ``source="seed"``). In both cases the call-site garbage is
    overwritten by the resolution path; the persisted records
    validate cleanly and round-trip with contextvar-derived values.

    Two failure modes signal a regression:
    1. Bug type A — call-site value leaks into the record AND
       schema accepts it: the assertion ``record["source"] ==
       "runtime"`` (or ``"seed"``) fails directly.
    2. Bug type B — call-site value leaks into the record AND
       schema rejects it: the I-6 wrapper swallows the failure
       and writes nothing; ``_today_capture_path`` then fails
       at the "exactly one capture file" assertion.

    Either failure mode means Step 6 has accidentally collapsed
    structural declaration into operational provenance — exactly
    the cleanup-pressure-resistance failure mode the §4.2 binding
    pair protects against.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    # Emission 1: no scope; call-site source is garbage.
    emit_divergence_capture(
        **base_writer_args(prompt="inert-1", source="this-is-garbage")
    )

    # Emission 2: inside scope; call-site source is different garbage.
    fixture_id = "fix-inert-test"
    with seed_dispatch_scope(fixture_id=fixture_id):
        emit_divergence_capture(
            **base_writer_args(prompt="inert-2", source="another-garbage")
        )

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)
    # 1 header + 2 records
    assert len(lines) == 3
    records = [json.loads(line) for line in lines[1:]]

    # Emission 1: no scope → persisted runtime, no fixture_id.
    assert records[0]["prompt"] == "inert-1"
    assert records[0]["source"] == "runtime"
    assert records[0]["fixture_id"] is None

    # Emission 2: scope active → persisted seed + fixture_id.
    assert records[1]["prompt"] == "inert-2"
    assert records[1]["source"] == "seed"
    assert records[1]["fixture_id"] == fixture_id
