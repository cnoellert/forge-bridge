# Generation Trust Model — Framing Seed

**Status:** SEED (DT-drafted, leads with Orch's position; awaiting room redline → converge).
**Scope:** ONE question, deliberately. Not a #104-style multi-Q pass.
**Origin:** surfaced by `feat/generation-dispatch-author-prompt` (generation dispatch slice 1) — a real operator hit the graph and revealed the M2 parity model doesn't fit it. Substrate-need-exposed-by-real-work, not process for its own sake.
**Gates:** generation going *live* (dual-path / any production caller). Does **NOT** gate offline slice-2 (author→render composition), which proceeds in parallel.

---

## The one question

**How does an additive, non-deterministic, no-legacy-equivalent operator earn live trust — when it structurally cannot ride the M2 parity-replay proof?**

Grounding (verified against `compare.py` / `parity_corpus.py`): generation is **not** in the parity path, and never can be. Every operator admitted before it (reads, editorial `operation`) was deterministic enough to replay-and-compare against legacy `run_chain_steps`. `author_prompt` is `idempotent_result=False`, cost-bearing, and has **no legacy chain-step equivalent at all**.

## Lead position (Orch) — the additive reframe

Parity-replay exists for exactly one job: **retire `run_chain_steps`** — prove the graph reproduces legacy behavior, flag-flip, delete. It is a *replacement* proof.

Generation is **additive capability, not a replacement.** It was never part of what cutover-parity is proving. So the tension dissolves the moment we stop trying to make a non-deterministic, no-legacy operator pass a replacement-proof it was never in:

> Generation earns trust on a **different axis** than deterministic replay — **real-output validation + cost-gating + human review of the authored artifact.**

This decouples generation from M2 cutover cleanly. M2 (slices 5/6) stays the `run_chain_steps` retirement track; generation rides its own trust track.

## The redline surface (what the room sharpens)

The reframe is right; the *content* of the trust axis is the open work. Sketch, to be pressure-tested:

1. **Real-output validation** — generation is validated by inspecting its actual produced artifact (the `GenerationArtifact`: `lifecycle_state`, `media_locator`, `media_content_sha256`, `failure_reason`), not by comparing two runs. What's the minimum validation bar before a generated artifact is "trusted enough" to flow downstream? (Terminal-state check + content present + sha recorded is the floor; is that sufficient, or does authorship need human sign-off like mutations need ratify?)
2. **Cost-gating** — generation costs money/compute per run. Where does the cost guard live — admission, boundary, runner, or the live daemon edge? Is there a budget/quota seam, or is cost the operator's problem out-of-band for now? (Bridge ships substrate, not policy — lean: cost-gating is a daemon-edge concern the consumer wires, named here but not built.)
3. **Human review vs. ratify** — mutations earn trust via operator `AssentRecord`. Generation is `no_state_mutation=True` (a make, not a host mutation) so it does **not** route through `commit`/ratify. But does an *authored artifact* (vs. a perception read) want a review affordance of its own — a lighter "accept this generated output" gesture distinct from the heavyweight mutation-ratify? Open.
4. **Concurrent-dispatch interaction (#88)** — generation blocks the executor for the whole submit/poll (`synchronous=True`, see ceiling note). When dispatch goes concurrent, does the trust model change (in-flight cost, partial cancellation via `cancellation_acknowledged`)? Name it; don't solve here.

## Decided-and-cheap (record, don't relitigate)

- **`synchronous=True` ceiling** — `author_prompt_and_wait` internalizes submit/poll, so the executor blocks until terminal (timeout-bounded). Add a `ponytail:` note on the admission record naming the async / #88-concurrent-dispatch collision. Acceptable for offline slice-1; flagged for the live track.
- **`"generation"` naming** — keep it as the **capability family** (it's in `KNOWN_CAPABILITY_FAMILIES`, peer-agnostic, not `"generators"`). Maturation condition, recorded now: *split to an `async-make` mechanism kind if a non-generation peer ever needs submit/poll* — at that point `"generation"` is family-naming the mechanism axis and the split pays for itself. Until then, no split (YAGNI).
- **`_artifact_text` dead-field lookup** — the boundary probes `text`/`final_text` fields that don't exist on the real `GenerationArtifact` (the `media_locator` file-read fallback is what works). One-line cleanup, non-urgent.

## What this seed does NOT do

- Does not block slice-1 merge (offline, clean, captured-verified end-to-end).
- Does not block slice-2 (author→render, offline composition — doesn't touch the live-trust question).
- Does not reopen the §0.5 mechanism-vs-peer doctrine (generation is already compliant: family-named kind, peer-agnostic boundary, package injected at the edge).

## Captured-verified baseline (so the room argues from facts)

Cross-checked against forge-generators `main`: `author_prompt` kwargs exact (`intent/context/target/style/driver/registry/data_root`); `LLMDriver`/`PlatformUuidRegistry` sigs match; `GenerationArtifact` fields + `to_transport_dict()` real; `lifecycle_state ∈ {submitted,polling,partial,complete,failed,cancelled}` and the boundary's `.value`-safe fail-closed mapping handles all six correctly. Executor byte-stable; `__all__` 19; no `forge_generators` import in composition; assent never threaded into generation.
