---
milestone: v1.7
thread: A
phase: A.3
phase_name: Hardening — operational integrity of the authority chain
status: closed
opened: 2026-05-29
closed: 2026-05-29
type: phase-close
derives_from: .planning/phases/A.3-thread-a-hardening/A.3-PLAN.md
implementation_arc: 51ee7e2..e4fd9c3 (7 commits, D1..D7; D8 close cursor here)
---

# A.3 — Phase close cursor

> **The authority chain is now inspectable and exercised.**
> A.1 compiled chat intent before execution. A.2 added assent-backed
> ratify/apply. A.3 hardened the operational surface around that chain:
> doctor visibility, async operator helpers, drift-invalidation smoke,
> UAT catalog, and auth deferral clarity.

## What shipped

```
51ee7e2  docs(A.3): defer ratification authentication binding
2ba2b9a  feat(A.3): add ratification console helpers
794c5a8  test(A.3): cover ratification console helpers
d4fd937  feat(A.3): add ratification doctor row
857e19d  test(A.3): cover ratification doctor row
9baa3c2  test(A.3): add drift invalidation smoke
e4fd9c3  docs(A.3): add authority-chain UAT catalog
```

Concrete deliverables:

- `docs/RATIFICATION.md` now names `decided_by` as an auth-deferred
  free-string placeholder, pending SEED-AUTH-V1.5.
- `forge_bridge.console.helpers` exposes async helper functions for
  recent ratifications, pending assent records, and recent failed applies.
- `fbridge doctor` now includes a seventh `ratification` row with
  `ok` / `loaded` / `fail` tri-state semantics.
- `tests/integration/test_a3_drift_invalidation_smoke.py` exercises
  preview -> drift -> ratify -> failed assent.
- `docs/UAT-A3.md` catalogs seven authority-chain UAT items.

## Verification

- Helper tests: 6 passed.
- Doctor ratification + existing runtime-doctor tests: 31 passed.
- Drift-invalidation smoke: 1 passed.
- Ruff clean on changed Python files.
- `forge_bridge.__all__` remains 19.

## Thread A authority-chain — architecturally sufficient

A.1 + A.2 closed the substrate. A.3 hardened it operationally. The
authority chain — NL → compile → graph-intent → preview → ratify
→ apply — is architecturally sufficient for the sync-apply
common case A.2 designed for, and operationally exercised through
the A.3 UAT catalog + drift-invalidation smoke.

A.3-CLOSE SIGNALS the work as sufficient. Thread A framing or
v1.7 milestone framing RULES on formal Thread A closure.

Future work opens as separate threads / milestones:
- **SEED-AUTH-V1.5** — auth identity binding (per L5 deferral)
- **Console ratification** — UI surface for assent (NOT Q5-safe
  via chat per inherited constraint)
- **Multi-turn graph-intent persistence** — graph-intent lifetime
  extension beyond single-session scope

See `docs/RATIFICATION.md` § Authentication for the explicit auth deferral.

## Carried Forward

- Live Flame UAT items 2-7 in `docs/UAT-A3.md` remain operator-run
  checks; A.3 implementation gates only item 1.
- The drift smoke found the real envelope shape is the existing
  chain-aborted `PLAN_STATE_DRIFT` envelope, not a new top-level
  `{ok: false, error: {code: drift_invalid}}` shape.
