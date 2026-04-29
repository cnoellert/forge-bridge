---
phase: 17-default-model-bumps
plan: 02
status: complete
requirements: [MODEL-01]
date: 2026-04-28
---

# 17-02 SUMMARY — MODEL-01 cloud-default bump (claude-opus-4-6 → claude-sonnet-4-6)

## Outcome

MODEL-01 acceptance closed. `_DEFAULT_CLOUD_MODEL` flipped from `"claude-opus-4-6"` to `"claude-sonnet-4-6"` in `forge_bridge/llm/router.py` as a single isolated value-flip commit per Phase 15 D-30 decoupled-commit mandate. Default-suite regression assertion updated. SEED-OPUS-4-7-TEMPERATURE-V1.5 planted to capture the AnthropicAdapter `temperature`-elision work needed before any future opus-4-7 bump becomes viable.

## Files modified

| File | Commit | Change |
|------|--------|--------|
| `forge_bridge/llm/router.py` | `edbfef6` | `_DEFAULT_CLOUD_MODEL` value flip + comment block update + class-docstring `Model:` and env-default lines |
| `tests/test_llm.py` | `edbfef6` | `test_default_fallback`: `router.cloud_model == "claude-sonnet-4-6"` |
| `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` | `05c5f78` | new — captures opus-4-7 `temperature`-rejection + AnthropicAdapter-always-sends-temperature facts |

## Commits (in order on main)

- `edbfef6` — `feat(llm/router): bump _DEFAULT_CLOUD_MODEL to claude-sonnet-4-6 (MODEL-01)` (2 files: router + test)
- `05c5f78` — `docs(seeds): plant SEED-OPUS-4-7-TEMPERATURE-V1.5` (1 file)
- merged to main as `7722f1c` (chore: merge executor worktree)

Decoupled-commit purity preserved: the bump commit (`edbfef6`) touches only `forge_bridge/llm/router.py` (one-line value flip + verbatim plan-prescribed comment/docstring mirrors) and `tests/test_llm.py` (the regression guard). `git blame` on line 72 of router.py reads "bump _DEFAULT_CLOUD_MODEL to claude-sonnet-4-6 (MODEL-01)".

## Acceptance criteria evidence

### Task 1 — bump + regression test

- `_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"` present at `forge_bridge/llm/router.py:72`
- `tests/test_llm.py:95` asserts `router.cloud_model == "claude-sonnet-4-6"`
- Default suite (executor pre-merge): `pytest tests/ -q -p no:pytest-blender` → 763 passed, 117 skipped, 0 failed in 22.40s
- Default suite (post-merge spot check): `pytest tests/test_llm.py -q -p no:pytest-blender` → 19 passed in 1.75s
- `git diff --name-only edbfef6~1 edbfef6` → `forge_bridge/llm/router.py`, `tests/test_llm.py` (commit isolation confirmed)

### Task 2 — SEED-OPUS-4-7-TEMPERATURE-V1.5 planted

- File present at `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` (83 lines)
- Frontmatter `name: SEED-OPUS-4-7-TEMPERATURE-V1.5` present
- Both required facts captured:
  1. `claude-opus-4-7` rejects `temperature` (cross-ref to v1.4 audit line 273)
  2. `AnthropicAdapter` currently always sends `temperature` (markdown inline-code)
- `## How to Apply` and `## Cross-References` sections present
- `git diff --name-only 05c5f78~1 05c5f78` → `.planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md`

### Task 3 — Live LLMTOOL-02 verification (human-in-the-loop, PASSED 2026-04-28)

```
$ FB_INTEGRATION_TESTS=1 pytest tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live -v -p no:pytest-blender
============================ test session starts ============================
platform darwin -- Python 3.11.14, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/cnoellert/Documents/GitHub/forge-bridge
configfile: pyproject.toml
plugins: anyio-4.12.1, playwright-0.7.2, cov-7.1.0, timeout-2.4.0, asyncio-1.3.0, base-url-2.1.0
asyncio: mode=Mode.AUTO
collected 1 item

tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live PASSED [100%]

============================ 1 passed, 1 warning in 4.52s ============================
```

Conditions verified before run:
- `ANTHROPIC_API_KEY` set (rotated mid-checkpoint after a paste-into-chat incident; v1.4-rotated key revoked, fresh key minted, history scrubbed)
- `FORGE_CLOUD_MODEL` unset (no env override — test ran against the new default)
- Sentinel `FORGE-INTEGRATION-SENTINEL-XJK29Q` returned in the live LLM response (test asserts on it; the test's own PASS confirms presence)
- 4.52s total elapsed — well under the test's `max_seconds` budget; ~13× headroom on the 60s default

Result: User confirmed `LLMTOOL-02 PASS`.

## Plan-internal contradictions (Rule 1, executor flagged at checkpoint, resolved here)

The executor flagged two grep acceptance criteria that cannot be satisfied alongside the plan's verbatim prescribed text:

1. **`grep -c 'claude-opus-4-6' forge_bridge/llm/router.py` returns `0`** — unsatisfiable. The plan's verbatim prescribed comment block (Edit 1, lines 138-143) deliberately keeps the historical reference: `"the Phase 17 (v1.4.x) bump from claude-opus-4-6 (deprecated; returned 500 from the live Anthropic API per v1.4 LLMTOOL-02 UAT)"`. This is documentation context, not a live model identifier. Verbatim prescribed text takes precedence.

2. **`grep -ci 'AnthropicAdapter currently' SEED-OPUS-4-7-TEMPERATURE-V1.5.md >= 1`** — fails as a bare grep because the prescribed seed text uses markdown inline-code backticks: `` `AnthropicAdapter` currently always sends ``. The semantic content is present; the bare grep pattern doesn't match because of the backtick interruption. `grep -F 'AnthropicAdapter` currently' .planning/seeds/SEED-OPUS-4-7-TEMPERATURE-V1.5.md` would match.

Resolution: executor (correctly) followed the plan's verbatim prescribed strings since they are more specific than the grep patterns and convey load-bearing historical context. All semantic acceptance is met. The grep patterns were authored before the verbatim text was finalized; future plans should grep against the verbatim text post-hoc rather than co-author both.

## Default behavior verified

```
LLMRouter().cloud_model == "claude-sonnet-4-6"   # was "claude-opus-4-6" pre-bump
LLMRouter().local_model == "qwen2.5-coder:32b"   # unchanged (P-03 deferral)
```

No other source files touched in either commit.

## Closures

- **MODEL-01:** acceptance fully closed (default-value assertion + live UAT both green; no env override; no other source files touched).
- **SEED-CLOUD-MODEL-BUMP-V1.4.x:** retired — its v1.4.x scope is closed by this plan. The seed file remains in `.planning/seeds/` for historical reference; the v1.5 successor for the opus-4-7 path is `SEED-OPUS-4-7-TEMPERATURE-V1.5.md` (planted by this plan).

## Unblocks

- Phase 17 close-out (verify-phase, security-phase, milestone tracking).
- v1.4.1 release ceremony — MODEL-01 was the cloud-side blocker; MODEL-02 closed via deferral in 17-03.
