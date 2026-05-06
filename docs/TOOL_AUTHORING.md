# Authoring MCP tools in forge-bridge

This document is the durable architectural reference for the **Canonical Empty-Arguments Contract (PR22)** that governs every tool registered with FastMCP via `mcp.tool()`. The operational version of the same rules lives at the top of `forge_bridge/mcp/tools.py` — they should be read together. The module docstring is binding; this document is the rationale, the vocabulary, and the migration guidance.

## Why this contract exists

The chat handler's PR20 deterministic forced-execution path invokes a tool with `arguments={}` whenever the message-narrower collapses to exactly one survivor. The same `arguments={}` shape is sent by `/api/v1/exec` when the deterministic chain engine reaches a single tool with no extracted parameters. Both paths are load-bearing for daily use; both produce identical Pydantic-validation failures when a tool's handler signature does not allow `{}`.

PR22 closed that gap by establishing a single, mechanically-enforceable rule: **every registered tool must accept `{}` either by trivially having no parameters, by making the wrapping `params` argument optional with a `None` default, or by genuinely requiring a field that the caller actually needs to supply**. The choice is not stylistic — it is determined by what the tool's input model legitimately requires.

The contract exists because, without it, every new tool that ships with an all-optional input model under `params: <Model>` (no default) silently re-introduces the failure. The smoke tests in Phase A.5 surfaced one such drift (`forge_list_staged`); a mechanical enforcement test prevents future drift.

## The three canonical patterns

These three patterns are conceptual vocabulary, not just signatures. Future contributors should be able to say "this tool should be Pattern B" and have that mean exactly one thing.

### Pattern A — zero args

```python
async def f() -> str: ...
```

Use when the tool has no parameters at all. The MCP `Arguments` schema is empty; `{}` is accepted trivially.

**Examples in the codebase:** `ping`, `list_projects`, `list_roles`, `forge_staged_pending_read`.

### Pattern B — defaultable params

```python
from typing import Optional

async def f(params: Optional[ListShotsInput] = None) -> str:
    if params is None:
        # treat as default-everything, OR return a structured _err() naming
        # the missing required-business field (the tool's choice).
        params = ListShotsInput()
    ...
```

Use when **all fields** in the input model are optional with sensible defaults, **or** the tool can return a useful structured-error envelope naming a missing business field rather than letting Pydantic raise. The body MUST handle `params is None`. The body MUST NOT raise on `None`.

**Examples in the codebase:** `list_shots`, `list_versions` (both return a structured `_err("project_id required")` when called without args, instead of letting Pydantic raise).

This pattern is what `forge_list_staged` migrated to in Phase A.5.2. Its input model has all-optional fields (status, limit=50, offset=0, project_id all default to None); when called with `{}` it now returns the full list with default pagination.

### Pattern C — required params

```python
async def f(params: GetShotInput) -> str: ...
```

Use **only** when the input model has at least one **required** field (`Field(..., ...)`). Pydantic correctly rejects `{}` because the caller is genuinely missing required input — that IS the contract. The schema is doing its job; surfacing the validation error to the chat handler tells the user exactly which field is missing.

**Examples in the codebase:** `get_shot` (requires `shot_id`), `update_shot_status` (requires `shot_id` + `status`), `forge_approve_staged` (requires `id` + `actor`), `forge_reject_staged` (same).

A Pattern-C tool's failure on `{}` is the correct outcome — it tells the LLM (or operator) "you forgot to provide the required input." Migrating it to Pattern B would silently swallow that signal.

## Anti-pattern (forbidden by enforcement)

```python
async def f(params: AllOptionalModel) -> str: ...   # ← forbidden
```

Where `AllOptionalModel`'s fields all have defaults. This silently re-introduces the original PR22 failure: the FastMCP-generated `Arguments` schema requires `params` as a non-null field, but the model itself permits `{}`-equivalent input — the caller has no way to satisfy both. The forced-call wrapper sends `{}`, Pydantic rejects, the user sees `Field required [type=missing] params`.

**The mechanical enforcement test catches this case at CI time, not at runtime.** A new tool that ships with an all-optional input model under Pattern C will fail the test and block the merge.

If your input model has all-optional fields, the correct pattern is **B**, not C. If you want the schema to surface "required" semantics, add the required field to the input model and use Pattern C — don't paper over it with Pattern C on an all-optional model.

## Decision tree (for new tools)

```
                       Does the tool need any parameters?
                              ├── No  → Pattern A (zero args)
                              └── Yes
                                    ↓
                  Does <Model> have any REQUIRED field
                  (Field(..., ...) without default)?
                              ├── No   → Pattern B (Optional[Model] = None)
                              └── Yes  → Pattern C (Model required)
```

## Mechanical enforcement

The test suite walks every registered tool, inspects the input schema (the FastMCP `Tool.inputSchema` JSON Schema), and asserts the runtime behavior matches the contract:

- If the input schema has **no required fields** → `mcp.call_tool(name, {})` MUST succeed (or return a structured error envelope; it MUST NOT raise a Pydantic `ValidationError`).
- If the input schema has **required fields** → `mcp.call_tool(name, {})` MUST surface a Pydantic-style validation error referring to the missing field. This is correct Pattern-C behavior.

The enforcement is **runtime-semantic**, not type-annotation-only — annotations can drift from registration metadata; only invocation tells the truth. See `tests/test_tool_contract_enforcement.py`.

A new tool that violates the contract fails the enforcement test at CI time. A registration-time assertion would be cleaner but the FastMCP registry is populated lazily by lifespan; the test runs after registration completes and gives the same coverage with simpler scaffolding.

## Migration path for existing drift

The mechanical enforcement test surfaces all current drift instances in the codebase. As of Phase A.5.2 closure, the known drift candidates outside of `forge_list_staged` (which was migrated in A.5.2) are tracked in `.planning/seeds/SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+.md`. They will fail the enforcement test once the test lands; the seed records the migration plan.

Migrating a Pattern-C-with-all-optional-fields tool to Pattern B is mechanical:

1. Update the handler signature: `params: <Model>` → `params: Optional[<Model>] = None`.
2. Update the impl: add an `if params is None: params = <Model>()` (or equivalent default-handling) at the top of the body.
3. Run the contract enforcement test — the migrated tool should now pass.
4. Add a regression test that exercises `mcp.call_tool(name, {})` and asserts the structured success envelope (or graceful structured error if the tool needs business input it cannot default).

The migration is small per tool. The cost is bounded; the discipline is binding going forward.

## Cross-references

- Module docstring at `forge_bridge/mcp/tools.py` — operational surface (binding).
- `tests/test_pr22_tool_contract.py` — the original PR22 contract tests (hand-picked tools).
- `tests/test_tool_contract_enforcement.py` — schema-driven mechanical enforcement (all registered tools).
- `.planning/seeds/SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+.md` — known drift backlog at A.5.2 closure.
- `.planning/phases/A.5-chain-execution-reliability-audit/PHASE-A.5-SPEC.md` — phase that landed `forge_list_staged` migration + mechanical enforcement.
- `forge_bridge/console/handlers.py` — `_execute_forced_tool` is the chat-side caller that sends `{}`; `api_v1_exec_handler` is the deterministic-engine caller that does the same.
