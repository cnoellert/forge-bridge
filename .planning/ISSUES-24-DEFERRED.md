# #24 deferred follow-ups — ready to file

Two issues #24 deliberately scoped out (DT grounding 2026-06-09). Drafts ready to paste into `gh issue create`. Filing is left to the operator (outward-facing).

---

## Issue 1 — Wire `register_all_siblings` at bootstrap (planner capability registry)

**Problem.** There are **two federation surfaces** on the `forge_bridge.siblings` entry-point group, and only one is wired at runtime:

| Surface | Mechanism | Feeds | Status |
|---|---|---|---|
| MCP tool-attach (#23) | `register_sibling_mcp_tools` → `<pkg>.bridge.registry:register_with(mcp)` | FastMCP tool list (`forge_*`) | **LIT** (proven live) |
| Capability registry | `register_all_siblings` → `register_capability` → `tool_registry` | planner capability snapshot (`pass_1` → `by_family("generation")`) | **DARK** |

`register_all_siblings` (`orchestration/discovery.py`, docstring: "feeds the planner's capability registry") is **never called outside tests** — `tool_registry` does not appear in `mcp/server.py` bootstrap. The planner federation registry is empty in the live daemon even though the MCP tool surface is lit. This is vision's parked **criterion 2** from #23.

**Why it matters.** Named upstream dependency of **#24(c)** — the live cross-peer generation-facts join. #24's (a)+(b) prove consumption without it; the live path needs `register_all_siblings` wired so `pass_1`'s `by_family("generation")` is non-empty (else: empty snapshot → zero candidates).

**Scope.** Wire `register_all_siblings` into MCP/daemon bootstrap (async; mind the D-14 `_server_started` guard, like the #23 hook). Must surface **generation-family** siblings (generators), not just perception. Per-sibling failures isolated.

**Acceptance.** Live daemon: a registered generation sibling appears in `tool_registry.by_family("generation")`, and a planner run builds a non-empty snapshot carrying that sibling's `generation_facts`.

---

## Issue 2 — Bridge request reference inventory (operand for role/count/input-first-frame feasibility)

**Problem.** #24 ingests the operator-declared `ReferenceRequirementSpec` (`accepts_roles`, `required_roles`, `requires_first_frame`, `max_references`) but wires **no feasibility filter** for roles/count/input-first-frame, because the **request-side operand does not exist** in typed form:
- `inputs_catalog["inputs"]` is ad-hoc untyped dicts.
- `inputs_catalog["role_assignments"]` is `{}` in every fixture and code path — nothing populates it.

So only the operator's *declared requirements* land; there is nothing to compare them against.

**Doctrine boundary.** Generators' `feasibility.py` (`InputInventory.present_roles`, `FeasibilityRecord`) is the **producer oracle** — per ADR-005 it is OUT of the contract. Bridge must **not** import it; bridge derives its own judgment from the typed facts against its own request inventory. This issue builds that inventory.

**Scope.** Populate a typed bridge-side request reference inventory (roles present, first-frame available, reference count) from the inputs catalog, then wire `pass_2` feasibility:
- `required_roles` ⊆ present roles
- reference count vs `max_references` (declared fact — hard-block is bridge's judgment; keep the policy named/isolated)
- **input** first-frame: does the request supply a frame, vs `reference_requirements.requires_first_frame`? (distinct from the dropped output `first_frame_guarantee`, Gate 0)

**Acceptance.** A request missing a `required_role` (or exceeding `max_references`) drops the candidate as infeasible; a satisfying request keeps it — exercised end-to-end through the planner.

Ref: `.planning/BRIEF-24-CONSUME-GENERATION-FACTS.md` §5–§6; DT grounding 2026-06-09.
