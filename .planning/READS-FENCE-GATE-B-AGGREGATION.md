# Reads fence — gate-(b): grounding aggregation targets

**Date:** 2026-06-10
**Author:** forge-bridge (DT), grounded against the live portofino DB + `_planner_front.py`
**Status:** Framing — **DT-verified + room-converged (2026-06-11), pass-to-code-ready for v1**; forcing case is **#40** (planner fabricates a "sequence" from duplicate shot-names)
**Lane:** Conversational reads / the reads fence family (twin of gate-(a), `#35` / `57085df`)

---

## TL;DR

gate-(a) grounds **filter terms** at the **plan** seam (status/role narrowing). #40 is a
different class: a fabricated **aggregation** at the **narrate** seam. The narrator was
handed a flat shot list and the word "sequence" and was implicitly asked to *compute the
group-by itself* — so it grouped by the wrong field (`name`, which had a visible 11×
collision) instead of the real-but-null field (`sequence_id`), and stated the result as
fact.

**Doctrine line that resolves it:** **aggregation is computation, not comprehension.** The
model owns comprehension (what the user meant; phrasing the answer). The substrate owns
computation (group / count / max). Today the narrator does both, and the *computation* half
is where it fabricates. gate-(b) moves the group-by/count into deterministic code and grounds
its target the same way gate-(a) grounds a filter: **model declares, code validates.**

---

## The forcing case, grounded

Query: *"which sequence has the most shots in portofino"* → confidently answered
*"surface_types, 10 shots."*

Ground truth in the live DB (verified 2026-06-10):

- **Zero `sequence` entities exist** anywhere (`entity_type` counts: media/shot/version/asset/assent_record — no `sequence`).
- Every portofino shot carries `attributes.sequence_id` — and it is **uniformly `null`**.
- `surface_types` was **not a sequence and not a real shot** — it was 11 duplicate test-debris shots sharing one name (now cleaned: portofino is 20 unique `tst_*` shots).

So the honest answer is *"no shots in portofino are assigned to a sequence."* The narrator
instead grouped by `name`, found `surface_types ×11`, and reported it as a sequence — a pure
field-substitution fabrication.

---

## Why gate-(a) cannot reach this

| | gate-(a) — shipped (`#35`) | gate-(b) — this doc |
|---|---|---|
| Axis | **filter** term (which entities) | **aggregation** target (group-by / count / max) |
| Seam | **plan** (pre-execute, pure vocabulary) | **plan** (vocabulary) **+ post-execute** (data) |
| Fabrication site | planner sets a filter arg from an invented mapping | narrator computes a group-by over a raw list and guesses the key |
| Fence | `ground_read_filters` re-derives `status`/`role` | `ground_read_aggregation` + a deterministic reducer |

`ground_read_filters` (`_reads_fence.py`) runs after parse / before execute and only governs
`SEMANTIC_FILTER_ARGS = ("status", "role")`. An aggregation never sets one of those args, so
gate-(a) is structurally blind to it. Confirmed: the #40 path passes gate-(a) clean.

---

## The design — two complementary moves

### Move 1 — declare + ground the aggregation target (model declares, code validates)

When the LAST user message asks a "which X has the most/fewest Y" / "how many Y per X" /
"count Y by X" question, the planner emits an `aggregation` declaration alongside the plan
(exactly as it already emits `filters`):

```json
{"plan": [{"tool": "forge_list_shots", "args": {"project_id": "<id>"}}],
 "filters": [],
 "aggregation": {"intent": "max_by_count",
                 "group_by": "sequence",          // verbatim phrase from the message
                 "group_field": "sequence_id",    // model's claim of the backing field
                 "over": "shot"}}
```

A new deterministic fence `ground_read_aggregation` validates it in **two checks at two seams**:

- **(b1) Vocabulary groundedness — pre-execute (twin of gate-(a)).** Does `group_by`
  resolve to a *known groupable dimension* of the `over` entity? Re-derive `group_field`
  against a **groupable-fields registry** (the allow-list of attributes/entity-refs a read
  may group by — `status`, `role`, `sequence_id`, … — defined the way `READ_PLANNER_ROLE_NAMES`
  bounds the role fence). If it resolves to nothing → clarify ("I don't have a way to group
  shots by 'flavour' — I can group by status / sequence / role. Which did you mean?").
  Never trust the model's `group_field` claim; code re-derives it.

- **(b2) Data groundedness — post-execute, pre-narrate (the new structural move).** After the
  population tool runs, the **substrate computes the aggregation deterministically** over the
  grounded `group_field`. For #40: `group-by sequence_id over the 20 shots → {null: 20}` → **0
  non-null groups**. A grouping whose field is uniformly null/empty is *ungrounded in data*:
  the deterministic answer is the **grounded absence**, not a narrator guess.

### Move 2 — compute the aggregation deterministically (the doctrine core)

When `aggregation` is declared and grounded, a deterministic reducer performs the
group/count/max over the executed result and hands the narrator the **computed answer as
evidence** — the narrator *phrases*, it does not *compute*:

- `{null: 20}` → evidence: `"sequence groups: 0 (all 20 shots have sequence_id = null)"` →
  narrator: *"None of portofino's 20 shots are assigned to a sequence."*
- a populated field → evidence: `"sequence groups: {seq_a: 12, seq_b: 8}; max = seq_a (12)"`
  → narrator phrases the computed winner.

This kills the whole class — *"which shot has the most versions", "how many shots per
status", "which role has the most media"* all become deterministic reductions over a grounded
field, phrased (never computed) by the model. The narrator can no longer eyeball a raw list
and invent a grouping, because it is never the thing doing the grouping.

---

## Shippable split

**Label v1 honestly — it is the *all-null / absent-grouping guard*, not "aggregation solved."**
v1 deterministically kills the #40 fabrication (uniformly-null / absent grouping). **Populated
aggregations stay narrator-computed — and therefore still fabricatable — until the Move 2
reducer (v1.1) hands computed evidence to `_narrate`.** Read "v1 closes #40" as exactly that,
never as "v1 kills aggregation fabrication." (DT/Creative redline, 2026-06-11.)

- **v1 (minimal, closes #40):** Move 1 + the **b2 absence-answer**. Declare the aggregation;
  if the grounded `group_field` is uniformly null/empty/absent, emit a deterministic
  grounded-absence response through the **existing clarify/response channel** — *no `_narrate`
  contract change*. Smallest diff; gate-(a)-shaped; directly closes the fabrication.
- **v1.1 (durable, kills the class — fast-follow, days not horizon):** Move 2 — generalize the
  reducer v1 already introduced (its null-detection *is* a group-by) from "there is no grouping
  evidence" to "here is the computed grouping evidence," and make `_narrate` consume that
  evidence. The narrator phrases computed aggregations instead of doing arithmetic over a raw
  list.

**Why split (the justification is structural, not effort):** v1 short-circuits *before*
narration through the channel gate-(a) already uses — zero narrate-path change. v1.1 *touches
`_narrate`* (the computed-evidence handoff). The seam between "no narrate change" and "narrate
contract change" is the real cut line; the mechanism (the reducer) is shared, so v1.1 is a fast
follow-on, not a distant phase.

---

## Scope / boundary (v1)

- **In:** single `group_by` over a single population tool result; `group_field` restricted to
  the groupable-fields allow-list; `intent ∈ {max_by_count, min_by_count, count, count_by}`;
  **uniformly-null / absent** grouping field → grounded-absence answer.
- **Partial-null is NOT in v1 (name it loudly, or it slips the fence).** A field that is
  populated on *some* rows and null on others is a *populated grouping with a null bucket* — it
  reduces and gets narrator-computed, so it stays fabricatable until v1.1's reducer hands
  computed evidence to `_narrate`. v1 covers *uniform* null/absent only. Do not let anyone read
  "aggregation fence" as covering the partial-null case.
- **Shape lock (resolved 2026-06-11):** the reducer groups on the **top-level `sequence_id`**
  key of each shot dict — `Shot.to_dict()` (`entities.py:228`) flattens it to top-level; the
  read path does **not** nest it under `attributes` (that is the raw DB-column layout only).
  Grouping on `attributes.sequence_id` would read the wrong path and silently mis-group.
- **Out (named, not rejected):**
  - Multi-hop aggregation across entity types via relationship edges (e.g. "which artist owns
    the most shots" if ownership is an edge, not a field) — needs traversal; defer with a
    falsifiable trigger (first real multi-hop aggregation query in the corpus).
  - An aggregation the model **omits** from both the plan and the declaration — the same v1
    boundary gate-(a) carries (needs query re-parsing / hand-rolled NLU). Out.
- **Complement, not replacement — narrate-seam hardening.** Tightening `_NARRATE_SYSTEM`
  ("never group entities by a field the user didn't name; never report an entity type absent
  from the evidence") is worth doing as belt-and-suspenders, but it is *probabilistic*. The
  deterministic gate owns correctness; the prompt is defense in depth. Do not sell the prompt
  as the fix.

---

## Contributing structural gap (worth a line)

`Sequence` is advertised in the planner vocabulary digest hierarchy
(`Project → Sequence → Shot/Asset → Version → Media`, `_vocab_digest.py:67`) but there is **no
`forge_list_sequences` read tool** — the planner can name the type but cannot query it, which
is what pushed it to substitute `forge_list_shots` and improvise. Move 2's deterministic
reducer *is* effectively the "sequences in this project" answer (group shots by `sequence_id`),
so it closes this gap without adding a thin entity-list tool. If a first-class sequence
listing is later wanted, it rides on the same grounded grouping.

---

## Cross-references

- gate-(a): `forge_bridge/console/_reads_fence.py`, `ground_read_filters`; commit `57085df` (`#35`).
- Plan/narrate seams: `forge_bridge/console/_planner_front.py` — fence call (`:274`); execute loop (`:280`); `_narrate` def (`:206`) + call site (`:295`). b2 inserts **after the execute loop, before the `_narrate` call** (`:293→:295`). (DT-verified, 2026-06-11.)
- Wire shape: `forge_bridge/mcp/tools.py:507` (`list_shots` → `entity_list` → `shots: [e.to_dict()]`); `forge_bridge/server/router.py:696`; `Shot.to_dict()` `forge_bridge/core/entities.py:224-234` — **`sequence_id` flattened to top-level**.
- Groupable-vocabulary source: `forge_bridge/console/_vocab_digest.py`; `forge_bridge/core/vocabulary.py`. Groupable-fields registry mirrors `SEMANTIC_FILTER_ARGS` / `READ_PLANNER_ROLE_NAMES`.
- Doctrine: CLAUDE.md "the cut line for synthesis" — *may synthesize explanations of facts that exist; may NOT synthesize facts that do not exist*. A group-by an LLM eyeballs is synthesis of a fact (the grouping) that the substrate never computed.
- Issue: **#40** (comprehension: planner fabricates entity aggregations). Data-cleanup sub-task done 2026-06-10 (11 `surface_types` debris shots removed; backup at `~/.forge-bridge/backups/issue40-surface_types-cleanup-2026-06-10.json`).
