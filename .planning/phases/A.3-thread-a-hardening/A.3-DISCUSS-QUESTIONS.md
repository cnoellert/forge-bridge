---
milestone: v1.7
thread: A
phase: A.3
phase_name: Hardening — operational integrity of the authority chain
status: phase-discuss
opened: 2026-05-29
drafted: 2026-05-29
type: phase-discuss
derives_from:
  - .planning/phases/A.3-thread-a-hardening/A.3-FRAMING.md (committed 87f6fe1)
  - .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-CLOSE.md
grounding: A.3-FRAMING v3 (87f6fe1) + this-session reads of forge_bridge/cli/runtime_doctor.py (6 rows verified — console/install_provenance/mcp_http/flame_bridge/state_ws/graph_store) + forge_bridge/console/ (no public helpers module yet — A.3 creates)
artifact_role: load-bearing — A.3-PLAN.md drafts from these rulings
---

# A.3 — Phase discuss: eight rulings against the v3 framing

This artifact rules on the 8 framing-grade questions A.3-FRAMING.md
surfaced. Architectural inheritance (Thread A laws + A.2
R-A2.1..R-A2.8 + sync-apply common case) is preserved verbatim from
framing — not relitigated here. Each ruling derives from the v3
lean; rationale is brief because framing already walks the
candidate shapes with cascade analysis.

## R-A3.0 — Scope: hardening + observability + auth-seed docs (Q-A3.0 (c) narrowed)

A.3 ships UAT runbook + observability extensions + auth-seed
deferral documentation. Sub-scope 3 (auth-seed docs) lands as a
section in `docs/RATIFICATION.md` alongside Sub-scope 2's doc
deliverable rather than as a separate file — under the narrowed
R-A3.3(d) this is pure doc work and doesn't warrant separate
shipping infrastructure.

**Why (c) over (b):** explicit deferral marking signals operator
expectations clearly (`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`);
collapsing the doc into Sub-scope 2's deliverable costs nothing
operationally and preserves Path X anti-scope discipline.

## R-A3.1 — UAT catalog supplied + drift smoke executed (Q-A3.1 (c))

A.3-PLAN.md enumerates the UAT runbook items; A.3 implementation
ships test infrastructure for the catalog AND executes the
drift-invalidation live smoke (named A.2 carry-forward). Multi-cycle
UAT executes operator-side post-A.3.

**Catalog candidate items** (PLAN locks final list against the L8
failure envelope):
- Drift-invalidation live smoke (carry-forward from A.2)
- Full chain exercise against live Flame project
- Recovery from each L8 failure class (graph-intent not found,
  apply mid-step failure, assent mismatch, store unavailable, etc.)
- Multi-cycle ratification cadence

**Why (c) over (b):** drift smoke is the highest-value gated item
per A.2 carry-forward; full multi-cycle UAT is operator workflow
that doesn't need to gate A.3 close. Catalog supply preserves
operational guidance without requiring A.3 to execute every item.

## R-A3.2 — New `ratification` doctor row (Q-A3.2 (a))

A.3 adds a 7th row to `fbridge doctor` per the Phase 24 `graph_store`
precedent. Tri-state semantics (PLAN locks final thresholds):

- `ok` — `assent_record` table reachable, schema matches, recent
  `assent.*` event activity within an operator-relevant window
- `loaded` — table reachable + schema matches, no recent events
- `fail` — unreachable / schema mismatch / event-emit path broken

**Why (a) over (b)/(c):** matches the `graph_store` row pattern
(consistency over invention); operationally discoverable distinct
from `postgres`/`install_provenance` rows (substrate state vs DB
health vs operator install state); tri-state maps the assent_record
lifecycle naturally.

## R-A3.3 — Auth-seed deferral documented; no code change (Q-A3.3 (d))

A.3 ships NO code-level change to `AssentRecordRepo.ratify()` or
any A.2-shipped substrate. A new section in `docs/RATIFICATION.md`
names the SEED-AUTH-V1.5 deferral, preserves the `decided_by`
free-string placeholder (R-A2.8 carries forward), and explicitly
does NOT prescribe the future integration shape — those are
SEED-AUTH-V1.5's framing decisions.

**Why (d) over (a)/(b)/(c):** signature change to A.2-shipped
substrate IS architectural extension regardless of safe defaults;
(a) and (c) violate the Thesis "NO new substrate primitives" in
the only honest reading; (b) loses the
operator-knowledge-of-future-shape hardening value (d) preserves
cheaply via deferral language
(`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`).

## R-A3.4 — Surface mcp_http partial-stack state; don't address supervision (Q-A3.4 (b))

The R-A3.2 doctor row makes `mcp_http not listening` operationally
visible. A.3 docs include "if mcp_http is not listening, restart
with `fbridge up`" runbook prose. A.3 does NOT extend
`install-bootstrap.sh`, does NOT add systemd/launchd posture
changes, does NOT add auto-restart logic.

**Why (b) over (a)/(c):** matches the operational-design-center
scope (A.3 hardens A.1+A.2 substrate; daemon supervision is a
separate operations concern); the doctor row addition covers the
observability half cheaply; (a) bridges into deployment-as-code
out of A.3 scope; (c) leaves the deployment observation 2026-05-29
unaddressed operationally.

## R-A3.5 — Python helpers in `forge_bridge.console.helpers` (Q-A3.5 (d))

A.3 ships a small helper module `forge_bridge/console/helpers.py`
(new public module — sibling to existing private `_chain_parse.py`,
`_chat_compile.py`, etc.) with functions like:

- `recent_ratifications(window: timedelta) -> list[AssentRecord]`
- `pending_assent_records() -> list[AssentRecord]`
- `recent_failed_applies(window: timedelta) -> list[...]`

Operators import from Python REPL or scripts. NO MCP tool
registration. NO HTTP endpoint. NO wire surface. NO Pydantic
schema. NO sanitization gates. Existing `forge_get_events` stays
the canonical wire surface for external consumers.

**Why (d) over (a)/(b)/(c):** (b) introduces new substrate primitive
under cover of operational closure (tool registry, schema,
provenance, sanitization — full MCP tool weight); (c) Q5-gated and
bridges into dashboard scope outside A.3; (a) leaves operator UX
too primitive. (d) is genuinely hardening-shaped — operational
trustworthiness improves; no new architectural surface.

**Q5-watch (preserved from framing F2):** if a future consumer
proposes audit-event subscription (Q-A3.5(c)), the
non-LLM-consumer constraint is constitutional — A.3 does not open
that path.

## R-A3.6 — A.2 carry-forward dispositions (Q-A3.6)

| # | Item | A.3 disposition |
|---|---|---|
| 1 | Authentication still deferred — `actor` is free string pending the auth seed | DEFER to SEED-AUTH-V1.5; A.3 documents the deferral per R-A3.3 |
| 2 | Chat conversational ratification remains out of scope | DEFER to post-A.3 / future phase per Q5 constitutional |
| 3 | Drift-invalidation live smoke remains a UAT item | LAND in A.3 per R-A3.1 |
| 4 | A.3 hardening opens after this close cursor | Self-referential — A.3 itself |

**Shift from framing's working table:** item 1's disposition
shifted from "A.3 ships auth-seed integration hook surface" to
"A.3 documents the deferral" per R-A3.3 absorption. The framing
table at Q-A3.6 still names the v1+v2 lean (hook surface); this
ruling supersedes it.

## R-A3.7 — A.3-CLOSE signals Thread A authority-chain work as architecturally sufficient (Q-A3.7 (a))

A.3-CLOSE includes a signal section naming Thread A's
authority-chain scope (NL → compile → graph-intent → preview →
ratify → apply) as architecturally sufficient (per Thesis F1
absorption — NOT "complete") and operationally hardened. The close
cursor SIGNALS; the Thread A framing or v1.7 milestone framing
RULES on formal closure (per Stage 1a P1 layer-ownership note).

Future work (SEED-AUTH-V1.5, Console ratification, multi-turn
graph-intent persistence) opens as separate threads / milestones
per the constitutional Q5 + Thread A out-of-scope items.

**Why (a) over (b)/(c):** the layer-ownership note holds; (a)
honors the constitutional Q5 anti-scope boundary; (b)/(c) propose
work streams A.3 doesn't have license to declare.

## Disposition summary

| Q | Ruling | Notes |
|---|---|---|
| Q-A3.0 | (c) narrowed | Sub-scope 3 doc rides in `RATIFICATION.md` |
| Q-A3.1 | (c) | Catalog + drift smoke gated; multi-cycle UAT post-A.3 |
| Q-A3.2 | (a) | New `ratification` row, tri-state per `graph_store` pattern |
| Q-A3.3 | (d) | Docs-only; no signature change to A.2 substrate |
| Q-A3.4 | (b) | Surface via R-A3.2 row + runbook; don't address supervision |
| Q-A3.5 | (d) | `forge_bridge.console.helpers`; no wire surface |
| Q-A3.6 | per table | Item 1 shifted to "docs deferral" per R-A3.3 |
| Q-A3.7 | (a) | A.3-CLOSE SIGNALS, higher framing RULES |

## What PLAN needs to lock

- Doctor row thresholds (recent-activity window, count semantics
  for tri-state)
- `forge_bridge.console.helpers` signatures + return types (against
  current `AssentRecord` shape — PLAN reads `assent_record.py` +
  `assent_record_repo.py`)
- UAT runbook item enumeration (L8 failure class coverage; one
  smoke per class)
- `docs/RATIFICATION.md` section structure for SEED-AUTH-V1.5
  deferral wording
- Drift-invalidation smoke test entry point + fixture shape
  (consumes A.2 D9 test infrastructure pattern)
- A.3-CLOSE signal-section template (per R-A3.7)
