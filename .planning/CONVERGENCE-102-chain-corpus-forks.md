# Convergence — #102 chain-corpus open design forks (M2 slice-5 prerequisite)

**Date:** 2026-07-02
**Subject:** How to take #102 (capture source for replayable `chain_steps`) from
"instrument built" to "slice-5-ready" — resolving four open forks.
**Method:** 4-view convergence (corpus-integrity / slice-5-pragmatist /
replay-correctness engineer / scope-boundary skeptic), grounded against `main`,
redlined.
**Status of #102:** instrument already built + merged (`forge_bridge/chain_corpus/`,
PR #103 `1cc3b4c`); open only because acceptance is DATA (a broad real-captured
corpus), not code.

---

## Headline finding (bigger than #102 — changes slice-5 scope)

The dual-path replay oracle's current parity proof is **degenerate**. The test
corpus (`tests/console/test_chain_corpus_capture.py`) is one fully-literal
inline-args step (`forge_is_greenscreen {shot_id, clip_ref}`) — the *only* shape
where the two paths cannot diverge:

- **Legacy** builds final call-args by runtime resolution/inheritance —
  `resolve_required_params` + injections (`sequence_name` backfilled from the
  prior step's result, `_step.py:419-427`).
- **Graph** builds call-args by **static parse** of step text
  (`_node_arguments` → `chain_compiler.py:129` `_step_arguments`). Per
  `boundary.py:11-13`: *"Edges are value-blind by design: upstream
  `NodeResult.output` is used for lineage only, not for kwarg extraction. The
  input-identity-to-kwarg mapping remains unbound pending #86."*

⇒ On any chain whose args depend on an upstream **result value** (the normal
inherited-arg multi-step shape), the two paths produce different args → different
`args_hash` → replay miss. This is the **known, documented #86 gap**, not a #102
defect. **Consequence: slice 5's parity population is bounded to static-kwarg
chains until #86 lands.** #102's own thesis (input variety is the risk) is exactly
what exposes it. Surfaced now, cheaply — far better than mid-cutover.

---

## Converged positions

### Fork 1 — resolver-probe replay desync (the crux)
**Ship an abstain-and-*count* replay-miss guard (c) + a scoped verify-now probe
(a); reject pure defer (b).**
A bare `KeyError` from the replay stub is the oracle running out of data, not a
parity answer — today it crashes (false-red) or, if wrapped naively, swallows
(false-green). Correct disposition = **abstention**, mirroring the capture side's
collision → `replayable=false` discipline (`_capture.py:107-111`). Engineer's
decisive mitigation: the miss must be **loud and countable** (tool, `args_hash`,
miss-rate), never silent — a rising miss-rate *is* the visible signal the two
paths' arg-construction diverges (the #86 boundary). Skeptic's surviving counter
is honored: the guard is **slice-5 harness** work, not a #102 instrument change —
the #102 test stub just gets a cheap version now so its green stops being false
confidence. Engineer won the crux.
- Forward direction confirmed harmless: extra resolver-probe rows in the trace are
  never looked up by the graph path (stub is content-keyed, not ordinal). The gap
  is the reverse — a graph call absent from the trace.
- `(tool_name, args_hash)` key is correct (full sha256 canonical JSON; no ordinal —
  execution-order-invariant, #88-safe). It is *not* a change that could close the
  #86 divergence; only a replay-side miss guard can make the oracle sound.

### Fork 2 — mutating chains Tier-0-only
**Accept, read-only-first (unanimous).** Not a concession — correct sequencing:
apply-args are the *peak* of the arg-divergence risk (most inheritance-dependent,
`_step.py:901-910`), branch on the verify result, and need a reconstructed
`AssentRecord`. And capturing an apply-trace would record captured **authority
decisions** (assent stays the operator's). Prove reads first, where a false-green
is cheap. Optional: name commit/mutating as structure-only in `COVERAGE_LIMIT`
(`reader.py:26-29`).

### Fork 3 — seed vs captured
**Don't build the seed writer (3-of-4; engineer decisive).** A hand-authored seed
has *literal self-contained args* (the only kind a human authors deterministically)
→ it **systematically selects for** the degenerate coincide-case and **excludes**
the inherited-arg divergence — the exact risk. A seed corpus would go green and
prove nothing. Only real capture exercises runtime-resolved args ("captured not
assembled" applied to replay fidelity). Pragmatist's "decouple harness-readiness"
need is **rejected** — met instead by fork-4's real bootstrap (real inherited-arg
rows). Keep the `source="seed"` field (free forward-compat, `_schema.py:16`,
bar-excluded by `reader.py:60`); if ever built, name it `harness-smoke`, never
`corpus`.

### Fork 4 — accumulation
**Drive a self-driven real-`captured` bootstrap now** (genuine capture, exercises
inherited args, de-risks the instrument + runs the fork-1 probe) — but the
**distribution bar stays gated on a second operator's organic dogfood** (one dev's
intents re-introduce author-blindness one level up; ecological validity, not a
theorem). Engineer's concrete invariant to bank: the replay loader **must
partition the trace by `request_id`** before building the content-addressed map —
the per-request collision guard (`_capture.py:88`) does not cover the shared daily
file (cross-request aliasing). #102's remainder = **activation + certification,
zero instrument build.**

---

## Dispositions

### Concrete next actions (now / soon)
1. **Fork-1 verify probe** — drive one real inherited-arg multi-step read chain
   through capture, replay both paths, watch it miss. Empirically confirms the #86
   boundary on slice-5 parity scope. Doubles as the first real-`captured` bootstrap
   row.
2. **Self-driven real-`captured` bootstrap** — de-risk the instrument + provide real
   inherited-arg rows for slice-5 harness dev (NOT the acceptance bar).
3. **Abstain-and-count replay-miss guard** — cheap soundness in the replay stub
   (slice-5 harness owns the full version).
4. **Document the `request_id`-partition invariant** for the replay loader.

### Intentionally unbound (re-open trigger)
- **Distribution/acceptance bar** — pending projekt-forge organic dogfood traffic +
  coverage certification (`reader.coverage_report` floor met by `source=="captured"`).
- **Value-inherited-kwarg parity** — pending **#86** (input-identity-to-kwarg
  mapping). Bounds slice 5's parity scope to static-kwarg chains until it lands.

### Rejected
- **Seed writer** — selects against the actual risk (false-confidence trap).
- **Mutation-replay-now** — peak arg-divergence + assent reconstruction; nothing
  slice 5 needs.
- **Ordinal/step-index replay keys** — locked; replay identity is
  execution-order-invariant (#88 concurrency landmine).
- **Fork-1 guard as capture-time re-execution** — violates reads-only observational
  posture + `executor.py` byte-stability.

---

## What this means for #102 / slice 5
- **#102 has no remaining instrument build.** Its remainder is activation
  (turn on `FORGE_BRIDGE_CHAIN_CORPUS_CAPTURE`) + certification (coverage floor met
  by organic dogfood). Everything else surfaced here is **replay-consumer /
  slice-5 harness** hardening or a **#86** dependency.
- **Slice 5's parity scope is bounded by #86** — validate static-kwarg chains now;
  value-inherited-kwarg chains wait on #86. The fork-1 probe makes this concrete.
