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

## Milestone: v1.4.x — Carry-Forward Debt

**Shipped:** 2026-04-30
**Phases:** 3 (17, 18, 19) | **Plans:** 10 | **Tasks:** 14
**Release:** v1.4.1 (annotated patch tag on top of v1.4.0)
**Audit:** `passed` — 9/9 requirements satisfied, 7/7 cross-phase integration wires verified, public `__all__` byte-identical to v1.4 close

### What Was Built

- **Phase 17 — Default model bumps (MODEL-01..02).** Cloud default flipped `claude-opus-4-6` → `claude-sonnet-4-6` as a single-line literal change after Plan 17-01 first extracted the two inline literals into `_DEFAULT_LOCAL_MODEL` / `_DEFAULT_CLOUD_MODEL` module constants (pure refactor, byte-identical values). MODEL-02 took deferral branch (b) — pre-run UAT against `qwen3:32b` produced cold-start `LLMLoopBudgetExceeded` driven by thinking-mode token verbosity (400-525 tokens/turn); empirical evidence + named candidate v1.5 fixes captured in `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (retargeted v1.4.x → v1.5). `SEED-OPUS-4-7-TEMPERATURE-V1.5` planted alongside.
- **Phase 18 — Staged-handlers test harness rework (HARNESS-01..03).** Migrated `staged_client` from `starlette.testclient.TestClient` (sync, private event loop) to `httpx.AsyncClient(transport=ASGITransport(app=app))`; awaited all 31 call sites across 3 console test files (HARNESS-01). `seeded_project` `@pytest_asyncio.fixture` wired into 3 FK-violating tests (HARNESS-02). Removed `FORGE_TEST_DB=1` opt-in gate from `_phase13_postgres_available()` and wrapped `pg_terminate_backend` teardown SQL in `try/except Exception` for the non-SUPERUSER `forge` role (HARNESS-03). Result: 22+ previously silently-skipped console tests now run; default `pytest tests/` 763p/117s/0err.
- **Phase 19 — Code-quality polish (POLISH-01..04).** WR-02 ref-collision guard — salvage helper now emits placeholder ref, call site overrides via `dataclasses.replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`; same `len(tool_calls)`-indexed namespace as the structured path so collisions are impossible (POLISH-01). Phase 13 `from_status="(missing)"` sentinel replaced with proper `Optional[str]`; FB-B 404/409 split discriminators rewired to `exc.from_status is None` (POLISH-02). `test_transition_atomicity` rewritten to single-session approve+flush+rollback observation against live Postgres (POLISH-03). `_strip_terminal_chat_template_tokens` helper in `OllamaToolAdapter` strips contiguous `<|im_start|>` / `<|im_end|>` / `<|endoftext|>` tail-token runs; `INJECTION_MARKERS` extended 8 → 10; provider-scoped — Anthropic untouched, no double-strip path through `console/handlers.py` (POLISH-04).

### What Worked

- **Audit-driven scoping at milestone open.** v1.4.x was scoped from the v1.4 close-out audit's `Known deferred items at close` list — every requirement traced back to a specific debt item with a concrete acceptance criterion. No re-litigation at discuss-phase time. The audit-as-spec pattern (v1.4 audit → v1.4.x requirements) made the patch milestone a mechanical execution of pre-locked debt.
- **Decoupled-commit purity for value flips paid off immediately.** Phase 17's split (17-01 refactor → 17-02 flip → 17-03 deferral docs) means `git blame` on `_DEFAULT_CLOUD_MODEL` line 72 reads "bump _DEFAULT_CLOUD_MODEL to claude-sonnet-4-6 (MODEL-01)" — not muddled with surrounding refactor noise. Future model bumps inherit a 1-line value-flip surface.
- **Pre-run UAT for default-value flips caught a regression before it shipped.** The MODEL-02 cold-start `LLMLoopBudgetExceeded` would have shipped to projekt-forge v1.5 as a degraded operator surface. Conservative-bump-first preserved the v1.4.0 baseline; the seed retargeting captured everything v1.5 needs to revisit (Run 1/Run 2 numerics, qwen3 thinking-mode token verbosity, named candidate fixes).
- **Removing the `FORGE_TEST_DB=1` gate immediately surfaced a hidden Phase 13 bug.** The previously-silently-skipped `test_transition_atomicity` was a vacuous `assert True  # placeholder` + a contradictory `assert row is None`. POLISH-03 then closed it with a real cross-session atomicity assertion. The opt-in gate had hidden the bug across the entire v1.4 milestone.
- **Worktree-isolated parallel execution scaled to wave-based plans within a phase.** Phase 19 ran POLISH-01/02/03 as Wave 1 in parallel worktrees (no shared files), then POLISH-04 as Wave 2 (depends on 19-01 — same `_adapters.py` file). The orchestrator merged each wave back atomically. No race conditions; wave dependency analysis was correct.

### What Was Inefficient

- **`gsd-tools audit-open` is still broken.** `ReferenceError: output is not defined` at line 786 (same as v1.2 close-out). Fell back to manual audit again. Worth fixing before the next milestone close.
- **`gsd-tools milestone complete` accomplishments auto-extraction is still noisy.** Pulled fragments like `"One-liner:"`, `"Phase:"`, `"None."`, and `"1. [Rule 1 - Bug] Plan-internal contradiction: ..."` from SUMMARY.md files whose structure varies. Hand-curated the MILESTONES.md entry to replace the auto-extracted bullets with structured per-phase narratives. The CLI's bullet-extraction heuristic should look for a specific `# One-liner` H1 anchor or skip extraction entirely.
- **`gsd-tools milestone complete` did not flip REQUIREMENTS.md traceability checkboxes.** All 9 v1.4.x requirements still showed `[ ]` (Open) in the archived REQUIREMENTS.md after the CLI ran. The audit had verified them all SATISFIED, but `requirements_updated: false` in the phase-complete output meant the checkbox flip didn't propagate. Hand-flipping at archive time was needed (the archive captures whatever state the source file is in).
- **STATE.md `Last Activity Description` field warning.** `gsd-tools milestone complete` printed `WARNING: STATE.md field "Last Activity Description" not found — update skipped.` Suggests STATE.md template drift between the CLI's expected schema and the actual file format. Cosmetic but worth tracking.
- **VALIDATION.md coverage is thin** — Phase 17 missing, Phase 18 missing, Phase 19 partial (draft generated by planner, not finalized). The Nyquist auditor never ran for any v1.4.x phase; documented as advisory tech debt in the audit but represents a genuine coverage gap. Consider making `nyquist_validation: true` config a hard pre-archive gate, not a soft advisory.
- **SUMMARY frontmatter `requirements_completed` field missing in 6 of 10 plans** (17-02, 17-03, 18-02, 18-03, 19-01, 19-02). The audit fell back to VERIFICATION.md as authoritative — so the milestone is correct — but the SUMMARY-template discipline gap means automated cross-references (3-source matrix in the audit) had to use `partial`-with-evidence rather than `pass`. Worth a planner-template tightening pass before v1.5.

### Patterns Established

- **Decoupled-commit purity for tunable defaults.** Phase 15 D-30 mandate (FB-C) generalized to all default-value flips — pure refactor (extract literal to module constant) ships separately from value flip (single-line literal change). `git blame` on the bumped line shows the bump message; `git blame` on the constant declaration shows the refactor. Re-validated in Phase 17 (cloud + local model defaults).
- **Conservative-bump-first with empirical-evidence deferral as a first-class outcome.** MODEL-02 deferral branch (b) is not a punt — it's a documented engineering decision with concrete numerics, named failure modes, and forward-pointing v1.5 candidate fixes. The seed retargeting (v1.4.x → v1.5) preserves both the historical context and the trigger conditions for revisit.
- **Default-on test fixture probes with `OSError` silent-skip.** Phase 18 HARNESS-03 removed the `FORGE_TEST_DB=1` opt-in gate from `_phase13_postgres_available()` and replaced with a `urlparse`-based probe that silently skips on `OSError`. CI green-state preserved (no Postgres reachable → silent skip); development hidden-regression surface eliminated.
- **Provider-scoped strip helpers colocated with consumer.** Phase 19 POLISH-04: `_strip_terminal_chat_template_tokens` lives in `OllamaToolAdapter` only; AnthropicAdapter source contains zero references; no double-strip path through `console/handlers.py`. FB-C D-09 colocation principle re-validated.
- **Single-session atomicity observation pins the actual SQLAlchemy/Postgres contract.** Phase 19 POLISH-03 replaced cross-session assertions that contradicted committed-state durability with a 26-line single-session observation: propose+commit (baseline persists) → approve+flush (in-flight visible) → rollback (in-flight reverts) → re-observe. Pattern reusable for any audit-trail tamper guard.
- **Audit-as-spec for patch milestones.** v1.4 milestone audit's `Known deferred items at close` list became v1.4.x's REQUIREMENTS.md. No re-research, no re-discuss — every requirement was a closed-form acceptance criterion against a specific debt item. Patch milestones earn their efficiency from this constraint.

### Key Lessons

1. **Sentinel-string discriminators are debt — replace with `Optional[T]` so the type system can see the contract.** Phase 13's `from_status="(missing)"` sentinel survived three phases routing FB-B 404/409 splits on a string literal that mypy/pyright couldn't see. POLISH-02 replaced with proper `Optional[str]` and rewired the discriminators. If a sentinel value carries semantic discrimination, it belongs in the type system.
2. **Pre-run UAT before flipping a default value.** MODEL-02 would have regressed the live operator surface. Run the candidate value through the actual operator UAT path first; capture cold-start, warm-run, and steady-state numerics; only flip if all three PASS. If any FAIL, document the failure mode + named candidate fixes in the seed and defer with empirical evidence.
3. **Default-on probes beat opt-in env gates for test fixtures.** Opt-in gates are silent disablers — the v1.4 `FORGE_TEST_DB=1` gate hid 22+ tests across the entire milestone, including a Phase 13 logic bug carried since FB-A. Default-on probes with `OSError` silent-skip preserve CI green state without hiding regressions in development.
4. **Helper placeholders + caller overrides via `dataclasses.replace`.** When a helper produces an immutable dataclass that the caller needs to amend (POLISH-01: ref derivation moved from helper literal to call-site composition), `dataclasses.replace(instance, field=value)` is the locked pattern. Helper emits placeholder, caller overrides at the call site — same indexing namespace as siblings prevents collisions.
5. **Audit-driven scoping makes patch milestones mechanical.** v1.4.x didn't need a research phase or a discuss phase per requirement — every requirement traced back to a specific debt item in the v1.4 audit's `Known deferred items` list with a concrete acceptance criterion. The patch milestone shipped in 3 days because the spec was already locked at v1.4 close.
6. **Worktree-based wave parallelization scales to within-phase plan groups.** Phase 19's Wave 1 (POLISH-01/02/03 — no shared files) executed in parallel worktrees; Wave 2 (POLISH-04 — depends on 19-01 — same `_adapters.py`) executed serially. Wave dependency analysis caught the file-overlap correctly. No race conditions, no manual merge conflicts.

### Cost Observations

- Model mix this milestone: primarily Opus 4.7 1M-context (orchestration, planning, audit, milestone close); Sonnet 4.6 for executor + verifier agents.
- Sessions: ~2 focused sessions (Phase 17/18 in one, Phase 19 + audit + close in another).
- Notable: 1M-context orchestrator held all 10 plan SUMMARYs + 3 phase VERIFICATIONs + REVIEW.md + REQUIREMENTS.md + ROADMAP.md + the v1.4 audit + the v1.4.x audit simultaneously during close. The 3-source cross-reference (REQUIREMENTS.md × VERIFICATION.md × SUMMARY frontmatter) ran in a single context window — much faster than v1.2's per-phase cross-reference passes.
- Notable: `gsd-tools milestone complete` saved time on archive scaffolding (created the milestone roadmap + requirements files + audit move + MILESTONES.md base entry in one command) but the AI-curation work (ROADMAP.md reorganization + accomplishment narratives + PROJECT.md evolution + retrospective + key-decision audit) remained the bulk of the close-out effort. The CLI handles ~15% of the close; the AI handles ~85%.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 3 | Standalone package extraction; learning-pipeline port from FlameSavant (JS → Python) |
| v1.1 | 3 | projekt-forge cutover to pip dependency; Option A shadow-remediation pattern emerged (Phase 5) |
| v1.2 | 3 | Observability + provenance end-to-end; `@runtime_checkable` Protocol pattern locked; cross-repo release ceremony proven at 3x (v1.2.0, v1.2.1, v1.3.0) |
| v1.4.x | 3 | Audit-as-spec for patch milestones; decoupled-commit purity for tunable defaults; default-on probes vs. opt-in env gates for test fixtures |

### Cumulative Quality

| Milestone | Shipped | Tests | Public API | Commits |
|-----------|---------|-------|------------|---------|
| v1.0 | 2026-04-15 | 159 | 11 | 66 |
| v1.1 | 2026-04-19 | 276 | 15 | 198 |
| v1.2 | 2026-04-22 | 289 | 16 | 263 |
| v1.4.x | 2026-04-30 | 865 | 19 | 689 |

### Top Lessons (Verified Across Milestones)

1. **Option A shadow remediation is the locked cross-repo pin pattern.** First discovered in Phase 5, re-validated in Phase 07.1, re-validated in Phase 8. `pip uninstall -y forge-bridge && pip install -e .` is not optional.
2. **Narrow Protocol/API beats wide Protocol/API at v1.x.** Explicit single-method Protocols (StoragePersistence, Phase 8) and narrow `__all__` re-exports (Phase 4) have been easier to evolve than wide contracts. YAGNI for public surfaces.
3. **UAT must exercise the live production call path.** Phase 6 → 7 → 8 chain had a missing hook that unit tests never caught. Only the Phase 8 UAT forcing function ("real MCP call produces a row") found it.
4. **Locked non-goals in PROJECT.md prevent scope creep.** v1.1's locked non-goals (LLMRouter hot-reload, shared-path JSONL writers) carried cleanly into v1.2 without re-litigation. Write them down when the decision is fresh.
