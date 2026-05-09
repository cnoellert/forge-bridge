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

from forge_bridge.corpus._capture import _DispatchContext


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
