# M2 Slice 5 — Shadow Reachability (graph engine's first live production caller)

## Success criterion

**Shadow produces replayable parity evidence from real production read traffic
without changing authoritative behavior.** Legacy `run_chain_steps` stays
authoritative and byte-identical; the graph path runs opportunistically
alongside it on live reads, and each run emits one interpretable
parity-evidence record. This is the graph engine's FIRST live production caller
— it has been offline-proven for the entire M2 arc (`GraphExecutor` byte-stable,
zero production callers).

This is **reachability + evidence-gathering only**. No authority flip (graph
stays SHADOW; the flip to graph-authoritative is slice 6), no mutations, does
not retire `run_chain_steps`.

## The seam

Chat (`console/_chat_compile.py`) and CLI exec (`console/_execute.py`) both call
`run_chain_steps(...)` in the READ branch — the
`graph_contains_commit_node(steps) == False` path, structurally fenced at
`_chat_compile.py:307` (NOT a runtime flag). The mutating branch (ratify/apply,
`_chat_compile.py:508`) never reaches the wrapper. Both read sites now call the
thin wrapper `run_chain_steps_with_shadow`.

## Replay is the intended mode; double-exec is the documented fallback

Two questions, two modes:

* **Replay** answers the milestone question — *"does `GraphExecutor` execute the
  same plan correctly?"* — by isolating the variable under test to the graph
  runtime. Legacy runs ONCE; every tool call it makes is captured in-memory by a
  transparent MCP proxy; the graph path replays those captured results instead
  of re-hitting real tools.
* **Double-exec** answers a *different* question — re-validation against the live
  world — and is the documented FALLBACK only, taken ONLY if records cannot be
  cleanly reconstructed for replay. It is gated to idempotent operators via
  `compare.py`'s `compare_strategy_for`.

**This slice runs replay and never falls back** — legacy's per-tool results are
cleanly exposed in-memory (see grounding pass Q1). Every record stamps
`comparison_mode ∈ {"replay","double_exec"}` so evidence can never silently mix
modes. The operator-idempotency class (`compare_strategy_for`) is recorded
separately as `operator_strategy` — it is evidence metadata, NOT the mode.

## Outcome taxonomy (one per record)

`{"match", "divergence", "replay_miss", "shadow_error", "shadow_timeout"}`

* **match / divergence** — graph reproduced (or did not reproduce) the legacy
  normalized status-vector + terminal output.
* **replay_miss** — a graph-requested tool call had no captured record under the
  match-key (or the chain could not be compiled to admitted graph IR). This is
  its OWN category — it is FIRST a corpus/keying limitation, never auto-labelled
  `divergence`. A *robustly-keyed* miss is #153 value→kwarg divergence evidence,
  analyzed downstream.
* **shadow_error / shadow_timeout** — a swallowed or timed-out shadow run lands
  as its own outcome and never vanishes. Otherwise "no divergence logged" would
  conflate "ran and matched" with "never finished".

## The skew-robust match-key (grounding pass Q2)

Key = `(tool_name, canonical_json(_canonical_args(arguments)))`. It must match
logically-identical calls despite normalization skew between how legacy
assembles arguments (token/JSON parsing in `_step.py`) and how the graph
assembles them (static config + the #153 edge-sourced kwarg merge), while still
DISTINGUISHING a genuinely-different or missing kwarg value — that difference is
exactly the #153 evidence a `replay_miss` carries.

Benign skews collapsed: key ordering (canonical JSON sorts); explicit `None` vs
an omitted kwarg (None dropped); scalar-type skew from parsing (`"5"`↔`5`,
`"true"`↔`True`); surrounding whitespace on string scalars. A different VALUE
survives normalization → different key → interpretable miss. That property is
what makes "a robustly-keyed miss is #153 evidence" hold.

## Shadow is instrumentation, not a wrapper feature

The wrapper (`console/_engine.py:run_chain_steps_with_shadow`) has ONE
responsibility: run the authoritative path and hand the already-computed legacy
body + in-memory records to the instrumentation hook (a no-op when the flag is
off). ALL operational concerns live in `composition/_shadow.py`: the
`FORGE_BRIDGE_SHADOW_COMPARE` flag (mirrors `chain_corpus/_capture.py`'s gate),
compile+compare orchestration, the inline time-box (`asyncio.wait_for`,
`SHADOW_BUDGET_S = 3.0s`), the outcome taxonomy + `comparison_mode` stamp,
error/timeout capture, and its OWN JSONL sink at
`~/.forge-bridge/chain-compare/shadow-compare-<date>.jsonl` (distinct path —
honors the no-shared-path-JSONL-writers non-goal; never writes
`~/.forge-bridge/executions.jsonl`).

A shadow failure can never regress a read: the authoritative body is returned by
the wrapper before the hook runs, `shadow_compare` never raises, and the wrapper
has a final backstop `try/except`. Flag-off is an exact passthrough of
`run_chain_steps` (fully reversible; the MCP is not even wrapped).

## #102 dependency collapse

The M2 framing gated slice 5 on *"a capture source that persists replayable
`chain_steps`"* (the #102 chain-corpus) — because the only execution log was the
learning-pipeline code log (no NL chat intents). **Shadow-over-live-reads
dissolves that gate:** it manufactures the equivalent replayable corpus from
*authentic operator read traffic* at the moment each read executes — no
hand-authored-corpus selection bias, no waiting on corpus accumulation. Slice 5
is therefore NOT blocked on #102; it produces the real-traffic evidence #102
wanted, as a by-product of being reachable.

## Invariants held

* `composition/executor.py` byte-for-byte UNCHANGED (shadow only READS its
  `NodeResult`s).
* Top-level `forge_bridge.__all__` == 19 (new module carries its own `__all__`).
* No new external deps. Reads-only (structurally fenced — the wrapper is only
  reached on the non-commit branch). Own JSONL sink.

## Slice 6 (deferred)

The authority flip — corpus-green → flag-flip → make the graph path
authoritative and retire `run_chain_steps`. Slice 5 is the evidence engine that
tells slice 6 whether the corpus is green.
