"""tests.corpus.test_pr7_dispatch_context — PR 7 Step 3+ tests.

Dispatch-provenance substrate (Step 3), scope surface (Step 4),
and resolution path (Step 5) tests for the contextvar layer
introduced in ``forge_bridge/corpus/_capture.py``.

See ``forge_bridge/corpus/_sources.py`` module docstring for the
14 inherited carriers + binding framing clarification (verbatim).
The §4.2 inert-parameter binding pair (verbatim, scope-local to
``_capture.py``) is documented at the production module; this
test module enforces the pair mechanically via
``test_call_site_source_value_is_inert`` (lands at Step 5).

Step-by-step test landings (per ``A.5.3.2-PR7-SPEC.md`` §6):

- Step 3 (this commit): ``test_dispatch_context_dataclass_is_frozen``.
- Step 4: ``test_scope_resets_on_exception``,
  ``test_nested_scope_inner_overrides``.
- Step 5: ``test_scope_inactive_persists_runtime``,
  ``test_scope_active_persists_seed_and_fixture_id``,
  ``test_call_site_source_value_is_inert``.

Total at PR 7 close: 6 tests in this file.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from forge_bridge.corpus._capture import (
    _DispatchContext,
    _dispatch_context,
    seed_dispatch_scope,
)


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
    path inside ``emit_divergence_capture``) lands at Step 5.
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
