# TF.4 Post-Gate #2 — Findings

**Run:** 2026-06-03, `qwen2.5-coder:14b` @ `1d54a12`
(S1 `compile_raw` raise-path capture). Three fresh live captures:

- `forge_bridge/translation_oracle/reference/postgate-slice2-run1/cases.jsonl`
- `forge_bridge/translation_oracle/reference/postgate-slice2-run2/cases.jsonl`
- `forge_bridge/translation_oracle/reference/postgate-slice2-run3/cases.jsonl`

**Stack:** editable checkout confirmed; Ollama local; Flame hook `:9999`
available; Postgres on `127.0.0.1:7533` via `FORGE_DB_URL`.
Frozen `reference/cases.jsonl` and existing `reference/postgate*` corpora
were not mutated.

---

## Finding 1 — #3 is now raw-scoped: trailing empty chain step

`list the projects` reproduced in all three fresh runs as:

```text
outcome: compile_error
abort_reason: CompileInvalidChainShape
observed_graph: []
well_formed_reason: invalid_chain_shape
compile_raw: 'forge_list_projects ->'
```

The raw rules out the guesses the room explicitly warned against:

- not prose/non-tool emission;
- not genuinely empty output;
- not wrong tool choice;
- not provider silence.

The defect shape is a **trailing empty chain segment** after an otherwise
correct tool: `forge_list_projects ->`. The #3 fix should therefore be scoped
as a chain-shape parse/serialization tolerance or prompt grammar slice:
either reject/repair a terminal empty segment deliberately, or prevent it.
The next fix should not be framed from prediction; the raw is the anchor.

## Finding 2 — ranking confirmed, not materially re-ordered

Across the three fresh runs:

- `detached_args`: 0/45. Slice #1 remains stable in the wild.
- `list projects` invalid-chain raise: 3/3. Stable and real.
- `gen_0460` budget/timeout: 1/3 in this batch, still variance/infra noise.
- `non_tool_step`: intermittent. It appeared on the shot-duration case in one
  fresh run and in prior postgate samples, but not as the dominant class.
- space-mangle/entity value-fidelity: stable. The four `30sec_edit 21`
  cases still fail exact entity value-fidelity; `30sec_21` still passes.

So the measured ordering holds:

1. Serialization/detached-args: fixed by Slice #1, with Prong B still the
   deterministic guarantee.
2. Entity value-fidelity / space-mangle: dominant content failure, measured by
   Slice #2.
3. `list projects` invalid-chain raise: next well-formedness sibling, now
   raw-scoped as a trailing empty segment.
4. `non_tool_step`: real but intermittent; not outranking #3.

## Finding 3 — desktop-wiring (C) stays gated

The fresh data does not promote desktop/context wiring as the next slice.
`rename this sequence with prefix tv` consistently reaches:

```text
flame_get_sequence_segments sequence_name=30sec_21
flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true
```

and then aborts with `UNRESOLVED_REQUIRED_PARAM`. This is still entangled
with entity-value corruption (`30sec_edit 21` absent, `30sec_21` substituted)
and apply/commit shape, not a clean proof that desktop context wiring is the
dominant next defect. C remains investigation-gated, not promoted.

## Finding 4 — S1 did the intended job

Before S1, the #3 row was blind: empty observed graph, invalid chain shape,
no raw. After S1, the same row is still behaviorally identical to chat and
capture consumers, but the corpus now carries the raw string needed to scope
the next slice. This is exactly the maturation condition for `compile_raw`.

No success-path raw threading was needed; the `compile_intent -> list[str]`
contract remains untouched.

---

## S3 Decision

Ratify #3 as a **trailing-empty-step invalid-chain-shape slice**, anchored by
`compile_raw == 'forge_list_projects ->'` across 3/3 fresh runs. The slice
should be model-free first: parser/normalizer unit pairs for terminal empty
segments, then a prompt clause only if useful. Do not merge it into
`non_tool_step`; the raw shows a different shape.
