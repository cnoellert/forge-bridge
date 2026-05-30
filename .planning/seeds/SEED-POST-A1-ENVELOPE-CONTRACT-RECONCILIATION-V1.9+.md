---
name: post-a1-envelope-contract-reconciliation
description: 8 tests assert the PRE-A.1 chat envelope ({messages, final_text, tool_trace}) while A.1 shipped the NEW envelope ({chain, stop_reason, request_id, tools_available, ..., preview}). Surfaced by v1.8 Thread B's KIND-3 harness fix, which removed the MagicMock-in-await obstruction and EXPOSED these as contract-evolution debt — not reliability debt. Reclassified OUT of Thread B; belongs to a v1.9/A-series contract-reconciliation arc with its own framing + acceptance criteria.
type: strategic-framing
planted_during: "v1.8 Thread B integration, 2026-05-29. The KIND-3 agent fixed the async-mock harness (mock_router.compile_intent = AsyncMock at 5 radiating fixture sites; commit 7e8cd75), which removed `TypeError: object MagicMock can't be used in 'await' expression`. Of 9 harness-blocked tests, 1 closed; the other 8 then failed on SUBSTANTIVE contract assertions against the obsolete pre-A.1 envelope. The agent correctly declined to chase them green ('Don't force a single-pattern explanation that doesn't fit') and surfaced them as a distinct class."
trigger_when: "v1.9 (or whenever the A-series / chat-contract surface is next opened for framing). These 8 are the regression surface for the post-A.1 chat envelope; they should be reconciled as part of any phase that touches chat-handler contract, arbitration, or chat parity — OR as a dedicated contract-reconciliation motion."
relates_to:
  - .planning/phases/A.1-thread-a-chat-intent-compile-stage/THREAD-A-CLOSE.md (the A.1 envelope change these tests pre-date)
  - .planning/seeds/SEED-MAIN-RELIABILITY-DEBT-V1.7+.md (Thread B parent; this is the KIND-4 reclassification)
---

# Seed — post-A.1 envelope contract reconciliation (v1.9+ A-series)

> **This is contract-evolution debt, not reliability debt.** v1.8 Thread
> B's job was to determine whether the chat/corpus test failures were
> infrastructure (harness) problems or real contract mismatches. The
> KIND-3 harness fix answered the question: once the
> `MagicMock-can't-await` obstruction was removed, 8 tests failed on
> their actual assertions because they encode the PRE-A.1 chat envelope.
> A.1 (Thread A, v1.7) changed that envelope. These tests are the
> regression surface for the change — they need rewriting against the
> new contract, which is design-bearing work with its own acceptance
> criteria, not a green-the-tests sweep. Thread B does NOT hold open on
> them.

## The contract change

**Pre-A.1 envelope (what these 8 tests assert):**
```
{ messages, final_text, tool_trace }
```
Arbitration routed through `complete_with_tools`; the verbatim-pass
contract and `call_count == 1` assertions were on that method.

**Post-A.1 envelope (what the handler now ships):**
```
{ chain, stop_reason, request_id, tools_available, ..., preview }
```
Arbitration now routes through `compile_intent` (compile-before-execute;
mutating chains emit a `preview` + `graph_intent_id`). The verbatim-pass
moved to `compile_intent`'s prompt arg.

## The 8 tests (the reconciliation surface)

```
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[disabled]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[enabled]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state[failing]
tests/corpus/test_pr4_chat_handler_integration.py::test_chat_handler_arbitration_invariant_under_capture_state_recovering[recovering]
tests/corpus/test_pr4_no_dependency.py::test_arbitration_completes_when_corpus_unavailable[single_step]
tests/integration/test_chat_endpoint.py::TestChatSanitizationE2E::test_handler_passes_messages_verbatim_to_router
tests/integration/test_chat_parity.py::TestChatParityStructural::test_chat_parity_browser_vs_flame_hooks
tests/integration/test_chat_parity.py::TestChatParityStructural::test_chat_parity_envelope_keys_locked
```

Per-test contract-drift shape (from Thread B integration analysis):

- **pr4 arbitration invariant (4 params).** `_assert_arbitration_invariance`
  helper requires `messages` in the response and asserts
  `complete_with_tools.call_count == 1`. Arbitration now routes through
  `compile_intent`, so both the key and the call-count target moved.
  The *invariant the test protects* (arbitration completes regardless of
  capture-state: disabled/enabled/failing/recovering) is still valid —
  it needs re-expressing against the new path, not deletion.
- **pr4 no-dependency (1).** Parametrized to expect
  `(messages, stop_reason, request_id)`; the `messages` key is gone. The
  underlying property (arbitration completes when `forge_bridge.corpus`
  is structurally absent — the no-dependency invariant) is STILL
  load-bearing and must be preserved through the rewrite. Do not weaken
  it to chase green.
- **chat_endpoint verbatim-pass (1).** The verbatim-pass contract was
  asserted on `complete_with_tools`; A.1 passes the prompt through
  `compile_intent`. Re-target the assertion to the new pass-through site;
  the sanitization-boundary property (handler does NOT re-sanitize;
  passes messages verbatim to the router) must survive.
- **chat_parity browser-vs-flame-hooks (1).** `KeyError: 'messages'` —
  parity is computed over the old envelope keys. Re-express over the new
  envelope; the parity property (same endpoint serves Web UI +
  projekt-forge Flame hooks with structurally identical responses) is
  the thing being protected.
- **chat_parity envelope-keys-locked (1).** Per its own docstring, this
  test is DESIGNED to fire when the envelope changes — it is an
  intentional sentinel. Its firing is CORRECT behavior. The work is to
  re-lock it to the post-A.1 key set (the new locked contract), making
  it the regression guard for the NEW envelope.

## What this seed does NOT do

- It does not rewrite the tests. Each rewrite is design-bearing — it
  must preserve the *property* each test protects (arbitration
  invariance, no-corpus-dependency, verbatim sanitization pass, parity,
  envelope-lock) while re-expressing it against the post-A.1 contract.
  That is framing-grade work, not a mechanical sweep.
- It does not weaken any assertion to reach green. The envelope-keys
  sentinel especially must be RE-LOCKED, not loosened.
- It does not block v1.8. Thread B is closed; these 8 are a known,
  named, classified residual carried forward intentionally per
  [[feedback-explicitly-unbound-vs-implicitly-rejected]].

## Status

**Parked as forward-pressure for v1.9 / A-series.** The 8 tests are a
stable, fully-classified failure surface on main (full suite: 8 failed,
2620 passed, 41 skipped at the v1.8 Thread B merge). They assert an
obsolete contract; A.1 is the authority on the new one. Promotes to an
active reconciliation phase when the chat-contract surface is next
framed, or as a dedicated motion.
