# BRIEF — D2 / Step-2.1: adopt the published registration types (de-shadow)

**Status:** EXECUTION-READY (discuss-ratified — strong lean YES, DT grounded LOW-RISK; operator routed). Grounded against `main @ 4be6d52`. Framing: `PHASE-6A-RUNG-2B-FRAMING.md` § D2 + § "DT grounding items — RESOLVED" item 1.

**Goal:** retire bridge's two local *shadows* of published forge-contracts types and use the contract types directly:
- `RegisterCapabilityCallable` (local alias, `registration.py:22`) → `forge_contracts.registration.RegisterCapabilityCallable`
- `BridgeRegistrationContext` (local frozen dataclass, `registration.py:26-40`) → `forge_contracts.registration.BridgeRegistrationContext` (pydantic)

**Why:** bridge already imports `CapabilityDeclaration`/`CapabilityRegistration` from the contract; these two are the last registration-protocol shadows. The siblings already import the *published* `BridgeRegistrationContext` — so today bridge constructs its own duck-typed twin and hands siblings a different class that happens to match. After D2 bridge and siblings share **one** type. This is the contained half of motion (2); it does **not** touch the planner (that's Rung B / D3). [[feedback_substrate_pass_translation_open]]

## Grounding (live reads @ `4be6d52`)
- Published `BridgeRegistrationContext` fields: `bridge_version` (REQUIRED) · `contract_version` (default `'v0.1'`) · `requested_families` (`list[str]`, factory default) · `dry_run` (default `False`) · `config` (factory default). Bridge constructs `{bridge_version, requested_families, dry_run, config}` at `discovery.py:145` — a subset; the published type accepts it and defaults `contract_version`.
- Published `RegisterCapabilityCallable` == bridge's local alias byte-for-byte (`Callable[[CapabilityRegistration], None]`).
- DT-confirmed: bridge **never reads context fields back** (constructed `:145`, forwarded as `ctx` param `:97` into `_invoke_sibling`, never inspected); `contract_version` referenced nowhere; `requested_families` never set-op'd bridge-side; request-all passes empty ⇒ `frozenset`→`list` is moot.

## Scope
- **IS:** delete the two local shadow definitions; source both names from `forge_contracts.registration`; keep them re-exported from `forge_bridge.orchestration` (back-compat, same names); construct the pydantic context at `discovery.py:145`; adapt any test that *constructs* the context or asserts `requested_families` is a `frozenset`.
- **IS NOT:** ❌ touch `RegisterToolCallable` (`registration.py:23`) — that is a **bridge-internal** alias of the `ToolRegistration`-shaped callback, **not** a contract shadow; leave it · ❌ touch `ToolRegistration` / `ToolRegistry` / the registry record (that's Rung B/D3) · ❌ any planner change · ❌ wire a dynamic `contract_version` (accept the `'v0.1'` default) · ❌ change `forge_bridge.__all__` (stays **19**; this lives under `forge_bridge.orchestration.__all__`, which keeps the same names).

## Changes — 3 files (+ test adaptations)

### 1. `forge_bridge/orchestration/registration.py`
- **Extend the contract import** (`:10`): add the two types. Use the module they're defined in:
  ```python
  from forge_contracts import CapabilityDeclaration, CapabilityRegistration
  from forge_contracts.registration import (
      BridgeRegistrationContext,
      RegisterCapabilityCallable,
  )
  ```
  (If the package re-exports them at top level, code may fold them into the first line for symmetry — code's call; whichever import resolves.)
- **Delete** the local `RegisterCapabilityCallable = Callable[...]` (`:22`) and the entire local `BridgeRegistrationContext` dataclass (`:26-40`).
- **Keep** `RegisterToolCallable` (`:23`) untouched — bridge-internal, not a shadow.
- The docstring content currently on the local class (the request-all / "do not pass bridge's local vocab" warning) is *behavioral guidance for the construction site* — relocate it as a comment at the `discovery.py:145` construction site so it isn't lost when the class is deleted. [[feedback_doc_provenance_discipline]]

### 2. `forge_bridge/orchestration/discovery.py`
- Import (`:21`) now resolves `BridgeRegistrationContext` from `registration` (which re-imports it from the contract) — no change needed if it keeps importing from `..registration`.
- **Construction site (`:145`)** — build the pydantic model; pass `requested_families` as a **`list[str]`** (not a `frozenset`) to match the published field, and omit `contract_version` (accept the `'v0.1'` default):
  ```python
  ctx = BridgeRegistrationContext(
      bridge_version=bridge_version,
      requested_families=list(requested_families or []),   # request-all = []
      dry_run=dry_run,
      config=dict(sibling_config.get(sibling_name, {})),
  )
  ```
  Carry the relocated "empty = request-all; never pass bridge's local family vocab" comment here.

### 3. `forge_bridge/orchestration/__init__.py`
- No name changes: `BridgeRegistrationContext` + `RegisterCapabilityCallable` stay imported from `.registration` (`:53-54`) and stay in `__all__` (`:99,103`). They now resolve to the contract types transparently. Confirm the re-export still imports cleanly.

### Test adaptations — `tests/test_sibling_registration.py`
- `:23` import + `:438` `captured: list[BridgeRegistrationContext]` annotation — fine as-is (same name).
- Any test that **constructs** `BridgeRegistrationContext(...)` must supply at least `bridge_version` (others default) and pass `requested_families` as a `list`. Any assertion that `ctx.requested_families` is a `frozenset` → assert `list`/membership instead. (DT: nothing set-ops it, so equality/membership assertions are the likely shape.)

## Acceptance
1. `grep -rn "class BridgeRegistrationContext\|^RegisterCapabilityCallable" forge_bridge/` → **zero** local definitions; both names resolve to `forge_contracts.registration.*` (e.g. `python -c "from forge_bridge.orchestration import BridgeRegistrationContext, RegisterCapabilityCallable; import forge_contracts.registration as r; assert BridgeRegistrationContext is r.BridgeRegistrationContext"`).
2. `RegisterToolCallable` still defined locally (`registration.py`) — **untouched** (proof we didn't over-scrub the bridge-internal alias).
3. `forge_bridge.__all__` → **19**; `forge_bridge.orchestration.__all__` unchanged (same names exported).
4. Live proof green: `tests/test_sibling_discovery_live.py` (bridge constructs the published context, request-all still empty, both primaries discovered). Full subset green: `pytest tests/test_sibling_registration.py tests/test_planner.py tests/test_sibling_discovery_live.py`; ruff clean on changed files.
5. The relocated request-all guidance comment lands at the `discovery.py` construction site (provenance preserved).
6. No diff to the planner, `ToolRegistration`, or `ToolRegistry`.

## Done-signal (post-merge)
One commit `refactor(phase-6a): adopt published BridgeRegistrationContext + RegisterCapabilityCallable (de-shadow)`. Update `PHASE-6A-RUNG-2B-FRAMING.md` § D2 → RESOLVED with the sha; note bridge and siblings now share one registration context type. Then **D3 (Rung B) is the only motion-2 piece left** — open it as a convergence pass, burden flipped: *what defect remains that only raw `CapabilityDeclaration` adoption solves?*
