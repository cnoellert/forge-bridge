---
phase: 07-tool-provenance-in-mcp-annotations
verified: 2026-04-21T20:35:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
requirements_closed:
  - PROV-01
  - PROV-02
  - PROV-03
  - PROV-04
  - PROV-05
  - PROV-06
success_criteria:
  roadmap_sc_1: passed     # tools/list surfaces five forge-bridge/* _meta keys
  roadmap_sc_2: passed     # .sidecar.json preferred, .tags.json fallback, missing sidecar no-crash
  roadmap_sc_3: passed     # _sanitize_tag rejects control/injection/>64; 16-tag, 4 KB budget
  roadmap_sc_4: passed     # readOnlyHint=False baseline on every synthesized tool
  roadmap_sc_5: passed     # projekt-forge pinned; UAT diff additive-only — via Phase 07.1 vehicle
release_artifacts:
  - tag: v1.2.0
    commit: 0987525b73dae69812d011bfeceff2df9f51ef91
    created_at: 2026-04-20T05:17:43Z
    github_release: https://github.com/cnoellert/forge-bridge/releases/tag/v1.2.0
    assets:
      - forge_bridge-1.2.0-py3-none-any.whl
      - forge_bridge-1.2.0.tar.gz
uat_evidence:
  path: .planning/phases/07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat/07.1-UAT-EVIDENCE.md
  method: real MCP client (Claude Code on Portofino) + Python MCP SDK probe — no monkey-patch
  synth_tool_under_test: synth_set_segment_gain
  code_hash_verified: 16ad4226dea7da72403d82f979de16a0afc36dd121ad832225981d4715072a59
gaps: []
human_verification: []
deferred: []
info_deferred:
  note: "6 info-level code-review items (IN-01..IN-06) deferred as out-of-scope per user directive. These are maintainability nits (unittest.mock import scope, eviction-order determinism docstring, silent except in cleanup paths, JSONL replay unbounded, local-import comment clarity). None block Phase 7 goal achievement."
---

# Phase 7: Tool Provenance in MCP Annotations — Verification Report

**Phase Goal (from ROADMAP.md § Phase 7):** Consumers calling `tools/list` over MCP see canonical provenance fields on every synthesized tool (origin, code_hash, synthesized_at, version, observation_count) under the `forge-bridge/*` namespace in `Tool._meta`, with consumer-supplied tags passing through a sanitization boundary that strips injection markers and enforces size budgets.

**Verified:** 2026-04-21T20:35:00Z
**Status:** passed
**Re-verification:** No — initial verification
**Regression gate:** `pytest tests/` → 278 passed, 2 warnings, 0 failures, 0 errors (run at verification time)

---

## Goal Achievement

### Observable Truths (merged from ROADMAP Success Criteria + per-plan must-haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MCP client calling `tools/list` receives `Tool._meta` payloads with the five canonical `forge-bridge/*` keys on every synthesized tool | VERIFIED | Phase 07.1 UAT step 4 — verbatim wire payload for `synth_set_segment_gain` shows `forge-bridge/origin: synthesizer`, `forge-bridge/code_hash: 16ad4226...`, `forge-bridge/synthesized_at: 2026-04-21T17:35:57.072122+00:00`, `forge-bridge/version: 1.2.1`, `forge-bridge/observation_count: 3`. Captured via Python MCP SDK probe against a live stdio projekt-forge subprocess — not a monkey-patch. |
| 2 | Synthesized tool registered with `.sidecar.json` envelope surfaces tags on MCP wire; legacy `.tags.json` sidecar still loads via grace path; missing sidecar still registers with default `_meta` and no crash | VERIFIED | `_read_sidecar` at `watcher.py:55-142` preferentially reads `.sidecar.json`, falls back to `.tags.json` (lines 105-127), returns `None` on missing/malformed (lines 76-83, 128-129). Verified live in UAT: `synth_set_segment_gain` loads v1.2 envelope (full five meta keys); pre-existing `synth_rename_segment` loads legacy `.tags.json` (step 4 evidence shows `_meta` with only `_source` + `forge-bridge/tags` — correct back-compat). Tests `test_sidecar_preferred_over_tags_json`, `test_legacy_tags_json_fallback_when_no_sidecar`, `test_missing_sidecar_returns_none`, `test_malformed_sidecar_returns_none_with_warning` in `tests/test_watcher.py::TestReadSidecar`. |
| 3 | Consumer-supplied tag containing control chars, injection markers, or exceeding 64 chars is rejected at `_sanitize_tag()` boundary with WARNING log; every synthesized tool's `_meta` payload stays ≤ 4 KB and ≤ 16 tags per tool | VERIFIED | `_sanitize_tag` at `sanitize.py:80-118` — `_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")` (line 62), `INJECTION_MARKERS` tuple of 8 patterns (lines 50-59), 64-char truncation after allowlist match (line 115), `logger.warning(...)` on every reject path. `apply_size_budget` enforces `MAX_TAGS_PER_TOOL=16` and `MAX_META_BYTES=4096` (lines 121-162), protects five canonical meta keys from eviction. 26 tests in `tests/test_sanitize.py` cover all reject/pass/redact/budget cases. WR-01 fix now also applies budget at `register_tool` write boundary (`registry.py:95-98`). |
| 4 | Every synthesized tool has `annotations.readOnlyHint=False` set explicitly at registration | VERIFIED | `registry.py:107-119` — `if source == "synthesized": effective_annotations.setdefault("readOnlyHint", False)`. UAT step 4 evidence shows `"annotations": {"readOnlyHint": false}` on `synth_set_segment_gain` wire payload. UAT step 6 confirms `flame_*` / `forge_*` builtin annotations preserved unchanged (no cross-contamination). Tests `test_register_tool_synthesized_defaults_readonly_false`, `test_register_tool_builtin_no_readonly_baseline`, `test_register_tool_explicit_readonly_not_overridden` in `tests/test_mcp_registry.py::TestProvenanceMerge`. |
| 5 | projekt-forge pinned to `forge-bridge @ git+...@v1.2.0` (superseded to `@v1.2.1` via Phase 07.1 hotfix); regression pytest green; `tools/list` diff additive-only on `synth_*`, no changes on `flame_*`/`forge_*` | VERIFIED | `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` line 25: `"forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@v1.2.1"` (pin landed at `@v1.2.0` 2026-04-20, re-pinned to `@v1.2.1` via Phase 07.1 Plan 03 commit `d6aee82`). Phase 07.1 UAT step 6 captures verbatim `_meta` dicts for four sampled builtins (`flame_ping`, `flame_context`, `forge_ping`, `forge_list_projects`) — every one carries ONLY `{"_source": "builtin"}`, no PROV-02 contamination. `synth_set_segment_gain` (step 4) carries the full five-key envelope. Additive-only contract proven. |
| 6 | Synthesizer writes `.sidecar.json` (not `.tags.json`) with envelope `{tags, meta, schema_version=1}` containing all five canonical `forge-bridge/*` keys | VERIFIED | `synthesizer.py:368-387` — envelope writer with literal `"forge-bridge/origin": "synthesizer"`, `hashlib.sha256(fn_code.encode()).hexdigest()` for code_hash, `datetime.now(timezone.utc).isoformat()` for synthesized_at, `_forge_bridge.__version__` for version, `count` passed through, `"schema_version": 1`. UAT step 3 verbatim sidecar file on disk: all five keys present; `schema_version == 1`; file at `~/.forge-bridge/synthesized/synth_set_segment_gain.sidecar.json`. Tests `test_sidecar_json_envelope_roundtrip`, `test_sidecar_meta_contains_all_five_canonical_keys`, `test_sidecar_written_with_empty_tags`, `test_legacy_tags_json_never_written_by_writer` in `tests/test_synthesizer.py::TestSidecarEnvelope`. |
| 7 | `register_tool` grows `provenance: dict | None = None` kwarg; only `forge-bridge/*` meta keys forwarded to `mcp.add_tool`; `_source` preserved; `register_tools` (public plural API) signature unchanged | VERIFIED | `registry.py:54-60` — new signature matches. Namespace filter at `registry.py:100-102`: `for k, v in prov_meta.items(): if k.startswith("forge-bridge/"): merged_meta[k] = v`. `_source` set first at line 84, never overwritten. `register_tools` at `registry.py:129-169` — parameters `[mcp, fns, prefix, source]` unchanged. Test `test_register_tools_signature_unchanged` enforces the freeze. |
| 8 | Async storage callback that raises is isolated — JSONL write succeeds, exactly one WARNING logged, no exception propagates (WR-01 gap closed) | VERIFIED | `execution_log.py:56-70` — `_log_callback_exception` done_callback captures async exception and emits `logger.warning("storage_callback raised — execution log unaffected", exc_info=...)`. Tests `test_async_storage_callback_exception_isolated` + `test_async_storage_callback_exception_does_not_propagate` in `tests/test_execution_log.py:332-390`. WR-01 = test-coverage gap; pre-existing implementation was already correct per 07-03-SUMMARY deviation note. |
| 9 | `ExecutionRecord` docstring correctly scopes to `record()` writes and cross-references `mark_promoted()` for partial row shape (WR-02 drift fixed) | VERIFIED | `execution_log.py:35-44` — new docstring reads "Mirrors the JSONL row written by ExecutionLog.record() — same field names, same types. NOT every JSONL row is an ExecutionRecord: ExecutionLog.mark_promoted() writes a separate partial row of shape {code_hash, promoted, timestamp} for promotion events." Old inaccurate "Mirrors the JSONL on-disk schema exactly" wording returns zero grep matches. |
| 10 | README.md documents conda `forge` env creation pattern (PROV-06) | VERIFIED | `README.md:66` — `## Conda environment` heading; lines 73-74: `conda create -n forge python=3.11 -y` + `conda activate forge`; line 80: `pip install -e ".[dev]"`; line 86: `pip install -e ".[dev,llm]"`. |
| 11 | v1.2.0 released as consumable milestone artifact: annotated tag + GitHub release with wheel + sdist; `mcp[cli]>=1.19,<2` pin bumped | VERIFIED | Annotated tag `v1.2.0` on commit `0987525b73dae69812d011bfeceff2df9f51ef91` (2026-04-20T05:17:43Z); GitHub release https://github.com/cnoellert/forge-bridge/releases/tag/v1.2.0 with `forge_bridge-1.2.0-py3-none-any.whl` + `forge_bridge-1.2.0.tar.gz` attached; `pyproject.toml:15` pins `"mcp[cli]>=1.19,<2"`. Note: currently-checked-out `pyproject.toml` reads `version = "1.2.1"` (Phase 07.1 hotfix bumped it); the v1.2.0 artifact is frozen at the annotated tag. Both releases ship. |

**Score:** 11 / 11 truths VERIFIED

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `forge_bridge/learning/synthesizer.py` | `.sidecar.json` writer with five canonical `forge-bridge/*` meta keys | VERIFIED | Lines 368-387 produce envelope; `.tags.json` retired from writer. |
| `forge_bridge/learning/sanitize.py` | `_sanitize_tag`, `apply_size_budget`, `SANITIZE_ALLOWLIST`, `MAX_TAGS_PER_TOOL=16`, `MAX_META_BYTES=4096`, `MAX_TAG_CHARS=64`, `INJECTION_MARKERS`, `_PROTECTED_META_KEYS` | VERIFIED | All exports present at expected line offsets (37, 38, 39, 42, 50, 65, 80, 121). |
| `forge_bridge/learning/watcher.py` | `_read_sidecar()` preferring `.sidecar.json`, falling back to `.tags.json`; `_scan_once` passes `provenance=` to `register_tool` | VERIFIED | `_read_sidecar` at lines 55-142; WR-02 type-guards at lines 87-100, 117-123; WR-03 feature-detect removed (line 184 is now unconditional). |
| `forge_bridge/learning/execution_log.py` | `ExecutionRecord` docstring correctly scopes to `record()` writes; `_log_callback_exception` done_callback isolation | VERIFIED | Lines 35-44 (docstring) + 56-70 (isolation path). |
| `forge_bridge/mcp/registry.py` | `register_tool(..., provenance=)` kwarg; namespace filter; `readOnlyHint=False` baseline; `register_tools` public API frozen | VERIFIED | Lines 54-126 (register_tool); 129-169 (register_tools unchanged). WR-01 fix at lines 95-98 applies `apply_size_budget` at write boundary. |
| `tests/test_synthesizer.py` | `TestSidecarEnvelope` class with round-trip + canonical-key + empty-tags + anti-regression tests | VERIFIED | Line 402, 4 tests. |
| `tests/test_sanitize.py` | 20+ tests: allowlist pass, redaction, control-char/injection/non-string reject, budget truncation, canonical-key protection | VERIFIED | 26 tests — `grep -c "def test_"` returns 26. |
| `tests/test_watcher.py` | `TestReadSidecar` class — sidecar-preferred, legacy fallback, missing, malformed, synthesized-tag prepend, injection drop, over-16 truncated | VERIFIED | Line 156, 8 original + 3 WR-02 regression tests = 11 cases; class scope confirmed. |
| `tests/test_mcp_registry.py` | `TestProvenanceMerge` class — provenance kwarg, _source preservation, readOnlyHint baseline, namespace filter, signature stability, WR-01 size-budget | VERIFIED | Line 198, 10 original + 3 WR-01 regression tests = 13 cases. |
| `tests/test_execution_log.py` | Async callback failure isolation + no-propagation tests (WR-01 coverage) | VERIFIED | Lines 332 + 370 — both tests present and passing. |
| `README.md` | `## Conda environment` section with `conda create -n forge python=3.11`, activation, editable install, dev/llm extras | VERIFIED | Line 66+. |
| `pyproject.toml` | Version bump + `mcp[cli]>=1.19,<2` pin | VERIFIED | Line 7: `version = "1.2.1"` (post-07.1 hotfix; v1.2.0 release tag is frozen at commit `0987525`). Line 15: `"mcp[cli]>=1.19,<2"`. |
| `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` | Pin bumped to `@v1.2.0` (or higher) | VERIFIED | Line 25 pins `@v1.2.1` — supersedes `@v1.2.0` via Phase 07.1 Plan 03 cross-repo re-pin, which Phase 7 explicitly defers to (07-04-SUMMARY narrates the supersession). |
| Annotated `v1.2.0` git tag + GitHub release | Wheel + sdist attached | VERIFIED | `git tag -l v1.2.0` returns `v1.2.0`; `gh release view v1.2.0 --repo cnoellert/forge-bridge` confirms title, assets (`forge_bridge-1.2.0-py3-none-any.whl`, `forge_bridge-1.2.0.tar.gz`), notes render as planned. |

All 14 expected artifacts: VERIFIED.

### Key Link Verification (data-flow wiring)

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `synthesizer.SkillSynthesizer.synthesize` | `<stem>.sidecar.json` file on disk | `output_path.with_suffix(".sidecar.json")` write | WIRED | `synthesizer.py:386-387` writes envelope after `manifest_register`. |
| `synthesizer` meta `forge-bridge/version` | `forge_bridge.__version__` | `_forge_bridge.__version__` local import | WIRED | Line 372 local import resolves `1.2.1` at runtime (proven in UAT — wire `forge-bridge/version` field shows `"1.2.1"`). |
| `watcher._scan_once` | `registry.register_tool` | `provenance=provenance` kwarg | WIRED | Line 184 unconditional call. WR-03 removed the dead feature-detect. |
| `watcher._read_sidecar` | `sanitize._sanitize_tag` | per-tag sanitization loop | WIRED | Line 134 `cleaned = _sanitize_tag(t)`. |
| `watcher._read_sidecar` | `sanitize.apply_size_budget` | final payload gate | WIRED | Line 142 `return apply_size_budget(payload)`. |
| `registry.register_tool` | `sanitize.apply_size_budget` | write-boundary defense (WR-01) | WIRED | Lines 95-98 unconditional budget call when provenance is supplied. |
| `registry.register_tool` | `mcp.add_tool(..., meta=merged_meta)` | MCP wire payload | WIRED | Lines 121-126; UAT step 4 wire capture proves end-to-end flow: sidecar on disk → `_read_sidecar` → `register_tool` → `mcp.add_tool` → `tools/list` response contains all five `forge-bridge/*` keys with byte-identical `code_hash` to the disk file. |
| `execution_log._log_callback_exception` | `logger.warning("storage_callback raised...")` | done_callback on async task | WIRED | Lines 66-70; covered by two new tests. |
| `projekt-forge/pyproject.toml` | `forge-bridge v1.2.x` git tag | git+URL pin | WIRED | Line 25 pin resolves `@v1.2.1` (shadow remediation docs at 07.1-03). |

All 9 key links: WIRED.

### Data-Flow Trace (Level 4) — tools/list end-to-end

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `tools/list` response (synth_*) | `Tool._meta` dict | `register_tool(..., provenance=_read_sidecar(path))` | Yes — verbatim wire payload in 07.1 UAT step 4 shows `synth_set_segment_gain._meta` with `forge-bridge/origin=synthesizer`, `code_hash=16ad4226...`, `version=1.2.1`, `observation_count=3` | FLOWING |
| `tools/list` response (flame_*/forge_*) | `Tool._meta` dict | `register_tool(..., source="builtin")` with no provenance | Yes — builtin registrations carry only `_source=builtin` (UAT step 6 captures `flame_ping`, `flame_context`, `forge_ping`, `forge_list_projects` — none leak PROV-02 keys) | FLOWING |
| synth tool `annotations` | `readOnlyHint` bool | `effective_annotations.setdefault("readOnlyHint", False)` for `source="synthesized"` | Yes — UAT step 4 wire payload: `"annotations": {"readOnlyHint": false}` | FLOWING |
| sidecar on disk | meta dict with five canonical keys | synthesizer envelope write | Yes — UAT step 3 verbatim sidecar contents match expected envelope; file on disk at `~/.forge-bridge/synthesized/synth_set_segment_gain.sidecar.json` | FLOWING |

All data-flow checks: FLOWING. No HOLLOW_PROP, no STATIC fallback, no DISCONNECTED source.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full test suite green | `pytest tests/ --tb=line -q` | 278 passed, 2 warnings, 0 failures (6.53s) | PASS |
| `register_tool` has `provenance` kwarg | `python -c "import inspect; from forge_bridge.mcp.registry import register_tool; assert 'provenance' in inspect.signature(register_tool).parameters"` | Implicit via test `test_register_tool_has_provenance_kwarg` | PASS |
| `register_tools` public API frozen | test `test_register_tools_signature_unchanged` asserts `[mcp, fns, prefix, source]` | Passes in suite | PASS |
| v1.2.0 git tag exists | `git tag -l v1.2.0` | Returns `v1.2.0`; annotated on commit `0987525` | PASS |
| GitHub release v1.2.0 exists with assets | `gh release view v1.2.0 --repo cnoellert/forge-bridge` | Title `v1.2.0 — Tool Provenance in MCP Annotations`; both wheel + sdist attached | PASS |
| projekt-forge pin active | `grep "forge-bridge @ git+" /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` | Line 25: `@v1.2.1` (supersedes `@v1.2.0` per 07.1) | PASS |
| README conda section | `grep "^## Conda environment" README.md` | Line 66 | PASS |

All spot-checks: PASS.

### Requirements Coverage (PROV-01..PROV-06)

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| PROV-01 | 07-01, 07-02 | `.sidecar.json` envelope `{tags, meta, schema_version=1}`; watcher `.sidecar.json` preferred with legacy `.tags.json` grace fallback | SATISFIED | synthesizer.py:368-387 writes envelope; watcher.py:55-142 reads with preference + fallback + malformed handling. UAT step 3 (disk) + step 4 (wire) + `test_sidecar_json_envelope_roundtrip` + `TestReadSidecar` all confirm. |
| PROV-02 | 07-03 | Five canonical `forge-bridge/*` keys in `Tool._meta`: origin, code_hash, synthesized_at, version, observation_count | SATISFIED | registry.py:100-102 merges only namespaced keys. **End-to-end proven via 07.1-UAT-EVIDENCE.md step 4:** verbatim `tools/list` response for `synth_set_segment_gain` carries all five keys with matching sidecar code_hash. The original 07-04 UAT used a monkey-patched harness and was superseded by the Phase 07.1 real-MCP-client UAT on 2026-04-21 — see 07-04-SUMMARY § "Deployment UAT — deferred to Phase 07.1". |
| PROV-03 | 07-02, 07-03 (WR-01 fix) | `_sanitize_tag` strips control chars, rejects injection markers, truncates to 64; `MAX_TAGS_PER_TOOL=16`, `MAX_META_BYTES=4096`, project/phase/shot/type allowlist; WARNING on reject | SATISFIED | sanitize.py lines 37-162 implement every ceiling and reject path; 26 tests in test_sanitize.py cover every branch. UAT step 4 wire payload shows `"forge-bridge/tags": ["synthesized"]` — confirms the read-boundary sanitizer ran and prepended the literal filter tag per TS-02.1. WR-01 fix extends budget to the write boundary (registry.py:95-98). |
| PROV-04 | 07-03 | `annotations.readOnlyHint=False` set explicitly at every synthesized registration (prevents MCP client auto-approve) | SATISFIED | registry.py:116-119 — `if source == "synthesized": effective_annotations.setdefault("readOnlyHint", False)`. UAT step 4 wire capture: `"annotations": {"readOnlyHint": false}`. Builtin cross-contamination guarded: UAT step 6 shows `flame_ping` / `forge_ping` retain their original `readOnlyHint: true`. |
| PROV-05 | 07-03 | Async storage-callback failure-path tests (WR-01); `ExecutionRecord` docstring drift (WR-02) | SATISFIED | `test_async_storage_callback_exception_isolated` (test_execution_log.py:332) + `test_async_storage_callback_exception_does_not_propagate` (line 370) both pass; ExecutionRecord docstring rewritten at execution_log.py:35-44 — old "Mirrors the JSONL on-disk schema exactly" wording has zero grep matches. |
| PROV-06 | 07-03 | README documents conda `forge` env creation pattern | SATISFIED | README.md:66-87 — new `## Conda environment` section with all required commands. |

All 6 PROV-0X requirements: SATISFIED. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (none blocker/warning) | — | — | — | — |
| `forge_bridge/learning/synthesizer.py` | 23 | `from unittest.mock import AsyncMock, patch` at module scope (IN-01) | Info | Deferred — test-harness import in production module is cosmetic; does not affect runtime behavior. Explicitly tagged out-of-scope per 07-REVIEW-FIX.md. |
| `forge_bridge/learning/sanitize.py` | 144-146 | Eviction order is dict-insertion-order but not documented (IN-02) | Info | Deferred — behavior is correct and stable in CPython 3.7+; only a documentation concern. |
| `forge_bridge/learning/watcher.py` | 175, 197 | `try: mcp.remove_tool(stem); except Exception: pass` (IN-03) | Info | Deferred — silent cleanup failure would leak stale registration, but no current bug. |
| `forge_bridge/learning/watcher.py` | 47-48 | `except Exception: logger.exception(...)` in 5s poll loop (IN-04) | Info | Deferred — ops concern about log flooding; no current incident. |
| `forge_bridge/learning/execution_log.py` | 147-180 | JSONL replay unbounded by file size (IN-05) | Info | Deferred — explicit out-of-v1 scope per review. |
| `forge_bridge/learning/synthesizer.py` | 372 | Local import comment lacks full cycle explanation (IN-06) | Info | Deferred — doc-only nit. |

**Zero blockers. Zero warnings after 07-REVIEW-FIX.md (all four WR-xx fixed, commits `96209cb`, `c6eeedf`, `3617b90`, `1c840fa` + `341ff92`).** Info items IN-01..IN-06 explicitly deferred as out-of-scope per user directive; they do not block Phase 7 goal achievement and will be candidate tech-debt items for a future hygiene phase.

### Human Verification Required

None. The Phase 07.1 UAT cycle — executed 2026-04-21 on Portofino via a real MCP client (`claude mcp add -s user projekt-forge ... -- python -m projekt_forge --no-db` with NO monkey-patches) — already completed the live deployment verification that Phase 7's SC5 requires. Evidence file `07.1-UAT-EVIDENCE.md` captures verbatim tool-call results, stderr streams showing the graceful-degradation message, MCP SDK probe payloads with byte-identical code_hash match between sidecar and wire, and four-builtin non-contamination samples. No additional human testing remains to unblock this phase.

### Cross-Reference: Phase 07.1 as the Canonical PROV-02 UAT Vehicle

Phase 7 Plan 04's UAT task originally attempted verification on 2026-04-20 via `/tmp/run_pf_mcp.py` — a runtime monkey-patch that wrapped `startup_bridge` with an external try/except to paper over a latent `ConnectionRefusedError` bug on `:9998`. That harness made the UAT "pass" but was not a deployment-path reproducer: any real user booting projekt-forge without a `:9998` listener would hit the same bug.

Phase 07.1 retroactively closes this gap:

- **Bug root cause:** `forge_bridge/mcp/server.py::startup_bridge` try/except guarded only `wait_until_connected()`, leaking `ConnectionRefusedError` from `_client.start()`.
- **Hotfix:** commit `8cfcb62` wraps BOTH `_client.start()` AND `wait_until_connected()` in a single try/except; nulls `_client` on failure so `shutdown_bridge()` skips cleanly. Released as `v1.2.1` on 2026-04-20 (commit `abd047c`).
- **Regression test:** `bb472c9` adds a failing-against-v1.2.0, passing-against-v1.2.1 test that boots the MCP server with `FORGE_BRIDGE_URL` pointed at a dead port and asserts `tools/list` still serves.
- **True UAT:** Phase 07.1 Plan 04 executed the deployment verification on 2026-04-21 via `claude mcp add -s user projekt-forge` — a real MCP client session, no shims — and captured verbatim wire payloads in `07.1-UAT-EVIDENCE.md`. The evidence proves all five PROV-02 `_meta` keys reach a real client on a freshly Ollama-synthesized tool, with zero contamination on builtin tools.

For Phase 7 verification purposes, treating `07.1-UAT-EVIDENCE.md` as the canonical PROV-02 evidence artifact (rather than the superseded 07-04 monkey-patch log) is the correct reading. 07-04-SUMMARY.md narrates this explicitly. The Phase 07.1 cycle did NOT modify Phase 7 PROV-0X scope — it simply retrofitted missing deployment evidence onto the v1.2.0 → v1.2.1 lineage.

---

## Gaps Summary

**None.**

All 11 observable truths are VERIFIED. All 14 required artifacts exist and are substantive + wired + data-flowing. All 9 key links are WIRED. All 6 PROV-0X requirements are SATISFIED. All 4 warning-level code-review findings (WR-01..WR-04) are closed per `07-REVIEW-FIX.md`. Full regression gate is green (278 passed, 0 failures).

The 6 info-level findings (IN-01..IN-06) are explicitly deferred as out-of-scope maintainability nits, not gaps in the phase goal.

## Release Ceremony Verification

| Artifact | Expected | Status |
|---|---|---|
| `pyproject.toml` version | Reflects release (v1.2.0 shipped; current HEAD is v1.2.1 hotfix) | VERIFIED — line 7: `version = "1.2.1"`; `mcp[cli]>=1.19,<2` at line 15 |
| Annotated `v1.2.0` git tag | On main, tagged commit | VERIFIED — commit `0987525b73dae69812d011bfeceff2df9f51ef91`, tagged 2026-04-20T05:17:43Z |
| GitHub release v1.2.0 | Wheel + sdist attached, notes describe PROV-01..06 | VERIFIED — https://github.com/cnoellert/forge-bridge/releases/tag/v1.2.0 carries `forge_bridge-1.2.0-py3-none-any.whl` + `forge_bridge-1.2.0.tar.gz`; notes enumerate PROV-01..PROV-06 + mcp pin rationale |
| projekt-forge pin bump | `@v1.2.0` or successor | VERIFIED — pinned at `@v1.2.1` (07.1-03 cross-repo re-pin, commit `d6aee82`) |
| projekt-forge regression | `pytest tests/` green at 422-baseline | VERIFIED via 07.1 SC4 — per 07-04-SUMMARY reference |
| Cross-repo UAT diff | Additive-only on synth_*, no regression on flame_*/forge_* | VERIFIED via 07.1-UAT-EVIDENCE.md steps 4+6 — additive `_meta` on `synth_set_segment_gain`, builtins show only `{"_source": "builtin"}` |

All release-ceremony artifacts: VERIFIED.

---

## Overall Verdict

**Phase 7 (Tool Provenance in MCP Annotations) — PASSED.**

The phase promised canonical `forge-bridge/*` provenance on every synthesized tool's `Tool._meta`, a sanitization boundary against prompt injection and PII leakage, explicit `readOnlyHint=False` safety baseline on synthesized tools, async callback hygiene, and v1.2.0 as a shippable milestone artifact. Every one of those promises has substantive, wired, and data-flowing implementation in the repository at the verification commit. The live-UAT evidence in `07.1-UAT-EVIDENCE.md` closes the final end-to-end gate by proving the full pipeline (sidecar → watcher sanitize → registry merge → MCP wire) delivers all five canonical keys to a real MCP client with byte-identical code_hash round-trip and zero contamination on builtin tools.

All 6 PROV-0X requirements are SATISFIED. Zero blocking issues. Zero unaddressed human-verification items. All four Phase 7 code-review warnings are closed. The release artifacts (v1.2.0 tag, GitHub release with wheel + sdist, projekt-forge pin bump with cross-repo UAT) are all in place, with the Phase 07.1 hotfix cycle adding v1.2.1 on top without altering Phase 7 scope.

Phase 7 close-out is unblocked. Phase 8 (SQL Persistence Protocol) can start.

---

_Verified: 2026-04-21T20:35:00Z_
_Verifier: Claude (gsd-verifier)_
_Method: Goal-backward verification against ROADMAP.md § Phase 7 success criteria + per-plan must_haves; cross-referenced Phase 07.1 UAT evidence for PROV-02 end-to-end_
