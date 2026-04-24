---
phase: 11
slug: cli-companion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seed derived from `11-RESEARCH.md` §"Validation Architecture". Per-task rows populated by planner.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (existing; `asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_cli_*.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds (CLI unit tests) · ~60 seconds (full suite) |
| **Coverage tool** | `pytest-cov` — Phase 11 Nyquist floor: 80% line coverage for `forge_bridge/cli/` |
| **Coverage command** | `pytest tests/test_cli_*.py --cov=forge_bridge/cli --cov-fail-under=80 -q` |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cli_*.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green AND coverage ≥ 80% on `forge_bridge/cli/`
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Populated by planner — one row per atomic task. Each row binds a task to its REQ-ID, test type, and automated command. Wave 0 tasks create the test files; subsequent tasks reference existing files.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _to be populated by gsd-planner_ | | | | | | | | | |

---

## Wave 0 Requirements

Test files Phase 11 must create before other tasks depend on them (the planner assigns these to Wave 0):

- [ ] `tests/conftest.py` — add `free_port()` and `console_server(free_port)` fixtures (shared across every `test_cli_*.py`)
- [ ] `tests/test_cli_commands.py` — CLI-01 subcommand registration stubs
- [ ] `tests/test_cli_client.py` — CLI-02 sync-httpx + `(ConnectError | TimeoutException | RemoteProtocolError)` → exit-2 matrix stubs
- [ ] `tests/test_cli_json_mode.py` — CLI-03 stdout-purity + P-01 corruption-guard stubs
- [ ] `tests/test_cli_rendering.py` — CLI-04 TTY / non-TTY / `--no-color` / `--quiet` stubs
- [ ] `tests/test_cli_tools.py` — TOOLS-03 list + filters + drilldown stubs
- [ ] `tests/test_cli_execs.py` — EXECS-03 list + `--since` parser + `--tool` client-side filter stubs
- [ ] `tests/test_cli_manifest.py` — MFST-05 list + `--json` stubs
- [ ] `tests/test_cli_health.py` — HEALTH-02 service-group panel stubs
- [ ] `tests/test_cli_doctor.py` — HEALTH-03 full check matrix + exit-code taxonomy stubs

*No framework install needed — `pytest` and `pytest-cov` are already in `[project.optional-dependencies].dev`.*

---

## Minimum Sample Sizes

Per-requirement test floors (from RESEARCH.md §"Minimum Sample Sizes"):

| Requirement | Min Samples | What they cover |
|-------------|-------------|-----------------|
| CLI-03 `--json` mode | 3 | positive · connection-error envelope · HTTP-error envelope |
| EXECS-03 `--since` parser | 5 | `Nh` · `Nd` · ISO-8601 with `Z` · malformed · ISO-8601 duration (rejected) |
| HEALTH-03 `doctor` | 6 | all-pass · critical-fail · degraded-warn · server-unreachable · JSONL-parse-fail · sidecar-unwritable |
| TOOLS-03 edges | 4 | `--origin` empty · `--namespace` empty · `--search` partial · `<name>` not-found |
| EXECS-03 edges | 4 | `--tool` empty · `--since` malformed · `--limit 0` · `--offset` beyond-end |
| HEALTH-03 edges | 3 | JSONL missing · disk-space warn/fail · `--json` exit-code preservation |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Soft dogfood UAT | SC#4 (ROADMAP) | Subjective "can I decipher the output without re-reading the source?" criterion per D-08 | Developer (CN/dev) runs `forge-bridge console tools` and `forge-bridge console execs --since 24h` against a live server, records a single `PASS / FAIL + note` line at `.planning/phases/11-cli-companion/11-UAT.md`. No fresh-operator requirement (Phase 10.1 D-44 does NOT apply per D-08). No 30-second timer. |
| Rich rendering on a real TTY | CLI-04 | `CliRunner` captures `Console(force_terminal=True)` output but can't confirm visual fidelity on a real terminal emulator | After unit tests pass, developer runs `forge-bridge console tools` and `forge-bridge console health` on an interactive terminal; confirms Rich tables/panels render as intended (amber header, SQUARE box, truncated 8-char hash, `Created ▼` sort glyph legible). Recorded in `11-UAT.md`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (10 test files + conftest fixtures)
- [ ] No watch-mode flags (`-f`, `--watch`, `--forever`) anywhere in plan tasks
- [ ] Feedback latency < 30s
- [ ] Coverage floor ≥ 80% on `forge_bridge/cli/` measured via `pytest-cov`
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
