---
phase: 19
slug: code-quality-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (auto mode) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options] asyncio_mode = "auto"`) |
| **Quick run command** | `pytest tests/llm/test_ollama_adapter.py tests/test_sanitize.py tests/test_staged_operations.py -v` |
| **Full suite command** | `FORGE_DB_URL=postgresql://forge:...@localhost:7533/forge_bridge pytest tests/ -v` |
| **Estimated runtime** | ~5–15s without DB (POLISH-01/02/04 paths); ~30–60s with DB (POLISH-03 atomicity) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (without DB if task is non-DB; with DB for POLISH-03 task)
- **After every plan wave:** Run full suite command with `FORGE_DB_URL` set
- **Before `/gsd-verify-work`:** Full suite must be green AND four grep-guards must return zero matches:
  - `! grep -nE '"0:"|f"0:\{' forge_bridge/llm/_adapters.py | grep -v '^\s*#'` (POLISH-01)
  - `! grep -rn '"(missing)"' forge_bridge/ tests/` (POLISH-02)
  - `pg_isready -h localhost -p 7533` returns 0 BEFORE running POLISH-03 verify (POLISH-03 must not silently skip)
  - `pytest tests/test_sanitize.py::test_injection_markers_count_locked -v` green (POLISH-04 count-lock)
- **Max feedback latency:** 60s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | POLISH-01 | T-19-01 (ref-collision via loosened salvage guard) | Salvaged ref derives from current `tool_calls` length; never literal `"0:"` | unit | `pytest tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback -v -k salvage_ref_derivation` | ✅ existing file; ❌ new test method (Wave 0 of P-01) | ⬜ pending |
| 19-01-02 | 01 | 1 | POLISH-01 | — | No literal `"0:"` in salvage helper or call site (post-fix grep guard) | guard | `! grep -nE '"0:"\|f"0:\{' forge_bridge/llm/_adapters.py \| grep -v '^\s*#'` | ✅ | ⬜ pending |
| 19-02-01 | 02 | 1 | POLISH-02 | T-19-02 (audit-trail / 404-vs-409 discriminator) | `from_status` is `None` for unknown UUID; non-None str for illegal transition; never `"(missing)"` | unit | `pytest tests/test_staged_operations.py::test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel -v` | ❌ new test (Wave 0 of P-02) | ⬜ pending |
| 19-02-02 | 02 | 1 | POLISH-02 | — | No `"(missing)"` literal in source/tests post-fix | guard | `! grep -rn '"(missing)"' forge_bridge/ tests/` | ✅ | ⬜ pending |
| 19-03-01 | 03 | 1 | POLISH-03 | T-19-03 (audit-trail tamper / dropped events) | Single-session approve+flush+rollback: 2 events visible mid-rollback, 1 event + status='proposed' post-rollback | unit (live Postgres) | `FORGE_DB_URL=postgresql://forge:...@localhost:7533/forge_bridge pytest tests/test_staged_operations.py::test_transition_atomicity -v` | ✅ existing test (rewrite-in-place) | ⬜ pending |
| 19-04-01 | 04 | 2 | POLISH-04 | T-19-04 (model-quality noise leakage) | Tail run of `<\|im_start\|>` / `<\|im_end\|>` / `<\|endoftext\|>` (with optional whitespace) is stripped from `_TurnResponse.text` | unit | `pytest tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterChatTemplateTailStrip -v -k terminal_chat_template_tokens_stripped` | ❌ new test (Wave 0 of P-04) | ⬜ pending |
| 19-04-02 | 04 | 2 | POLISH-04 | — | Clean prose (no chat-template tokens) passes through unchanged | unit | same suite, `-k clean_prose_passes_through_unchanged` | ❌ new test (Wave 0 of P-04) | ⬜ pending |
| 19-04-03 | 04 | 2 | POLISH-04 | — | `len(INJECTION_MARKERS) == 10` after extension (count-lock guard, was 8) | unit | `pytest tests/test_sanitize.py::test_injection_markers_count_locked -v` | ✅ existing test (assertion bump in same atomic commit) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/llm/test_ollama_adapter.py` — extend `TestOllamaToolAdapterBugDFallback` with new test method for POLISH-01 salvage-ref derivation; add new `TestOllamaToolAdapterChatTemplateTailStrip` class for POLISH-04 (two test methods: noise-tail strip + clean-prose passthrough)
- [ ] `tests/test_staged_operations.py` — add `test_lifecycle_error_from_status_is_optional_str_never_missing_sentinel` for POLISH-02; replace body of existing `test_transition_atomicity` for POLISH-03
- [ ] `tests/test_sanitize.py` line 177 — bump count-lock assertion from `== 8` to `== 10` (atomic with P-04 marker tuple extension)

*Existing infrastructure used:* `session_factory` (Phase 13/18), `_fake_response_dict` + `_FakeTool` (Phase 16.2), `EventRepo`, `StagedOpRepo` — all already imported by target test files.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| POLISH-03 must run against LIVE Postgres, not skip silently | POLISH-03 | Phase 18 HARNESS-03 made `_phase13_postgres_available()` skip silently when no DB is reachable. CI-friendly but hides "did my fix actually work?" — operator MUST confirm a green run with the env var set. | 1. `pg_isready -h localhost -p 7533` returns 0. 2. `FORGE_DB_URL=postgresql://forge:...@localhost:7533/forge_bridge pytest tests/test_staged_operations.py::test_transition_atomicity -v` returns "1 passed" (NOT "1 skipped"). 3. P-03 SUMMARY.md captures the run output. |
| POLISH-03 RED→GREEN evidence (documents-only per CONTEXT D-09) | POLISH-03 | RED experiment is NOT landed as a commit; it stays in SUMMARY.md as text evidence. | 1. Locally remove `await session.rollback()` line from rewritten test. 2. Run pytest: confirm fails with `assert 2 == 1` or similar. 3. Restore line. 4. Re-run pytest: confirm pass. 5. SUMMARY.md records both runs verbatim. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (8/8 above — 4 unit, 2 grep guards, 1 count-lock, 1 manual-only operator verify)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (every task in the map has an automated command)
- [ ] Wave 0 covers all MISSING references (3 new test methods + 1 assertion bump enumerated above)
- [ ] No watch-mode flags (pytest non-watch)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (flip after planner consumes this contract)

**Approval:** pending
