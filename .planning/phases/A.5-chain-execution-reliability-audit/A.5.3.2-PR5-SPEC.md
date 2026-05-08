# A.5.3.2 PR 5 — Spec (chain-step integration)

**Status:** drafted 2026-05-08 (post-PR-4-close session). Derived
from `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`). The framing is
the binding pre-spec contract; this spec is the implementation
contract derived from it.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1); architecturally prohibited
  patterns (§5.3).
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology + identity.
- `A.5.3.2 PR 3` (commit `a9e3e47`) — capture builder + writer +
  reader.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; four risks; integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration contract; allowlist mechanism (§4.2);
  participation-creep grep (§4.3); capture-state-cycling fixture
  (§5).
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherits. **Mandatory predecessor read.**
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — risk profile
  inherited from PR 4; surface geometry asymmetry; three §4.7
  open questions resolved (caller-owned identity, ambiguity
  rejection captured, latency budget unchanged).

**Successor (NOT this spec):** PR 6 (visual-asymmetry executable
lint backstop). PR 6 inherits the two operational call sites
(handlers.py + _step.py) as the input set for crystallizing the
canonical pattern into executable lint.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Eleven carrier sentences travel verbatim into:

1. The chain-step integration site's adjacent comment block at
   `forge_bridge/console/_step.py::execute_chain_step`.
2. The PR 5 commit message body.
3. (Where applicable) the new test file's module docstring.

Seven inherit verbatim from PR 4 (CLOSE §1.5); four are additive
PR 5 carriers introduced by this framing.

**Inherited from PR 4 — risk-category shift (verbatim):**

> **PR 4 is the controlled introduction of observational
> side-effects into live arbitration surfaces.**

> **The risk category has shifted from persistence-substrate risk
> to participation-creep risk.**

**Inherited from PR 4 — integration-discipline quartet (verbatim):**

> **The call site is the source of the three explicit inputs.**
>
> **The integration layer passes truth.**
>
> **The integration layer never reconstructs truth.**
>
> **The builder does not discover runtime state.**

**Inherited from PR 4 — finalized-state contract (verbatim):**

> **Capture emission occurs only after arbitration state is
> finalized for the current execution path. Capture records
> completed arbitration observations, not provisional intermediate
> state.**

**Additive — PR 5 second-call-site framing (§0 of framing):**

> **PR 5 is the second call site under the integration discipline
> PR 4 established. The risk profile is inherited; the surface
> geometry is not.**

**Additive — PR 5 caller-owned deployment identity (§0 + §2.1 of
framing):**

> **The chain-step's deployment identity is the caller's view, not
> the global daemon registry view.**

**Additive — PR 5 ambiguity rejection + verbatim list discipline
(§2.2 of framing):**

> **Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths. `pr20_condition_met`
> is always False and `collapse_occurred` is False on all
> rejection paths. These semantics differ from the chat-handler
> case and must not be silently overloaded.**

**Additive — PR 5 measured-not-inferred no-dependency coverage
(§5 of framing):**

> **No-dependency coverage at the chain-step surface must be
> measured, not inferred. The existing probe drives only the
> chat-handler single-step path; PR 5 owns the responsibility to
> extend coverage to the chain-step path empirically.**

A reader who encounters PR 5's call-site code without reading the
full spec should encounter these sentences first. The seven PR 4
carriers establish the integration discipline; the four PR 5
carriers establish the surface geometry asymmetry. Neither set
substitutes for the other.

---

## 1. Real job + success condition

**Real job:** *"Pass the four authoritative truth surfaces from
the chain-step call site through to capture emission while
preserving arbitration invariance under all four capture states.
Per-step emission; per-chain-invocation deployment identity
stability. Ambiguity rejection captures truthfully without
overloading chat-handler field semantics."*

The four surfaces at this site (analogous to PR 4's four; CLOSE
§3.1 maps the structural differences):

- **Deployment identity** (`registered_tools` field) — the caller-
  passed `tools` parameter. Per framing §2.1: caller's view, not
  the global daemon registry view. Stable across the steps of one
  chain invocation; cross-chain variance is the caller's identity
  definition, not the chain step's.
- **Runtime topology** (`candidate_set_post_reachability` field) —
  same caller-passed `tools` parameter. **Collapses with
  deployment identity at this surface** (CLOSE §3.1) — there is
  no reachability filter at the chain-step site; that filter ran
  upstream in `handlers.py`.
- **Arbitration input** (`candidate_set_post_pr14` field) — post-
  message-filter set, captured after `filter_tools_by_message`
  but before `deterministic_narrow`.
- **Arbitration output** (`narrower_decision` + `pr20_condition_met`
  + `collapse_occurred` + `ambiguity_state` + `narrower_latency_ms`)
  — final arbitration state at the moment narrowing concludes,
  per the §2.2 chain-step semantics table (success path: single-
  match list; rejection paths: zero-match `[]` or multi-match list
  verbatim).

**Success condition:** *"With `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`,
the chain-step executor emits one Layer 1 record per chain step
(N steps → N records, all sharing the same
`registered_tools_snapshot_hash`). With the gate disabled (or
capture failing), `execute_chain_step`'s externally observable
behavior is byte-identical to pre-PR-5. Operator-visible behavior
of multi-step chains is unchanged regardless of capture state."*

**Per-step emission discipline (binding):** capture fires once per
`execute_chain_step` invocation, NOT once per `run_chain_steps`
invocation. Multi-step chains produce N records; each record's
deployment identity hash is identical (the caller threads the same
`tools` list through every step), but the per-step arbitration
inputs and outputs vary. There is no aggregate per-chain capture;
there is no "summary record" emitted at chain close. Each step's
arbitration is its own observed event.

---

## 2. Scope

**In scope:**

- **Chain-step call site** — `forge_bridge/console/_step.py::
  execute_chain_step` narrowing path. Surface the four
  authoritative inputs as named snapshots; add narrower-latency
  instrumentation; insert one capture invocation at the unified
  post-narrowing-finalization point (BEFORE the `if len(filtered)
  != 1` rejection branch) per the §5.1 visual-asymmetry pattern.
- **Shape A topology** at `_step.py` module load — guarded import
  (`try / except ImportError`) with fallback bindings, mirroring
  `handlers.py`'s import shape (PR 5 framing §1 + CLOSE §3.4 →
  option (a) committed).
- **Allowlist extension** — `console/_step.py` joins
  `console/handlers.py` in
  `tests/corpus/test_pr3_discipline.py::_ALLOWLIST`. One-line
  tuple growth.
- **Participation-creep grep verification** — the existing
  `test_pr4_participation_creep.py` ALREADY walks `_step.py`
  (PR 4 wrote it forward-narrowing per spec §4.3). PR 5's work at
  this surface is **verification-only**: the test continues to
  bite correctly when `_step.py` lands its emission imports,
  because the emission targets are in `_PERMITTED_CORPUS_IMPORTS`.
  No test code change required; spec §4.3 surfaces the
  operational reality.
- **No-dependency coverage extension** — extend
  `test_pr4_no_dependency.py` to drive a multi-step chain prompt
  under the corpus-sentinel patch (path 1 from framing §5,
  preferred). Path 2 (sibling test file) is the explicit fallback
  if path 1 surfaces concrete in-test friction during incarnation.
- **Integration test bundle** —
  `tests/corpus/test_pr5_chain_step_integration.py` shipping the
  four-state arbitration-invariance probe (parametrized over
  `disabled / enabled / failing / recovering`) + dedicated
  recovering test + dedicated latency-delta test. Five tests
  total per CLOSE §3.5.
- **Helper extension** — `tests/corpus/_pr4_helpers.py`
  (canonically renamed in spirit but not in path; see §6.1
  decision) adds `_drive_chain_request` analogous to
  `_drive_chat_request` and a chain-envelope variant of
  `_assert_arbitration_invariance` /
  `_assert_arbitration_response_equivalent`.

**Out of scope (deferred per framing):**

- **Visual-asymmetry executable lint** → PR 6 (locked per framing
  §6 + PR 4 framing §1.1; both rationales documented there). PR 5
  ships the second operational call site that PR 6 will use as
  input.
- **Stray-header-mid-file warning sharpness** → PR 6 polish or
  v1.5.x patch (PR 4 framing §4.2).
- **Comparator** → Gate 4.
- **Schema bump** → PR 5 framing §7 explicitly forbids. The chain-
  step surface ships under v1 unchanged. Field semantics are
  documented at the call sites, not encoded as a schema variant.
- **Refactoring `handlers.py` to eliminate destructive `tools = ...`
  rebinds** → out of scope here; PR 5 does not touch
  `handlers.py`'s integration site (which already shipped at PR 4
  step 6).
- **Adding a fifth `capture_state_cycling` state** → PR 5 framing
  §1 explicitly forbids. The fixture is closed for extension at
  the spec layer.

If the spec begins drifting toward "while we're here, let's also
refactor X" or "this would be a good time to lint Y," **stop and
re-scope.** The framing's risk-profile-inherited articulation
depends on PR 5 staying focused on the four risks at the new
surface geometry.

---

## 3. The four risks → named tests

| # | Risk | Named test (this PR) |
|---|------|---------------------|
| **1.1** | Visual-asymmetry preservation at the call site | Code-review-only check (per PR 4 framing §1.1, executable lint deferred to PR 6). PR 5 ships no test for 1.1; reviewers verify the §5.1 visual pattern at `_step.py`'s narrowing-finalization boundary directly. PR 6 will use both call sites (handlers.py + _step.py) as input for lint design. |
| **1.2** | Capture-call-site state coupling — arbitration invariance | `test_chain_step_arbitration_invariant_under_capture_state[<state>]` — parametrized over the four states from `capture_state_cycling` (enabled / disabled / failing / recovering). Asserts arbitration-equivalent envelope and bounded latency delta per state. **PR 4's single most important invariant** carries forward unchanged at the new surface. |
| **1.3** | Arbitration-decision feedback through capture (participation creep) | `test_narrowing_subsystem_imports_zero_corpus_modules_except_capture` (existing) continues to bite. **No new test code; verification only.** PR 5's `_step.py` emission imports are in `_PERMITTED_CORPUS_IMPORTS`, so the test passes. Bite-verification: a contributor adding `from forge_bridge.corpus.reader import ...` to `_step.py` would cause the test to fail. |
| **1.4** | Observational side-effects vs observational dependencies | `test_arbitration_completes_when_corpus_unavailable` extended (path 1, preferred) or sibling `test_pr5_chain_no_dependency.py` added (path 2, fallback). Drives a multi-step chain prompt under the corpus-sentinel patch; asserts the chain completes successfully (well-formed envelope, no exception, latency within budget). **Measured, not inferred** per framing §5. |

Plus the PR 3/PR 4 discipline-grep test continues in allowlist
mode with `console/_step.py` added (§4.2 below).

---

## 4. Module surface

### 4.1 Chain-step call site (`_step.py::execute_chain_step`)

**Implementation approach: caller-owned `tools` as deployment
identity; named snapshots at narrowing-finalization; single
unified capture invocation BEFORE the rejection branch.**

Per framing §2.1, the inbound `tools` parameter IS this surface's
deployment identity. There is no separate `mcp.list_tools()` fetch
at this surface. Per framing §2.2, capture fires at
narrowing-finalization regardless of success/rejection — the
guard `if len(filtered) != 1` is downstream of the capture call.

**The four snapshot points:**

| Snapshot | Captured at | Source |
|---|---|---|
| `registered_tools` | At function entry, BEFORE any local rebinds | The inbound `tools` parameter; caller's view. Per framing §2.1: "deployment identity is the caller's view, not the global daemon registry view." |
| `tools_post_reachability` | Same as `registered_tools` (collapses) | No reachability filter at this surface; the chat handler's upstream filter already ran. CLOSE §3.1 names this collapse explicitly. |
| `tools_post_pr14` | After `filtered = filter_tools_by_message(tools, step_text)` (existing line 85) | Arbitration input |
| Final narrowing state | After the `if len(filtered) > 1: ...` block (existing lines 86-89), where `filtered` holds the post-deterministic-narrow result | Arbitration output |

**Latency instrumentation:**

A new `narrower_started = time.perf_counter()` lands immediately
before line 85 (`filtered = filter_tools_by_message(...)`). The
`narrower_latency_ms = (time.perf_counter() - narrower_started) *
1000.0` measurement lands after the `if len(filtered) > 1` block
and before the capture invocation.

The latency measurement happens **regardless of
`divergence_capture_enabled()`** — measurement is part of the
arbitration path, not the capture path. Same structural protection
as PR 4 §4.1: a later "let's only measure when capturing"
simplification would couple arbitration timing to capture state
and weaken the §1.4 no-dependency property.

**Module-load topology (Shape A — option (a)):**

`_step.py` adds a guarded import block at module top, mirroring
`handlers.py`'s shape (handlers.py:90-115):

```python
try:
    from forge_bridge.corpus import (
        divergence_capture_enabled,
        emit_divergence_capture,
    )
except ImportError as _corpus_import_error:
    # Direct getLogger call: this branch executes during module-
    # load-time topology resolution before the module-level logger
    # binding below exists. Same rationale as handlers.py:99-101.
    logging.getLogger(__name__).warning(
        "forge_bridge.corpus is structurally absent at _step load; "
        "divergence-capture disabled for this process lifetime. "
        "(Import-time observation, distinct from "
        "FORGE_BRIDGE_DIVERGENCE_CAPTURE env-driven gating.) "
        "import_error=%s",
        _corpus_import_error,
    )

    def divergence_capture_enabled(*_args, **_kwargs) -> bool:
        return False

    def emit_divergence_capture(*_args, **_kwargs) -> None:
        pass
```

`_step.py` does not currently import `logging` or `time` at module
top (check: imports are `from __future__ import annotations`,
`json`, `typing.Any`, and `forge_bridge.console._tool_filter`).
PR 5 adds **both** at module top, and they are required and
distinct:

- `import logging` — for the module-load-time WARNING in the
  ImportError fallback branch of the Shape A topology block above
  (the `logging.getLogger(__name__).warning(...)` call); and for
  the module-level `logger = logging.getLogger(__name__)` binding
  added alongside (mirroring handlers.py:117). `_step.py` has no
  existing module-level logger binding today; one lands as part
  of step 6.
- `import time` — for the `time.perf_counter()` calls in the
  narrower-latency instrumentation (§4.1 above). The latency
  measurement runs regardless of capture state, so the import is
  not optional or guarded.

Naming both explicitly so the spec reader does not assume one
covers the other.

**The capture call site (the §5.1 visual-asymmetry pattern):**

The capture invocation lands at the **unified post-narrowing-
finalization point** — after the `if len(filtered) > 1:` block
(line 89 in current code) and BEFORE the `if len(filtered) != 1:`
rejection branch (line 90). This single insertion point fires for
all three narrowing outcomes (single-match success, multi-match
rejection, zero-match rejection) because narrowing has finalized
at this point regardless of which downstream path takes over.

**Architectural property — capture is arbitration-aware, not
branch-aware (binding):** the single insertion point preserves
capture's relationship to the arbitration event itself, not to
its downstream semantic interpretations. Two insertion points
(one in the success branch, one in the rejection branch) would
make capture observe two downstream interpretations of finalized
state rather than the finalized state itself. Arbitration finishes
once; capture observes once; what happens *to* the finalized
state downstream is the consumer's interpretation, not the
observer's responsibility. This framing carries forward into the
PR 5 commit message body alongside the visual-asymmetry rationale.

**Subsequent failure paths (e.g., MULTIPLE_PROJECTS) do not
re-trigger capture:** capture has already emitted at narrowing-
finalization. The `MULTIPLE_PROJECTS` envelope returned from the
DISAMBIGUATION_KEY branch (lines 106-120 of the current code)
executes after capture has recorded the truthful single-tool
narrowing result. The capture record reflects what the narrower
*decided*; subsequent params-resolution failure is a separate
event the capture record does not need to encode. This closes the
"what about MULTIPLE_PROJECTS?" gap without special-casing it at
the call site.

```python
async def execute_chain_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
) -> dict:
    """Run a single chain step end-to-end.

    [existing docstring continues unchanged]
    """
    from forge_bridge.console._chain_parse import extract_chain_context
    from forge_bridge.console._name_resolve import resolve_name_from_candidates
    from forge_bridge.console._param_extract import extract_explicit_params
    from forge_bridge.console._tool_chain import (
        DISAMBIGUATION_KEY,
        resolve_required_params,
    )

    # PR 5 §4.1 — deployment identity snapshot. Per framing §2.1:
    # the chain-step's deployment identity is the caller's view,
    # not the global daemon registry view. The inbound `tools`
    # parameter IS this surface's deployment identity. Cross-chain
    # variance is the caller's identity definition, not the
    # chain step's.
    registered_tools = tools

    # PR 5 §4.1 — runtime topology snapshot collapses with
    # deployment identity at this surface. There is no
    # reachability filter here; that filter ran upstream in
    # handlers.py. Per A.5.3.2-PR4-CLOSE.md §3.1, this collapse
    # is a real semantic difference between the two call sites
    # and is surfaced explicitly rather than silently overloaded.
    tools_post_reachability = tools

    user_params = extract_explicit_params(step_text)

    merged: dict = {**(inherited_context or {}), **user_params}
    requested_name = merged.get("project_name")
    resolver_input = {k: v for k, v in merged.items() if k != "project_name"}

    # PR 5 §4.1 — narrower-latency instrumentation. Measurement
    # happens regardless of divergence_capture_enabled() per spec:
    # latency belongs to the arbitration path, not the capture
    # path. Decoupling protects against a later "let's only
    # measure when capturing" simplification that would couple
    # arbitration timing to capture state.
    narrower_started = time.perf_counter()
    filtered = filter_tools_by_message(tools, step_text)

    # PR 5 §4.1 — arbitration-input snapshot. Captures the
    # post-PR14 set BEFORE deterministic_narrow has a chance to
    # collapse it. Used by collapse_occurred derivation.
    tools_post_pr14 = filtered

    if len(filtered) > 1:
        narrowed = deterministic_narrow(filtered, step_text)
        if len(narrowed) < len(filtered):
            filtered = narrowed
    narrower_latency_ms = (time.perf_counter() - narrower_started) * 1000.0

    # ── Capture is emitted after arbitration decisions are finalized
    #    and must not structurally participate in the arbitration
    #    pipeline. (PR 3 spec §0; PR 4 framing §0.)
    #
    #    PR 4 is the controlled introduction of observational
    #    side-effects into live arbitration surfaces. The risk
    #    category has shifted from persistence-substrate risk to
    #    participation-creep risk. (PR 4 framing §0.)
    #
    #    The call site is the source of the three explicit inputs.
    #    The integration layer passes truth. The integration layer
    #    never reconstructs truth. The builder does not discover
    #    runtime state. (PR 4 framing §3.)
    #
    #    Capture emission occurs only after arbitration state is
    #    finalized for the current execution path. Capture records
    #    completed arbitration observations, not provisional
    #    intermediate state. (PR 4 spec §0.)
    #
    #    PR 5 is the second call site under the integration
    #    discipline PR 4 established. The risk profile is
    #    inherited; the surface geometry is not. (PR 5 framing §0.)
    #
    #    The chain-step's deployment identity is the caller's
    #    view, not the global daemon registry view. (PR 5
    #    framing §0 + §2.1.)
    #
    #    Ambiguity rejection is an arbitration outcome. Capture
    #    must record it. At this surface, narrower_decision
    #    carries the filtered list verbatim at narrowing
    #    finalization — including zero-match and multi-match
    #    rejection paths. pr20_condition_met is always False and
    #    collapse_occurred is False on all rejection paths. These
    #    semantics differ from the chat-handler case and must not
    #    be silently overloaded. (PR 5 framing §2.2.)

    if divergence_capture_enabled():
        emit_divergence_capture(
            prompt=step_text,
            registered_tools=registered_tools,
            candidate_set_post_reachability=tools_post_reachability,
            candidate_set_post_pr14=tools_post_pr14,
            narrower_decision=filtered,
            pr20_condition_met=False,
            collapse_occurred=(
                len(filtered) == 1 and len(tools_post_pr14) > 1
            ),
            ambiguity_state=_ambiguity_state_for_chain_step(len(filtered)),
            narrower_latency_ms=narrower_latency_ms,
            source="runtime",
        )

    if len(filtered) != 1:
        return {"error": {
            "type": "tool_selection_ambiguous",
            "message": (
                f"Step matched {len(filtered)} tools; chain steps must "
                "select exactly one. Use a more specific verb/noun "
                "(e.g. 'list versions' instead of just 'list')."
            ),
            "candidates": [
                getattr(t, "name", str(t)) for t in filtered[:5]
            ],
        }}
    tool_name = filtered[0].name

    # [rest of function unchanged from current implementation]
```

**Pattern requirements (binding per Gate 1 §5.1, framing §1.1):**

- The blank line + comment block + explicit `if
  divergence_capture_enabled():` guard are part of the contract,
  not stylistic preference.
- Capture happens AFTER `filtered` has been bound to its final
  narrowed value and `narrower_latency_ms` has been measured.
- Capture happens BEFORE the `if len(filtered) != 1:` rejection
  branch. **One insertion point covers all three narrowing
  outcomes** — single-match success, zero-match rejection,
  multi-match rejection.
- The `if divergence_capture_enabled():` guard is at the call
  site, NOT inside `emit_divergence_capture`. Same visual-
  asymmetry discipline as PR 4.

**Field-derivation semantics (binding — chain-step variant per
framing §2.2):**

| Field | Value | Rationale |
|---|---|---|
| `registered_tools` | inbound `tools` parameter | Caller's view; framing §2.1 |
| `candidate_set_post_reachability` | inbound `tools` parameter | Collapses with `registered_tools`; framing §2.1 + CLOSE §3.1 |
| `candidate_set_post_pr14` | post-message-filter `filtered` | Arbitration input; before deterministic_narrow |
| `narrower_decision` | post-narrow `filtered` | **Filtered list verbatim at narrowing finalization.** `[]` on zero-match rejection, `[a, b, …]` on multi-match rejection, `[a]` on single-match success. No empty-list suppression, no sentinel, no semantic overloading. |
| `pr20_condition_met` | hardcoded `False` | **Always False at this surface** — there is no LLM fall-through path here, so the PR20 short-circuit semantics do not apply. Framing §2.2 lock. |
| `collapse_occurred` | `len(filtered) == 1 and len(tools_post_pr14) > 1` | True only on the multi-to-single success path. **False on all rejection paths** (zero-match-to-error and multi-match-to-error). Framing §2.2 lock. |
| `ambiguity_state` | `_ambiguity_state_for_chain_step(len(filtered))` | Translation helper; produces `zero_survivor` / `single_survivor` / `multi_survivor` per the PR 4 spec §4.1 constraint (deterministic, one-line, no inferential logic). |
| `narrower_latency_ms` | measured per perf_counter | Per-step latency; per-emission budget per framing §2.3 |
| `prompt` | `step_text` | The step's input text (the chain-parsed segment) |
| `source` | `"runtime"` | Per PR 3 schema |

**`_ambiguity_state_for_chain_step` helper:**

```python
def _ambiguity_state_for_chain_step(n: int) -> str:
    """Translate narrowing-count to the schema's ``ambiguity_state``
    string at the chain-step surface. Translation-only; no
    inferential logic per the binding constraint in
    ``A.5.3.2-PR4-SPEC.md`` §4.1.

    Mirrors handlers.py::_ambiguity_state_for; the helpers are not
    deduplicated because the chat-handler and chain-step views of
    `ambiguity_state` are orthogonal authority surfaces (PR 5
    framing §2.2 architectural protection bullet 3) and conflating
    them via shared helper extraction would introduce a hidden
    cross-site coupling that schema-validation shortcuts could
    later exploit. Same translation behavior; independent surface.
    """
    return {0: "zero_survivor", 1: "single_survivor"}.get(n, "multi_survivor")
```

**Helper-duplication rationale (binding):** the chat handler's
`_ambiguity_state_for` and `_step.py`'s
`_ambiguity_state_for_chain_step` produce identical output for
identical input. They are not deduplicated into a shared module
helper deliberately. Per the orthogonal-truth-surfaces discipline
(PR 3 §5; framing §2.2 protection bullet 3), the two call sites'
field-semantics surfaces are orthogonal — extracting a shared
helper would create a hidden coupling vector that future
"harmonization" PRs could exploit to silently overload field
semantics across sites. The duplication is the protection. A
future PR proposing to extract the shared helper is rejected at
the spec layer.

### 4.2 Allowlist extension

`tests/corpus/test_pr3_discipline.py::_ALLOWLIST` grows from one
entry to two:

```python
_ALLOWLIST: tuple[str, ...] = (
    "console/handlers.py",
    "console/_step.py",
)
```

One-line tuple growth. Per PR 4 spec §4.2's forward-extension
clause: "PR 5 adds `console/_step.py` as the second allowlisted
entry." Spec amendment requirement: this spec is the amendment.

The discipline-grep test's failure-message contract (PR 4 spec
§4.2) does not change shape — the failure message naturally
expands to name both allowlisted entries when listing the current
allowlist.

### 4.3 Participation-creep grep — verification only

`tests/corpus/test_pr4_participation_creep.py` ALREADY walks
`forge_bridge/console/_step.py` (PR 4 spec §4.3 wrote it
forward-narrowing in anticipation of PR 5). The test's
`_NARROWING_SUBSYSTEM` tuple already contains:

```python
_NARROWING_SUBSYSTEM: tuple[str, ...] = (
    "console/_tool_filter.py",
    "console/_step.py",
)
```

**No code change to the test in PR 5.** The framing §4 language
"PR 5 step 3 extends the test to cover the chain-step surface"
operates at the level of *effective coverage* (the test was
prophetic before PR 5 landed `_step.py`'s emission imports;
post-PR-5 the `_step.py` row is exercised, not just declared).
At the *implementation* level, no test code is modified.

**What PR 5 step 3 actually does:**

1. **Verify the existing test continues to bite correctly** after
   step 6 lands `_step.py`'s emission imports. The emission
   targets (`_capture` / `divergence_capture_enabled` /
   `emit_divergence_capture`) are already in
   `_PERMITTED_CORPUS_IMPORTS`, so the test passes.
2. **Optional docstring polish** — if any forward-narrowing
   "future" tense remains in the test's docstring that no longer
   applies after PR 5 lands, replace with present tense. The
   existing docstring's "future corpus modules" language refers
   to Gate 4 surfaces and remains appropriate; no change required
   unless review surfaces friction.
3. **Run the test before and after step 6** to confirm the bite
   profile: pre-step-6 the test passes trivially (no `_step.py`
   imports of corpus); post-step-6 the test passes because the
   emission imports are permitted; bite-verification for the
   protected property is exercised by mutating step 6's import
   to a forbidden corpus surface (e.g., `from
   forge_bridge.corpus.reader import read_capture_file`) and
   confirming the test fires.

This step is **verification, not extension** at the code level.
Surfacing the distinction explicitly so the spec reader does not
go looking for a code change in the participation-creep test that
does not exist.

---

## 5. The capture-state-cycling fixture (reuse — closed for extension)

`tests/corpus/_pr4_helpers.py::capture_state_cycling` ships
unchanged from PR 4. PR 5 reuses the fixture without modification:

| State | Mechanism | What this exercises |
|---|---|---|
| `disabled` | env var unset; corpus dir does not exist | Zero capture path; pre-PR-5 baseline behavior |
| `enabled` | env var = `"1"`; corpus dir is tmp_path; corpus package healthy | Successful-capture path |
| `failing` | env var = `"1"`; `Path.open` mocked to raise `OSError` | I-6 failure-invisibility at integration level |
| `recovering` | env var = `"1"`; first capture attempt fails (mock raises once), subsequent capture succeeds | Inter-call state independence |

**The fixture is closed for extension at the spec layer.** PR 5
must NOT add a fifth state. Per PR 4 framing §1.2 + PR 5 framing
§1: adding states (e.g., `permission_denied`, `partial_write`,
`disk_full`) would duplicate PR 3's I-6 unit-level coverage at the
integration level without adding new architectural invariants.
Removing any of the four loses a distinct property.

The fixture's `(state, corpus_dir)` yield tuple, scoped-failing-
open mechanism, and indirect-parametrization API all carry
unchanged.

---

## 6. Integration test plan

All new tests live under `tests/corpus/`. The chain-step end-to-
end fixture machinery composes against existing helpers in
`tests/corpus/_pr4_helpers.py` plus PR-5-specific additions named
below.

### 6.1 New test file

**`tests/corpus/test_pr5_chain_step_integration.py`** — the
arbitration-invariance test bundle for the chain-step surface.

Five tests total per CLOSE §3.5, mirroring PR 4's geometry:

1. **`test_chain_step_arbitration_invariant_under_capture_state[disabled]`**
2. **`test_chain_step_arbitration_invariant_under_capture_state[enabled]`**
3. **`test_chain_step_arbitration_invariant_under_capture_state[failing]`**
4. **`test_chain_step_recovering`** — dedicated test, not parametrized.
   Three-block geometry inherited from PR 4 (visible duplication
   of request #1 / request #2 preserved). Per PR 4 CLOSE §5.3:
   "the recovering state is qualitatively different from the
   other three (temporal contamination probe vs. nominal
   correctness), so its test function is qualitatively different
   (three-block vs. two-block, two invocations vs. one)."
5. **`test_chain_step_capture_latency_within_budget`** — dedicated
   latency test. Min-of-N timing comparison between `disabled`
   and `enabled` states. **Target < 5ms; hard ceiling < 20ms**
   per framing §2.3. Exceeding the target triggers investigation,
   NOT threshold adjustment.

**Test geometry per state (parametrized + recovering):**

Each parametrized test drives a chain request through the chain-
step executor (NOT through the chat handler — direct
`execute_chain_step` invocation OR via `run_chain_steps`, decision
at incarnation per CLOSE §3.5) and asserts:

- The chain-step return envelope's structure is arbitration-
  equivalent across all four states (per
  `_assert_arbitration_response_equivalent_chain` — chain-envelope
  variant of PR 4's helper, see §6.2 below).
- The return envelope shape matches the success path
  (`{"result": ..., "extracted_context": ..., "tool": ...,
  "params": ...}`) on single-match success, OR the rejection
  envelope (`{"error": {"type": "tool_selection_ambiguous", ...}}`)
  on multi-match/zero-match rejection — depending on the test
  prompt.
- The latency delta between `enabled` and `disabled` is bounded:
  **target < 5ms; hard ceiling < 20ms.**
- For `enabled`: exactly one Layer 1 record was written per
  `execute_chain_step` invocation; the record's
  `narrower_decision` matches the actual `filtered` list at
  emission time; the record's `registered_tools_snapshot_hash`
  matches the caller-passed `tools` list's hash;
  `pr20_condition_met` is always False on disk; `collapse_occurred`
  matches the multi-to-single success-path predicate.
- For `failing`: zero records on disk; one WARNING logged per
  emission attempt; chain-step return envelope identical to
  `disabled` modulo expected differences.
- For `recovering`: across two arbitration invocations, exactly
  one record on disk (the second attempt's record); no on-disk
  residue from the first attempt's failure.

**Coverage of both success and rejection paths (binding):**

The spec requires at least one enabled-state integration assertion
to exercise the multi-match rejection path empirically. Preferred
shape: parametrize the enabled-state integration test over
`[single_match, multi_match]`. Fallback: introduce a sixth
dedicated rejection-path test only if the parametrized form
materially weakens the visible two-block geometry.

This locks the architectural requirement (rejection-path
empirical bite-verification) while preserving incarnation
flexibility on the mechanism. Without this assertion, the silent-
overload failure mode described in framing §2.2 is not bite-
verified empirically — the schema-field-semantics table would
remain a documentation claim rather than a tested invariant.

### 6.2 Helper extensions (`_pr4_helpers.py`)

**Decision: extend `_pr4_helpers.py` in place; do not rename.**

The file's name encodes its history (PR 4 introduction), not its
ownership. Per CLOSE §3.5: "The construction-helper analog
`_drive_chain_request` (or equivalent) lives in `_pr4_helpers.py`
(rename to `_pr_helpers.py`?) or in a new `_pr5_helpers.py`.
Decision deferred to PR 5 framing." This spec resolves: extend
`_pr4_helpers.py`. Rationale: rename creates churn across import
sites for zero architectural gain; a new `_pr5_helpers.py` would
fragment the shared infrastructure across two files for the same
zero gain. The file's docstring is updated to acknowledge the
shared infrastructure spans PR 4 + PR 5.

**Additions:**

- **`_drive_chain_request(*, tools_list=None, prompt=...)`** —
  analogous to `_drive_chat_request`. Drives a chain request
  through `execute_chain_step` (or `run_chain_steps`, decision at
  incarnation) under the same TestClient-style construction
  pattern. Returns `(envelope, mcp_mock)` — the chain envelope
  and the mock used to capture `mcp.call_tool` invocations.
- **`_assert_chain_step_arbitration_invariance(envelope, ...,
  expected_tool_names)`** — chain-envelope variant of
  `_assert_arbitration_invariance`. Asserts the chain return shape
  (success-path or rejection-path), the tool selection, and the
  arbitration-output upstream of LLM stochasticity (which does
  not apply at this surface — chain-step is fully deterministic
  post-narrowing).
- **`_assert_chain_step_arbitration_response_equivalent(env_a,
  env_b)`** — chain-envelope variant of
  `_assert_arbitration_response_equivalent`. The IS-compared /
  IS-ignored boundary differs from PR 4's chat-envelope variant
  per CLOSE §3.5 ("chain steps return `{"result": ..., "tool":
  ..., "params": ...}` on success, not `{"messages": [...],
  "stop_reason": ..., "request_id": ...}`"). Helper docstring
  re-derives the boundary.

The PR 4 helpers (`_make_test_tool`, `_passthrough_filter`,
`_stub_chat_result`, `capture_state_cycling`,
`_scoped_failing_open`, `_read_records`,
`_assert_no_failed_write_residue`,
`_assert_authority_surface_invariance`) are reused without
modification.

### 6.3 No-dependency test extension (path 1, preferred)

`tests/corpus/test_pr4_no_dependency.py::
test_arbitration_completes_when_corpus_unavailable` is
parametrized over `[single_step_prompt, multi_step_chain_prompt]`:

```python
@pytest.mark.parametrize(
    "prompt",
    [
        "hi",  # single-step path; existing PR 4 coverage unchanged
        "list projects -> list shots",  # multi-step path; PR 5 coverage
    ],
    ids=["single_step", "multi_step_chain"],
)
def test_arbitration_completes_when_corpus_unavailable(
    monkeypatch, tmp_path, prompt,
):
    # ... existing test body, prompt parameterized ...
```

Both prompts must complete successfully under the corpus-sentinel
patch. The multi-step prompt drives `_execute_chain →
run_chain_steps → execute_chain_step` end-to-end, exercising
`_step.py`'s Shape A guarded import + emission fallback.

**Path 2 (sibling test file) is the explicit fallback.** If the
parametrization surfaces concrete in-test friction during
incarnation (e.g., the multi-step prompt's MCP-call expectations
require a fixture shape the existing test cannot accommodate
without architectural distortion), a new file
`tests/corpus/test_pr5_chain_no_dependency.py` may be added
instead. The framing §5 preference order is binding; the choice
itself is an incarnation finding documented in PR 5 close.

### 6.4 Existing tests that should stay green

All 124 corpus tests in the forge env (118 in forge-bridge env)
must continue to pass without modification, with these intentional
modifications:

- `test_pr3_discipline.py::test_zero_production_imports_outside_corpus`
  — `_ALLOWLIST` grows by one entry (§4.2).
- `test_pr4_no_dependency.py::test_arbitration_completes_when_corpus_unavailable`
  — parametrized over single-step + multi-step prompts (§6.3 path
  1, preferred). Existing single-step coverage unchanged.

`test_pr4_participation_creep.py` is **not modified** (§4.3).

### 6.5 Test count delta

PR 5 adds:

- chain-step integration: **6 effective pytest IDs** — 4 cycling-
  state parametrizations of `test_chain_step_arbitration_invariant_under_capture_state`
  (one of which is the `enabled` state, which is itself
  parametrized over `[single_match, multi_match]` per §6.1
  rejection-path coverage requirement, adding one ID), plus the
  dedicated recovering test, plus the dedicated latency test.
  Mechanically: 4 + 1 + 1 = 6 IDs in the new file. (If
  incarnation falls back to the sixth-dedicated-test shape per
  §6.1, the count remains 6 IDs but the geometry shifts: 4
  cycling-state + recovering + latency + sixth dedicated
  rejection = 7 IDs. Update at PR 5 close if the fallback
  fires.)
- helper additions: 0 test functions, ~80 LOC of helper machinery

Modified: 2 (allowlist tuple growth + no-dependency
parametrization). The no-dependency test's pytest ID count grows
from 1 to 2 (single_step + multi_step_chain).

Final count target (forge env, Python 3.11):
- 124 + 6 (new file) + 1 (no-dependency parametrization delta) =
  **131 corpus tests pass.** Same 4 pre-existing failures
  (stdio_cleanliness ×2, typer_entrypoint ×2 — confirmed
  unrelated to A.5).

Final count target (forge-bridge env, Python 3.12):
- 118 + 6 (new file) + 1 (no-dependency parametrization delta) =
  **125 corpus tests pass.** One new file may collection-skip
  due to jinja2 importorskip, raising the file-skip count from 2
  to 3 if the integration tests construct the chat handler app
  under jinja2 dependency. Adjust at incarnation.

If the §6.1 rejection-path coverage falls back to sixth-dedicated-
test shape, recompute: forge → 132, forge-bridge → 126.

---

## 7. Implementation sequence

The framing §6 pause-and-surface clause names two structural seams
that warrant a pause for sanity-check during implementation:

- Chain-step call site shape (§4.1) — the substantive integration.
- Integration test bundle geometry (§6.1) — the participation-
  creep boundary work.

The natural sequencing (mirrors PR 4's; CLOSE §2.4 cadence):

0. **Schema decision: no bump.** PR 5 explicitly does NOT modify
   the schema. The decision is recorded in this spec (§2 out-of-
   scope) and surfaces in the PR 5 commit message body. No
   code change. Verification: `git diff` of `_schema.py` is empty
   at PR 5 close.

1. **Polish step (reserved).** PR 4 step 1 was the cold-vs-warm
   topology docstring polish. PR 5 step 1 is reserved for any
   analogous polish surfaced during spec drafting; this spec
   surfaces none. **Step 1 is a no-op for PR 5.** Skipped.

2. **Allowlist transition** (§4.2) — add `console/_step.py` to
   `_ALLOWLIST` in `tests/corpus/test_pr3_discipline.py`. One-
   line tuple growth. Lands BEFORE step 6 (the test must allow
   the import when it appears). **Light-touch review** per CLOSE
   §2.4: structural plumbing.

3. **Participation-creep grep verification** (§4.3) — run
   `test_pr4_participation_creep.py` to confirm it passes before
   step 6 (trivially, no `_step.py` corpus imports yet).
   Verification step; no code change unless docstring polish
   surfaces. **Light-touch review.**

4. **Helper extension** (§6.2) — add `_drive_chain_request`,
   `_assert_chain_step_arbitration_invariance`,
   `_assert_chain_step_arbitration_response_equivalent` to
   `tests/corpus/_pr4_helpers.py`. Update file docstring to
   acknowledge shared PR 4 + PR 5 infrastructure. **Light-touch
   review.**

5. **No-dependency check extension** (§6.3) — parametrize
   `test_arbitration_completes_when_corpus_unavailable` over
   single-step + multi-step prompts (path 1). If path 1 surfaces
   in-test friction, fall back to path 2 (sibling file) and
   document the deviation. **Light-touch review** unless
   path 1 → path 2 fallback fires (then full review of the
   sibling file).

6. **Chain-step integration** (§4.1) — the four named snapshots +
   narrower-latency instrumentation + Shape A guarded import +
   capture call. This is the substantive change. **Full three-
   round review** per CLOSE §2.4: participation-creep boundary
   work.

7. **Integration tests** (§6.1) — five-test bundle in
   `test_pr5_chain_step_integration.py`. **Full three-round
   review.** Pre-step-7 verification: run
   `test_pr4_participation_creep.py` post-step-6 to confirm the
   bite profile (continues to pass with `_step.py` emission
   imports in place).

8. **Run full suite + verify counts.** Both envs (forge 3.11 and
   forge-bridge 3.12). Confirm:
   - **131 corpus tests pass in forge env** (124 baseline + 6
     new file IDs + 1 no-dependency parametrization delta;
     update to 132 if §6.1 fallback fires).
   - **125 corpus tests pass in forge-bridge env** (118 baseline
     + 6 new file IDs + 1 no-dependency parametrization delta;
     update to 126 if §6.1 fallback fires; +1 file-skip count
     possible if jinja2 absent and the new file's app
     construction needs jinja2).
   - Same 4 pre-existing failures (stdio_cleanliness ×2,
     typer_entrypoint ×2).
   - chat handler tests (`tests/console/test_chat_handler.py`) —
     50/50 unchanged.

9. **Surface for review** (writer's-room cadence). Step 6 + step
   7 receive full three-round review; surrounding steps run
   light-touch.

**Natural pause points** (per framing §6 pacing clause):

- Between step 5 and step 6 — verifies surrounding machinery
  (allowlist + grep verification + helpers + no-dependency
  extension) before chain-step integration's complexity layers
  on top.
- Between step 6 and step 7 — verifies the call-site code in
  isolation (manually drive a chain step with capture enabled,
  inspect the on-disk record) before the integration tests
  layer their full assertion machinery on top.

A third smaller pause point may surface between step 0 and step 2
if the schema-decision verification surfaces any unexpected diff.

---

## 8. Phase-end conditions for PR 5

| Trigger | Response |
|---|---|
| All five chain-step integration tests pass + participation-creep grep continues to pass + no-dependency parametrization passes both prompts + allowlist-transitioned discipline grep passes | PR 5 closes; PR 6 spec drafts. |
| `test_chain_step_arbitration_invariant_under_capture_state[<any state>]` regresses on a future PR | Hard CI failure; **PR 4's single most important invariant** has been violated at the chain-step surface. The participation boundary may have already been crossed regardless of internal architecture claims. |
| `test_narrowing_subsystem_imports_zero_corpus_modules_except_capture` regresses on a future PR | The narrowing subsystem (`_tool_filter.py` + `_step.py`) has acquired a forbidden corpus dependency. Reject at CI; review surfaces the §1.3 framing violation and the framing's forward-extension clause. |
| `test_arbitration_completes_when_corpus_unavailable[multi_step_chain]` regresses on a future PR | The chain-step arbitration layer has acquired a hard dependency on capture infrastructure. Reject at CI; the framing's §1.4 carrier sentence has been violated: *"The arbitration layer now expects capture infrastructure to exist."* |
| A future PR proposes to consolidate `_ambiguity_state_for` and `_ambiguity_state_for_chain_step` into a shared module helper | Rejected at the spec layer per §4.1 + framing §2.2 protection bullet 3. The two helpers' identical output is the protection against silent overload, not redundancy to be eliminated. |
| A future PR proposes to fetch a fresh `mcp.list_tools()` snapshot inside `execute_chain_step` for the `registered_tools` field | Rejected at the spec layer per framing §2.1. The chain-step's deployment identity is the caller's view; reaching for the global registry would silently corrupt the deployment identity hash and drift records from arbitration's actual input. |
| A future PR proposes to suppress `narrower_decision` to `[]` on rejection paths or to use a sentinel marker | Rejected at the spec layer per framing §2.2. The list expresses the actual narrowing result; rejection is expressed by the surrounding fields and the downstream envelope, not by suppressing the field. |
| A future PR proposes to set `pr20_condition_met` to True at the chain-step surface based on "narrowing succeeded deterministically" | Rejected at the spec layer per framing §2.2 silent-overload paragraph. The PR20 short-circuit is a chat-handler concept that does not exist at the chain-step site. |
| A future PR proposes to add a fifth `capture_state_cycling` state | Rejected at the spec layer per framing §1 + §5. The fixture is closed for extension; spec amendment is the only path. |
| A future PR proposes to read prior corpus records to enrich the `tool_selection_ambiguous` error envelope | Rejected at the spec layer per framing §4. The participation-creep boundary forbids corpus-read surfaces from arbitration code paths, even within the file-level allowlist. |

---

## 9. Cross-references

- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — this spec's
  binding pre-spec contract; resolves three §4.7 open questions.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state; §2 inheritance, §3 surface differences, §4.7 questions
  resolved here.
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; integration-discipline quartet (verbatim into call-site
  comment block).
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration; allowlist mechanism (§4.2); participation-creep
  grep (§4.3); capture-state-cycling fixture (§5);
  `_ambiguity_state_for` translation-only constraint (§4.1).
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §8.8 — live correlation
  prohibition; same shape as risk 1.3.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern at the
  call site (binding; §4.1 here implements it at the second
  surface).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-prohibited
  patterns at the capture call sites.
- `forge_bridge/console/_step.py` (PR 5 modifies) — chain-step
  executor; integration site at lines 52-147.
- `forge_bridge/console/_engine.py` (PR 5 reads only) —
  `run_chain_steps` caller; threads the same `tools` list to
  every step.
- `forge_bridge/console/handlers.py` (PR 5 does not modify) —
  chat-handler entry point; `_execute_chain` passes its post-
  reachability `tools` to `run_chain_steps`.
- `forge_bridge/console/_tool_filter.py` (PR 5 verifies via
  participation-creep grep) — narrowing implementation; must not
  import any corpus module except the emission path.
- `tests/corpus/test_pr3_discipline.py` (PR 5 modifies §4.2) —
  allowlist tuple grows by one entry.
- `tests/corpus/test_pr4_participation_creep.py` (PR 5 verifies
  §4.3) — no code change; bite continues to fire correctly.
- `tests/corpus/test_pr4_no_dependency.py` (PR 5 modifies §6.3
  path 1) — parametrized over single-step + multi-step prompts.
- `tests/corpus/_pr4_helpers.py` (PR 5 extends §6.2) — add
  chain-envelope helpers; reuse fixture and assertion machinery.
- `tests/corpus/test_pr5_chain_step_integration.py` (PR 5
  creates §6.1) — five-test bundle.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.3 —
  property-preservation discipline; the 11 carriers are
  instances.

---

## Resume protocol — what the next session does with this spec

1. **Read the framing first** (`A.5.3.2-PR5-FRAMING.md`). The
   surface geometry asymmetry (§2) is the load-bearing context;
   skipping it is how the chain-step integration accidentally
   collapses field semantics across the two call sites.
2. **Read this spec.** Confirm the four risks → named tests
   mapping (§3); the call-site shape (§4.1); the schema field
   semantics table (§4.1 chain-step variant); the allowlist
   extension (§4.2); the participation-creep grep verification
   (§4.3); the integration test bundle (§6.1); the no-dependency
   extension path (§6.3 path 1 preferred); the implementation
   sequencing (§7).
3. **Surface for review** before any code is written. Per the
   established discipline, the spec is reviewed; deviations
   re-open the artifact for explicit re-review, not absorbed
   silently.
4. **Implement** against the named tests in §6, in the sequence
   from §7. Step 6 + step 7 receive full three-round review;
   surrounding plumbing runs light-touch.
5. **Run the discipline + participation-creep + no-dependency
   tests** before committing each step. All three must remain
   green at every step boundary.
6. **Commit** with the eleven carrier sentences distributed
   across the call-site comment block (§4.1 lays them out
   verbatim) and the PR 5 commit message body.
7. **Close PR 5 with `A.5.3.2-PR5-CLOSE.md`** following the PR 4
   close artifact's structure.

Do not begin implementing without re-reading the framing. The
schema field semantics (§4.1 chain-step variant) and the helper-
duplication rationale (§4.1 binding) are the most likely sites
of silent drift if the framing is short-circuited.
