---
name: SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+
description: Backlog of MCP tools currently using PR22 Pattern C with all-optional input models — should be migrated to Pattern B. Migration is mechanical; surfaced by the contract enforcement test in tests/test_tool_contract_enforcement.py once it lands.
type: forward-looking-idea
planted_during: 2026-05-06 (Phase A.5.2 — canonical empty-arguments contract established + forge_list_staged migrated)
trigger_when: The mechanical contract enforcement test lands and surfaces these tools as failing, OR a smoke-test run lands the narrower on one of these tools and reproduces the same Pydantic validation error that A.5.2 closed for forge_list_staged
---

# SEED-TOOL-CONTRACT-PR22-MIGRATION-V1.5+

## Background

Phase A.5.2 (2026-05-06) established the **Canonical Empty-Arguments Contract (PR22)** as load-bearing project vocabulary. See `docs/TOOL_AUTHORING.md` for the durable architectural reference, and the module docstring at the top of `forge_bridge/mcp/tools.py` for the operational binding.

A.5.2 fixed **only** the tool that surfaced in smoke tests (`forge_list_staged`) and planted this seed for the remaining known drift. The phase boundary was deliberate: the canonical-contract decision plus mechanical enforcement is the load-bearing output; sweeping migrations across multiple tools were not necessary for the phase goal and would have constituted scope creep.

## Drift backlog

The following tools currently use PR22 **Pattern C** (`params: <Model>` required) but their input models have **all-optional fields** — the same drift signature as `forge_list_staged` had before A.5.2 migrated it. All fail the mechanical enforcement test in `tests/test_tool_contract_enforcement.py`; they are present in the test's `KNOWN_PR22_DRIFT` allowlist as the explicit migration queue.

The first two were known when this seed was first planted. The other three were **surfaced by the mechanical enforcement test itself** at the moment it landed in A.5.2 — they had been latent in the codebase but invisible-by-inertia. That visibility is the protective value the test exists to produce.

| Tool | File:Line | Input model | Required fields |
|------|-----------|-------------|------------------|
| `forge_list_media` | `forge_bridge/mcp/tools.py:list_media` | `ListMediaInput` | none — all four (`project_id`, `status`, `shot_name`, `kind`) are `Optional[str] = Field(default=None, ...)` |
| `forge_list_published_plates` | `forge_bridge/mcp/tools.py:list_published_plates` | `ListPublishedPlatesInput` | none — all four (`project_id`, `shot_name`, `sequence_name`, `colour_space`) are `Optional[str] = Field(default=None, ...)` |
| `forge_get_events` | `forge_bridge/mcp/tools.py:get_events` | `GetEventsInput` | none — `project_id` and `entity_id` are `Optional[str] = Field(default=None, ...)`; `limit` is `int = Field(default=20, ...)` |
| `forge_blast_radius` | `forge_bridge/mcp/tools.py:blast_radius` | `BlastRadiusInput` | none — all three (`media_id`, `media_name`, `project_id`) are `Optional[str] = Field(default=None, ...)` |
| `flame_prune_batch_xml` | `forge_bridge/tools/batch.py:prune_batch_xml` | `PruneBatchXmlInput` | none — both fields (`batch_path`, `shot_dir`) are `str = Field(default="", ...)` (empty-string default is technically Pattern-B-equivalent at the inner-model layer; outer `params` is still required) |

These have not surfaced in operator-visible failures yet because the message-narrower has not landed on any of them as a single survivor for an empty-arguments call. They are latent bugs that would surface the moment a chat prompt or `/api/v1/exec` invocation collapses to one of them.

## Migration recipe (mechanical, per tool)

Each tool migrates with the same three-step pattern that `forge_list_staged` followed in A.5.2:

1. **Update the handler signature** (in `forge_bridge/mcp/tools.py`):
   ```python
   # Before (Pattern C with all-optional model — anti-pattern):
   async def list_media(params: ListMediaInput) -> str: ...

   # After (Pattern B):
   async def list_media(params: Optional[ListMediaInput] = None) -> str: ...
   ```

2. **Handle `params is None` at the top of the body** — canonical "default everything" interpretation:
   ```python
   if params is None:
       params = ListMediaInput()
   ```
   The body's existing logic (filtering on `params.status`, `params.shot_name`, etc.) then runs against the all-defaults instance, which means "list everything with default filters."

3. **Run the contract enforcement test** — should now pass for the migrated tool.

That's it per tool. Cost is bounded: ~5 lines of code per tool plus the test pass.

## Acceptance criteria when this lands

- `tests/test_tool_contract_enforcement.py` passes for both `forge_list_media` and `forge_list_published_plates` (was failing before).
- Both tools, when invoked through `/api/v1/exec` or the chat handler's PR20 short-circuit with no arguments, return a structured success envelope (the unfiltered list) instead of a Pydantic validation error.
- A regression test exercises each tool's `{}` invocation directly and asserts the structured envelope shape.

## Why deferred

The A.5.2 phase boundary was "establish the contract + enforce it + close the surfaced bug." The remaining migrations are mechanical and known; deferring them keeps A.5.2 narrow and lets the mechanical enforcement test surface the migration list as a failing-test queue rather than as silent backlog. That visibility is itself the protective mechanism — the test fails, the migration becomes obvious, the work is bounded.

If the mechanical enforcement test surfaces additional drift instances beyond the two named here (for example, in flame_* tools or in synthesized tools that later acquire all-optional input models), they should be appended to this seed's drift table at the time of discovery.

## Cross-references

- `docs/TOOL_AUTHORING.md` — the durable architectural reference for the contract.
- `forge_bridge/mcp/tools.py` (module docstring) — the operational binding.
- `tests/test_tool_contract_enforcement.py` — the mechanical enforcement test that surfaces these as failures.
- `tests/test_pr22_tool_contract.py` — the original PR22 tests (hand-picked tools); a good template for per-tool regression coverage during migration.
- `.planning/phases/A.5-chain-execution-reliability-audit/PHASE-A.5-SPEC.md` — phase that established the contract and migrated `forge_list_staged`.
