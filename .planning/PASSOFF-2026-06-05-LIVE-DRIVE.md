# Passoff — 2026-06-05 live drive (federation E2E unblocked + render ontology)

**State:** `main` clean and pushed (HEAD `e39bbe8`). Phase 7 generation vertical (V1–V3) verified earlier; this passoff covers the **live drive** that unblocked the forge_core/Blender round-trip against the live bridge and resolved the `render` ontology. forge-bridge side is **done and live**; the remaining work is **forge_core (pipeline) + a coordinated daemon restart**.

---

## ► PIPELINE HANDOFF — implement first thing (forge_core side)

**The room ruling: render is a media ROLE on the node, NOT a `render_of` relationship.** Content-type lives on the node role; the edge is generic `member_of`. (Provenance = `produces`, lineage = `derived_from`, containment = `member_of` — kept orthogonal.)

**The bridge side is already done & live** — `render` media role is seeded in the operator DB (`:7533`) and on `main` (role_class `media`, key `00000000-0000-0000-0010-000000000007`).

**forge_core change to make:** in `forge_core.render_client.PublishOp` (and anywhere emitting `*_of`):
- Replace `create_relationship(media, shot, "render_of")` → **`member_of(media → shot)`** with the **media's role set to `render`**.
- If `plate_of` exists: same shape — `member_of(media → shot)` + role ∈ existing media roles (a plate is typically `raw`, or `grade` if graded). **Do not** add `plate_of`.
- `render_of` / `plate_of` do **not** exist in the bridge and won't be added (by design).

**PREREQUISITE before pipeline can use `role=render`:** the running daemons hold the *old* in-memory role set. **Restart required** so the registry loads `render`:
```
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge-server   # state_ws :9998
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge          # console/mcp :9996/:9997
```
That same restart also activates the **completed ping correlation** (see below). DB row is already seeded; restart is purely to reload code.

**Reconciliation reference** (for plate/other media): bridge media roles are `raw, grade, denoise, prep, roto, comp, render`. Track roles (separate category) are `primary, reference, matte, background, foreground, color, audio`.

---

## What landed this session (all on `main`, pushed)

1. **Daemon ownership made durable** — three-generation launchd pile-up untangled; `:9998` now has **one managed owner** (`com.cnoellert.forge-bridge-server`), supervised. The recurring "stale daemon" was a **launchd-vs-fbridge** confusion: `fbridge up/down` can't touch launchd-supervised daemons (they show "external"). Distinguish with `sudo launchctl list | grep forge`; restart managed jobs with `kickstart -k`, never `kill`.
2. **Packaging root cause fixed (`58d65f7`)** — `pip install -e .` was failing since Phase 6A because the `forge-contracts @ git+…` direct-reference dep needed `[tool.hatch.metadata] allow-direct-references = true`. Without it, every install silently degraded to a **non-editable** site-packages copy → daemon served stale code → restart "bandaid" that never stuck. Now editable installs work; the env is re-anchored to the checkout; provenance is `ok`.
3. **state_ws correlation fixed (`9083e7f` + `8b3384c`)** — cross-repo envelope skew: bridge keys the correlation id `"id"`, forge_core keys `"msg_id"` and matches replies on `ref_msg_id` (response branch) / bare `msg_id` (pong branch). Fix = bridge-side **bilingual**: read either inbound key; echo the id under `id` + `ref_msg_id` + `msg_id` on all replies. **Catalog path live-verified** (entity_get returns real NOT_FOUND, no hang). Ping completes on next daemon restart. Full writeup: `.planning/STATE-WS-CORRELATION-CONTRACT.md`.
4. **`render` media role added (`496ae8c`)** — see handoff above. Migration `0010`, applied live.

**Result:** the agnostic SDK seam (forge_core ↔ bridge) is **mechanically proven end-to-end** — ImportOp + PublishOp execute live against the catalog. The last edge waits only on the forge_core `render_of → member_of+role=render` swap.

---

## Durable follow-up (named, not yet done) — the recurrence pattern

**Three independent cross-repo vocabulary skews this session:** (1) capability families [Phase 6A], (2) transport correlation envelope, (3) role/relationship vocabulary. Same root: forge_core and forge-bridge independently define shared nouns; eventually they diverge. **Durable fix: move shared vocabulary into `forge-contracts`** — and grounding showed it's **three** vocabularies (track roles, media roles, relationship types), plus the wire envelope. This is the next contract-vocabulary reconciliation milestone, not a render-specific task. The bilingual correlation shim and the render role are both *unblocks*, not the canonical end-state (don't retire the shim until both sides speak a contract envelope).

## Open coordination items
- [ ] forge_core: `render_of → member_of + role=render` (pipeline, first thing).
- [ ] Daemon restart (`-server` + main) to load `render` + the ping shim — at pipeline's next break.
- [ ] (later) contract-vocabulary milestone: roles + relationships + wire envelope → forge-contracts.
- [ ] (orthogonal hygiene, not blocking) guard `uuid.UUID(<client field>)` in entity/query handlers → return INVALID not INTERNAL on malformed ids.
