---
milestone: v1.7
thread: A
phase: thread-close
opened: 2026-05-29
type: thread-close
derives_from:
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-FRAMING.md
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-CLOSE.md
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md
  - .planning/phases/A.3-thread-a-hardening/A.3-CLOSE.md
artifact_role: thread-level closure — rules on Thread A formal closure per A.3 R-A3.7 signal
---

# Thread A — formally closed

> **What this artifact is.** Writing-room ruling on Thread A formal
> closure, per A.3-CLOSE R-A3.7's layer-ownership note:
> *"A.3-CLOSE SIGNALS the work as sufficient. Thread A framing or
> v1.7 milestone framing RULES on formal Thread A closure."* This
> artifact carries the Thread A framing-layer ruling.
>
> **Precedent observation.** First thread-level close cursor in the
> project. Thread B closed 2026-05-25 and Thread C closed 2026-05-27
> via milestone-level passoff archaeology (no dedicated
> THREAD-B-CLOSE.md / THREAD-C-CLOSE.md). Thread A gets a dedicated
> close cursor because A.3 R-A3.7 specifically named the
> layer-ownership requirement and the framing layer is the closest
> match.

## Ruling

**Thread A is formally closed.** The authority chain — NL → compile
→ graph-intent → preview → ratify → apply — is architecturally
sufficient for the sync-apply common case Thread A scoped, and
operationally hardened through the A.3 UAT catalog + drift-
invalidation smoke.

The ruling follows the signal from A.3-CLOSE; no separate evidence
was sought beyond what A.3 already grounded.

## Scope synthesis — what Thread A shipped

| Phase | Closed | Substrate delivered |
|---|---|---|
| A.1 | 2026-05-28 (242b8e9) | Chat compile → graph-intent + preview (`LLMRouter.compile_intent()`, preview SSE taxon `preview_emitted`, graph-intent persistence pre-ratify; authority-model retired across 3 surfaces / 2 transports / 4 contract shapes — 37 tests dispositioned) |
| A.2 | 2026-05-29 (bebf24a) | Ratification + enforced apply (`AssentRecord` + `AssentRecordRepo` + 4 `assent.*` event types; `CommitNode.verify` assent extension; `fbridge ratify` CLI + `POST /api/v1/ratify` endpoint; store-and-replay substrate at `_engine.py` + `_step.py`) |
| A.3 | 2026-05-29 (9ae2f21) | Operational hardening (`_check_ratification` doctor row tri-state; `forge_bridge.console.helpers` operator helpers; `docs/UAT-A3.md` 7-item runbook; drift-invalidation smoke; `docs/RATIFICATION.md` auth-seed deferral section) |

**Public API preservation.** `forge_bridge.__all__` remained at 19
across all three phases. `pyproject.toml` version remained at 1.4.1.
The A.2-shipped substrate was byte-equivalent across A.3 — anti-
scope discipline held.

## What Thread A does NOT carry — separate threads / milestones

Per A.3-CLOSE R-A3.7 + inherited Thread A out-of-scope items:

- **SEED-AUTH-V1.5** — auth identity binding. A.3 L5 documents the
  deferral at `docs/RATIFICATION.md` § Authentication. The
  `decided_by` field remains free-string until that milestone
  defines validation, identity resolution, and integration shape.
- **Console ratification** — UI surface for assent. NOT Q5-safe via
  chat per Thread A's inherited constitutional constraint
  (LLM never owns assent). A separate operator-surface phase or
  thread.
- **Multi-turn graph-intent persistence** — graph-intent lifetime
  extension beyond single-session scope. Thread A scoped to sync-
  apply common case; multi-turn is out of scope.
- **Tool-calling determinism** — backgrounded for Thread A per the
  THREAD-A-FRAMING grounding note; a different concern from the
  authority chain.

## Methodology archaeology from the Thread A arc

- **Cadence convention shift mid-arc.** Mid-Thread-A the writing-
  room cadence drifted toward methodology-surface inflation; the
  operator named it 2026-05-29 (*"the discipline framework is
  generating its own overhead"*). The lighter convention
  memorialized at `[[feedback-cadence-artifacts-shrink-to-load-bearing]]`
  landed mid-A.3 (193-line discuss + 337-line plan vs A.2's 901 +
  2456 line precedents). Convention shift documented in
  `[[passoff-2026-05-29-v1-7-thread-a-a3-writing-room-arc-landed-writing-room-role]]`.
- **Substrate-shape grounding discipline matured.** The memory at
  `[[feedback-substrate-shape-grounding-at-plan-stage]]` reached
  5 within-project instances across 4 surface manifestations
  (shape / convention / flow / envelope) over the Thread A arc.
  The envelope-shape manifestation (A.3 L4 drift smoke) added
  catch-surface refinement: runtime-path tracing reaches a
  manifestation that discoverable-surface Stage 1b does not.
- **Role-boundary discipline.** Writing-room + active-testing
  surface preserved across A.1 + A.2 + A.3 arcs. Implementation
  execution ran in separate sessions for A.2 and A.3 per the
  pattern; A.1 ran inline. 30+ within-day phase progressions across
  the arc; zero role violations.

## Cross-links

- **Phase closes:** [A.1-CLOSE.md](../A.1-thread-a-chat-intent-compile-stage/A.1-CLOSE.md) — preview substrate; [A.2-CLOSE.md](../A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md) — ratify+apply substrate; [A.3-CLOSE.md](../A.3-thread-a-hardening/A.3-CLOSE.md) — hardening + sufficiency signal
- **Thread A framing:** [THREAD-A-FRAMING.md](./THREAD-A-FRAMING.md) — the five rulings that bound Thread A's three-phase arc
- **Milestone:** [v1.7-ARTIST-READINESS-FRAMING.md](../../milestones/v1.7-ARTIST-READINESS-FRAMING.md) — milestone-level framing; §Status is stale (2026-05-25, pre-Thread-B-close) and pending refresh at v1.7 milestone closure

## Carried forward to v1.7 milestone closure

When v1.7 milestone closure runs:

- Surface Thread A formal closure (this artifact)
- Surface Thread B + Thread C closures (existing milestone-level archaeology)
- Refresh `v1.7-ARTIST-READINESS-FRAMING.md` § Status from 2026-05-25 stale state to milestone-close-ready
- Rule on milestone-level carry-forwards (SEED-AUTH-V1.5 as separate milestone; Console ratification + multi-turn graph-intent as future-thread scoping)
- Run milestone-level audit per the project's existing milestone-close discipline
