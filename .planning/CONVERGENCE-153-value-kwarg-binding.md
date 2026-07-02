# Convergence — #153 input-identity→kwarg VALUE binding in the M2 graph engine

**Date:** 2026-07-02
**Subject:** How to bind the value→kwarg mapping so inherited-arg chains execute
correctly through the graph path — the slice-6 cutover blocker (slice 6 cannot
retire `run_chain_steps` for inherited-arg chains until this binds).
**Method:** 4-view convergence (graph-purist / cutover-pragmatist / IR-architect /
scope-skeptic), grounded against `main`, redlined.
**Status:** design decided; build not yet scoped.

---

## Decision

**Reject the monolithic (a)/(b)/(c) framing. Build (b) in its *cheap* form:** a
**compiler-authored extractor node** + an **edge-sourced *mechanical* kwarg-merge**
on the MCP boundary — following the shipped `ForeachBoundary` precedent. **Zero new
IR.** `executor.py` byte-stable.

Concretely:
- A small **extractor primitive** whose body is the singleton-guarded which-key
  logic (reuse `extract_chain_context`, `_chain_parse.py:129-152`), emitting a
  **single-key `{kwarg: value}` dict** as its typed output. The runtime which-key
  decision lives *inside this visible node*.
- The dict rides a **normal value-edge** into a **nominated named input port** on
  the downstream MCP node — the same edge-value mechanism `ForeachBoundary` already
  consumes (`foreach_boundary.py:46-56` reads `upstream.output` cleanly, shipped in
  the foreach cutover #133–#144).
- `MCPToolBoundary` gains **one mechanical branch**: source the existing
  `metadata.scalars` merge (`boundary.py:130-145`, already `kwargs.update(scalars)`)
  from a declared input port's `resolved_inputs[port].output` instead of static
  config. The boundary gets **zero extraction meaning** — just a merge.
- The **compiler** authors the extractor nodes + edges. For the tool-name
  special-cases (`format_result.data`, `selected_segments`), the compiler wires the
  edge explicitly at author-time (it knows the tool then) → the tool-name decision
  becomes **visible compile-time edge-authoring in the GraphSpec, not runtime
  boundary `if tool_name in {...}`**.

---

## Reasoning that carried it (who won the redline)

1. **Cost collapse — architect + purist beat the pragmatist.** (a)'s whole case
   ("smallest diff; (b) is a milestone") rested on (b) needing new port typing — and
   it doesn't. The extractor emits a single-key dict (the name rides in the *value*,
   not the port type), which `infer_topology` already types and the existing
   `metadata.scalars` merge already consumes. So (b)-cheap ≈ one primitive + one
   mechanical boundary branch + one config field ≈ (a)'s cost. **Verified:**
   `boundary.py:130-145` (the scalars merge) + `foreach_boundary.py:46-56` (clean
   edge-value read already shipped).
2. **Runtime-conditionality is not an obstacle — beats the pragmatist's load-bearing
   redline.** "Static authorability of *structure* ≠ static resolution of *value*."
   The compiler authors the extractor statically; the singleton-guarded which-key
   decision runs at runtime *inside the visible node*. Ambiguity becomes documented
   node behavior, not hidden dispatch magic. Over-insertion is safe:
   `normalize_tool_args` (`boundary.py:80`) drops keys the downstream tool doesn't
   accept.
3. **Doctrine — (a) breaks the line at the worst moment.** (a) puts extraction
   *meaning* in the value-blind boundary (reverses its stated invariant) and
   **forecloses the operator-drivable graph — "you can't drive what you can't see."**
   (b)-extractor keeps the boundary mechanical, meaning in a node. First live cutover
   sets the founding precedent.
4. **Skeptic's value-class split refines scope (load-bearing).** Do NOT replicate the
   tool-name special-cases as runtime `if tool_name in {...}` in the boundary — that
   copies legacy cruft into a second author (drift, [[project_one_canonical_author_per_representation]]).
   The compiler authors those edges. Also: the skeptic's ground fact that
   `boundary.py:13`'s "unbound pending #86" is **stale** — value-flow is already bound
   cleanly in `ForeachBoundary`; #153 is narrowly "`MCPToolBoundary` grows the same
   clean edge-reading."

---

## Structural seam — the one pin-before-build
**Merge precedence:** static `config["arguments"]` vs edge-sourced kwargs. Legacy
folds context *into* kwargs with a specific precedence (public `sequence_name` wins
over payload backfill, `_step.py:673-675`); must be pinned against legacy parity and
tested via `compare.py`. **This is the ONLY legitimate reason to fall back to a
short, explicitly-named transitional (c)** — if precedence can't be cleanly pinned
in this slice. Cost is settled; only this could force a transition.

## Intentionally unbound (re-open trigger)
- **Exact merge precedence** — pending grounding against legacy's fold order.
- **Multi-edge fan-in** ("which upstream supplies the value") — the compiler produces
  linear single-edge chains today; unbound pending a real fan-in inherited-arg case.
- **3-key context as *re-resolution* not value-flow** (skeptic's deeper reframe) —
  pending the "tools = macros over contextual input resolution" north-star mechanism.
  The extractor node is the honest *interim* that models it as clean value-flow and
  doesn't block cutover; full re-resolution-from-context is a bigger motion.

## Rejected
- **(a) implicit boundary-replication** — meaning in the value-blind boundary;
  forecloses the operator-drivable graph; copies tool-name cruft into a second author.
- **(i) new named-value port kind** — the ONLY true structural fossilization (mutates
  the frozen `PortTopology` algebra); unnecessary (name rides in the extractor's dict).
- **(c) as the default** — no maturation trigger → #86 redux; admissible only as the
  precedence-pin fallback.
- **#153 as a monolithic cutover blocker** — it's narrowly `MCPToolBoundary` growing
  the clean edge-value read `ForeachBoundary` already has.

---

## Next: scope the build
Extractor primitive (`graph/` node vocab + admission entry) · compiler edge-authoring
(`chain_compiler.py`) · the one mechanical boundary merge branch (`boundary.py:_node_arguments`)
· the merge-precedence pin + `compare.py` parity against `run_chain_steps` · reads-only
(mutating apply-args deferred per `.planning/CONVERGENCE-102-chain-corpus-forks.md` Fork 2)
· `executor.py` untouched (byte-stable guard).
