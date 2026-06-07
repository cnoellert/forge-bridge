# Cycle-1 Seam Freeze — Pass-to-Code Brief

**Executor:** DT. **Source of authority:** `.planning/Q4-SEAM-ALLOCATION.md` (banked convergence).
**Scope:** freeze **#5 (role registry)** + **#4a (relationship-edge vocab)** only.
**Explicitly NOT in scope:** #4b owner-type enum, #3 binding, #6 transport, clock-topology split — all deferred with triggers (see Q4 doc). Do not touch them.

**Principle:** the read-side correlate already shipped (edge-traversal readers, `32ec8ba`, live-verified). This is the **contract-side half** — publish the `version_of`/role vocabulary as shared nouns so forge-core and forge-bridge stop defining them independently (the render-skew class of bug).

---

## Grounded inputs (verified, lock against these)

- **Role members** (`forge_bridge/core/vocabulary.py:154-181`, `STANDARD_ROLES`):
  - **track** (`role_class="track"`): `primary, reference, matte, background, foreground, color, audio`
  - **media** (`role_class="media"`): `raw, grade, denoise, prep, roto, comp, render`
- **Relationship edges** (`forge_bridge/core/registry.py:670-678`, built-ins): `member_of, version_of, derived_from, produces` (live counts confirmed: produces 45 / version_of 20 / derived_from 2 / member_of 2).
- **Contract pattern** (`forge_contracts/capabilities.py`): `TypeAlias` + module constants + `frozenset` + `ContractModel(extra="allow", frozen=True)`; single `CONTRACT_VERSION`.

---

## Part A — forge-contracts (separate repo: `~/GitHub/forge-contracts`)

1. **New module** `src/forge_contracts/vocabulary.py` (mirror `capabilities.py` idiom — constants + frozensets; a small descriptor model only if it reads cleaner):
   - Role classes: `ROLE_CLASS_MEDIA = "media"`, `ROLE_CLASS_TRACK = "track"`.
   - `KNOWN_MEDIA_ROLES: frozenset = {raw, grade, denoise, prep, roto, comp, render}`.
   - `KNOWN_TRACK_ROLES: frozenset = {primary, reference, matte, background, foreground, color, audio}`.
   - `KNOWN_RELATIONSHIP_TYPES: frozenset = {member_of, version_of, derived_from, produces}` (+ their one-line semantics, from registry.py).
   - **Extension rule, published explicitly in the module docstring:** validate `role_class ∈ {media, track}`; **membership is OPEN** — these are *known* members, not an *allow-list*. Custom/unlisted roles are permitted (codifies bridge's existing registry: protected built-ins + `register()`). Same open rule for relationship types.
2. **Additive bump:** `CONTRACT_VERSION "v0.1" → "v0.2"`; export the new names from `__init__.__all__`; keep `ContractModel` `extra="allow"`. Tag **`v0.2`** (bridge pins by git tag).
3. **Tests:** the known-sets are importable; the extension rule is documented and not enforced as a closed enum.

**Success (this layer):** role classes + known members + edge nouns + the open-extension rule importable from forge-contracts `v0.2`. Nothing about *who emits* lives here.

## Part B — forge-bridge (this repo)

1. Re-pin `forge-contracts @ git+...@v0.2` in `pyproject.toml`.
2. **No-drift invariant (the actual ask):** bridge's built-in role names+classes (`STANDARD_ROLES`) and built-in relationship-type names must be **sourced-from or validated-against** the contract's known sets, so they cannot silently diverge. Recommended mechanism: have bridge's built-in *name/class* definitions reference the contract constants (build local enrichment on top); fallback if too invasive: a consistency test asserting bridge built-ins ⊇ contract known-sets. DT picks the mechanism; the invariant is **no drift**.
3. ⚠️ **Guards (reject violations):**
   - **Do NOT rewrite bridge's `Role`** — it carries `order`, `generation_floor`, flame `L0x` aliases. The contract owns *names + classes*; bridge keeps the operational metadata. A "clean rewrite for conformance" here is an infra regression.
   - **Open registry, NOT closed enum** — bridge validation keeps allowing off-list roles. **Two live extension-member cases must not become contract violations: `role: plate` and `role: workfile` (Phase 39, 2026-06-07).** Validate `role_class`, not membership. (`workfile` rides as an open extension member — it is NOT added to `KNOWN_MEDIA_ROLES`; see the workfile ruling.)
4. **Success (this layer):** built-in role/edge names sourced-or-validated against contract `v0.2`; local enrichment intact; existing role/registry tests green byte-equivalently; a test that *fails on drift*.

## Part C — forge_core / forge-pipeline (consumer) — COORDINATE, likely DEFER

Adopt the contracted nouns (emit roles + edges against the shared vocabulary). ⚠️ **forge-pipeline is under active concurrent work (phases 38/39).** Do **not** edit that repo without coordinating — Part C rides after A/B land and after a heads-up to whoever is in 38/39. A and B deliver the shared vocabulary; C is the consumer adopting it on its own clock.

---

## Repo map & sequence
1. **Part A** — forge-contracts repo → module + v0.2 tag.
2. **Part B** — forge-bridge repo → re-pin + no-drift wiring + guards + drift test.
3. **Part C** — forge_core/pipeline → adopt (coordinate; defer behind 38/39).

A→B are bridge-side and executable now. C is consumer-side and gated on coordination.
Reference shapes here are shapes, not rewrite mandates — match each repo's idiom.

---

## Execution result (2026-06-07) — A + B SHIPPED

- **Part A** forge-contracts: `73197b1` `feat(vocabulary)` — pushed to `main` + **tag `v0.2`** on remote. CONTRACT_VERSION v0.1→v0.2, package 0.2.0. 15/15 green.
- **Part B** forge-bridge: `bfc7e25` `feat(contracts)` — re-pin @v0.2 + `tests/test_contract_vocabulary_alignment.py` (no-drift guard). Env reinstalled to forge-contracts 0.2.0; full suite 2858 green against installed v0.2. Both guards held (Role untouched, open registry preserved).
- **Mechanism chosen:** validate-against (drift-failing test), NOT import-time coupling of `core/vocabulary.py` to the contract — keeps the central module resilient if the contract pkg is absent.
- **Drift-test directions (deliberate):** roles `==` contract (all 14 built-ins frozen); rel-types contract `⊆` bridge (the 4-noun freeze is a subset; bridge also ships references/peer_of/consumes, not yet contracted).

## Part C carry-forwards (forge_core adoption — Phase 40; do NOT edit forge-pipeline without coordinating 38/39)

Pipeline verified the federation surface against v0.2 (GO). Rulings banked for Part C:

1. **`render_of` swap is ALREADY DONE** (correction to earlier passoff blocker): forge_core's `render_client.PublishOp` already emits `member_of` + `derived_from` (publish_op.py:4-8, explicit), not a bespoke `render_of`. Only remaining `render_of` is **legacy read-side lineage traversal** (handlers.py blast_radius/lineage), not an emission — retire with the legacy ws-substrate.
2. **`reference` is canonical; do NOT add a `ref` alias to the contract.** forge_core emits `role="ref"`; contract knows `reference`. Fix is consumer-side normalization `ref→reference` at adoption — adding an alias would enshrine the skew the freeze exists to kill.
3. **`workfile` / lifecycle — eventual home intentionally UNBOUND** (Creative redline + Orch synthesis 2026-06-07). "editable-source vs produced-output" is NOT a role question (USD smell test: one type, both states → cuts across types → can't be a `role_class`). It's evidence of a possible *lifecycle* axis orthogonal to role. Axis map: Role (Media, contracted) / Task (Version) / Lifecycle? (undetermined). Already half-collapsed: media `role_class` carries `generation_floor` (`vocabulary.py:167-181`, raw=0 source / rest=1+ produced). **Falsifiable trigger:** watch role-string minting — one role string spanning editable+produced contexts → lifecycle is orthogonal (keep off role axis); minting state-specific role strings → the collapse. Needs a watch-home or it stays unbound forever. **If real, prefer edge over attribute** — but per Pipeline's shapes (workfile→`version_of`→shot bridge_store_adapter.py:369; render→`member_of`+`derived_from` publish_op.py:146,157) `version_of` is overloaded, so it'd need a NEW source edge, not free derivation. Do NOT add a `source` role_class on the next source artifact. Full framing in `HANDOFF-2026-06-07-CYCLE-1-AND-PIPELINE.md`.
   - **`task`** (workstream owning a lineage): lives on **Version**, orthogonal to role; single canonical home, derive by traversal, NEVER dual-source (`parent_id`/`shot_id` lesson); vocabulary stays open/local until multiple repos+DCCs exercise it (owner-type lesson: freezes follow diversity).
4. **`{media, comp}` role_class skew** lives only in forge_core's **retired legacy ws-substrate** (handlers.py:811, db/models.py:318 CHECK) — not on the federation surface. Reconcile-when-retired, not a contract concern.
5. **Pin-lag (benign):** forge-pipeline's pyproject still declares forge-contracts v0.1 while the env has v0.2 (same class as the forge-bridge v1.5.1 gap). Cosmetic pip warning; clean up in Phase 40 (bump pipeline → v0.2 + forge-bridge → new tag together).

**Pipeline owns the consumer-side post-flip check:** re-run pipeline contract + workfile suites against the v0.2 env to confirm green (their offer; closes the loop without any Part C edits yet).
