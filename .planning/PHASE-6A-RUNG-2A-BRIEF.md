# BRIEF — Rung 2A: decompose the discovery record from invocation state

**Status:** READY TO IMPLEMENT (ratified framing 2026-06-05, deliberately not yet started). Grounded against `main @ 4b88bf2`. Full framing + rationale: `PHASE-6A-DISCOVERY-ALIGNMENT.md` § "Registry-type separation — framing input → RATIFIED FRAMING."

**Goal:** the registry's stored record must stop carrying invocation state. Drop `handler` from `ToolRegistration` (it becomes the declaration record). The handler still flows *through* `register` to its binding home (`GenerationDriverRegistry`) — it's just no longer *stored* on the record. Zero downstream ripple (the planner reads `.handler` 0×; grounded).

**Principle:** `register` is the split point — `register_capability(CapabilityRegistration)` → (a) declaration → registry, (b) handler-if-present → `GenerationDriverRegistry`. Preserve the battle-tested topology ([[feedback_brief_examples_as_behavioral_reference_shapes]]); this is a surgical field-drop + a param move, **not** a rewrite.

## Scope
- **IS:** drop `handler` from the stored record; declaration-pure registry; route `handler`→`drivers.py` at register-time; leave the `backend_id` seam named-in-code.
- **IS NOT:** ❌ store `CapabilityDeclaration` directly (deferred rung B) · ❌ adopt the published `BridgeRegistrationContext`/`RegisterCapabilityCallable` (Step-2.1, deferred with B) · ❌ build any invocation/dispatch path or capability→driver resolver · ❌ widen the generation-only snapshot · ❌ **introduce any uniform `InvocationHandler` abstraction** (invocation is family-shaped; no evidence two families need the same one).

## Changes — 3 files

### 1. `forge_bridge/orchestration/registration.py`
**(a)** `ToolRegistration` — remove the `handler` field → `{tool_id, family, payload_family, schema, capabilities}`. Update docstring: "Bridge-internal DECLARATION record (discovery-side, invocation-free)… invocation binding is NOT stored here — see ToolRegistry.register."

**(b)** `tool_registration_from_capability` — delete the `handler=registration.handler,` line from the returned `ToolRegistration`. Note in docstring that the handler is routed by `register`, not stored.

**(c)** `ToolRegistry.register` — take `handler` as a keyword param, read it there instead of `tool.handler`:
```python
def register(self, tool: ToolRegistration, *, sibling_name: str, handler: Any = None) -> None:
    if tool.tool_id in self._tools:
        raise DuplicateToolIdError(tool.tool_id)
    # The registry stores declaration-only records. Invocation binding is
    # family-shaped + invocation-time: route the handler to its binding home
    # (generation -> GenerationDriverRegistry); never store it on the record.
    # SEAM (named, not filled): backend_id reconciliation. The driver's own
    # handler.backend_id is independent of the planner's declaration-derived
    # backend_identity_triple (planner_passes pass_1); nothing reconciles them.
    # Materialize the reconciler only when a plan step first needs to EXECUTE a
    # selected capability (Phase 7). See PHASE-6A-DISCOVERY-ALIGNMENT.md.
    if tool.family == "generation" and handler is not None:
        _validate_generation_handler(tool.tool_id, handler)
        if self._generation_driver_registry is not None:
            self._generation_driver_registry.register_driver(handler)
    self._tools[tool.tool_id] = tool
    self._pending_events.append(...)  # unchanged
```

### 2. `forge_bridge/orchestration/discovery.py`
In `register_all_siblings`'s inner `register_capability` callback, forward the handler:
```python
def register_capability(registration: CapabilityRegistration):
    tool = tool_registration_from_capability(registration)
    tool_registry.register(tool, sibling_name=sibling_name, handler=registration.handler)
    families_registered.add(tool.family)
```

### 3. `tests/test_sibling_registration.py`
- `_tool(...)` helper — drop `handler` from the `ToolRegistration(...)` it builds (and from its signature).
- The **ToolRegistry unit tests** that exercise generation validation pass the handler via the new `register` param, e.g. `registry.register(_tool("gen.bad", family="generation"), sibling_name="s", handler=_MissingBackendIdDriver())`. Affected: `test_tool_registry_register_and_query`, `…invalid_generation_missing_backend_id`, `…invalid_generation_missing_poll`, `…generation_wires_driver_registry`, `…generation_without_driver_registry`.
- The `register_all_siblings` **integration tests are unchanged** — they go through `register_capability` (which now forwards `registration.handler`); `_cap(...)` already carries the handler on the `CapabilityRegistration`.

## Acceptance
1. `grep -rn '\.handler' forge_bridge/orchestration/ forge_bridge/store/` → **only** the `register` param + its routing in `registration.py`; **no `tool.handler` anywhere**, none in `planner_passes.py`/snapshot.
2. `ToolRegistration` has **no `handler` field**; stored `_tools` records are declaration-only.
3. Generation validation + driver-routing still fire (handler via param): the 5 unit tests pass with assertions intact (`InvalidGenerationDriverError` on bad drivers; `get_driver(...)` side-effect on good ones).
4. **Full orchestration suite green** (`pytest tests/test_sibling_registration.py tests/test_planner.py tests/test_replay_engine.py tests/test_manifest_assembler.py` + the rung-1 classification test) and **ruff clean** on the 3 changed files.
5. **Live proof unaffected** — `tests/test_sibling_discovery_live.py` still passes (declaration-only siblings already registered with `handler=None`; behavior identical).
6. Snapshot/planner untouched (no diff in `planner_passes.py`).

## Done-signal (post-merge)
One commit `feat(phase-6a): rung 2A — decompose declaration record from invocation state`. Mark Rung 2 **landed** in `PHASE-6A-DISCOVERY-ALIGNMENT.md` + the workstream memory, noting the `backend_id` seam is now named-in-code at the register site.
