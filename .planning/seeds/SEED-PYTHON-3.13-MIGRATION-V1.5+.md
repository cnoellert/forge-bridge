# SEED-PYTHON-3.13-MIGRATION-V1.5+

**Planted:** 2026-05-07
**Source:** Phase A.5.3.2 PR 4 step 0 (corpus rename) — surfaced when a 3.12-only f-string blocked the corpus suite from running under the 3.11 forge env, hiding diagnostic recourse during the Flame-2027 rollout window
**Activation:** **NOW.** Forcing function is live in production.
**Trigger condition:** already met — Flame 2027 (Python 3.13) shipped April 2026 and is being deployed to operator workstations; forge-bridge must coexist with Python 3.13 without architectural drift

## External forcing function

Flame 2027 shipped in **April 2026** with **Python 3.13** as its embedded interpreter. Operator workstation deployments are happening now. The Flame HTTP bridge runs *inside* Flame's interpreter, so the bridge code path executes under whatever Python version Flame ships with — there is no choice in the matter once an operator updates Flame.

This is not a "we should think about updating someday" seed. The forcing function is external, has already happened, and is propagating through deployments at this moment.

## Current runtime state (snapshot 2026-05-07)

| Surface | Python version | Notes |
|---------|---------------|-------|
| `forge` conda env (operator workstation parity, dev/UAT) | **3.11** | Mirrors a still-deployed Flame 2025 era; not yet cut over |
| `forge-bridge` conda env (canonical corpus test env) | **3.12** | Currently the working test environment; ships green for the corpus suite |
| Flame 2027 (production target) | **3.13** | Live deployments in flight |
| Corpus production code (`forge_bridge.corpus.*`) | verified 3.11 + 3.12 | Verified by suite passing under both after the PR-4-pre fix landed (commit prior to this seed) |
| Corpus test suite | verified 3.11 + 3.12 | Same commit |
| Rest of `forge_bridge.*` (LLM router, console, MCP, store, learning, etc.) under 3.13 | **unverified** | This is the audit unit of work below |

## Bridge currently in place

The PR-4-pre commit (immediately preceding this seed) refactored a single 3.12-only f-string in `tests/corpus/test_pr3_writer.py` so the corpus suite collects cleanly under 3.11. That refactor is **operational-recourse preservation during the migration window**, not a commitment to multi-version test support indefinitely. It exists so that if a 3.11 forge-env regression appears during the migration, an operator can still run the corpus suite to diagnose it instead of crashing at collection time.

The forge-bridge env (3.12) remains the **canonical** corpus test environment. The 3.11 + 3.12 dual-pass property is a transitional invariant, not a permanent contract.

## Migration scope (a future phase, NOT PR 4)

PR 4 lands as scoped (chat-handler call-site integration). The migration unit of work below is a separate phase or milestone, sequenced after Gate 1 settles:

1. **Production-code audit under 3.13.** Run the full `forge_bridge.*` test suite under 3.13. Triage every failure; classify as (a) genuine 3.13 incompatibility, (b) test fixture gap, (c) dependency cascade.
2. **Dependency compatibility check.** Inventory every transitive dependency in `pyproject.toml` (`[dev]`, `[llm]`, `[test-e2e]` extras) and verify each has a 3.13-compatible release. Block migration on any dependency that has not.
3. **Flame 2027 integration audit.** Verify the Flame HTTP bridge (`flame_hooks/forge_bridge/scripts/forge_bridge.py`), the `flame_*` MCP tools, and the `forge_bridge.flame` helpers all work under 3.13's interpreter. PyAttribute, Wiretap SDK, `flame.schedule_idle_event`, and any C-extension touchpoints need explicit verification.
4. **Dev environment migration.** Cut `forge-bridge` env to 3.13. Decide whether `forge` env stays at 3.11 (Flame 2025 parity) or moves to 3.13 (Flame 2027 parity) — depends on which Flame version operators are still running in production.
5. **Documented runtime requirements.** Update `pyproject.toml` `python_requires`, `INSTALL.md`, the `python -m forge_bridge` invocation guidance, and `CLAUDE.md`'s "How to Get Running" section to reflect the new minimum and tested-against versions.
6. **Drop the transitional 3.11 dual-pass.** Once the canonical test env is 3.13, the PR-4-pre refactor's *rationale* (preserving 3.11 diagnostic recourse) lapses. The refactor itself is harmless and need not be reverted; the architectural commitment to test under 3.11 is what ends.

## Architectural framing

This is **runtime-adjacency preservation**. forge-bridge has four overlapping runtimes, and they must stay in compatible alignment:

- **Host application runtime** — Flame's embedded interpreter (the version forge-bridge has no choice about).
- **Integration tooling runtime** — the `forge-bridge` package + its dependencies + the operator-side `forge-bridge` CLI.
- **Debugging runtime** — the test suite and `forge doctor` and any operator-reachable diagnostic.
- **Operational verification runtime** — UAT scripts, the smoke tests in `scripts/`, the manifest-read helpers, and any `forge_bridge`-installed entry points run during install verification.

When these four drift apart on Python version, the operator workflow develops gaps that look like minor irritations individually (a missed traceback, a broken `forge doctor` mode, a fixture that no longer collects) but that compound into "we can't reproduce the operator's report" — which is the failure mode this seed prevents.

## Load-bearing invariant carried through migration

> **The corpus subsystem's test environment must run on whatever Python version the production daemon runs on.**

That sentence applies symmetrically: when the production daemon is 3.13, the corpus test env must include 3.13. When the daemon was 3.11/3.12 transitionally, the suite ran under both. The invariant is "the diagnostic surface tracks the production surface," not a specific Python version pin.

A reader who encounters drift between these in a future phase should restore alignment, not paper over the gap.

## What this seed does NOT cover

- It does not deprecate 3.12 right now. forge-bridge env stays 3.12 until the audit above lands.
- It does not require an immediate Flame 2027 integration audit. That depends on operator-deployment cadence; the seed surfaces the work, the phase that picks it up sequences it.
- It does not commit to LTS support for any specific Python version range. Migration is one-direction (forward), not a multi-version maintenance contract.

## Operational note

`pytest-blender` remains a `forge`-env harness issue with the documented workaround `-p no:pytest-blender`. It is **not** part of this seed's scope, **not** part of PR 4 scope, and **not** part of the migration unit of work above. It is a per-developer environment annoyance, recorded here only so the next migrator does not re-derive the workaround during a 3.13 cutover.

## Suggested closure path when this seed activates as a phase

- Phase title shape: "Python 3.13 + Flame 2027 runtime alignment."
- Discuss-phase: gather the deployment-cadence signal from the operator (which Flame versions are live and projected) before scoping the audit.
- Plan-phase: sequence the production-code audit before the dependency check (compile-time errors surface dependency gaps automatically).
- Execute-phase: each migration touchpoint atomic; the dev-env cut is the last commit because reverting it has the largest blast radius.

## Cross-references

- `CLAUDE.md` § "How to Get Running" — current install path assumes `python=3.11`; this is the primary doc that diverges first.
- `pyproject.toml` `python_requires` (current) — needs revision in the migration phase.
- `tests/corpus/test_pr3_writer.py:436` (PR-4-pre commit) — the diagnostic-recourse fix this seed contextualizes.
- `SEED-EXTERNAL-DEPENDENCY-PREFLIGHT-PROBES-V1.5+.md` — adjacent in shape (runtime-adjacency preservation across external surfaces); migration audit might productively land alongside.
- `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`, `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` — same pattern of "external thing changed, internal posture must catch up."
