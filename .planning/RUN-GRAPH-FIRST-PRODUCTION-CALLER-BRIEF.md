# `run_graph` — first production caller for the graph runtime (#66 / #104 live reachability)

**Status:** BUILD BRIEF (Orch + Creative + DT converged). DT redlines + verifies; extra attention on Caution #1.
**Base:** main `c4683ad`. **Asked-for by:** forge-pipeline (#104) — "land live daemon wiring + a runnable graph entrypoint/example; confirm registry + receipt sink." **Origin:** dropped #66 slice-2 (mechanism-demo tangent) for the production caller Pipeline actually needs.

---

## 0. Load-bearing framing — this is a NAMED, BOUNDED crossing of "zero production callers"

`run_graph` is genuinely the **first production caller** of `GraphExecutor`/`UnifiedDispatch` (verified: no live construction anywhere in non-test code). That crosses the project's most-repeated invariant, so it is articulated deliberately, not silently.

**This slice proves the production execution substrate, not planner parity** (Creative) — it introduces the first live caller of `GraphExecutor` for *additive* operations and therefore sits entirely outside the Track-B chain-corpus/parity gate. The graph runtime can become production infrastructure *before* it becomes the chat runtime; those are separate milestones.

**Two live-reachability tracks — separate, do not conflate:**
- **Track A (THIS slice):** first production caller for **additive federated operations** (`traffik.editorial.apply_steps`). No legacy `run_chain_steps` equivalent → **no parity obligation → NOT corpus-gated.** Same reasoning as the generation-trust reframe: additive ≠ replacement. Real, bounded, north-star.
- **Track B (slice 5/6 — STILL CLOSED):** dual-path cutover of the existing **chat/NL** surface onto the graph. Has a parity obligation against `run_chain_steps`, is **corpus-gated** (n=1 specimen trap). **Untouched by this slice.**

**The guard that keeps A from becoming a backdoor into B (write it down, enforce it):** `run_graph(spec)` is general — it executes *any* `GraphSpec`, including legacy-equivalent operators (a read, a `flame_rename_shots` commit). That is fine for authority (a `commit` node still routes through `CommitBoundary → ratify` regardless of entrypoint). **But `run_graph` MUST NOT be wired into the chat handler** — that would flip the chat surface onto the graph without the corpus, i.e. the gated Track-B cutover through the back door. **This slice's exposed surface = CLI + direct Pipeline caller ONLY.** Any future network surface is another adapter over `run_graph`, never a chat-path wiring.

---

## 1. The build (lean)

**`forge_bridge/orchestration/run_graph.py`** (or nearest orchestration home) — the single production entrypoint:
```python
async def run_graph(spec, *, registry=None, receipt_dir=None) -> dict[str, NodeResult]:
    """Construct the live UnifiedDispatch and execute a GraphSpec. First production caller."""
    runner = build_operation_runner(registry)          # registry threaded straight through (Pipeline owns registration)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=runner),
        # mcp/primitive/foreach/commit/generation boundaries keep their defaults
    )
    return await GraphExecutor(dispatch).run(spec)
```
- **CLI:** `fbridge graph run <spec.json>` — a *thin* wrapper over `run_graph` (the `fbridge graph` group already exists: `list`/`show`). CLI and all tests invoke the **exact same** `run_graph` — no parallel impl.
- **Receipt sink:** default `~/.forge-bridge/operation-receipts/`, overridable via `build_operation_runner(registry=None, receipt_dir=DEFAULT)`. **Decision (Caution #3 — the runner owns BOTH key derivation AND the receipt-path default; sequencing is load-bearing):** the idempotency_key is **derived inside the runner** (the `uuid5` content-hash) when the caller omits it. So `run_graph` **cannot** name `<idempotency_key>.jsonl` up front — it doesn't know the derived key until the runner computes it. Therefore the default path is applied **inside the runner, after key derivation**: when `node.config` carries no `receipt_path`, the runner writes `<receipt_dir>/<derived_idempotency_key>.jsonl`. Do **not** apply the default in `run_graph` before dispatch (it would force every caller to supply an explicit key). Receipts = JSONL execution evidence (review reads the files), not durable domain artifacts. **Append-log keyed by logical operation:** a derived-key (omitted-key) operation with identical `(operation_type, state, step_plan)` across two runs collides into the same file **by design** (that's idempotency, not a bug); a caller wanting per-run isolation supplies distinct keys.
- **First live production graph (intentionally minimal — NOT "canonical"):** one **single-node** `traffik.editorial.apply_steps` GraphSpec under examples/ (step_plan from `config["arguments"]`), documented "**run with Pipeline's registry**." It's a production smoke test, not the canonical demo — composition is the point of `GraphExecutor`, so heterogeneous-composition examples become canonical later. Name/document it as minimal-by-intent.
- **Tag:** cut a Bridge release tag once this lands so Pipeline pins a release, not `fc58540`.

## 2. DT's build cautions — baked in (captured, not assembled)
1. **The example is NOT stock-Bridge-green.** `registry=None → get_default_registry()` has **no editorial operator** → the example returns `NO_PROVIDER` → boundary error. It's green only when **Pipeline passes a registry carrying `TraffikEditorialOperator`.** Bridge's own test must **register a FAKE operator** into a registry and pass it. Document the example as "run with Pipeline's registry" — never claim stock-runnable. (This is exactly where a green test could mislead — DT's focus.)
2. **Single-node example.** #104's proof was 2 nodes (`build_step_plan → apply_steps`), but `build_step_plan` is **not admitted** — only `apply_steps` is. So the live runnable example is **single-node** (proves live operation dispatch, not edge composition — already proven offline). A 2-node live graph = +1 admission, **out of scope**; name it single-node.
3. **Receipt-path seam — runner owns key-derivation + default together (sequencing).** The default canNOT be applied in `run_graph` before dispatch because the idempotency_key is derived inside the runner; apply the default inside the runner after derivation. See §1. The one thing that bites in code if unstated.

## 3. Guardrails (binding)
- `executor.py` **byte-stable** — this slice lives entirely in orchestration + CLI, never composition.
- **No chat-handler wiring** (§0 guard). Exposed surface = CLI + Pipeline caller only.
- **No peer operator hardcoded** in Bridge — registry threaded through; Pipeline owns `TraffikEditorialOperator` registration (federation = implementation boundary).
- `forge_bridge.__all__` stays **19**; no `forge_core`/`traffik` import in composition.

## 4. Acceptance bar
Another repo can call `run_graph()`, execute a real `GraphSpec` through the production `UnifiedDispatch`, get uniform `NodeResult`s + receipts — **without `GraphExecutor` knowing anything about Pipeline, Traffik, or transport.** Bridge tests prove it with a fake operator + injected registry (single-node apply_steps green; missing-registry → `NO_PROVIDER` error NodeResult; CLI invokes the same `run_graph`; `executor.py` 0-diff).

## 5. Tests
- `run_graph` with a fake `OperationDispatchBoundary` registry → single-node apply_steps → `NodeResult(ok)` + receipt written to the default sink.
- `registry=None` (no editorial) → `NO_PROVIDER` → deterministic error NodeResult (proves Caution #1 honestly).
- CLI `graph run <spec.json>` round-trips through the same `run_graph`.
- `executor.py` byte-stable assertion.

## 6. Out of scope
HTTP/daemon route (YAGNI until a 2nd consumer); 2-node live graph (+1 admission); `TimelineDelta→Flame` (Track-B-adjacent, commit/ratify, design-only — blessed, not built); `artifact_type` population.
