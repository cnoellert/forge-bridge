# BRIEF — D4: fix the `perceptual`→`perception` consumer-vocab routing defect

**Status:** EXECUTION-READY. Pulled standalone *ahead of* Rung B and Step-2.1 (room convergence 2026-06-05: Orch framing + DT grounding-verify + Creative sequencing). Grounded against `main @ b5fb79b`. Full framing: `PHASE-6A-RUNG-2B-FRAMING.md` § D4 / Finding 3.

**Why standalone + first:** this is a **live routing defect**, not an aesthetic alignment. It exists independent of B (both record shapes carry `declaration.family`), it is currently producing incorrect behavior against real Vision, and every concrete defect removed sharpens the post-2A evidence for whether B earns a planner re-ripple at all. Clear the bug before opening the convergence. [[feedback_routing_vs_implementation_vs_reachability]]

## The defect (grounded — `planner_passes.py:242-265`, pass_3 content-policy-bypass transform insertion)
```python
perceptual = planner.tool_registry.by_family("perceptual")   # DEAD VOCAB → always [] vs real Vision
matte      = planner.tool_registry.by_family("matte")
provider   = perceptual[0] if perceptual else (matte[0] if matte else None)
```
The registry stores `declaration.family` verbatim (`registration.py:70`); contract-conformant Vision declares **`perception`** (`KNOWN_CAPABILITY_FAMILIES`), never `perceptual`. So `by_family("perceptual")` is **always empty in production**, and the provider selection for the `rule-14` content-policy bypass degrades to:
- **Mis-route (perception + matte both present):** silently selects the **matte** provider for a content-policy bypass that should route to the perception classifier. Wrong `providing_operator`, wrong transform.
- **False refusal (perception present, no matte):** `provider is None` → raises `transform_unavailable` for a transform that *was* satisfiable.

Content-policy/governance-adjacent (`rule-14`, `content_policy_real_person_classifier`) — the routing target is not cosmetic.

**Why it stayed invisible (twin masks):** (1) `test_planner.py:483` builds its provider with `family="perceptual"` — the test mirrors the bug, so it passes [[feedback_fixture_shape_mirrors_production]]; (2) the live proof (`test_sibling_discovery_live.py`) runs a capability *query* only, never pass_3.

## Scope
- **IS:** correct the single divergent consumer-side family literal `perceptual` → `perception`; correct the refusal message string; un-mask the test fixture; add a discriminating regression that would have caught the production divergence.
- **IS NOT:** ❌ Rung B (declaration-storage) · ❌ Step-2.1 (de-shadow context) · ❌ widen the generation-only fallback snapshot (`planner_passes.py:84`) · ❌ any change to the provider-preference *ordering* (perception-preferred, matte-fallback is intended — only the family string was wrong) · ❌ touch the `matte`/`generation` literals (verified correct against `KNOWN_CAPABILITY_FAMILIES`).

## Changes — 2 files

### 1. `forge_bridge/orchestration/planner_passes.py` (pass_3, ~line 248)
```python
perception = planner.tool_registry.by_family("perception")   # was "perceptual"
matte      = planner.tool_registry.by_family("matte")
provider   = perception[0] if perception else (matte[0] if matte else None)
```
And the refusal message (~line 254): `"...no perceptual/matte provider"` → `"...no perception/matte provider"`. (Local variable rename `perceptual`→`perception` is for legibility; the load-bearing change is the `by_family` argument.)

### 2. `tests/test_planner.py`
- **Un-mask** `test_plan_transform_inserted_when_provider_exists` (~line 483): change the registered provider's `family="perceptual"` → `family="perception"`. With the source fixed this still passes; against the *old* source it would now fail — that is the point (the fixture stops mirroring the bug).
- **Add a discriminating regression** — register **both** a `perception` provider and a `matte` provider, assert the inserted transform's `providing_operator` is the **perception** provider's `tool_id` (not matte). Against the bug (`perceptual` query empty) this picks matte and fails; against the fix it picks perception and passes. This is the test that would have caught the production divergence. (A second assertion — perception-only, no matte, asserts a transform is inserted rather than `transform_unavailable` — covers the false-refusal mode; include if cheap.)

## Acceptance
1. **Completeness proof (equivalence class):** `grep -rn 'by_family(' forge_bridge/` and every family-string literal in `planner_passes.py`/`planner.py`, diffed against `KNOWN_CAPABILITY_FAMILIES` — confirm `perceptual` was the **only** divergent consumer-side literal and no `perceptual` remains anywhere in `forge_bridge/`. [[feedback_grep_c_completion_invariant]] (DT verified the class is complete at 2 sites — re-confirm post-edit it's 0.)
2. The discriminating regression **fails on the pre-fix source** and **passes on the fixed source** (demonstrate the unmask, don't just assert green).
3. Full planner suite green: `pytest tests/test_planner.py` + the orchestration subset (`test_sibling_registration.py`, `test_sibling_discovery_live.py`); ruff clean on the 2 changed files.
4. No diff to provider-preference ordering, the generation fallback snapshot, the registry, or `registration.py` — this is a consumer-vocab fix only.

## Done-signal (post-merge)
One commit `fix(phase-6a): route content-policy transform to perception (was dead 'perceptual' vocab)`. Update `PHASE-6A-RUNG-2B-FRAMING.md` § D4 → RESOLVED with the commit sha; note the equivalence class closed at 0 residual `perceptual` literals. D2 (Step-2.1) remains discuss-ready; D3 (Rung B) re-opens for convergence with the burden flipped — *what defect remains that only raw `CapabilityDeclaration` adoption solves?*
