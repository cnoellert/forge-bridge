# Pass-to-code brief — bridge #24: consume `GenerationCapabilityFacts`

**Status:** DT-grounded against live files 2026-06-09 (eve). Operator-handed (skips orch re-draft).
**Doctrine:** facts come from the contract (`GenerationCapabilityFacts`); judgments (feasibility, ranking) are derived in bridge. ADR-005 / [facts-judgment spine].
**Producer ready:** generators `82698f9` projects 17 conformant declarations, each carrying `metadata["generation_facts"]`.

---

## 0. The one correction that reshapes everything

The original draft pointed the seam at `discovery.py → register_all_siblings`. **That is wrong.** `register_all_siblings` builds the *tool registry*, and the declaration metadata already flows untouched from there into the capability snapshot:

- `registration.py:59` — `tool_registration_from_capability` does `capabilities=dict(declaration.metadata or {})`. So `ToolRegistration.capabilities` **is** the declaration metadata.
- `planner_passes.py:82,93` (pass_1) — snapshot entry is built as `capabilities_opaque: caps` where `caps = tool.capabilities`.

**Therefore `snapshot_entry["capabilities_opaque"]` equals `declaration.metadata` byte-for-byte**, and `generation_facts` rides through with zero new plumbing. The entire change lives in **`planner_passes.py`** — no `discovery.py`, no `registration.py`, no snapshot-schema, no store changes.

---

## 1. Hard precondition — the pin (do this first, in order)

The bridge `forge` env still has `forge-contracts 0.2.0` (non-editable). The v0.3 types (`GenerationCapabilityFacts`, `BackendIdentityTriple`, `ReferenceRequirementSpec`) **do not import yet**. Sequence is strict:

1. `pyproject.toml:23` — bump `...@v0.2` → `...@v0.3`.
2. `pip install -e ".[dev,llm]"` (must follow the bump, or it reinstalls v0.2 over the env; `allow-direct-references` already set).
3. Verify: `python -c "from forge_contracts.generation import GenerationCapabilityFacts, GENERATION_FACTS_KEY; print('ok')"`.
4. Only then write code.

> ⚠ Generators reported "env now has v0.3 editable" — that was *their* interpreter, not bridge's `forge` env. Don't trust it; the verify step above is the gate.

---

## 2. The contract shape (v0.3, read from source)

```python
# forge_contracts/generation.py
GENERATION_FACTS_KEY = "generation_facts"   # lives inside CapabilityDeclaration.metadata

class BackendIdentityTriple(ContractModel):   # the cross-peer join key
    surface: str; path: str; auth_mechanism: str; revision: str

class ReferenceRequirementSpec(ContractModel):
    accepts_roles: list[str] = []
    required_roles: list[str] = []
    requires_first_frame: bool = False
    max_references: int | None = None         # declared FACT, not enforcement

class GenerationCapabilityFacts(ContractModel):
    backend_identity: BackendIdentityTriple
    reference_requirements: ReferenceRequirementSpec = ReferenceRequirementSpec()

    @classmethod
    def from_metadata(cls, metadata) -> "GenerationCapabilityFacts | None":
        # None when GENERATION_FACTS_KEY absent. RAISES pydantic.ValidationError
        # when the key is present but malformed. <-- this matters, see §4.
```

---

## 3. The change (three edits, all in `planner_passes.py`)

**3a. pass_1 (`:80-96`) — prefer the typed triple.** Today it reads `caps.get("backend_identity_triple")` and synthesizes a `{surface, path}` fallback. Prefer `GenerationCapabilityFacts.from_metadata(caps).backend_identity` when facts are present; keep the existing fallback when absent. (Reference shape, not a rewrite mandate — preserve the existing fallback behavior for non-facts tools.)

**3b. pass_2 (`:116`, candidate filter) — derive feasibility from facts.** Inside the per-entry loop, parse `facts = _safe_facts(entry)` (see §4). Wire feasibility on **only the requirements that have a request-side operand today**:
- **first-frame → DO NOT wire any new filter (Gate 0 resolved, §5).** And **do not touch the existing `:143` `first_frame_guarantee` filter** — it's bridge-internal and load-bearing across the suite (many fixtures stamp `first_frame_guarantee: True` to survive it). #24 leaves it exactly as-is.
- `requires_identity_lock` / `identity_lock_support` — already handled at `:147`; leave intact. Genuine support fact, safe to read as-is.
- **`required_roles` / `max_references` → DEFER (see §6). Do not wire a filter against an empty operand.**

Net: pass_2 gains the typed-facts *parse* (for the join triple + degrade guard) but **no new candidate-drop logic** — every honest filter needs a request-side operand that doesn't exist yet. The typed-facts value #24 delivers is ingestion + join, not new feasibility.

**3c. pass_5 (`:293`) — ranking already exists.** Incorporate facts only as needed; no structural change required. Keep the derived `surface.path` string as the internal dict key (see §7).

---

## 4. Graceful degrade — `from_metadata` RAISES, it doesn't just return None

`from_metadata` returns `None` only when the namespace key is **absent**. A **present-but-malformed** payload raises `pydantic.ValidationError`. Since pass_1 loops over *all* generation tools, one malformed payload would crash planning for every sibling. Wrap it:

```python
def _safe_facts(entry):  # reference shape
    caps = _capabilities(entry)
    try:
        return GenerationCapabilityFacts.from_metadata(caps)   # None if absent
    except ValidationError:
        # emit a registration/planning warning event; fall back to untyped caps.
        # Do NOT crash, do NOT silently drop a human-declared backend.
        return None
```

Off-namespace declarations (non-generation families, un-republished generators) → `None` → existing untyped path, no regression. This satisfies the original Q4 "graceful degrade," made correct for the raise case.

---

## 5. Gate 0 — `first_frame` semantic collision: RESOLVED (generators `7644664`)

Generators confirmed the two are **not** equal and **dropped the flat `first_frame_guarantee` key entirely** from their projection (it was their bug — stamping an output-named key from an input value; they publish no output-first-frame fact, ADR-001). The honest input requirement stays typed at `generation_facts.reference_requirements.requires_first_frame`.

**Consequences for #24:**
- **Do not write any new first-frame filter into pass_2.**
- **Leave the existing `:143` `first_frame_guarantee` filter untouched** — it's bridge-internal and load-bearing in the test suite (fixtures stamp `first_frame_guarantee: True` synthetically; they don't go through generators' projection, so generators' drop doesn't break bridge tests).
- **Live-path divergence (defer, don't fix in #24):** in the live (c) path, generators' real declarations no longer carry `first_frame_guarantee`, so the `:143` filter would over-drop generation candidates *if* a live request sets `deliverable.requires_first_frame`. The honest replacement is an **input-feasibility** check ("does the request have a frame to supply?") against `reference_requirements.requires_first_frame` — which needs the same request-side inventory operand that's unbuilt. **Folds into the deferred "request reference inventory" gap (§6), not #24.**
- Adjacent (generators-confirmed): `identity_lock_support`, `upload_support`, `estimated_cost`, `chain_depth`, `content_policy_real_person_classifier` are genuine support/cost facts, safe to read as-is. (`upload_support` is uniformly `True` on their surface — won't discriminate.)

---

## 6. Honesty cap — what #24 does NOT deliver

The request-side reference inventory does not exist in typed form: `inputs_catalog["inputs"]` is ad-hoc untyped dicts; `role_assignments` is `{}` in every fixture and path. So `required_roles` and `max_references` have **no operand to filter against**. Generators' `feasibility.py` (`InputInventory.present_roles`, `FeasibilityRecord`) is the **producer oracle** — per ADR-005 it is OUT of the contract; **do NOT import it.** Bridge derives its own judgment from facts against its own inventory, which is unbuilt.

**Action:** defer role/count feasibility behind a named **"bridge request reference inventory"** gap (a request-modeling deliverable, its own future issue). #24's (a)+(b) green must not launder into "feasibility works."

---

## 7. Residual join-key note (no migration needed)

The full `backend_identity_triple` is *already* stored on every snapshot entry and pass_2 already reads `revision` off it (`:159`). `backend_id_from_snapshot_entry` derives `surface.path` as the dict key. Keep it. Only widen the derivation if a real colliding-backend case (same surface.path, different auth/revision) appears — none exists today. No string→triple type migration.

---

## 8. Acceptance ladder

- **(a) unit — drift-proof.** Instantiate `GenerationCapabilityFacts(...)` from the real forge-contracts type → put it under `metadata[GENERATION_FACTS_KEY]` → feed through `tool_registration_from_capability` (**not** discovery.py) + pass_1 snapshot build → pass_2 filters (feasible + infeasible + malformed-degrade cases) → pass_5 ranks → assert join on `BackendIdentityTriple`. Fixture built from the contract type so it can't drift.
- **(b) stub-sibling — real round-trip now.** A minimal `forge_bridge.siblings` entry-point publishing a contract-valid `generation_facts` declaration, registered through the **real `register_all_siblings`** path → planner filters/ranks live through real machinery. Proves the integration (a) can't. Doubles as generators' conformance reference. (b) calls `register_all_siblings` *directly* — it does NOT need bootstrap wiring.
- **(c) FLAGGED — live cross-peer, double-gated.** Real generators' 17 declarations joined live. Gated on **both**: (i) the §1 pin bump, **and** (ii) criterion-2 — `register_all_siblings` wired at bootstrap so the planner's capability registry is non-empty in the live daemon (it is currently DARK; `register_all_siblings` is never called outside tests). File criterion-2 as its own issue, scoped to surface **generation-family** siblings. Do not let (a)+(b) green imply (c).

---

## 9. Constraints

`forge_bridge.__all__` == 19 (untouched) · version 1.5.1 · ruff clean · no new external libs · off-namespace declarations degrade with no planner regression · DT verifies, doesn't self-implement.
