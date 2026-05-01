---
phase: 20
plan: "03"
subsystem: install
tags: [readme, docs, install, status-table, quick-start, v1.4.1]
dependency_graph:
  requires:
    - phase: 20-01
      provides: canonical-version-1.4.1, D17-consistency-guard
  provides:
    - readme-install-section-v1.4.1
    - readme-current-status-table-v1.4.1
  affects:
    - README.md
    - docs/INSTALL.md (Plan 20-04 will cite this section)
tech_stack:
  added: []
  patterns: [surgical-section-replacement, preserve-verbatim-discipline]
key_files:
  created: []
  modified:
    - README.md
key_decisions:
  - "Replaced Current Status table wholesale — 7 stale rows (incl. 'canonical vocab: In design') → 19-row table enumerating every shipped subsystem with version anchor"
  - "Renamed 'Install the MCP server' section to 'Install forge-bridge' to reflect that it installs the whole platform, not just a single component"
  - "Used FORGE_BRIDGE_HOST env-var pattern in the run section instead of the removed --bridge-host CLI flag"
  - "Five-surface smoke test block in 'Test the connection' covers Flame hook, MCP CLI, Web UI, chat, and forge-bridge console doctor"
  - "All preserve-verbatim sections (Vision, Architecture, Conda environment, Install the Flame hook, Repository Structure, Documentation, Relationship to projekt-forge, Design Principles, License) left byte-identical"
requirements-completed: [INSTALL-03]
duration: ~8 minutes
completed: "2026-04-30"
---

# Phase 20 Plan 03: README Install Section + Current Status Table Refresh Summary

**README install section and Current Status table rewritten to v1.4.1 reality: stale flags removed, mandatory extras documented, five-surface smoke tests added, all 14 shipped subsystems enumerated in table (correcting the misleading 'canonical vocab: In design' claim).**

## Performance

- **Duration:** ~8 minutes
- **Started:** 2026-04-30
- **Completed:** 2026-04-30
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Replaced the 7-row stale Current Status table with a 19-row table that accurately enumerates v1.4.1 shipped subsystems (canonical vocabulary, Artist Console, CLI, staged ops, LLMRouter, chat endpoint, learning pipeline, WebSocket server — all now Shipped with version anchors)
- Rewrote the install/run/test section: removed non-existent `--http --port 8080` and `--bridge-host` CLI flags, added `[dev,llm]` mandatory extras, added stdin-keepalive note, added five-surface smoke test block covering all 5 live surfaces
- Plan 20-01 curl URL invariant preserved (`v1.4.1` in curl line 120 and version prose line 123); D-17 consistency test remains green

## Task Commits

1. **Task 1: Replace README "Current Status" table + "Install/Run/Test" install-section blocks** — `89a2918` (docs)

## Files Created/Modified

- `/Users/cnoellert/Documents/GitHub/forge-bridge/.claude/worktrees/agent-a0bc53315ae7fdc6e/README.md` — Two surgical section replacements: (1) Current Status table lines 52–63, (2) Install/Run/Test blocks lines 120–141. All other sections preserved verbatim.

## Decisions Made

- Renamed the section heading from "### Install the MCP server" to "### Install forge-bridge" — the pip install now covers the whole platform (Web UI, CLI, chat, MCP), not just an MCP server component.
- The FORGE_BRIDGE_HOST env-var override pattern replaces the removed `--bridge-host` CLI flag. The plan specified this as the correct pattern (verified in RESEARCH §A2: "the MCP server reads FORGE_BRIDGE_HOST env var not a CLI flag").
- Five smoke commands in "Test the connection" follow the D1 per-surface smoke commands from RESEARCH.md exactly.

## Diff Summary: What Changed vs. What Was Preserved

### Section 1: "## Current Status" table — REPLACED

| Before | After |
|--------|-------|
| 7 rows | 19 rows |
| "Canonical vocabulary spec: 🔧 In design" | "Canonical vocabulary layer: ✅ Shipped (v1.0)" |
| No Artist Console row | ✅ Shipped (v1.3.1, Phases 10/10.1) |
| No CLI row | ✅ Shipped (v1.3.1, Phase 11) |
| No Staged ops row | ✅ Shipped (v1.4, FB-A + FB-B) |
| No LLMRouter row | ✅ Shipped (v1.4, FB-C) |
| No Chat endpoint row | ✅ Shipped (v1.4, FB-D + 16.1 + 16.2) |
| "Event-driven channel system: Planned" (misleading — WS server ships) | Nuanced: WS server Shipped; canonical pub/sub layer Planned |

Table also now includes: intro sentence with v1.4.1 date + milestone summary, Postgres persistence, WebSocket clients, Tool provenance, StoragePersistence, Learning pipeline.

### Section 2: "### Install the MCP server" + "### Run the MCP server" + "### Test the connection" — REPLACED

**Install section:** `pip install -e .` → `pip install -e ".[dev,llm]"` with explanation of what each extra provides and warning that bare install silently breaks chat + synthesis.

**Run section:**
- Removed: `python -m forge_bridge --bridge-host 192.168.1.100` (non-existent CLI flag)
- Removed: `python -m forge_bridge --http --port 8080` (Web UI does not launch via --http; it auto-starts on :9996)
- Added: `tail -f /dev/null | python -m forge_bridge` (stdin-keepalive for headless hosts)
- Added: `FORGE_BRIDGE_HOST=192.168.1.100 python -m forge_bridge` (correct env-var override pattern)
- Added: cross-reference to `docs/INSTALL.md` (Plan 20-04)

**Test the connection:** Open localhost:9999 (Flame console only) → Five-surface smoke test block covering Flame hook (:9999/status), MCP CLI, Web UI (:9996/ui/), chat endpoint, and forge-bridge console doctor. Added ANTHROPIC_API_KEY optional note.

### Sections preserved VERBATIM (unchanged bytes)

- "## Vision" — lines 9–13 ✅
- "## Architecture" diagram block — lines 17–36 ✅
- "### Current Implementation (Phase 1)" prose — lines 38–48 ✅
- "## Conda environment" — lines 66–105 ✅
- "### Install the Flame hook" including curl URL v1.4.1 and version default prose — lines 111–132 ✅
- "## Repository Structure" block — lines 193–224 ✅
- "## Documentation" links — lines 228–234 ✅
- "## Relationship to projekt-forge" — lines 237–242 ✅
- "## Design Principles" — lines 245–255 ✅
- "## License" — lines 259–261 ✅

## Plan 20-01 Consistency Guard: PASSED

```
pytest tests/test_install_hook_version_consistency.py -x
2 passed, 1 warning in 0.01s
```

Both D-17 regression tests pass:
- `test_install_hook_default_version_matches_pyproject`: script default v1.4.1 == pyproject 1.4.1
- `test_readme_curl_url_version_matches_pyproject`: README curl URL v1.4.1 == pyproject 1.4.1

## Verification Grep Results

```
# New content present
grep -q 'http://localhost:9996/ui/' README.md         → PASS
grep -q '/api/v1/chat' README.md                      → PASS
grep -q 'forge-bridge console doctor' README.md       → PASS
grep -q 'pip install -e "\.\[dev,llm\]"' README.md   → PASS
grep -q 'tail -f /dev/null' README.md                 → PASS
grep -q 'Artist Console' README.md                    → PASS
grep -q 'Staged-operations platform' README.md        → PASS
grep -q 'LLMRouter agentic' README.md                 → PASS
grep -q 'Canonical vocabulary layer' README.md        → PASS

# Stale content purged
--http --port 8080 count:         0  → PASS
--bridge-host 192.168.1.100 count: 0  → PASS
"🔧 In design" count:             0  → PASS

# Plan 20-01 invariant preserved
curl URL v1.4.1 count:            1  → PASS (one occurrence, untouched)

# Preserve-verbatim sections
## Vision present                 → PASS
## Architecture present           → PASS
## Conda environment present      → PASS
### Install the Flame hook present → PASS
## Repository Structure present   → PASS
## Documentation present          → PASS
## Relationship to projekt-forge  → PASS
## Design Principles present      → PASS
## License present                → PASS
```

## Phase 21 Candidates (preserve-verbatim drift logged, NOT fixed here)

The following sections are out-of-date but are explicitly Phase 21 scope (per CONTEXT.md D-10/D-11). Logged here for Phase 21 planning:

1. **"### Current Implementation (Phase 1)" prose (lines 38–48)**: Describes the project as "the Flame endpoint — an HTTP bridge". v1.4.1 reality is that forge-bridge is now a full 5-surface platform. Phase 21 rewrites "What This Is" + "Vision" sections.

2. **"## Repository Structure" block (lines 193–224)**: Lists `server.py` (legacy orphan), `tools/` only. Missing: `cli/`, `console/`, `core/`, `llm/`, `learning/`, `store/`, `mcp/`. Phase 21 will refresh the repository layout to match v1.4.1 reality.

3. **ANTHROPIC_API_KEY mention in "Test the connection"**: Added a note in the new section about ANTHROPIC_API_KEY being optional. If Phase 23 adds more operational guidance, this note may be expanded.

## README-to-INSTALL.md Path Alignment

The new install section now agrees with what Plan 20-04 (docs/INSTALL.md) will document:
- Same `pip install -e ".[dev,llm]"` install command
- Same FORGE_BRIDGE_HOST env-var override pattern (not --bridge-host CLI)
- Same five-surface smoke test set (D1 per RESEARCH.md)
- Cross-reference `docs/INSTALL.md` added to the run section so readers know where the full guide lives

No divergence between README and INSTALL.md on these points.

## Known Stubs

None. All changes are concrete content updates. No placeholder text, no hardcoded empty values, no "coming soon" strings.

## Threat Flags

No new security surface. Changes are documentation-only. Per threat register T-20-06 and T-20-07 (mitigate dispositions): both mitigations now applied — Current Status table corrected, stale CLI flags removed and replaced with the env-var override pattern that actually works.

## Deviations from Plan

None — plan executed exactly as written. Two edits to README.md, all preserve-verbatim sections untouched, Plan 20-01 curl URL invariant preserved, full test suite green.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `README.md` exists and was modified | FOUND |
| Commit `89a2918` exists | FOUND |
| `http://localhost:9996/ui/` present in README.md | FOUND |
| `/api/v1/chat` present in README.md | FOUND |
| `forge-bridge console doctor` present in README.md | FOUND |
| `pip install -e ".[dev,llm]"` present in README.md | FOUND |
| `tail -f /dev/null` present in README.md | FOUND |
| `--http --port 8080` absent from README.md | CONFIRMED (count=0) |
| `--bridge-host 192.168.1.100` absent from README.md | CONFIRMED (count=0) |
| `🔧 In design` absent from README.md | CONFIRMED (count=0) |
| curl URL v1.4.1 preserved (Plan 20-01 invariant) | FOUND (count=1) |
| `pytest tests/test_install_hook_version_consistency.py -x` | 2 passed |
| `pytest tests/ -x` | 845 passed, 41 skipped, 0 failed |
| 20-03-SUMMARY.md exists | FOUND |
