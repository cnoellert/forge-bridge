# TF.1 — Translation Layer Inventory

**Scope:** name + bound the scattered translation machinery TF.1 formalizes (not build — formalize).
Grounded against live source. Counts are archaeology-grade — recount before citing elsewhere.

---

## The six components

| # | Component | Role (translation activity) | Resolution point(s) | Axis |
|---|---|---|---|---|
| 1 | `compile_intent` (`router.py:647`) | NL → chain-step graph | **compile** | produces both classes |
| 2 | `filter_tools_by_message` + `deterministic_narrow` (`_tool_filter.py`) | capability resolution (tool selection) | **compile** (+ PR20 forced-execution path) | — |
| 3 | `resolve_query_entities` (`resolver.py:59`) | entity resolution | **compile** (enrich, `handlers.py:1657`) **AND dispatch** (`_step.py:568`) — **the straddle** | both |
| 4 | `extract_explicit_params` (`_param_extract.py:87`) | explicit-param extraction (the "explicitly ratified" set) | **dispatch** (`_step.py:253`; wins the `:261` merge) | compile-resolved |
| 5 | `apply_source_routing` (`_source_route.py`, SR.1) | reads source-routing | **post-compile**, reads branch | — |
| 6 | `apply_executor_routing` (`_executor_route.py`, C2) | mutation executor routing (→ commit-bearing chain) | **post-compile**, before commit-classification | — |

## Straddle map (where resolution completes)

- **Compile-side:** `compile_intent` · tool filter/narrow · `apply_source_routing` · `apply_executor_routing`
  · the enrich-time `resolve_query_entities` (`handlers.py:1657`).
- **Dispatch-side:** `extract_explicit_params` (`:253`) · `_extract_semantic_step_params` →
  `resolve_query_entities` (`:568`) · the param merge (`:261`) · the honest-decline net (`:407`).
- **The straddle = component 3** runs at *both* — and the dispatch instance is where context-resolved params
  complete (and where the Phase-4 `desktop` wiring lands).

## Two structural facts that anchor the contract

- **Unwired `desktop`** (`resolver.py:61`) — the param exists ("accepted for the eventual live-Flame
  validation pass") but is never passed at either call site → today both resolution points are **text-only**.
  This is the **context-resolution enablement gap** (defect #3's mechanism): the open sequence lives in
  desktop state, the resolver can take it, nobody supplies it. Wiring it = the Phase-4 contextual fix, at the
  **dispatch** instance of component 3 (where live state is reachable).
- **The honest-decline net** (`:407`, `UNRESOLVED_REQUIRED_PARAM` → "specify the exact sequence name") — not
  a translation component but the system's existing **uncertainty-preservation** mechanism. Example-salience
  defeats it (TF.1-CONTRACT §5): a lifted example masquerades as explicit (captured by component 4),
  bypassing the net. Inventoried here so Phase 4 treats restoring it as a first-class benefit.

## Notes for downstream phases

- **Phase 2 (taxonomy):** the five failure classes map onto these components — grounding (3/4 + tool
  descriptions) · routing (2, incl. PR20-shadows-compile) · extraction (4) · entity-resolution (3) ·
  contextual/stateful (3-dispatch + the unwired `desktop`).
- **Phase 3 (oracle):** validates context-resolved params at both straddle points (component 3, both sides).
- **Phase 4 (quality):** example-strip targets the tool-description corpus feeding component 1; the
  contextual fix wires `desktop` into component 3-dispatch; the provenance signal rides components 3/4 output.
