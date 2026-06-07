# Handoff — 2026-06-07 — Cycle-1 Seam Freeze shipped; Pipeline / Phase-40 inputs

**Audience:** forge-pipeline / Pipeline team (Phase 40 owners).
**Status:** Cycle-1 (#5 role vocab + #4a edge vocab) **shipped, verified, live.** Nothing blocks Pipeline.

---

## TL;DR

forge-contracts **v0.2** is published; forge-bridge is re-pinned, drift-guarded, and the
portofino daemon is restarted onto it. The shared role/edge vocabulary is now a single source
of truth — peers stop defining `version_of`/roles independently (the render-skew bug class is
structurally closed). Two things for Pipeline: **(1)** run your consumer-side post-flip check,
**(2)** Phase 40 = forge_core adoption + doc cleanup, with all rulings banked below so nothing
gets relitigated.

## What shipped & where (everything pushed)

| Repo | Ref | What |
|---|---|---|
| forge-contracts | `main @ 73197b1` + tag **`v0.2`** | new `forge_contracts.vocabulary`; `CONTRACT_VERSION v0.1→v0.2`; pkg `0.2.0` |
| forge-bridge | `main @ 4b47a43` | re-pin `@v0.2` + no-drift test; edge-traversal readers (`32ec8ba`); Cycle-1 doc |
| portofino env | — | forge-contracts **0.2.0** installed (pin resolves from tag) |
| portofino daemon | — | restarted → live on `4b47a43` + v0.2; **v0.2 is on the federation wire now** |

Full detail: `forge-bridge/.planning/CYCLE-1-PASS-TO-CODE.md` (brief + execution result).

## The shared vocabulary (v0.2) — conform to this

Import from `forge_contracts.vocabulary`:

- **`role_class` — CLOSED:** `{media, track}` (the only validated axis).
- **`KNOWN_MEDIA_ROLES` (OPEN):** `raw, grade, denoise, prep, roto, comp, render`
- **`KNOWN_TRACK_ROLES` (OPEN):** `primary, reference, matte, background, foreground, color, audio`
- **`KNOWN_RELATIONSHIP_TYPES` (OPEN):** `member_of, version_of, derived_from, produces`
- **Rule:** membership is OPEN (known ≠ allow-list) — custom roles/edges are permitted and NOT
  rejected. Only `role_class ∈ {media, track}` is enforced.

## Pipeline — do now (consumer-side post-flip check)

Run the pipeline **contract + workfile** suites against the v0.2 env to confirm green. This is
your own offer and closes the loop — **no Part C edits required for it.** (Pipeline pre-verified
the federation surface: no `role_class` emitted on the wire, edges are all contract nouns,
`CONTRACT_VERSION` not hard-pinned → additive bump is safe.)

## Phase 40 / Part C — forge_core adoption (rulings banked — do NOT relitigate)

> ⚠️ forge-pipeline was under active 38/39 work — coordinate before editing it.

1. **`reference` is canonical.** forge_core emits `role="ref"`; normalize `ref → reference`
   **consumer-side**. Do NOT add a `ref` alias to the contract — that would enshrine the skew.
2. **`workfile` / lifecycle — eventual home intentionally UNBOUND** (Creative redline + Orch
   synthesis 2026-06-07). "editable-source vs produced-output" is **NOT a role question** —
   smell test: a single type (e.g. a USD assembly) can be editable-working in one place and
   published-deliverable in another, so source/output cuts across artifact types and **can't be a
   `role_class`.** Workfile pressure is evidence of a possible *second axis* — **lifecycle**,
   orthogonal to role — not evidence for a `source` role_class. Workfile rides as an open
   media-extension member for now. Corrected axis map: **Role** (Media, contracted) · **Task**
   (Version, below) · **Lifecycle?** (undetermined — may not even be a formal axis yet).
   - **Already half-collapsed today:** media `role_class` carries a latent source/produced signal
     via `generation_floor` (`forge_bridge/core/vocabulary.py:167-181` — `raw=0` "never produced"
     vs else=`1+` "product of a process"). `raw` is a source already wearing a media-role hat.
   - **Falsifiable resolve trigger** (don't count source artifacts — watch whether artifact-type
     and stage vary *independently*): does a single **role string** appear in both an editable and
     a produced context → lifecycle is a real orthogonal axis, keep source OFF the role axis; or
     does the vocabulary start **minting state-specific role strings** → that's the collapse
     happening. Same-type-both-states = proof; never-overlapping types only weakly supports role.
     **The trigger needs a watch-home** (something observing role-minting across repos/DCCs) or
     "unbound pending pressure" silently becomes "unbound forever."
   - **If lifecycle resolves real, prefer edge topology over a stored Media attribute**
     (edge-over-attribute). ⚠️ But per Pipeline's reported Phase-39 shapes — workfile → `version_of`
     → shot (`bridge_store_adapter.py:369`); render → `member_of`+`derived_from`
     (`publish_op.py:146,157`) — existing edges do NOT cleanly carry it: `version_of` is
     **overloaded** (workfiles AND produced versions use it). Edge-expressing lifecycle would need
     a *new, cleaner* source edge (e.g. `edited_from`) — itself a contract decision, not free
     derivation. (Pipeline to confirm; forge-pipeline under active 38/39 — don't probe/edit.)
   - **Do NOT add a `source`/`workfile` `role_class` when the next source artifact appears** — only
     once confident source/output belongs on the role axis *at all*. `role_class` is the closed,
     highest-cost axis; freezing the wrong correction there is the premature-axis-mutation avoided
     all year.
3. **`render_of` swap is ALREADY DONE** (Pipeline-verified): `render_client.PublishOp` already
   emits `member_of` + `derived_from` (publish_op.py:4-8). Only remaining `render_of` is
   **legacy read-side lineage traversal** (handlers.py blast_radius/lineage) — retire with the
   legacy ws-substrate, not an emission fix.
4. **`{media, comp}` role_class skew** (Pipeline-reported: handlers.py:811, db/models.py:318
   CHECK) lives only in forge_core's **retired legacy ws-substrate** DB — not on the federation
   surface. Reconcile-when-retired.
5. **Doc cleanup (folded into Phase 40):**
   - `forge-contracts/README.md:28` still says *"released as 0.1.0 with default contract version
     v0.1"* — stale, now `0.2.0`/`v0.2`.
   - `forge-contracts/docs/BRIDGE-DISCOVERY-RUNTIME-CHECKLIST.md` documents a `v0.1`
     **exact-match** handshake. NOT enforced in code (forge-bridge orchestration has zero
     `contract_version` comparisons), but reconcile the doctrine to "additive/compatible" to
     match the actual `extra="allow"` design — otherwise a sibling implementing it literally
     would reject v0.2 declarations.
   - Add a `v0.2` vocabulary doc (repo convention has `*-v0.1.md` versioned docs).
6. **Pin-lag (benign):** forge-pipeline's `pyproject.toml` still declares forge-contracts `v0.1`
   while the env has `0.2.0` (cosmetic pip warning). Bump pipeline → v0.2 **and** forge-bridge →
   the new tag together in Phase 40.
7. **`task` (workstream owning a lineage — comp/fx/lighting/editorial) lives on Version, not
   Media.** Task describes the lineage; media are artifacts the lineage emits (task-on-media =
   `sequence_name` on a render frame). Same edge-over-attribute discipline just shipped: **single
   canonical home on Version; derive by traversal everywhere else; NEVER dual-source** (the
   `parent_id`/`shot_id` episode — duplicate ownership is guilty until proven innocent). Task is
   **orthogonal to role.** Task **vocabulary stays OPEN/local** for now — contract it only after
   multiple repos + DCCs exercise the same taxonomy (owner-type lesson: freezes follow diversity,
   not precede it; one production worldview shouldn't mint the taxonomy as canon today).

## Operational note (forge-core stdio MCP)

After the conformance fix (forge-pipeline `8dbc01a`), **both** flame and blender plugins
conform, so `forge_core` now **requires an explicit `FORGE_DCC`** selector when >1 DCC plugin is
installed. Set `FORGE_DCC=flame` (or `blender`) in each launch/MCP `env`. Documented in
forge-pipeline `7caad5f`. (This is why the local forge-core MCP needs `FORGE_DCC=flame` added to
`~/.claude.json` to reconnect.)

## Authoritative pointers

- `forge-bridge/.planning/CYCLE-1-PASS-TO-CODE.md` — brief + execution result + Part C carry-forwards.
- `forge-bridge/.planning/Q4-SEAM-ALLOCATION.md` — the convergence behind the freeze.
