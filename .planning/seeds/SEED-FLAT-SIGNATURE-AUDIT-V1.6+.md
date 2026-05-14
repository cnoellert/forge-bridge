---
name: SEED-FLAT-SIGNATURE-AUDIT-V1.6+
description: Phase 23.1 in-flight discovery — the project-wide convention of "every tool function takes a Pydantic BaseModel first parameter" generates NESTED JSON schemas FastMCP exposes to the LLM. The chat model consistently fails to produce the nested shape and dispatch fails BEFORE the tool body runs. flame_execute_python was carved out and flattened; the wider convention audit (which other tools silently suffer the same failure mode?) is deferred to v1.6.
type: convention-audit
planted_during: Phase 23.1 author-walk on portofino 2026-05-14 — Gate 3 surfaced silent dispatch failure on flame_execute_python; root-cause investigation revealed FastMCP generates `{"params": {"code": "..."}}` nested schema from `execute_python(params: ExecutePythonInput)` signature. Model could not generate the nested shape. Flat signature → flat schema → instant fix.
trigger_when: v1.6 milestone opens OR a second flame_* tool surfaces dispatch failure with the same shape (model picks tool, zero wrapper logs, status=tool_error in router) OR FastMCP schema introspection is being updated for any reason OR the per-tool latency / error-rate doctor surface from SEED-FLAME-EXEC-OBSERVABILITY-V1.6+ ships and shows other tools with anomalous error rates
---

# SEED-FLAT-SIGNATURE-AUDIT-V1.6+

## The Convention

Project convention (enforced by `tests/test_tools.py::test_pydantic_coverage`): every parameterized tool function in `forge_bridge/tools/{batch,project,publish,reconform,switch_grade,timeline,utility}` takes a single Pydantic BaseModel as its first argument. Examples:

```python
async def list_libraries(params: Optional[ListLibrariesInput] = None) -> str: ...
async def rename_shots(params: RenameShotsInput) -> str: ...
async def set_segment_attribute(params: SetSegmentAttributeInput) -> str: ...
```

The convention was introduced for typing consistency, schema-generation predictability, and parameter-validation centralization. It's been in the codebase since the v1.0 tool parity phases.

## The Problem (Discovered 2026-05-14)

FastMCP introspects function signatures to generate the JSON schema each tool exposes to the LLM. With a BaseModel-wrapped signature, the generated schema is **nested**:

```json
{
  "required": ["params"],
  "properties": {
    "params": { "$ref": "#/$defs/ExecutePythonInput" }
  }
}
```

The chat model must generate `{"params": {"code": "...", "main_thread": false}}` — a nested wrapped shape with an explicit `params` key at the top level. The model consistently generates the flat `{"code": "...", "main_thread": false}` shape instead. Pydantic validation fails at FastMCP dispatch BEFORE the function body runs. Zero tool-wrapper log records emit. The router logs `tool=flame_execute_python status=tool_error elapsed_ms=N` without ever calling the function.

The failure is silent to the model (it sees an "error" but doesn't know the args shape was wrong) and silent to the operator (no wrapper logs, no traceback, just "tool_error" with no detail).

## What 23.1 Did

Flattened `flame_execute_python` only. Function signature changed from:

```python
async def execute_python(params: ExecutePythonInput) -> str: ...
```

to:

```python
async def execute_python(code: str, main_thread: bool = False) -> str: ...
```

Generated schema becomes flat:

```json
{
  "required": ["code"],
  "properties": {
    "code": {"type": "string"},
    "main_thread": {"type": "boolean", "default": false}
  }
}
```

Tests `test_utility_models` and `test_pydantic_coverage` got carve-outs for `execute_python` explicitly. Tests `test_flame_execute_python_mcp_schema_is_flat_not_nested` was added as a regression guard.

## What 23.1 DID NOT Do

The other ~30 tool functions in `forge_bridge/tools/` still use BaseModel-wrapped signatures. Some are infrequently called (the chat surface doesn't currently exercise most of them through model-authored args), but several are first-class candidates for the same silent failure:

- `flame_rename_shots` — model has to compose rename args
- `flame_set_segment_attribute` — model has to compose attribute updates
- `flame_publish_sequence` — model has to compose publish parameters
- `flame_find_media` — already showed `status=tool_error` repeatedly in the 23.1 author-walk log alongside `flame_execute_python`. Same failure mode? Worth investigating.
- All `flame_assign_roles`, `flame_clone_version`, `flame_create_version`, etc. — any tool the model is expected to invoke with non-trivial args.

The 23.1 forcing function was "the dogfood query converges." Auditing the wider tool surface is feature-creep on a ship-blocker patch and explicitly out of scope.

## The Audit (v1.6 Scope)

A v1.6 audit phase should:

1. **Enumerate** all parameterized tool functions across the seven `tools/` modules.
2. **Probe each tool's MCP schema** via the same pattern 23.1 used:

    ```python
    from mcp.server.fastmcp import FastMCP
    from forge_bridge.mcp.registry import register_builtins
    mcp = FastMCP("audit")
    register_builtins(mcp)
    for name, tool in mcp._tool_manager._tools.items():
        schema = tool.parameters
        nested = "params" in schema.get("properties", {}) and \
                 "params" in schema.get("required", [])
        print(f"{name}: nested={nested}")
    ```

3. **Cross-reference against the router's per-tool `status=tool_error` rates** (from the structured logs SEED-FLAME-EXEC-OBSERVABILITY-V1.6+ ships). Tools with high `tool_error` rates AND nested schemas are confirmed instances of the 23.1 failure mode.
4. **Decide the policy** — three options:
   - **Flatten all parameterized tools** to direct kwargs. Drops the BaseModel convention entirely. Most aggressive; widest behavioral change; cleanest result. Tests test_utility_models / test_pydantic_coverage get retired or repurposed.
   - **Flatten only tools the model actually invokes with non-trivial args.** Keep BaseModel for tools called primarily by code (consumers, tests, the chain engine with explicit JSON). Narrower; preserves typing benefit for internal callers; requires per-tool judgment.
   - **Teach FastMCP to flatten BaseModel signatures at registration time.** Most architectural — adapt the registry layer so wrapped functions automatically expose flat schemas. Keeps the developer-side BaseModel ergonomics while fixing the LLM-side schema problem. Requires the deepest change.

The right answer depends on how many tools turn out to suffer the silent-dispatch failure. If it's 1-3, narrow flattening. If it's 10+, the registry-layer fix wins. If it's all of them, drop the convention.

## Why Plant Now

Three reasons:

1. **The discovery is fresh and the framing matters.** Without the seed, the 23.1 `_FLAT_SIGNATURE_EXCEPTIONS = {"execute_python"}` carve-out reads as ad-hoc magic rather than principled deviation. The seed converts the deviation into a milestone-level policy question.
2. **`flame_find_media` and other 23.1 walk surfaces showed `status=tool_error` patterns.** That's a second instance hiding in plain sight. v1.6's audit phase has a concrete starting point.
3. **The convention is enforced by tests.** Any future developer who tries to flatten another tool will hit the same `test_pydantic_coverage` failure. The seed names the canonical workaround (add to `_FLAT_SIGNATURE_EXCEPTIONS`) and explicitly defers the wider audit.

## Activation Triggers

Any of:

1. **v1.6 milestone opens** — natural sequencing; the audit composes cleanly into v1.6 Phase 26 (Console Exec view + schema universalization).
2. **A second flame_* tool surfaces the dispatch failure** with the same fingerprint: model picks tool, zero wrapper logs, router status=tool_error, args_hash repeats. The 23.1 walk already showed `flame_find_media` with this shape — first re-investigation point.
3. **FastMCP schema introspection updates** — any FastMCP version bump or schema-generation change is a chance to audit; piggyback the protocol-layer fix on that work.
4. **Per-tool error-rate doctor surface ships** (per SEED-FLAME-EXEC-OBSERVABILITY-V1.6+ Stage 4). Doctor showing flame_X with anomalous tool_error rate is the empirical trigger for "audit X's signature first."

## Cross-References

- 23.1 in-flight gap-fix: [forge_bridge/tools/utility.py](forge_bridge/tools/utility.py) — `execute_python` signature flatten (the working pattern).
- 23.1 regression guard: [tests/test_flame_execute_python.py](tests/test_flame_execute_python.py) — `test_flame_execute_python_mcp_schema_is_flat_not_nested`.
- 23.1 convention carve-outs: [tests/test_tools.py](tests/test_tools.py) — `_FLAT_SIGNATURE_EXCEPTIONS` constant in `test_utility_models` and `test_pydantic_coverage`.
- 23.1 CONTEXT: [.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md](.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md) — original phase boundary (this seed is post-walk archaeology, not in original scope).
- v1.6 framing: [.planning/milestones/v1.6-FRAMING.md](.planning/milestones/v1.6-FRAMING.md) — §11.1 Phase 26 schema universalization.
- Sibling seed: `SEED-FLAME-EXEC-OBSERVABILITY-V1.6+` — the per-tool error-rate doctor surface that surfaces audit candidates empirically.

## The One-Line Lesson

> A typing convention chosen for developer ergonomics can silently break the LLM-callable surface. Audit before you assume "the convention is fine because the tests pass" — the tests test the wrong layer.

23.1 found this for one tool. v1.6 should find it for all of them.
