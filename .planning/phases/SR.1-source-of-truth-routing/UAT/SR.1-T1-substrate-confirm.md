# SR.1-T1 — Source-of-truth confirmation + candidate-set grounding

Status: **done, daemon authority.** Two grounded results: (A) the reachable-win count
(2/3) via a live read; (B) the routing-mechanism reality via running the deterministic
filter/narrow functions. Both pin SR.1 to ground truth before any code.

## A. Reachable win — 2/3 (live `flame_get_sequence_segments`)

Driven read-only through the **live projekt-forge MCP** (Flame 2026.2.2 / 013_13_13 /
Timeline tab — the dogfood context), no `:9990` bring-up. `flame_get_sequence_segments
("30sec_edit 21")` → **25 live segments.** Per-segment fields:
`track_idx, layer_num, seg_name, shot_name, source_name, file_path, role, head,
record_in, record_out, start_frame, forge_*, duration`.

| Read | Attribute | Live result | Verdict |
|---|---|---|---|
| **R8** path | `file_path` | present on all 25 (e.g. `…/B002C002_260302_RNTM.0399078.exr`) | **✅ answerable** |
| **R10** duration | integer frames | present on all 25 (53, 34, 33, 27, …; `frame_rate` 23.976) | **✅ answerable** |
| **R9** timewarp | — | **not in the live return** (no segment-effects field) | **✗ capability gap** |

**Locked: 2/3 via `flame_get_sequence_segments`.** R9 escalated docstring → collector
source → live daemon call (the right order; presence asserted, absence verified) —
ground-truth agrees with the source-read. R9 = capability gap (no read tool holds it) →
carry-forward, out of SR routing scope.

**Layer multiplicity (for the plan, not for SR.1 scope):** shots `tst_010..tst_200`,
several on multiple layers (`tst_010` on L01+L02; `tst_110` on L01/L02/L03) → a shot maps
to N segments. "shot 10 on 30sec_edit 21" is doubly ambiguous (which ordinal, which
layer). The answer is per-segment-per-layer. **This is segment-selection, NOT
source-of-truth — SR.1 surfaces it, does not resolve it** (Creative's boundary).

## B. Candidate-set grounding — the routing mechanism reality

Ran the real `filter_tools_by_message` + `deterministic_narrow` (pure functions) over a
tool list containing the forge_get_shot family + `flame_get_sequence_segments`:

| Input | `deterministic_narrow` result | timeline tool reachable? |
|---|---|---|
| `"forge_get_shot"` (the **compiled step**) | `[forge_get_shot, forge_list_shots, forge_get_shot_stack/versions/lineage/deps]` | **NO** — dropped by max-overlap |
| `"what is the duration of shot 10 on 30sec_edit 21"` (**user intent**) | `[forge_get_shot, forge_get_shot_*]` | **NO** — not even in the filter |
| `"get segments on 30sec_edit 21"` (tool's own vocab) | `[flame_get_sequence_segments]` | **YES** |

**Finding:** the substrate mismatch is **lexical**. The user's natural attribute words
("shot", "duration") share name-tokens with forge *entity* tools; `flame_get_sequence_segments`
shares none, so it is **not a candidate to "prefer."** A within-candidate-set
substrate-bias (the discuss's cycle-1 mechanism) **cannot reach the timeline tool.**

**The usable signal is the sequence reference.** Both failing phrasings carry "on
30sec_edit 21"; the differentiator is that the user's attribute vocabulary
lexically out-votes it. So the coarse mechanism must be: **a sequence reference present
in the read → route to the timeline substrate (inject/force `flame_get_sequence_segments`,
which consumes `sequence_name`), overriding the forge-lexical attribute match.** Coarse
(keyed on sequence-ref presence), deterministic, no per-attribute map. This is
**compile-adjacent** (it overrides the tool the compiler/lexical-match chose) — which
re-opens the mechanism-location question (compile-time vs post-compile injection) with
real data.

## Net

2/3 reachable win is ground-truth (R8+R10 live; R9 confirmed capability gap). The
routing mechanism is **not** a candidate-set bias (the timeline tool isn't a candidate);
it is **sequence-reference-signal routing** — coarse, deterministic, compile-adjacent.
SR.1's plan-mechanism (compile-time selection vs post-compile injection) needs the
room's steer before authoring, since it now touches the compile boundary SR was scoped
to avoid.
