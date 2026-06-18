# M2 Slice 1 — Fix-Back Brief #2 (post-ultra-review of PR #94)

**Date:** 2026-06-18 · **Status:** pass-to-code (remediation) · **Branch:** `feat/m2-slice1-unified-dispatch` (append commits; PR #94 updates on push).
**Parents:** [[M2-SLICE-1-SEAM-DESIGN]] · [[M2-SLICE-1-FIXBACK]] · framing [[M2-PARITY-AND-CUTOVER-FRAMING]].
**Source:** cloud ultra-review of PR #94 → 1 real defect + 2 nits, all confirmed against the branch by Orch triage.
**For:** a code session. Examples are **reference shapes, not rewrite mandates** — match surrounding idiom.

## Triage summary

| Item | ultra id | Sev | Disposition |
|------|----------|-----|-------------|
| **FB-U1** | bug_004 | normal | **MERGE GATE** — filter severs forward-only lineage |
| **FB-U2** | bug_005 | nit | bundle — stale read/perception docs + conflated error message |
| **FB-U3** | merged_bug_002 | nit | bundle (guard only) — `normalize_chain_body` flat-fills `ok` |

One fix-back pass on the same branch, then re-verify, then merge. **Do not touch `executor.py`** (FB3 invariant — total assent-token ban must stay green). `__all__` stays 19.

---

## FB-U1 (MERGE GATE) — mint `artifact_id` in `PrimitiveBoundary` + lineage test

**Confirmed on branch.** `_run_filter`'s success `NodeResult` sets `status`/`run_id`/`output`/`output_topology`/`artifact_type`/`source_artifact_ids`/`resolved_class` but **omits `artifact_id`** → defaults `None`. `MCPToolBoundary` mints `artifact_id=self._artifact_id_factory()` (`boundary.py:50,92`). Both boundaries derive lineage by filtering `if result.artifact_id is not None`. So on the shipped `GREENSCREEN_FILTER_ROTO` vertical:

```
greenscreen (MCP)  → artifact_id=uuid_G, source_artifact_ids=()
filter (primitive) → artifact_id=None,   source_artifact_ids=(uuid_G,)
roto (MCP)         → source_artifact_ids=()   ← uuid_G dropped: filter's None id is filtered out,
                                                  and roto does NOT walk filter.source_artifact_ids
```

**greenscreen vanishes from roto's recorded provenance** — the forward-only lineage invariant (`node_result.py:41`; `executor.py:40-42`) is severed at every primitive node. This corrupts the audit/replay provenance the `admission.py` / `resolved_class` machinery exists to serve; slice 3 (mutation traceability) and slice 6 (cutover) consume lineage and would compound from a broken base.

**Why 43-green masked it:** the compare gates only `status_vector` + normalized `terminal_output` (which *strips* `artifact_id`); every existing lineage test (`test_m1_boundary_adapter.py`, `test_m1_fan_in_vertical.py`, `test_m1_boundary_contract.py`, `test_m1_operator_sequence_compiler.py`) asserts across **MCP→MCP only** — none places a primitive in the middle. Same fixture/coverage-gap class as the FB1 toy-fake gap.

**Fix — MINT, not propagate** (Orch + ultra agree). Give `PrimitiveBoundary` an injectable `artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4` field (mirror `MCPToolBoundary` at `boundary.py:50`) and set `artifact_id=<minted>` on the success `NodeResult` in `_run_filter`. Filter becomes an **addressable derived artifact**, giving a walkable chain `greenscreen → filter → roto`.
- *Why mint, not passthrough:* the propagate alternative (`result.artifact_id or result.source_artifact_ids`) makes filter **invisible** in lineage — wrong, because the filter genuinely transformed the data (narrowed the collection) and must be addressable. Mint matches the seam design's "PrimitiveBoundary mints with `run_id`/`artifact_id`/`source_artifact_ids` exactly as `MCPToolBoundary`."
- *Mechanics:* `_run_filter` is a module-level function today — thread the factory (or the minted id) in from `dispatch`, the same way `resolved_class` is threaded. Code's call on the exact shape.
- *Error path:* the `_error()` results also omit `artifact_id`; minting there is **optional** (error nodes' downstream is short-circuited by the abort wrapper). The **ok path is the gate.**

**Parity-safe (no compare regression):** `artifact_id` is normalized out of the terminal compare, and `source_artifact_ids` is never compared — minting changes neither side's `CompareSnapshot`.

**Required test (the missing coverage that let this ship):** a lineage assertion across a primitive on `GREENSCREEN_FILTER_ROTO`:
- `filter.artifact_id is not None`,
- `filter.source_artifact_ids == (greenscreen.artifact_id,)`,
- `roto.source_artifact_ids == (filter.artifact_id,)` — the forward-only chain proven *through* the primitive node.

---

## FB-U2 (nit, bundle) — `boundary.py` scope wording + split the conflated error message

FB2 admitted roto as a make (`mcp.synchronous_make`), but `boundary.py` still claims read-only scope in four places — a contradiction this PR introduced:
- **Module docstring** (`boundary.py:16-18`): *"Generation/make operators are intentionally not admitted here … belong to M2, not this read-only boundary."* → now admits **reads + synchronous makes**.
- **Class docstring** (`:39`) and **`UnsupportedCompositionNodeError` docstring** (`:35`): drop "read/perception"-only framing.
- **The two error branches** (`:64-72`) both raise the same `"outside M1 read/perception boundary"` string for *semantically different* failures. Split them:
  - not-admitted (`AdmissionRejected`): `f"{node.operator_id!r} is not admitted to the M2 dispatch surface"` (keep `from exc`).
  - admitted-but-not-mcp (`dispatch_kind != "mcp"`): `f"{node.operator_id!r} is admitted but not an MCP operator (dispatch_kind={admission.dispatch_kind!r}); route via UnifiedDispatch"`.

Messaging/doc only — no behavioral change.

---

## FB-U3 (nit, bundle — GUARD ONLY) — `normalize_chain_body` must fail loud on statuses it can't represent

`normalize_chain_body` (`compare.py:~134-148`) only branches on `body['status'] == 'error'` and silently flat-fills `'ok'` for everything else — including `clarification_needed` (which `run_chain_steps` returns via `_recovery.response_body`) and future per-node `partial`/`abstained`. Slice-1's all-`ok` corpus doesn't trigger it, but the harness is positioned as a **reusable** parallel-run-compare boundary; the first reuse with an abstaining op or a clarifying step would report a **silent, opaque parity divergence**.

**Scope = guard only.** Add a fail-loud check: raise `ValueError` naming the offending status when `body['status']` is **not** in the recognized set (success-equivalent + `'error'`). *(Read `forge_bridge/console/_recovery.py` `response_body` for the exact success-status sentinel before writing the set.)* This converts a silent footgun into a loud, named error — the project's honest-failure-over-plausible-success discipline.

**Do NOT implement** clarification / partial / abstained *handling* — that is slice-2 Seam-D scheduled work (failure-path parity row). This guard becomes the slice-2 extension point. A small test feeding a `clarification_needed`-shaped body should assert it **raises**, not silently equals.

---

## Acceptance (re-verify before merge)

- **FB-U1:** lineage test green — `roto.source_artifact_ids == (filter.artifact_id,)` and `filter.source_artifact_ids == (greenscreen.artifact_id,)`; existing 43 still green; parity compare unchanged.
- **FB-U2:** `boundary.py` docstrings reflect read + synchronous-make; the two error branches are distinct strings.
- **FB-U3:** `normalize_chain_body` raises (with the offending status named) on an unrepresentable body; a test asserts it.
- **Invariants:** `executor.py` byte-untouched vs `main`; `__all__` 19; ruff clean; full suite green.

## Instructions for code

1. **Same branch** (`feat/m2-slice1-unified-dispatch`); append atomic commits (one per FB-U item). Push updates PR #94 in place.
2. **FB-U1 is the merge gate** — it must land. Mint via an injectable factory (symmetry with `MCPToolBoundary`) and add the across-a-primitive lineage test (the coverage that was missing).
3. **Do not touch `executor.py`** (assent-token-ban invariant). **Do not implement** clarification/partial/abstained handling in FB-U3 — guard only; handling is slice 2.
4. **Report back:** the lineage-test result (the three assertions), the FB-U3 raise-test result, suite count, `len(forge_bridge.__all__)` (must stay 19), ruff status.
