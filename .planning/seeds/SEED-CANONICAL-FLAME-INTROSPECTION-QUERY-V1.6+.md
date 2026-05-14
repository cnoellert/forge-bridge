---
name: SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+
description: Treat "What are the clips on Reel 1" as the load-bearing canonical regression query for the entire chat-convergence story. Tests semantic retrieval, tool ranking, introspection escalation, runtime convergence, and graph completeness in one sentence. Promote from 23.1 docstring test pin to a named operational fixture / CI smoke path / v1.6 benchmark.
type: operational-fixture
planted_during: Phase 23.1 author-walk on portofino 2026-05-14 — Gate 3 surfaced the dogfood query as deceptively load-bearing; the cross-writer reframe established it as the canonical bellwether for whether bridge's introspection story is operationally believable
trigger_when: v1.6 milestone opens OR a new chat surface ships (REPL, foundry dialog, Console exec view) OR a regression of the 23.1 docstring repositioning surfaces OR a CI / benchmark / eval surface is added
---

# SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+

## The Query

```
What are the clips on Reel 1
```

That's it. One sentence. Five words after "What are."

## Why This Query Is Load-Bearing

This query was the dogfood failure that opened Phase 23.1. The pre-23.1 chat surface couldn't converge on it within the 120s server-side LLM budget — the local 32b model loops on narrow `flame_*` tools that return adjacent-but-insufficient data (e.g., `flame_list_desktop` returns reel clip *counts* but not clip *names*) and burns the entire budget without producing an answer. Phase 23.1 (a) registered the existing `execute_python` function as `flame_execute_python` and (b) rewrote its docstring to position it as the canonical Flame introspection surface, so the model has an escape hatch the dogfood query can route to.

But that's the surface story. What this query *tests* is deeper:

- **Semantic retrieval** — can the model bridge operator domain vocabulary ("clips", "reel") to tool affordance vocabulary ("execute", "python") when the tool name itself has no token overlap with the query?
- **Tool ranking** — given 50+ flame_* / forge_* tools, can the model identify `flame_execute_python` as the right answer for an introspection query that no narrow tool covers?
- **Introspection escalation** — does the model correctly escalate from narrow flame_* tools to the escape hatch when the narrow tools return adjacent-but-insufficient data, rather than looping?
- **Runtime convergence** — does the model produce an answer within the 125s outer chat budget without hitting the FB-C 120s inner LLM cap?
- **Graph completeness** — does bridge's substrate actually expose the data the query asks for (yes — `flame.project.current_project.current_workspace.desktop.reel_groups[*].reels[*].clips`)?

A single query that tests five orthogonal substrate properties. That's why it's load-bearing.

## Why It Belongs as a Named Fixture, Not Just a Docstring Pin

Phase 23.1 pinned the query in two places:
- The `Example 1` body of `flame_execute_python`'s docstring (LLM pattern-match material).
- The `CANONICAL_FLAME_INTROSPECTION_QUERY` constant in `tests/test_flame_execute_python.py` (static test pin against drift).

Both are correct but local. The query deserves promotion to a shared fixtures module — somewhere like `tests/fixtures/canonical_queries.py` or `forge_bridge/_canonical_queries.py` — so that:

1. **The chat REPL phase (v1.6 Phase 25)** can include a `/smoke` slash command that fires the query against the live chat endpoint and reports convergence status.
2. **CI smoke** (when CI gets built) can run the query against a mocked-Flame substrate as a fast-feedback regression gate.
3. **Evals / benchmark fixtures** can include the query in a wider canonical-query battery for new-model qualification (default-model bumps, opus migrations, cloud-vs-local routing decisions).
4. **The schematic v2.0** can use the query as a demo input — operator types it, schematic shows the model picking `flame_execute_python`, the Python author-runtime executes against Flame's data graph, the entity graph updates with the result.

A docstring example tests "did the model see this shape." A fixtures-module entry tests "does the system converge on this query under production conditions." The latter is what v1.6+ wants.

## What the Query Does NOT Test (For Honesty)

This is one query. It's load-bearing but it's not comprehensive. It does not test:

- **Mutation** — the canonical query is read-only. The mutation surface (staged-ops, main_thread=True) is its own regression path.
- **Multi-turn conversation** — the canonical query is single-shot. A v1.6 REPL test for multi-turn ("show me Reel 1's clips" → "now their durations") is a separate fixture.
- **Cross-domain queries** — "compare clip names on Reel 1 with published shots in the registry" exercises the entity graph + cross-tool composition; that's a v1.7+ fixture.
- **LLM provider variation** — the canonical query is exercised against whatever the configured local model is. v1.6's default-model-bump seed (`SEED-DEFAULT-MODEL-BUMP-V1.4.x`) wants its own variant suite.
- **Failure-mode convergence** — what happens when Flame is unreachable mid-query, or when Reel 1 doesn't exist? Each warrants its own canonical query.

The single canonical query is a smoke, not a coverage matrix. v1.6+ should grow the matrix; the canonical query stays as the bellwether.

## Activation Triggers

Any of:

1. **v1.6 milestone opens** — natural sequencing for promotion to shared fixtures module.
2. **A new chat surface ships** (REPL Phase 25, foundry dialog from `SEED-FLAME-CHAT-FOUNDRY-V1.6+`, Console exec view Phase 26) — the query becomes the smoke test for the new surface.
3. **A regression of the 23.1 docstring repositioning surfaces** — if a future cleanup strips the "canonical answer" / "reflective surface" positioning, the canonical query may stop converging again. The fixtures-module entry serves as the canary.
4. **CI / benchmark / eval surface is added** — the query is a natural seed for whatever testing infrastructure v1.6+ ships.
5. **Default-model-bump evaluation** (per `SEED-DEFAULT-MODEL-BUMP-V1.4.x`) — the canonical query is one of the empirical gates for "does this new model converge on what the old model converged on?"

## Implementation Notes

When promoted, the canonical query should carry:

- **The exact string** — `"What are the clips on Reel 1"`.
- **The expected tool selection** — `flame_execute_python` (not `flame_list_desktop`, not `flame_context`).
- **The expected convergence time bound** — under the FB-C 120s inner cap on the current default model; tighter targets for future models.
- **The expected output shape** — a JSON object with `reel` and `clips` keys, where `clips` is a list of strings.
- **The expected substrate prerequisites** — a live Flame session with a populated desktop containing a reel named "Reel 1" with at least one clip.

A minimal fixture shape:

```python
@dataclass(frozen=True)
class CanonicalQuery:
    query: str
    expected_tool: str
    convergence_budget_s: float
    expected_output_shape: dict[str, type]
    substrate_prereq: str

CANONICAL_FLAME_INTROSPECTION_QUERY = CanonicalQuery(
    query="What are the clips on Reel 1",
    expected_tool="flame_execute_python",
    convergence_budget_s=120.0,
    expected_output_shape={"reel": str, "clips": list},
    substrate_prereq="live Flame session with populated desktop + 'Reel 1' reel containing >=1 clip",
)
```

## Cross-Reference

- Phase 23.1 docstring pin: [forge_bridge/tools/utility.py](forge_bridge/tools/utility.py) — Example 1 of `execute_python.__doc__`.
- Phase 23.1 test pin: [tests/test_flame_execute_python.py](tests/test_flame_execute_python.py) — `CANONICAL_FLAME_INTROSPECTION_QUERY` constant + `test_canonical_regression_query_constant_is_stable`.
- Phase 23.1 CONTEXT: [.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md](.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md) — §4 Gate 3 (author-walk against this query) and §6 D-20 (in-flight gap-fix discipline).
- v1.6 framing: [.planning/milestones/v1.6-FRAMING.md](.planning/milestones/v1.6-FRAMING.md) — §11.5 Phase 24 narrows because the MCP-side tool shipped here; the query naturally becomes one of v1.6 Phase 25 (chat REPL) smoke checks.
- Sibling seed: `SEED-COLD-LOAD-UX-V1.6+` (to be planted) — user-side feedback during cold model load, observed during the same author-walk.

## Why Plant Now

The query has been *de facto* canonical since the conversation that opened 23.1 — it's been cited repeatedly across:

- The framing conversation that drafted v1.6-FRAMING.md.
- The 23.1 CONTEXT's Gate 3 verification clause.
- The 23.1 docstring's Example 1.
- The 23.1 test suite's `CANONICAL_FLAME_INTROSPECTION_QUERY` constant.
- The post-walk cross-writer reframe that named it "the canonical bellwether for whether bridge's introspection story is operationally believable to artists."

That's five citations of the same query as load-bearing in a single phase. The pattern is unambiguous: this query is canonical *now*; what's missing is the operational substrate that lets it be referenced from anywhere in the codebase. Planting the seed captures the framing before it dilutes into "we kept mentioning that query in Phase 23.1" — and gives v1.6's REPL / Console-exec / foundry phases a ready hook to promote against.

Bridge's graph-native runtime story (per [.planning/milestones/v1.6-FRAMING.md](.planning/milestones/v1.6-FRAMING.md)) is operationally believable to artists *if and only if* bridge can answer this query naturally. That's not architectural philosophy — it's an empirical claim. The seed converts the claim into a testable fixture.
