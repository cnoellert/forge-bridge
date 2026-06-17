"""Regression guard for forge-bridge#69: the fail-closed authority gate.

Context. `test_exec_stage_entry.py` / `test_stage_chain.py` mock
`forge_assess_drift` with ``annotations.readOnlyHint=True``. That lets the
routing-real chain pass the exec-path authority gate *in tests* — but the real
vision op shipped **without** that declaration, so on the live daemon it
classified ``mutating`` and was rejected at step 0 (forge-vision#2). The
fixtures, by asserting the happy path through a ``readOnlyHint=True`` mock,
neutralized the regression surface for "is a sibling read op actually drivable
on the exec path?".

These tests assert the gate *directly*, not around it:

1. ``dispatch_authority`` fail-closed semantics as a truth table — a tool must
   carry ``readOnlyHint is True`` (strict identity) to be a read; anything else
   (missing, ``False``, ``None`` annotations, truthy-but-not-``True``) is
   mutating.
2. The exec entry (``execute_command``) rejects a sibling tool that omits
   ``readOnlyHint`` with ``unauthorized_mutation`` / ``classification:
   mutating`` — i.e. the exact live forge-vision#2 symptom, reproduced without
   a mock that hides it.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from forge_bridge.console._authority import dispatch_authority
from forge_bridge.console._execute import execute_command
from tests.console.test_pr30_chain import _text_block

_DRIFT_CHAIN = (
    "forge_assess_drift -> if(disposition == drifted) -> stage(ee_drift_review)"
)


def _tool(annotations) -> SimpleNamespace:
    return SimpleNamespace(
        name="forge_assess_drift",
        annotations=annotations,
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


# ── 1. Fail-closed truth table ────────────────────────────────────────────────
# dispatch_authority returns True == "treat as mutating" == block on read path.

@pytest.mark.parametrize(
    ("annotations", "is_mutating", "why"),
    [
        (SimpleNamespace(readOnlyHint=True), False, "explicit read authority"),
        (SimpleNamespace(readOnlyHint=False), True, "explicitly not a read"),
        (SimpleNamespace(idempotentHint=True), True, "readOnlyHint absent → fail closed"),
        (None, True, "no annotations at all → fail closed"),
        (SimpleNamespace(readOnlyHint="true"), True, "truthy-but-not-True → fail closed"),
        (SimpleNamespace(readOnlyHint=1), True, "1 is not True (strict identity)"),
    ],
)
def test_dispatch_authority_is_fail_closed(annotations, is_mutating, why):
    assert dispatch_authority(_tool(annotations)) is is_mutating, why


# ── 2. Exec path rejects an undeclared sibling read (the forge-vision#2 symptom)


def _assessment(disposition: str) -> dict:
    return {"disposition": disposition, "artifact": {}}


class _UndeclaredAssessMCP:
    """Exposes `forge_assess_drift` WITHOUT readOnlyHint — like vision shipped it.

    The op genuinely only reads, but absent the declaration bridge cannot know
    that and fail-closes. This is the mock the masking fixtures should have used
    to keep the regression surface alive.
    """

    async def list_tools(self):
        # annotations carries a routing family but NOT readOnlyHint — exactly
        # the live gap: a family signal is not a mutation-safety fact.
        return [_tool(SimpleNamespace(family="validation"))]

    async def call_tool(self, name, arguments):  # pragma: no cover - must never run
        raise AssertionError(
            "call_tool reached: a mutating-classified tool must be blocked "
            "before dispatch on the read-only exec path"
        )


@pytest.mark.asyncio
async def test_exec_rejects_sibling_read_missing_readonlyhint(session_factory):
    result = await execute_command(
        _DRIFT_CHAIN,
        mcp=_UndeclaredAssessMCP(),
        session_factory=session_factory,
    )

    assert result["status"] == "error", result
    blob = json.dumps(result)
    assert "unauthorized_mutation" in blob, result
    assert "forge_assess_drift" in blob, result


@pytest.mark.asyncio
async def test_exec_admits_sibling_read_with_readonlyhint(session_factory):
    """The positive control: declaring it read-only makes the same chain run."""

    class _DeclaredAssessMCP:
        async def list_tools(self):
            return [_tool(SimpleNamespace(readOnlyHint=True))]

        async def call_tool(self, name, arguments):
            return _text_block(json.dumps(_assessment("drifted")))

    result = await execute_command(
        _DRIFT_CHAIN,
        mcp=_DeclaredAssessMCP(),
        session_factory=session_factory,
    )

    # Not blocked by the gate: it gets past classification and dispatches.
    assert "unauthorized_mutation" not in json.dumps(result), result
