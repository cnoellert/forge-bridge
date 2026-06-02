# SR.1 — Acceptance (live-verified)

Status: **PASS.** The 2/3 reachable win is realized live — sequence-scoped timeline reads
route to the substrate that holds the answer.

## Implementation landed (4 commits)

- `6f3fe90` feat — route sequence-scoped shot reads to Flame segments
- `f4ad78f` fix — execute source-routed reads with reachable tools (only route when
  `flame_get_sequence_segments` is registered)
- `4912e3b` fix — preserve qualified sequence references
- `9f24fde` fix — keep mixed-separator Flame sequence names

The three fixes are the predicted trap closing: the rewritten step must **carry a faithful
sequence reference** (qualified + mixed-separator, e.g. `30sec_edit 21`) so downstream
`sequence_name` resolution succeeds, and must only fire when the target is reachable.

## Mechanism (as shipped, matches plan)

`forge_bridge/console/_source_route.py::apply_source_routing(user_prompt, steps, tools)` —
deterministic, reads-only: detect a sequence reference via 24.11 `resolve_query_entities`;
if present AND `flame_get_sequence_segments` is registered, rewrite each forge-entity
shot/segment step (`forge_get_shot` family + `forge_list_shots`) to
`flame_get_sequence_segments <sequence_ref>`. Fail-safe: no sequence ref OR target absent →
steps unchanged. Hooked at `_chat_compile.py:205`, after the commit-node branch (reads-path
only; mutating/Door-C untouched).

## Verification

- `pytest -q` → **2688 passed / 41 skipped** (+9 vs DI.2 close); focused SR.1 / resolver /
  compile tests pass; ruff clean on touched files; `forge_bridge.__all__` = **19**.
- Live (daemon provenance `9f24fde`): **R8 (path) and R10 (duration) both routed to
  `flame_get_sequence_segments 30sec_edit 21` and returned real segment payloads**
  (`sequence`, `frame_rate`, `segments`, `count`) — instead of aborting at
  `forge_get_shot`'s `shot_id`. The substrate-selection failure is corrected.

## Boundary held

Reads-only; fail-safe; coarse by substrate (`forge_*`→`flame_*`), no per-attribute map; no
LLM; no reinterpretation; DI.1 untouched. **Out of scope (surfaced, not resolved):** R9
timewarp (capability gap — no read tool); ordinal "shot 10" → which segment + layer
multiplicity (the read returns all segments; the answer-pass has the data).
