# S3 Capture-Flow — PLAN (seam RULED; supersedes PLAN §S3)

**Status:** seam settled (`S3-SEAM-ORCH.md` + room ruling): Option B (dedicated capture endpoint) + tested route-separation invariant; outcome vocab = `preview_emitted`, `blocked_at_ratify` removed. **Base:** `main @ a5186f1`. Dev-box-first, then live-stack.

## Final architecture (pinned)
```
Operator prompt
  → request-time world_state RAW snapshot (in-Flame, FOCUS_SNAPSHOT_PY)
  → POST prompt-only → /api/v1/chat        (compile stays desktop-blind; SSE)
  → receive compiled_graph (list(outcome.steps)) + terminal outcome taxon
  → POST {prompt, compiled_graph, outcome, world_state_raw, provenance}
       → /api/v1/context-capture            (storage-only; NEVER compiles)
       → assemble_world_state → build_record → append_record
```
The compile route never receives world_state; the capture route never compiles. Resolver-blindness is structural (route separation) and **tested** (S3.3).

## Steps (dev-box-testable first → live-stack last)

### S3.0 — Outcome-vocab correction (Fork-2 ruling) *(dev-box)*
Remove `blocked_at_ratify` from `OUTCOME_VALUES` (it is interpretation, not observation; the observed mutation terminal taxon is `preview_emitted`). Pre-publication vocab correction — the corpus is seed-only, no real records exist, so `SCHEMA_VERSION` stays `"1"` (nothing shipped used it). Scope: `_schema.py` (value + comment), regenerate seed (rec1 IDX-13 + rec4 control → `preview_emitted`), update `test_schema.py` + `test_focus.py` fixtures.
- **Acceptance:** `blocked_at_ratify` absent everywhere; `OUTCOME_VALUES` aligns to SSE taxa exactly (`chain_complete, preview_emitted, apply_complete, chain_aborted, compile_error, error`); seed + all tests green.

### S3.1 — `compiled_graph` exposure (the sole live-path touch) *(dev-box testable)*
Add `"compiled_graph": list(outcome.steps)` to the `compile_complete` SSE event (`handlers.py:1209-1213`). Exposure-only — `outcome.steps` is already computed; fires pre-regime-branch for reads AND mutations. No change to compile/dispatch/routing/filtering/ratify.
- **Acceptance:** the `compile_complete` SSE event carries `compiled_graph` (list[str]) equal to `outcome.steps`, for a read and a mutation; existing chat tests unchanged (behavior identical). Test via the console SSE harness.

### S3.2 — `/api/v1/context-capture` endpoint (storage-only) *(dev-box testable)*
New handler in a **NEW module** `console/_context_capture.py` that imports ONLY `forge_bridge.context_pressure` (assemble/build/append) — **never** the compile path. Wire `Route("/api/v1/context-capture", context_capture_handler, methods=["POST"])` into `app.py`. Payload `{prompt, compiled_graph, outcome, world_state_raw, provenance}` → `assemble_world_state(world_state_raw, source=provenance.context_source)` → `build_record(...)` → `append_record(...)`. Read-only w.r.t. the live system (no Flame/pipeline mutation; only corpus append). Canonical assembler/builder server-side = single source of truth (the Option-B benefit).
- **Acceptance:** POST a fixture payload → a valid record appended (TestClient); malformed payload → 4xx with schema error; rate-limit/auth parity with sibling endpoints as applicable.

### S3.3 — Route-separation invariant (the ruling's additional requirement) *(dev-box)*
Compile-blindness becomes a **tested guarantee**, two ways:
- **Structural:** `console/_context_capture.py` does not import `compile_intent` / `run_compile_branch` / any compile-path entrypoint (static check — ast/import scan of the module).
- **Behavioral:** patch the compile entrypoints to raise; POST to `/api/v1/context-capture`; assert they are never invoked and the capture still succeeds.
- **Acceptance:** both checks green; a deliberate `import`-of-compile in the capture module fails the structural test (the guard has teeth).

### S3.4 — Console capture flow (in-Flame orchestration) *(live-stack gated)*
The SGTK-Console script: request-time `FOCUS_SNAPSHOT_PY` snapshot → POST prompt-only to `/api/v1/chat` (SSE; read `compile_complete.compiled_graph` + terminal taxon) → POST to `/api/v1/context-capture`. Maps terminal SSE taxon → `outcome` verbatim (observed fact). Needs the **live stack**: `:9996` daemon + Flame Console (NOT the executor wiring — Option-B captures at preview; the bootstrap-gap blocks only apply).
- **Acceptance (workstation):** a real Console prompt (read + mutation) produces a valid paired record on the daemon corpus; `world_state` present; `analysis=None`; the `/chat` POST carries prompt-only (resolver-blind verified on the wire).

## Sequencing + workstation dependency
Dev-box: S3.0 → S3.1 → S3.2 → S3.3 (all testable in isolation; substrate lands + tests before the consumer). Live-stack: S3.4 (the workstation dependency enters here — first step needing the running `:9996` daemon + Console). 

## The three proofs (Creative — locked by this plan)
1. **Resolver-blind:** route separation (S3.2) + tested invariant (S3.3); `/chat` POST is prompt-only.
2. **Preview-capture boundary:** capture after compiled_graph/preview, before ratify/apply; mutations record `preview_emitted`; no executor needed.
3. **No behavior mutation:** only S3.1's exposure-only field touches the live path; capture only appends.

## Constraints
`context_pressure.__all__` unchanged unless the endpoint needs a new export; `forge_bridge.__all__` 19; `SCHEMA_VERSION` "1"; `compile_intent`/`parse_chain`/`run_compile_branch` behaviorally untouched; no new external libs. The capture endpoint reuses the canonical assembler/builder — no second implementation of capture behavior anywhere.
