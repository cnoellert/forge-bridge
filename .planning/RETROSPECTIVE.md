# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.2 — Observability & Provenance

**Shipped:** 2026-04-22
**Phases:** 3 (Phase 7, Phase 07.1 hotfix, Phase 8) | **Plans:** 12 | **Tasks:** 17
**Releases:** v1.2.0, v1.2.1, v1.3.0 (3 annotated tags)

### What Was Built

- **Phase 7 (v1.2.0):** `.sidecar.json` envelope write-path + canonical `_meta` provenance (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`) in MCP `Tool._meta` under `forge-bridge/*` namespace. `_sanitize_tag()` boundary with injection rejection + 64-char/16-tag/4 KB budgets. Explicit `annotations.readOnlyHint=False` on every synth tool.
- **Phase 07.1 (v1.2.1 hotfix):** `startup_bridge` graceful degradation — MCP server now boots cleanly when the standalone WS server on `:9998` is unreachable. Re-UAT of PROV-02 via real MCP client session replacing the Phase 7-04 monkey-patched harness.
- **Phase 8 (v1.3.0):** `StoragePersistence` `@runtime_checkable` Protocol (single `persist` method per D-02 narrowed from original 3-method scope). Cross-repo SQLAlchemy adapter in projekt-forge + Alembic revision 005 + `isinstance` startup-time sanity gate + idempotent `on_conflict_do_nothing`. Full end-to-end chain: `bridge.execute() → _on_execution_callback → ExecutionLog.record() → _persist_execution → PG INSERT`.
- **LRN-05 gap closure (Phase 8 deviation):** The Phase 6 hook `forge_bridge.bridge.set_execution_callback()` was defined but never installed by any production caller — surfaced during Phase 8 live UAT when a real MCP call produced zero rows. Fixed in-scope.

### What Worked

- **Planning discipline paid off.** Each phase had a discuss → research → plan → execute cadence with CONTEXT.md locking the user's decisions before planning. Phase 8 in particular hit `D-01..D-14` lockdown which made plan reviews fast (no re-litigating narrow-Protocol vs wide-Protocol or sync-vs-async at plan time).
- **Release ceremony repeats well.** Three ceremonies this milestone (v1.2.0, v1.2.1, v1.3.0) all followed the same pattern — commit → annotated tag → push → `python -m build` → `gh release create`. The Phase 5-00 template adapted cleanly to Phases 7-04, 07.1-02, 08-03.
- **Cross-repo re-pin pattern stuck.** Option A shadow remediation (`pip uninstall -y forge-bridge && pip install -e .`) locked in Phase 07.1-03 transferred to 08-03 without modification. `pip show` location check (site-packages vs source tree) became the routine final verification.
- **Worktree-isolated parallel execution** worked smoothly for independent waves. Each wave's executor ran in an isolated git worktree; the orchestrator merged them back atomically. No race conditions observed when plans genuinely didn't share files.
- **UAT-driven gap discovery.** Phase 8 UAT required the MCP surface to actually produce a row in `execution_log` — refusing to fake that path surfaced a 3-phase-old missing hook (LRN-05). Strict UAT was the only forcing function that found it.

### What Was Inefficient

- **Harness hiccup during Phase 8 close.** Claude Code's cwd-detection logic got stuck mid-session (reported working directory as missing even though the filesystem was fine). Required a Claude restart to resume — not a GSD workflow issue but cost ~5 minutes of confusion + forced handoff-via-memo dance.
- **`gsd-tools audit-open` is broken.** `ReferenceError: output is not defined` at line 784/786. Milestone-close workflow depends on this for pre-close audit — had to fall back to a manual audit. Not a blocking defect but adds friction.
- **`gsd-tools phase complete 08` didn't fully update ROADMAP.md** — left the Phase 8 row as `0/3 Planned` despite returning `roadmap_updated: true`. Had to manually fix `[ ] → [x]` and the progress-table row before archive would capture the correct shipped state. Suspected selector/regex brittleness against the free-form list entries (as opposed to the standard `[ ] Phase N: name (plans) — completed date` format).
- **Milestone accomplishments auto-extraction produced fragments.** `gsd-tools milestone complete` pulled `"Plan:"` and `"One-liner:"` bullets from SUMMARY.md files whose structure varies. Had to hand-curate the MILESTONES.md entry.
- **Stale git worktrees accumulated.** Five `.claude/worktrees/agent-*` directories remained from prior phases because the harness `locked by claude agent` lock prevented `git worktree remove --force`. Harmless but cluttered `git worktree list` output.

### Patterns Established

- **D-## locked decisions in CONTEXT.md** before planning. Each Phase 8 plan could reference `D-02`, `D-07`, `D-11` etc. by ID in commit messages, tests, and code comments. Traceable, searchable, and forced decisions to happen once (at discuss-phase time) rather than drifting during execution.
- **Rule-3 deviations for unanticipated gaps** in the shipped artifact's call path are legitimate in-scope fixes — but must be documented in SUMMARY.md + VERIFICATION.md with commit hash. LRN-05 was handled this way: not expanded into a Phase 8.1, not deferred to "next milestone" — fixed inline because it blocked the phase's own UAT criterion.
- **Cross-repo commits stay local until UAT passes.** projekt-forge's 7 commits for Phase 8 were created inside the Phase 8 workstream but not pushed to origin until the milestone-close sign-off. Keeps the push atomic with the final shipped state; lets the user audit the full diff before anything goes public.
- **Security review for credential-adjacent code paths.** `_persist_execution`'s DB-error logger was reviewed specifically for credential leakage via `str(exc)` — SQLAlchemy's `OperationalError` walks its exception chain and includes `asyncpg.InvalidPasswordError` (which carries the connection URL). Logging only `type(exc).__name__` is the locked pattern.

### Key Lessons

1. **UAT against the live production call path, not a harness.** Unit tests that call `log.record()` directly masked the LRN-05 missing-hook gap for three phases (6, 7, 8). The Phase 8 UAT criterion — "real `bridge.execute()` produces a row in `execution_log`" — is what actually exercised the full chain. For observability wiring that spans multiple phases, the UAT query should come from a real MCP/HTTP surface, not from an imported module with a direct `record()` call.
2. **Narrow Protocols beat wide Protocols.** D-02 in Phase 8 narrowed `StoragePersistence` from 3 async methods to 1 sync method. Rationale: the only current consumer (projekt-forge) has no batch or shutdown use case; adding them would freeze a contract with no grounding. `BatchingStoragePersistence` sub-Protocol is trivial to add later if real demand emerges. YAGNI works specifically well for `@runtime_checkable` Protocols because the contract becomes the API surface consumers write against.
3. **Runtime adapter attachment for `@runtime_checkable` Protocols.** Plain functions can satisfy method-based Protocols by attaching a self-referencing attribute: `_persist_execution.persist = _persist_execution`. Worth documenting because the first-pass `isinstance()` failure is opaque.
4. **Cross-repo release sequences are mechanical.** forge-bridge tag → push → wheel + sdist → GitHub Release → consumer pin bump → `pip uninstall && pip install -e .` → UAT. Each step has a specific gate; skipping one produces silent false positives (Phase 5's editable-shadow bug is the object lesson). Consider a `gsd-release-ceremony` helper that walks this sequence + verifies each gate.
5. **`conda run -n forge --no-capture-output`** is required for any Python one-liner that needs to return output to the caller. Without `--no-capture-output`, conda eats stdout and the command looks silent/broken. Worth hardcoding into the release/UAT scripts or encoding in `.claude/settings.local.json` as a project convention.
6. **Route MCP UAT through the process the user is actually running.** Claude Code's `mcp__projekt-forge__*` tools connect to processes Claude Code itself spawned at session start — NOT to the user's interactive `python -m projekt_forge`. If the user restarts projekt-forge to pick up a fix, Claude Code's MCP client is still attached to the old process. For UAT: either restart Claude Code entirely, or drive the real path via a non-MCP surface (direct `bridge.execute()` from a fresh Python process against the live Flame HTTP bridge).

### Cost Observations

- Model mix this milestone: primarily Opus 4.7 1M-context (orchestration + planning + long phase reviews); Sonnet 4.6 for executor agents (gsd-executor, gsd-verifier, gsd-code-reviewer).
- Sessions: ~1 focused session for Phases 7-8 execution + a handful of planning/review sessions.
- Notable: The 1M-context orchestrator could hold all three phase SUMMARY.md files + PROJECT.md + ROADMAP.md + multi-file diffs simultaneously — made the UAT-driven LRN-05 discovery much faster (could cross-reference the Phase 6 hook definition against three phases of unit-test usage in one context window).

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 3 | Standalone package extraction; learning-pipeline port from FlameSavant (JS → Python) |
| v1.1 | 3 | projekt-forge cutover to pip dependency; Option A shadow-remediation pattern emerged (Phase 5) |
| v1.2 | 3 | Observability + provenance end-to-end; `@runtime_checkable` Protocol pattern locked; cross-repo release ceremony proven at 3x (v1.2.0, v1.2.1, v1.3.0) |

### Cumulative Quality

| Milestone | Shipped | Tests | Public API | Commits |
|-----------|---------|-------|------------|---------|
| v1.0 | 2026-04-15 | 159 | 11 | 66 |
| v1.1 | 2026-04-19 | 276 | 15 | 198 |
| v1.2 | 2026-04-22 | 289 | 16 | 263 |

### Top Lessons (Verified Across Milestones)

1. **Option A shadow remediation is the locked cross-repo pin pattern.** First discovered in Phase 5, re-validated in Phase 07.1, re-validated in Phase 8. `pip uninstall -y forge-bridge && pip install -e .` is not optional.
2. **Narrow Protocol/API beats wide Protocol/API at v1.x.** Explicit single-method Protocols (StoragePersistence, Phase 8) and narrow `__all__` re-exports (Phase 4) have been easier to evolve than wide contracts. YAGNI for public surfaces.
3. **UAT must exercise the live production call path.** Phase 6 → 7 → 8 chain had a missing hook that unit tests never caught. Only the Phase 8 UAT forcing function ("real MCP call produces a row") found it.
4. **Locked non-goals in PROJECT.md prevent scope creep.** v1.1's locked non-goals (LLMRouter hot-reload, shared-path JSONL writers) carried cleanly into v1.2 without re-litigation. Write them down when the decision is fresh.
