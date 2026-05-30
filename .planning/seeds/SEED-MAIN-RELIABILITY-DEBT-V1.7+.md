---
name: main-reliability-debt
description: 24 test failures on main at HEAD 65af768 (v1.8 open), re-baselined from the obsolete C.1 10-failure inventory. Three failure KINDS — test-ordering pollution (7 tests, pass isolated), real logic/source drift (7 tests), async-mock harness bug (8 tests) — plus the C.1 PR22 cluster now RESOLVED by bebf24a. Thread B (v1.8) promotes this to active reliability cleanup, B-full, fix-kind order.
type: strategic-framing
planted_during: "C.1 close, 2026-05-27 (original 10-failure inventory). RE-BASELINED 2026-05-29 at v1.8 Thread B open — full-suite run at HEAD 65af768 produced 24 failures, not 10; the C.1 identity-stable baseline was invalidated by Thread-A + phase-4b + PR4 work landing in the interval per [[feedback-baseline-drift-invalidates-controls]]."
trigger_when: "ACTIVE — promoted to v1.8 Thread B (main reliability cleanup). B-reframe-first (this rewrite) → B-full in fix-kind order (ordering pollution → tokens/CLI/source drift → async harness)."
superseded_baseline: "C.1 10-failure / 5-cluster inventory (commit 32e8cfb). Preserved as archaeology in § C.1 origin below; DO NOT use as the work scope — see § v1.8 re-baseline."
---

# Seed — main reliability debt (re-baselined for v1.8 Thread B)

> **Re-baselined 2026-05-29.** The C.1 inventory (10 failures, 5
> clusters, identity-stable) was the correct record for its era but is
> now obsolete. A contemporaneous full-suite run at v1.8 open (HEAD
> `65af768`) produced **24 failures**. Per
> [[feedback-baseline-drift-invalidates-controls]], an inherited
> failure list is not a safe work scope — it was re-verified, not
> trusted. This rewrite carries the re-verified inventory; the C.1
> archaeology is preserved below but is NOT the scope.

## v1.8 re-baseline — the live inventory (HEAD 65af768)

Full default suite: **24 failed, 2604 passed, 41 skipped** (125s).
Every failing cluster was re-run in isolation to separate genuine
logic debt from test-ordering pollution from environmental/harness
defects. Three failure KINDS emerged — the C.1 framing's "5 clusters
of similar debt" no longer holds.

### KIND 1 — test-ordering pollution (7 tests; pass isolated, fail in suite)

Cheapest high-value fix. These pass when run alone, fail only under
full-suite ordering — module-state bleed, not logic debt.

```
tests/test_utility_ping.py::test_ping_failure_path_echoes_bridge_url
tests/test_utility_ping.py::test_ping_success_path_still_echoes_bridge_url
tests/test_utility_ping.py::test_ping_failure_path_bridge_url_reflects_current_bridge_module_state
tests/test_sanitize.py::TestSanitizeTag::test_sanitize_rejects_log_warning_on_control_char
tests/test_sanitize.py::TestSanitizeTag::test_sanitize_rejects_log_warning_on_injection
tests/test_sanitize.py::TestApplySizeBudget::test_budget_truncates_tag_list_at_16
tests/test_synthesizer.py::TestPreSynthesisHook::test_pre_synthesis_hook_exception_falls_back_to_empty_context
```

Isolation evidence: `test_utility_ping.py` → 3 passed alone;
`test_sanitize.py` + `test_synthesizer.py` → 4 passed alone. The ping
cluster's behavioral shape matches the C.1 Cluster-4 note exactly
("pass in isolation; fail under full-suite ordering"). Likely one or
two shared-module-state culprits (the ping cluster touches
`bridge` module state; sanitize touches logging/allowlist state).
First fix-kind in B-full.

### KIND 2 — real logic / source drift (7 tests)

Genuine debt; fails isolated too.

```
tests/test_typer_entrypoint.py::test_bare_forge_bridge_boots_mcp_not_help
tests/test_typer_entrypoint.py::test_console_port_flag_sets_env
tests/test_timeline_gap_fill.py::test_gap_fills_tracks_segments_by_id
tests/test_timeline_gap_fill.py::test_pass2_skips_segments_already_used_as_gap_fills
tests/test_console_stdio_cleanliness.py::test_mcp_stdio_frames_are_clean_while_console_under_load
tests/test_console_stdio_cleanliness.py::test_stderr_contains_no_access_log_lines
tests/test_public_api.py::test_no_forge_specific_strings
```

Sub-shapes, each its own root cause:

- **CLI drift (typer, 2).** `--console-port` option genuinely absent
  from the CLI (`test_console_port_flag_sets_env` → `SystemExit(2)`,
  "No such option: --console-port"); bare-invocation boot behavior
  also drifted. Phase 11 + 20.x + 24.x all touched `fbridge`; one of
  them dropped/renamed the option the test asserts.
- **Timeline source-grep stale (gap_fill, 2).** These are
  *source-pattern* tests — they assert `gap_fills.add(id(...))` and
  `id(seg) in gap_fills` substrings exist in `timeline.rename_shots`
  source. The impl was rewritten (the function body the test greps no
  longer contains those patterns); the test was not updated alongside.
  Decision needed at fix time: is the gap-fill *behavior* still
  correct (test is stale and should be rewritten to assert behavior,
  not source) OR was the behavior lost in the rewrite (real
  regression)? Must read the current `rename_shots` body before
  deciding — do NOT just delete the assertion.
- **`portofino` token leak (public_api, 1).** REAL violation.
  `forge_bridge/tools/utility.py:305` contains the literal word
  `portofino` in a comment ("...mis-classify the portofino
  env-file"). The PKG-03 banned-token guard
  (`portofino|assist-01|ACM_`) is correctly firing. Fix: reword the
  comment to remove the host-specific token. One-line fix.
- **Stdio cleanliness (console_stdio, 2).** Fails isolated; 15s-timeout
  patterns under console-startup load. Needs investigation — adjacent
  to Phase 24.2 daemon-routed work + 16.x SSE streaming. Lowest
  confidence on root cause; investigate at fix time.

### KIND 3 — async-mock harness bug (8 tests)

```
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[disabled]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[enabled]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[failing]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state_recovering[recovering]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_capture_latency_delta_bounded
tests/corpus/test_pr4_no_dependency.py::test_arbitration_completes_when_corpus_unavailable[single_step]
tests/integration/test_chat_endpoint.py::TestChatSanitizationE2E::test_handler_passes_messages_verbatim_to_router
tests/integration/test_chat_parity.py::TestChatParityStructural::test_chat_parity_browser_vs_flame_hooks
tests/integration/test_chat_parity.py::TestChatParityStructural::test_chat_parity_envelope_keys_locked
```

(9 lines = 8 distinct + the 500 visible in both parity asserts.)
Shared failure signature: `TypeError: object MagicMock can't be used
in 'await' expression` → handler returns HTTP 500. A fixture mocks a
coroutine (the LLM router / chat handler call path) with plain
`MagicMock` where `AsyncMock` is required. Phase-4b / PR4-era test
harness. Likely **one fixture pattern fix radiating across 8 tests**
— per [[feedback-mock-three-tier]], this is a stub/contract-enforcer
that was never exercised against the real async call path. Last
fix-kind in B-full (largest blast radius, but probably single root
cause).

### RESOLVED since C.1 — strike from scope

- **PR22 / `flame_execute_python` (C.1 Cluster 5).** Already fixed by
  `bebf24a test(PR22): recognize flat required tool schemas`
  (the C.1 close named this exact fix path; it landed during A.2).
  `flame_execute_python` no longer appears in PR22 drift; the test
  recognizes flat-signature-with-required-field tools. Do NOT
  re-address.

## Fix-kind order (B-full, ratified by operator 2026-05-29)

1. **KIND 1 — ordering pollution** (7 tests). Find the shared-state
   culprit(s); cheapest, unblocks clean suite signal for the rest.
2. **KIND 2 — logic/source drift** (7 tests). `portofino` token
   (trivial) → CLI drift → timeline source-grep (needs behavior
   decision) → stdio cleanliness (investigate).
3. **KIND 3 — async-mock harness** (8 tests). One fixture fix,
   verify it radiates.

Each kind is its own commit cluster. Re-run full suite after each
kind; the goal is **24 → 0** (true CI-green, the C.1 seed's actual
intent), not partial.

## C.1 origin (archaeology — NOT the scope)

> Preserved verbatim-in-substance from the original seed. This is the
> record of how the debt was first surfaced. The 10-failure /
> 5-cluster inventory below is OBSOLETE as work scope (see § v1.8
> re-baseline); it is kept because it documents the discovery
> mechanism and the failure-shape-stability disposition that cleared
> C.1.

C.1's acceptance gate (full pytest suite passes) surfaced 10 failing
tests + 1 PR22 violation that pre-dated C.1, identity-matched between
pre-C.1 commit `32e8cfb` (with new test_asset_tools.py removed) and
post-C.1 commit `8ea4a40`. Per [[feedback-classify-don't-chase]]:
corpus-scope instruments surface archival imperfections that are not
regressions; classification determines disposition. C.1 shipped clean;
the debt was named for follow-on motion.

The original five clusters: (1) console-startup binding stdio
cleanliness; (2) CLI entrypoint bare-invocation + flag wiring; (3)
Flame timeline gap-fill segment tracking; (4) ping fixture / module-
state divergence (pass isolated, fail in suite); (5) PR22 mechanical
compliance for `flame_execute_python` (flat-signature pattern not in
PR22's A/B/C taxonomy — now resolved by `bebf24a`).

Architectural framing (still valid): per
[[feedback-decomposition-recomposition-validation-arc]], this is a
recomposition surface — the v1.7 acceptance-gate discipline made
previously-silent debt visible by running the corpus end-to-end. Per
[[feedback-failure-shape-stability-as-disposition-evidence]], the C.1
identity-match (10→10) cleared the C.1 disposition decisively. The
v1.8 re-baseline does NOT contradict that — C.1's 10 were stable
*at C.1*; the additional 14 accrued in the Thread-A/phase-4b/PR4
interval, which is exactly the drift [[feedback-baseline-drift-invalidates-controls]]
predicts and why contemporaneous re-verification was required before
scoping Thread B.

## Status

**ACTIVE — v1.8 Thread B (main reliability cleanup).** Re-baselined
inventory above is the work scope. B-reframe-first complete (this
rewrite); B-full proceeds in fix-kind order. Target: 24 → 0.
