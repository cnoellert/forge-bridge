"""Mechanical enforcement of the Canonical Empty-Arguments Contract (PR22).

Schema-driven, runtime-semantic. Walks every tool registered against a fresh
FastMCP instance (builtins + staged-ops resources), inspects each tool's
``inputSchema``, and **invokes** ``call_tool(name, {})`` to observe what the
tool actually does — not just what its annotations claim.

Contract (see ``forge_bridge/mcp/tools.py`` module docstring +
``docs/TOOL_AUTHORING.md``):

  - If a tool's input schema has **no required fields** (Pattern A or
    Pattern B), invocation with ``{}`` MUST NOT surface a Pydantic
    ``ValidationError`` / ``Field required`` signal. The tool MAY return
    a structured error envelope from its body (e.g. "MISSING_PROJECT_ID")
    or fail with an unrelated runtime error (WS bridge unbound, Postgres
    unreachable) — those are out of scope. The contract is specifically
    about the Pydantic Arguments-schema boundary.

  - If the input schema has **required fields** (Pattern C), invocation
    with ``{}`` is expected to produce a validation error somewhere — the
    schema is doing its job. No assertion is made on this case; Pydantic
    correctly catching missing required fields is the contract working.

The discriminator between the two patterns is the JSON Schema's ``required``
list, which FastMCP populates from the handler signature at registration.
The test is therefore not a tautology — it cross-checks runtime behavior
against what the registration metadata claims about required fields.

Why runtime-semantic, not annotation-only: Python annotations can drift
from runtime truth (lazy evaluation under ``from __future__ import
annotations``, get_type_hints failing silently, decorator chains that
override the wrapper's annotations). Only invocation tells the truth.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest


# ── Helpers ─────────────────────────────────────────────────────────────────


def _looks_like_pydantic_validation_error(payload: str) -> bool:
    """Heuristic: does the payload contain Pydantic-validation-error fingerprints?"""
    s = payload.lower()
    return (
        "validation error" in s
        or "field required" in s
        or "type=missing" in s
    )


def _has_drift(input_schema: dict) -> bool:
    """Detect the PR22 anti-pattern: outer schema requires ``params`` (Pattern C
    signature) but the inner input model has NO required fields of its own.

    This is the actual drift signature — the bug A.5.2 fixed for ``forge_list_staged``.
    A tool with ``params: <Model>`` (no default) where ``<Model>`` is all-optional
    produces an outer JSON Schema with ``required: ["params"]`` referencing a
    ``$defs.<Model>`` whose own ``required`` list is empty (or absent). Calling
    such a tool with ``{}`` fails Pydantic at the outer ``params`` boundary even
    though the inner model would have happily accepted ``{}``.

    Schema shapes:

      Pattern A (zero args):       no `properties`, no `required`. → OK.
      Pattern B (Optional default): outer `properties.params` is `anyOf[$ref, null]`
                                    with `default: null`; outer `required` does NOT
                                    include `params`. → OK.
      Pattern C correct:            outer `required: ["params"]`, inner `<Model>.required`
                                    has at least one field. → OK (schema doing its job).
      Pattern C drift (this fn):    outer `required: ["params"]`, inner `<Model>.required`
                                    is empty/absent. → BUG.
    """
    if not input_schema:
        return False
    outer_required = input_schema.get("required") or []
    if "params" not in outer_required:
        return False
    properties = input_schema.get("properties") or {}
    params_prop = properties.get("params") or {}
    ref = params_prop.get("$ref")
    if not ref:
        # Inlined schema (no $ref) — inspect its required list directly.
        inner_required = params_prop.get("required") or []
        return len(inner_required) == 0
    if not ref.startswith("#/$defs/"):
        # Unfamiliar $ref shape — be conservative; not flagged as drift.
        return False
    def_name = ref[len("#/$defs/"):]
    defs = input_schema.get("$defs") or {}
    inner = defs.get(def_name) or {}
    inner_required = inner.get("required") or []
    return len(inner_required) == 0


def _has_required_inner_fields(input_schema: dict) -> bool:
    """True iff the tool is correct Pattern C (outer requires ``params`` AND
    the inner model has at least one required field). Used to discriminate
    correct Pydantic rejection from the drift case during runtime invocation."""
    if not input_schema:
        return False
    outer_required = input_schema.get("required") or []
    if "params" not in outer_required:
        return False
    properties = input_schema.get("properties") or {}
    params_prop = properties.get("params") or {}
    ref = params_prop.get("$ref")
    if not ref:
        inner_required = params_prop.get("required") or []
        return len(inner_required) > 0
    if not ref.startswith("#/$defs/"):
        return False
    def_name = ref[len("#/$defs/"):]
    defs = input_schema.get("$defs") or {}
    inner = defs.get(def_name) or {}
    inner_required = inner.get("required") or []
    return len(inner_required) > 0


# Known PR22 drift backlog — see SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+.md.
# Tools listed here are non-compliant but acknowledged; the test acts as the
# explicit migration backlog. Removing a tool from this set without migrating
# it (or adding one without updating the seed) fails the test loudly.
#
# This list was three names long when first written (the seed-known instances).
# The mechanical enforcement test itself surfaced two additional drift instances
# at A.5.2 implementation time: ``forge_get_events``, ``forge_blast_radius``,
# and ``flame_prune_batch_xml``. They were absorbed into the migration backlog
# rather than into A.5.2's scope, consistent with the phase-boundary directive
# ("fix only forge_list_staged now; plant seed for the rest").
#
# This is the substantive value of mechanical enforcement: drift that was
# previously invisible-by-inertia became visible the moment the test landed.
KNOWN_PR22_DRIFT = frozenset({
    "forge_list_media",
    "forge_list_published_plates",
    "forge_get_events",
    "forge_blast_radius",
    "flame_prune_batch_xml",
})


# ── Fixture: fresh FastMCP with builtins + staged-ops registered ────────────


@pytest.fixture(scope="module")
def populated_mcp():
    """Build a fresh FastMCP and register the same tool surface the daemon does.

    Module-scoped because FastMCP doesn't permit re-registering the same name;
    a function-scoped fixture would fail on the second test. The staged-ops
    impls require a console_read_api with a working ``get_staged_ops`` method
    — we mock just enough to let the tools' bodies return cleanly when invoked
    with ``{}``.
    """
    from mcp.server.fastmcp import FastMCP

    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI
    from forge_bridge.console.resources import register_console_resources
    from forge_bridge.mcp.registry import register_builtins

    mcp = FastMCP("forge_bridge_contract_test")
    register_builtins(mcp)

    # Build a minimal but functional ConsoleReadAPI so register_console_resources'
    # closures don't crash when invoked. ManifestService is real (lightweight);
    # ExecutionLog is mocked. The read paths return empty results — sufficient
    # for the contract test, which doesn't care about content.
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    mock_log._storage_callback = None

    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    # Stub the staged-ops read methods used by _list_staged_impl /
    # _get_staged_impl / forge_staged_pending_read.
    async def _empty_staged(**_kw):
        return [], 0
    async def _no_op_get(_id):
        return None
    api.get_staged_ops = _empty_staged          # type: ignore[assignment]
    api.get_staged_op = _no_op_get              # type: ignore[assignment]

    # session_factory is only consumed by approve/reject impls — Pattern C tools
    # whose required-field schema makes them reject {} before reaching the body.
    # A None placeholder is safe here.
    register_console_resources(mcp, ms, api, session_factory=None)

    return mcp


# ── Mechanical enforcement: every registered tool ──────────────────────────


def test_pr22_every_registered_tool_satisfies_canonical_contract(populated_mcp):
    """Walk every registered tool. Classify by schema (Pattern A, B, C-correct,
    or C-drift). For Pattern A/B, invoke with ``{}`` and verify runtime
    semantics match — runtime call MUST NOT surface a Pydantic validation
    error. For Pattern C-correct, the schema is doing its job; no runtime
    assertion. For Pattern C-drift (the anti-pattern), the tool name MUST
    appear in ``KNOWN_PR22_DRIFT`` (which is the explicit migration backlog
    documented in SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+).

    Forcing functions:

    - A new tool that ships under Pattern C-drift fails this test (it's
      not in KNOWN_PR22_DRIFT) — author must either migrate to Pattern B
      or update the seed and the allowlist.
    - A KNOWN_PR22_DRIFT tool that gets fixed without removing it from the
      allowlist fails this test (the schema no longer matches the drift
      signature) — the cleanup completes only when the allowlist updates.
    - A schema-compliant tool whose runtime invocation surfaces a Pydantic
      error fails this test (annotation/runtime divergence — the case the
      user emphasized: annotations can drift from runtime truth)."""

    async def run():
        tools = await populated_mcp.list_tools()
        return tools

    tools = asyncio.run(run())
    assert tools, "registry should be populated; if empty, the fixture is broken"

    drift_observed: set[str] = set()
    runtime_violations: list[tuple[str, str]] = []  # (name, evidence)

    for tool in tools:
        schema = tool.inputSchema or {}

        if _has_drift(schema):
            drift_observed.add(tool.name)
            # Don't bother runtime-invoking known drift — it's classified
            # by schema and the runtime would just confirm what we know.
            continue

        # Schema is compliant — runtime must agree. Invoke with {}.
        async def call():
            return await populated_mcp.call_tool(tool.name, {})

        try:
            result = asyncio.run(call())
            text = json.dumps(result, default=str) if not isinstance(result, str) else result
        except Exception as exc:
            text = f"{type(exc).__name__}: {exc}"

        if _looks_like_pydantic_validation_error(text):
            if _has_required_inner_fields(schema):
                # Pattern C correct — Pydantic rejected {} because the inner
                # model has at least one required field. That's the contract
                # working as designed.
                continue
            # Pattern A or B compliant by schema, but runtime produced a
            # Pydantic error. That's annotation/runtime divergence — exactly
            # the case the runtime-semantic test is designed to catch.
            runtime_violations.append((tool.name, text[:300]))

    # ── Assertions ─────────────────────────────────────────────────────────

    failures: list[str] = []

    new_drift = drift_observed - KNOWN_PR22_DRIFT
    if new_drift:
        failures.append(
            "NEW PR22 drift detected (not in KNOWN_PR22_DRIFT or "
            "SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+):\n"
            "  " + ", ".join(sorted(new_drift)) + "\n"
            "Either migrate the tool to Pattern B "
            "(params: Optional[<Model>] = None + body handles params is None) "
            "or, if the drift is intentional and acknowledged, add the name to "
            "KNOWN_PR22_DRIFT and update the seed."
        )

    accidentally_fixed = KNOWN_PR22_DRIFT - drift_observed
    if accidentally_fixed:
        failures.append(
            "Tools fixed but still listed as KNOWN_PR22_DRIFT:\n"
            "  " + ", ".join(sorted(accidentally_fixed)) + "\n"
            "Remove from KNOWN_PR22_DRIFT in this test AND from "
            "SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+. Migration is complete; "
            "the backlog should reflect that."
        )

    if runtime_violations:
        failures.append(
            "Annotation/runtime divergence (schema is compliant but runtime "
            "{} call surfaced Pydantic error):\n" +
            "\n".join(f"  - {name}\n    evidence: {ev}" for name, ev in runtime_violations)
        )

    if failures:
        pytest.fail("\n\n".join(failures))


def test_pr22_forge_list_staged_specifically_accepts_empty_args(populated_mcp):
    """Hand-named regression: forge_list_staged was the surfaced bug in
    Phase A.5. Its migration (Pattern C → Pattern B) is the load-bearing
    fix this phase landed. Lock it explicitly so a future revert can't
    silently re-introduce the bug under a passing aggregate test."""

    async def call():
        result = await populated_mcp.call_tool("forge_list_staged", {})
        # FastMCP call_tool may return a list of TextContent or a structured
        # tuple. Get the text payload either way.
        if isinstance(result, list) and result:
            return getattr(result[0], "text", str(result[0]))
        if isinstance(result, tuple) and len(result) >= 2:
            blocks = result[0]
            if isinstance(blocks, list) and blocks:
                return getattr(blocks[0], "text", str(blocks[0]))
            structured = result[1] or {}
            return structured.get("result", json.dumps(structured))
        return json.dumps(result, default=str)

    payload = asyncio.run(call())
    assert "validation error" not in payload.lower(), (
        f"forge_list_staged regressed to Pattern C: {payload!r}"
    )
    assert "field required" not in payload.lower(), (
        f"forge_list_staged regressed to Pattern C: {payload!r}"
    )
    # Canonical "list everything with default pagination" envelope.
    parsed = json.loads(payload)
    assert "data" in parsed, f"missing data envelope: {parsed!r}"
    assert "meta" in parsed, f"missing meta envelope: {parsed!r}"
    assert parsed["meta"].get("limit") == 50, parsed
    assert parsed["meta"].get("offset") == 0, parsed
