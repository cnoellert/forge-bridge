---
name: SEED-TEST-CONTRACT-DRIFT-AUDIT-V1.6+
description: Audit pattern for tests that pass despite the contract they claim to lock having drifted underneath them. Multiple incidents observed across phases — locked-key tests asserting stale key sets, integration tests skipping silently when probes fail, CLI tests checking flags that no longer exist. Capture the pattern, design CI detection.
type: meta-process
planted_during: Phase A chat-contract realignment (2026-05-05) — surfaced when test_chat_parity_envelope_keys_locked was found asserting a 3-key envelope while the handler had been emitting 6 keys for months
trigger_when: a v1.6+ milestone has slack for tooling work OR a regression slips past test gates AND traces to a test that was passing despite the contract drifting OR CI runtime spend justifies investing in drift detection
---

# SEED-TEST-CONTRACT-DRIFT-AUDIT-V1.6+: tests passing despite contract drift

## Pattern Observed

Across multiple phases, tests have been found to pass while the contract they were nominally locking had silently drifted. Three recurring shapes:

1. **Stale-lock tests.** A test asserts `body.keys() == {a, b, c}` to "lock the envelope contract." The handler later grows additional keys. The test still passes because of how the assertion was written (e.g., subset checks that should have been exact-match), or because the test was never actually firing on the real code path, or because a fixture stripped the response to a subset before assertion.
   - **Phase A example:** `test_chat_parity_envelope_keys_locked` asserted exactly `{messages, stop_reason, request_id}` while the handler had been emitting `tools_available`, `tools_filtered`, `tool_enforced` since PR14/PR15. The test was already broken on pre-Phase-A main but the failure was not surfaced — `git stash && pytest` revealed it during Phase A's mock-update sweep.

2. **Silently-skipped integration tests.** Tests gated on a runtime probe (TCP port, env var, model availability) skip-not-fail when the probe fails. The skip count grows over time. Coverage erodes silently.
   - **v1.4.x example:** Per the user-memory record, 26 staged-tests were silently skipping due to a gated probe + asyncpg loop conflict — see memory `project_v1_4_x_harness_debt`.

3. **CLI/env mismatch tests.** A test invokes a CLI flag or asserts on env-var behavior that no longer matches the actual implementation. The test fails *only* on the dev's machine because of local env state, but passes in CI because CI scrubs env. Or vice versa.
   - **Phase A example:** `test_get_local_native_client_strips_v1_suffix_from_host` asserts `host == 'http://localhost:11434'` but fails locally when `FORGE_LOCAL_LLM_URL` points to assist-01. Pre-existing, surfaced incidentally during Phase A.
   - **Phase A example:** `test_console_port_flag_sets_env` asserts on `--console-port` flag that no longer exists. The Typer CLI has drifted and the test never caught it.

## Why This Matters

Tests that pass despite drift are worse than tests that don't exist. They give the merge process false confidence. The contract IS the test surface. When the test surface lies, downstream consumers (Ask dialog, schematic, external integrators) build on broken assumptions and break later, in production, with nothing in CI to point at.

The Phase A realignment was salvageable because the contract drift was small and the test surface was small enough to audit by hand. If the schematic's wire shape drifts the same way, debugging will be much harder — graph-rendering bugs are visual, not symptomatic.

## Scope (when this seed activates)

A bounded audit + tooling pass:

1. **Locked-key audit.** Find every test that locks an HTTP envelope or wire-contract key set. For each:
   - Verify the assertion matches the handler's actual response.
   - If using `set(body.keys()) >= {required_keys}` (subset), upgrade to `==` (exact).
   - Write a one-line manifest of every locked envelope and its asserting test, so future contract changes can grep + audit.

2. **Silent-skip audit.** Find every `pytest.skip` / `@pytest.mark.skipif` and classify:
   - **Runtime probe** (e.g., `if not _ollama_reachable(): skip`) — log the skip count over time so erosion is visible. Consider: when integration probes fail in CI, fail loudly instead of skipping silently.
   - **Env var** — make the env-var name a CI-required check.
   - **Optional dependency** — fine, but tag in pytest markers so suite reports separate "skipped because optional" from "skipped because broken."

3. **CLI/env reality check.** Run every CLI test in a clean env. Run again with the user's local env. Flag any that pass differently in the two — those are environment-coupled tests masquerading as contract tests.

4. **CI detection.** Add a CI job that periodically diffs handler response shapes against the locked-key tests' expectations. When they diverge, fail the job — even if the locked-key test itself still passes.

## Detection Strategies (research scope)

- **Snapshot testing for envelopes.** Tools like `pytest-snapshot` or hand-rolled JSON snapshots could lock the canonical response shape per route. Drift surfaces as a snapshot diff, not as a passing test that's actually broken.
- **Schema-driven validation.** Pydantic / msgspec models for response envelopes; tests assert `Model.model_validate(body)` works, fails on extra/missing keys.
- **Silent-skip rate alarm.** Compare "tests collected" vs "tests run" over the last N CI runs. A ratio that drops without explanation is the alarm.
- **Coverage-as-contract.** If a code path's coverage drops below a threshold, fail CI — the most reliable way to catch a test that USED to exercise a branch but now doesn't because of a fixture change.

## Boundaries

In scope (when this seed activates):
- Audit + remediation pass on the existing test suite.
- One CI signal that surfaces drift going forward (chosen from the strategies above).
- Documentation of the patterns + remediation for future contributors.

Out of scope:
- Rewriting the test suite into a different framework.
- Property-based / fuzz testing — orthogonal effort.
- Performance regression detection — different problem class.

## Why Plant Now

Phase A's hands-on test audit surfaced three concrete drift instances within a single sweep — strong signal that the pattern is widespread, not localized. The user explicitly named it as a "pattern observed across multiple incidents" worth capturing. Planting the seed now gives v1.6+ planning a concrete artifact to reference and prevents this from staying tribal-knowledge-only.

This is the kind of meta-tooling work that pays off slowly but compounds — every contract this catches is a production incident that didn't happen.
