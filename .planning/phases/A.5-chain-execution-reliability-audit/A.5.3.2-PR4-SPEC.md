# A.5.3.2 PR 4 — Spec (chat handler integration)

**Status:** drafted 2026-05-07. Derived from `A.5.3.2-PR4-FRAMING.md`
(commit `2281baf`). The framing is the binding pre-spec contract;
this spec is the implementation contract derived from it.

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
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5),
  atomic-append discipline (§6.5), corruption locality (§9).
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; four risks; integration-discipline quartet.

**Successor (NOT this spec):** PR 5 (chain-step call site at
`console/_step.py`). PR 5 inherits this spec's allowlist
mechanism, capture-state-cycling fixture, and integration-test
shape — adding the second allowlist entry without re-litigating
the call-site contract.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Seven carrier sentences travel verbatim into:

1. The chat-handler integration site's adjacent comment block.
2. The PR 4 commit message.
3. (Where applicable) the new test files' module docstrings.

Six come from the PR 4 framing; the seventh — the
finalized-state contract — was added during this spec's
review pass to make observational-timing discipline explicit.

**From the framing — risk-category shift (§0):**

> **PR 4 is the controlled introduction of observational
> side-effects into live arbitration surfaces.**

> **The risk category has shifted from persistence-substrate risk
> to participation-creep risk.**

**From the framing — integration-discipline quartet (§3):**

> **The call site is the source of the three explicit inputs.**
>
> **The integration layer passes truth.**
>
> **The integration layer never reconstructs truth.**
>
> **The builder does not discover runtime state.**

**From the framing — observational dependency prohibition (§1.4):**

> **The arbitration layer now expects capture infrastructure to
> exist.**
>
> *(That sentence must remain false for the lifetime of this
> architecture.)*

**From this spec's review pass — finalized-state contract:**

> **Capture emission occurs only after arbitration state is
> finalized for the current execution path. Capture records
> completed arbitration observations, not provisional intermediate
> state.**

PR 4 is the first phase where observational *timing* becomes
architecturally meaningful. The architecture must explicitly
distinguish finalized arbitration observation from provisional
intermediate state — capturing earlier than finalization would
record state the system never operated on, and the corpus would
become a record of what the system was *thinking about*, not what
it *did*. That distinction is the difference between an
observational instrument and a participating speculator.

A reader who encounters PR 4's call-site code without reading the
full spec should encounter these sentences first. They establish
the risk profile that determines what belongs at the call site and
what does not.

---

## 1. Real job + success condition

**Real job:** *"Pass the four authoritative truth surfaces from
the chat-handler call site through to capture emission while
preserving arbitration invariance under all capture states."*

The four surfaces (§3 framing quartet):

- **Deployment identity** (`registered_tools`) — full registered
  tool set as held by the MCP server, captured before any
  filtering.
- **Runtime topology** (`candidate_set_post_reachability`) —
  post-reachability set, captured after the reachability filter
  but before the message filter.
- **Arbitration input** (`candidate_set_post_pr14`) — post-PR14
  message-filter set, captured after `filter_tools_by_message`
  but before `deterministic_narrow`.
- **Arbitration output** (`narrower_decision` + `pr20_condition_met`
  + `collapse_occurred` + `ambiguity_state` + `narrower_latency_ms`)
  — final arbitration state at the moment narrowing concludes.

**Success condition:** *"With `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1`,
the chat handler emits one Layer 1 record per arbitration. With
the gate disabled (or capture failing), the chat handler's
externally observable behavior is byte-identical to pre-PR-4.
Operator-visible behavior is unchanged regardless of capture
state."*

---

## 2. Scope

In scope:

- **Chat-handler call site** — `forge_bridge/console/handlers.py`
  narrowing path: surface the four authoritative inputs as named
  snapshots; insert one capture invocation at the unified
  post-narrowing point per the §5.1 visual-asymmetry pattern.
- **Allowlist parameter for discipline grep** — replace
  `_FORBIDDEN_NEEDLES` filtering with explicit allowlist
  parameter; add `console/handlers.py` as the first allowlisted
  entry.
- **Participation-creep grep test** (§1.3 framing) — new
  executable test asserting the narrowing subsystem
  (`forge_bridge.console._tool_filter` and
  `forge_bridge.console._step`) imports zero modules from
  `forge_bridge.corpus` *except* `_capture` (the legitimate
  emission path).
- **Capture-state-cycling fixture** (§1.2 framing) — new test
  fixture cycling four states: enabled / disabled / failing /
  recovering. Tests reference this fixture explicitly via
  parametrization.
- **Integration tests** — chat-handler end-to-end exercising the
  capture-state-cycling fixture. Asserts arbitration response
  byte-identity across all four states.
- **No-dependency assertion** (§1.4 framing) — integration test
  that asserts arbitration completes successfully when the corpus
  package is structurally absent (import-aliased to a sentinel
  that raises on access).
- **Cold-vs-warm topology docstring note** (UAT 4.1 in framing) —
  small docstring addition to `_topology.py::snapshot_topology`.
  Lands in the same commit as PR 4.

Out of scope (deferred per framing):

- Chain-step integration → PR 5.
- Visual-asymmetry executable lint → PR 6 (locked per framing
  §1.1; both rationales documented there).
- Stray-header-mid-file warning sharpness → PR 6 polish or
  v1.5.x patch (UAT 4.2 in framing).
- Comparator → Gate 4.
- Refactoring `handlers.py` to eliminate destructive `tools = ...`
  rebinds toward the cleaner `_step.py` shape — out of scope here;
  PR 4 introduces named *snapshots* without changing existing
  rebinds (Option C below). A future cleanup PR may unify; PR 4
  is integration, not refactoring.

If the spec begins drifting toward "while we're here, let's also
refactor X" or "this would be a good time to lint Y," **stop and
re-scope.** The framing's risk-category articulation depends on
PR 4 staying focused on the four risks.

---

## 3. The four risks → named tests

| # | Risk | Named test (this PR) |
|---|------|---------------------|
| **1.1** | Visual-asymmetry preservation at the call site | Code-review-only check (per framing §1.1, executable lint deferred to PR 6). PR 4 ships no test for 1.1; reviewers verify the §5.1 visual pattern at the call site directly. |
| **1.2** | Capture-call-site state coupling — arbitration invariance | `test_chat_handler_arbitration_invariant_under_capture_state[<state>]` — parametrized over the four states from the capture-state-cycling fixture (enabled / disabled / failing / recovering). Asserts byte-identical response envelope and bounded latency delta per state. **PR 4's single most important invariant** per framing §1.2. |
| **1.3** | Arbitration-decision feedback through capture (participation creep) | `test_narrowing_subsystem_imports_zero_corpus_modules_except_capture` — grep test that walks `forge_bridge.console._tool_filter` and `forge_bridge.console._step` source asserting zero imports from `forge_bridge.corpus` except `_capture`. Forward-extends to future corpus-read/analysis modules per framing §1.3. |
| **1.4** | Observational side-effects vs observational dependencies | `test_arbitration_completes_when_corpus_unavailable` — integration test that aliases `forge_bridge.corpus` to a sentinel raising on access; asserts the chat handler completes successfully (well-formed response, no exception, latency within budget). The strongest possible no-dependency test. |

Plus the existing PR 3 discipline-grep test transitions to
allowlist mode (see §4.2 below).

---

## 4. Module surface

### 4.1 Chat-handler call site (`handlers.py`)

**Implementation approach: Option C — named snapshots, no
destructive rebind change.**

The current call site destructively rebinds the local variable
`tools` at three points (lines 940, 1042, 1064 of `handlers.py`),
which would lose the authoritative pre-filter sets if the capture
call read `tools` directly. PR 4 surfaces named snapshots at the
moments of authority; the existing rebinds are preserved
unchanged.

**Rationale (carries from framing §3):** *"The integration layer
passes truth. The integration layer never reconstructs truth."*
Capturing at the moment of authority and passing forward
satisfies the discipline. Reconstructing the registered set from
the post-filter set + topology would violate it. Option C is
minimal change + maximum truth preservation. Option B (full
refactor toward `_step.py`'s clean variable shape) is out of scope
per §2.

**The four snapshot points:**

| Snapshot | Captured at | Source |
|---|---|---|
| `registered_tools` | After `await _mcp_server.mcp.list_tools()` (line 905-equivalent) | Full MCP-registered set; deployment identity |
| `tools_post_reachability` | After `filtered_tools = await filter_tools_by_reachable_backends(tools)` (line 932-940-equivalent), but BEFORE the existing `tools = filtered_tools` rebind has any chance to be misread | Post-reachability set; runtime topology |
| `tools_post_pr14` | After `tools = filter_tools_by_message(tools, last_user_text)` at line 1042 — this is the first time `tools` holds the post-PR14 set | Arbitration input |
| Final narrowing state | After the PR21 `if tools_filtered_count > 1: ...` block at line 1061-1065, where `tools` holds the post-deterministic-narrow set | Arbitration output |

**The capture call site (the §5.1 visual-asymmetry pattern):**

The capture invocation lands at the **unified post-narrowing
point** — after line 1065's PR21 block, before line 1089's PR20
short-circuit check. This single insertion point fires for both
arbitration paths (PR20 forced-tool and general LLM dispatch),
because narrowing has finalized at this point regardless of which
downstream path takes over. Per the §0 finalized-state carrier:
*"Capture emission occurs only after arbitration state is
finalized for the current execution path. Capture records
completed arbitration observations, not provisional intermediate
state."*

```python
# After PR21 narrowing block (existing, unchanged):
if tools_filtered_count > 1:
    narrowed = deterministic_narrow(tools, last_user_text)
    if len(narrowed) < len(tools):
        tools = narrowed
        tools_filtered_count = len(narrowed)
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
#    The integration layer passes truth. The integration layer
#    never reconstructs truth. (PR 4 framing §3.)
#
#    Capture emission occurs only after arbitration state is
#    finalized for the current execution path. Capture records
#    completed arbitration observations, not provisional
#    intermediate state. (PR 4 spec §0.)

if divergence_capture_enabled():
    emit_divergence_capture(
        prompt=last_user_text,
        registered_tools=registered_tools,
        candidate_set_post_reachability=tools_post_reachability,
        candidate_set_post_pr14=tools_post_pr14,
        narrower_decision=tools,
        pr20_condition_met=(
            tools_filtered_count == 1
            and tools_filtered_count < tools_available_count
        ),
        collapse_occurred=(
            tools_filtered_count == 1
            and len(tools_post_pr14) > 1
        ),
        ambiguity_state=_ambiguity_state_for(tools_filtered_count),
        narrower_latency_ms=narrower_latency_ms,
        source="runtime",
    )
```

**Pattern requirements (binding per Gate 1 §5.1, framing §1.1):**

- The blank line + comment block + explicit `if
  divergence_capture_enabled():` guard are part of the contract,
  not stylistic preference.
- Capture happens AFTER `tools` has been bound to its final
  narrowed value and `narrower_latency_ms` has been measured.
- Capture happens BEFORE the PR20 short-circuit and BEFORE the
  general LLM dispatch path. One insertion point covers both
  downstream paths.
- The `if divergence_capture_enabled():` guard is at the call
  site, NOT inside `emit_divergence_capture`. The visual
  asymmetry — observation is gated; arbitration is not — must be
  visible at the reading level.
- `_ambiguity_state_for(n)` is a tiny private helper in
  `handlers.py` returning `"single_survivor"` for n=1,
  `"multi_survivor"` for n>1, `"zero_survivor"` for n=0. (The
  empty case is guarded against at line 1113 of the current code,
  but the schema requires the field; the helper handles it
  defensively.)

  **Constraint on `_ambiguity_state_for` (binding):** *"This
  helper exists only to translate numeric narrowing state into
  the schema's required string representation. It must remain
  deterministic, one-line, and free of inferential logic."*
  Small translation helpers are common future-growth surfaces
  for hidden classification, interpretive branching, and
  participation creep. This helper is translation-only, not
  inference-bearing. A future PR proposing to add "smart"
  ambiguity detection (e.g., "if multi_survivor but the tools
  share a common prefix, classify as semi_collapsed") is
  rejected at the spec layer — that interpretation belongs in
  Layer 2 or a higher analytic layer, not in the capture call
  site.

**Field-derivation semantics (binding):**

Two field-derivation choices in the call-site code carry
non-obvious load-bearing semantics. They were caught during this
spec's review pass and corrected before any production records
existed; documenting them here so future readers don't relitigate.

- **`pr20_condition_met` (renamed from `pr20_fired` during this
  spec's review pass).** The expression
  `tools_filtered_count == 1 and tools_filtered_count <
  tools_available_count` measures *the PR20 branch condition is
  currently satisfied before execution*, not *the PR20 path
  fired*. Capture occurs **before** the branch executes. The
  field must describe present observed truth rather than future
  path certainty. Treated as a v1 schema correction caught
  during integration review **before any production corpus
  existed** — preferred name `pr20_condition_met` over
  `pr20_will_fire` because *condition_met* describes present
  truth only.

  **Implementation impact:** the rename lands in PR 4's commit:
  `forge_bridge/corpus/_schema.py` (`_REQUIRED_NARROWER_KEYS` +
  `_validate_narrower`), `forge_bridge/corpus/_capture.py`
  (builder field name + writer parameter name), and any tests
  referencing the old field (`tests/corpus/test_pr1_skeleton.py`,
  `tests/corpus/_pr3_helpers.py::base_writer_args`). All must
  rename in the same commit; the spec's §7 implementation
  sequence anchors this as step 0 (before any other work).

- **`collapse_occurred` records the multi-to-single transition
  specifically, not generic set reduction.** The expression
  `tools_filtered_count == 1 and len(tools_post_pr14) > 1`
  fires only when narrowing collapsed an ambiguous candidate
  set into a single survivor. Generic shrinkage
  (`tools_filtered_count < len(tools_post_pr14)` — the original
  expression) would fire on any reduction, including
  multi-survivor → fewer-multi-survivor refinement, which is
  not the diagnostic signal A.5.3.2 is investigating.

  *"This field records the specific multi-to-single transition
  the phase is investigating, not generic set reduction."*

  The corpus exists to classify divergence patterns where the
  narrower's collapse-to-determinism diverges from what the
  planner would have chosen. A field that fires on any
  refinement (multi → still-multi-but-fewer) would dilute that
  signal with cases the analysis does not need to interpret.

**Latency instrumentation:**

A new `narrower_started = time.perf_counter()` lands immediately
before line 1042 (`tools = filter_tools_by_message(...)`). The
`narrower_latency_ms = (time.perf_counter() - narrower_started) *
1000.0` measurement lands after the PR21 block and before the
capture invocation. Cost is one `perf_counter` call (sub-microsecond
on Linux/macOS), so the measurement satisfies §1.2's "bounded
latency contribution under capture-enabled" requirement trivially.

The latency measurement happens **regardless of
`divergence_capture_enabled()`** — measurement is part of the
arbitration path, not the capture path. This is structural
protection against a later "let's only measure when capturing,
to save the perf_counter call" simplification that would couple
arbitration timing to capture state. The cost of the measurement
when capture is disabled is negligible; coupling it to capture
state would weaken the §1.4 no-dependency property.

### 4.2 Allowlist parameter for the discipline grep

PR 3's `tests/corpus/test_pr3_discipline.py::test_zero_production_imports_outside_corpus`
walks `forge_bridge/` (excluding `forge_bridge/corpus/`) and
asserts no production code path imports `forge_bridge.corpus`.

PR 4 transitions this test to allowlist mode by adding an
`_ALLOWLIST: tuple[str, ...]` constant naming the relative paths
of files permitted to import the corpus:

```python
# Files explicitly permitted to import forge_bridge.corpus.
# Each entry is one named call-site integration. PR 4 adds the
# chat-handler integration; PR 5 will add the chain-step
# integration. Growth is reviewable at the spec layer per
# A.5.3.2-PR4-FRAMING.md §2 ("bounded asymmetry, named
# explicitly, more durable than literal asymmetry maintained by
# ignoring real integration").
_ALLOWLIST: tuple[str, ...] = (
    "console/handlers.py",
)
```

**Test logic (revised):**

- Walk the production tree excluding `corpus/`.
- For each `.py` file, compute its path relative to
  `forge_bridge/`.
- If the relative path is in `_ALLOWLIST`, skip the import check.
- Otherwise, scan for `from forge_bridge.corpus` /
  `import forge_bridge.corpus` and add to offenders.

**Failure-message contract:**

When the test fails, the message names the allowlist explicitly
so future contributors understand the boundary:

> *"PR N discipline violated: `<path>` imports `forge_bridge.corpus`
> but is not in the allowlist (currently: `console/handlers.py`).
> Either: (a) the import is genuine integration — add the file to
> `_ALLOWLIST` with spec amendment, or (b) the import was
> accidental — remove it. The bounded asymmetry is what protects
> against participation creep at unrelated call sites; mocking,
> removing, or inverting this test is rejected at the spec layer
> per `A.5.3.2-PR4-FRAMING.md` §2."*

**Forward extension:** PR 5 adds `console/_step.py` as the second
allowlisted entry. Each future PR introducing a new corpus call
site must explicitly amend `_ALLOWLIST` and document the
addition in its spec.

### 4.3 Participation-creep grep test (new)

`tests/corpus/test_pr4_participation_creep.py::test_narrowing_subsystem_imports_zero_corpus_modules_except_capture`:

Walks `forge_bridge/console/_tool_filter.py` and
`forge_bridge/console/_step.py` source. Asserts:

- Zero imports of `from forge_bridge.corpus.reader` /
  `import forge_bridge.corpus.reader`.
- Zero imports of any future corpus module *except* `_capture`.

The test is implemented as a positive list rather than a negative
denylist:

```python
# The narrowing subsystem may import ONLY the emission path.
# Any other corpus module surface — reader, comparator (Gate 4),
# replay-analysis helpers, historical lookup, corpus-derived
# heuristic surfaces — is a participation-creep boundary
# violation. The test enforces one-directional observational
# flow: arbitration → capture → corpus, never the reverse.
#
# Future corpus modules inherit the prohibition automatically:
# any new corpus module surfaces should NOT appear in the
# narrowing subsystem's import set, and PRs introducing such
# modules carry the responsibility to extend this test.

_PERMITTED_CORPUS_IMPORTS: tuple[str, ...] = (
    # Only the emission path:
    "forge_bridge.corpus._capture",
    "forge_bridge.corpus.divergence_capture_enabled",
    "forge_bridge.corpus.emit_divergence_capture",
    # Public-API access via top-level package is allowed only
    # for the emission names; the test inspects what's actually
    # imported, not just the module path.
)
```

The test extracts every `forge_bridge.corpus.<X>` reference from
the narrowing subsystem source and asserts each is in the
permitted set.

**Why this protection lives in PR 4 and not PR 3:** the
narrowing subsystem is the participation-creep target. PR 3
established the persistence layer; the participation-creep risk
only became operational when integration began (PR 4). The
forward-extension clause in framing §1.3 means future corpus
modules (Gate 4 comparator, replay-analysis, historical lookup,
corpus-derived heuristics) automatically inherit the prohibition
— the test enforces "narrowing imports only `_capture`," which
naturally rejects all future corpus-read surfaces.

---

## 5. The capture-state-cycling fixture

Per framing §1.2: the architectural concern introduced in PR 4
deserves explicit fixture vocabulary. Stretching the existing
chat-handler fixtures to absorb capture-state cycling is rejected
at the spec layer.

### 5.1 Fixture states (four)

| State | Mechanism | What this exercises |
|---|---|---|
| `disabled` | env var unset; corpus dir does not exist | Zero capture path; pre-PR-4 baseline behavior |
| `enabled` | env var = `"1"`; corpus dir is tmp_path; corpus package healthy | Successful-capture path |
| `failing` | env var = `"1"`; `Path.open` mocked to raise `OSError` | I-6 failure-invisibility path; arbitration must complete |
| `recovering` | env var = `"1"`; first capture attempt fails (mock raises once), subsequent capture succeeds | Transition between failure and success; verifies no state retained between writes (§residue test from PR 3) |

### 5.2 Fixture API

```python
# tests/corpus/_pr4_helpers.py (new)

CaptureState = Literal["disabled", "enabled", "failing", "recovering"]


@pytest.fixture
def capture_state_cycling(
    request, monkeypatch, tmp_path,
) -> Iterator[CaptureState]:
    """Configure the capture environment per the parametrized state.

    Tests that exercise arbitration invariance under capture states
    request this fixture with @pytest.mark.parametrize("capture_state",
    ["disabled", "enabled", "failing", "recovering"], indirect=True).

    Per A.5.3.2-PR4-FRAMING.md §1.2, this fixture is binding for
    every test that asserts arbitration invariance. Stretching older
    chat-handler fixtures to absorb capture-state cycling is
    rejected at the spec layer — older fixtures answer different
    questions, and conflating them obscures which assertion is
    protecting which property.
    """
    state: CaptureState = request.param
    # ... implementation per the table above ...
    yield state
```

### 5.3 Why these four states (not more, not fewer)

- **`disabled`** is the baseline — pre-PR-4 behavior. Without it,
  we can't verify that the addition of the capture call leaves
  the disabled path unchanged.
- **`enabled` (success)** is the happy path. Without it, capture
  isn't actually exercised under realistic conditions.
- **`failing`** exercises I-6 at integration level. PR 3's
  unit-level failure-invisibility tests already pin the writer's
  return-None / log-WARNING behavior; the integration test
  verifies the *response envelope* is invariant when capture
  fails — distinct property.
- **`recovering`** verifies no inter-call state retention. The
  PR 3 residue test (`test_failed_write_leaves_no_capture_residue`)
  pins this at unit level for two consecutive emissions; the
  integration version verifies the chat handler doesn't develop
  a "we already failed once, skip subsequent attempts" cache.

Adding more states (e.g., `permission_denied`, `partial_write`,
`disk_full`) would duplicate PR 3's I-6 coverage at the
integration level without adding new architectural invariants.
Removing any of the four loses a property.

---

## 6. Integration test plan

All tests live under `tests/corpus/`. The chat-handler-end-to-end
fixture machinery may import from `tests/console/` if compatible
shapes already exist — PR 4 does not create a new chat-handler
test client.

### 6.1 New test files

**`tests/corpus/_pr4_helpers.py`** — `capture_state_cycling`
fixture + supporting MockTool-list helpers (the fixture sets up
realistic registered tool lists for the chat handler to receive).

**`tests/corpus/test_pr4_chat_handler_integration.py`** — the
arbitration-invariance test bundle:

- `test_chat_handler_arbitration_invariant_under_capture_state[disabled]`
- `test_chat_handler_arbitration_invariant_under_capture_state[enabled]`
- `test_chat_handler_arbitration_invariant_under_capture_state[failing]`
- `test_chat_handler_arbitration_invariant_under_capture_state[recovering]`

Each test drives a representative chat request through the
chat handler and asserts:
- The response envelope's structure is byte-identical across all
  four states (modulo `request_id` and timestamps, which are
  ignored in the comparison).
- The HTTP status code is identical.
- The latency delta between `enabled` and `disabled` is bounded:
  **target < 5ms; hard ceiling < 20ms.** *"Exceeding the target
  triggers investigation, not threshold adjustment."* PR 4 remains
  observational append-only integration, not persistence-budget
  engineering. Unexpected latency growth is suspicious,
  diagnostically important, and architecturally meaningful — not
  merely "within budget." A test that fails at 7ms because the
  capture path acquired hidden complexity is the correct outcome;
  raising the budget to absorb the hidden complexity is the
  failure mode this framing rejects.
- For `enabled`: exactly one Layer 1 record was written; the
  record's `narrower_decision` matches the actual
  arbitration-output `tools` list.
- For `failing`: zero records on disk; one WARNING logged
  (matching the PR 3 failure-invisibility log shape); response
  envelope identical to `disabled` modulo expected differences.
- For `recovering`: exactly one record on disk (the second
  attempt's record); the failed first attempt produced no on-disk
  residue.

**`tests/corpus/test_pr4_participation_creep.py`** — see §4.3.

**`tests/corpus/test_pr4_no_dependency.py`** — the §1.4 no-dependency
assertion:

- `test_arbitration_completes_when_corpus_unavailable` — patches
  `sys.modules["forge_bridge.corpus"]` to a sentinel module whose
  every attribute access raises `AttributeError`. Drives a chat
  request through the chat handler. Asserts the request completes
  with a well-formed response (status 200 or expected error
  code), no exception propagates from the corpus-import attempt,
  and the response envelope is structurally well-formed.

  The test fixture restores `sys.modules` on teardown. The chat
  handler must not crash, hang, or produce a malformed response
  when the corpus package is structurally absent. **Per framing
  §1.4: this is the strongest possible test of the
  no-dependency property — if arbitration runs without corpus,
  the dependency is structurally absent.**

### 6.2 Existing tests that should stay green

All 117 corpus tests + the existing chat-handler test suite must
continue to pass without modification, with one exception:

- `tests/corpus/test_pr3_discipline.py::test_zero_production_imports_outside_corpus`
  — **modified** to use the allowlist parameter (per §4.2). The
  test name stays the same; the implementation gains the
  `_ALLOWLIST` parameter and the failure message expands. This is
  a single intentional modification, not a removal or mock.

### 6.3 Test count delta

PR 4 should add roughly:

- chat-handler integration: ~4 (one per cycling state)
- participation-creep grep: ~1
- no-dependency assertion: ~1
- helpers/fixture: 0 test functions, ~50 LOC of fixture machinery

Total: ~6 new tests. Modified: 1 (the discipline grep transitions
to allowlist mode).

Final count target: 117 + 6 = ~123 corpus tests pass. Same 4
pre-existing failures. Full suite ~1622 passing.

---

## 7. Implementation sequence

The framing's pause-and-surface clause names three structural
seams that may warrant a pause for sanity-check during
implementation:

- Call-site shape (§4.1).
- Allowlist mechanism (§4.2).
- Capture-state-cycling fixture (§5).

The natural sequencing:

0. **`pr20_fired` → `pr20_condition_met` schema rename** (§4.1
   semantic correction). Lands FIRST because every subsequent
   step depends on the corrected field name. Touches:
   - `forge_bridge/corpus/_schema.py` —
     `_REQUIRED_NARROWER_KEYS` + `_validate_narrower` (rename
     the key + the error message).
   - `forge_bridge/corpus/_capture.py` —
     `_build_capture_record` and `emit_divergence_capture`
     (rename the parameter + the dict key in the built record).
   - `tests/corpus/test_pr1_skeleton.py` —
     `_valid_record()` (rename the field) +
     `test_validate_rejects_non_bool_pr20_fired` (rename the
     test function and the field reference).
   - `tests/corpus/_pr3_helpers.py` —
     `base_writer_args` (rename the kwarg).
   - Any other test that references `pr20_fired` literally.

   **Verification:** full corpus test suite (117 tests) green
   after the rename and before any other PR 4 work begins. The
   rename is a v1 schema correction caught during integration
   review **before any production corpus existed**; it is not a
   `SCHEMA_VERSION` bump because no on-disk records carry the
   old name in production.

1. **Cold-vs-warm topology docstring note** (UAT 4.1) — small
   docstring-only addition to `_topology.py::snapshot_topology`.
   Lands early so subsequent work has the cleaner documentation
   in place.
2. **Allowlist transition** (§4.2) — convert
   `test_zero_production_imports_outside_corpus` to allowlist
   mode. Add `console/handlers.py` to the allowlist *before* the
   chat-handler integration lands (the test must allow the import
   when it appears).
3. **Participation-creep grep** (§4.3) — new test. This is
   structural, can land independent of the integration code.
4. **`_pr4_helpers.py` + `capture_state_cycling` fixture** (§5).
   Fixture scaffolding lands before the tests that depend on it.
5. **No-dependency test** (§1.4) — independent of integration.
6. **Chat-handler integration** (§4.1) — the four named snapshots
   + capture call. This is the substantive change; landing it
   here means earlier steps validated the surrounding machinery
   first.
7. **Integration tests** (§6.1) — the four cycling-state tests
   land alongside the integration code.
8. **Run full suite + verify counts.**
9. **Surface for review.**

The natural pause point (per framing's pacing clause) is between
steps 5 and 6 — after all surrounding machinery is in place but
before the chat-handler integration lands. A pause here would
verify the allowlist + grep + fixture + no-dependency framework
works in isolation, before the integration's complexity layers on
top.

A second, smaller pause point exists between step 0 (the schema
rename) and step 1 — verifying the rename landed cleanly before
moving on. The rename touches multiple files; if any test was
overlooked, that surfaces here rather than mid-integration.

---

## 8. Phase-end conditions for PR 4

| Trigger | Response |
|---|---|
| All four cycling-state arbitration-invariance tests pass + participation-creep grep passes + no-dependency test passes + allowlist-transitioned discipline grep passes | PR 4 closes; PR 5 spec drafts. |
| `test_chat_handler_arbitration_invariant_under_capture_state[<any state>]` regresses on a future PR | Hard CI failure; **PR 4's single most important invariant** has been violated. The participation boundary may have already been crossed regardless of internal architecture claims. |
| `test_narrowing_subsystem_imports_zero_corpus_modules_except_capture` regresses on a future PR | The narrowing subsystem has acquired a forbidden corpus dependency. Reject at CI; review surfaces the §1.3 framing violation and the framing's forward-extension clause. |
| `test_arbitration_completes_when_corpus_unavailable` regresses on a future PR | The arbitration layer has acquired a hard dependency on capture infrastructure. Reject at CI; the framing's §1.4 carrier sentence has been violated: *"The arbitration layer now expects capture infrastructure to exist."* |
| A future PR proposes to remove the discipline-grep test ("PR 4 made it obsolete") | Rejected at the spec layer per framing §2. The bounded asymmetry is what protects against participation creep at unrelated call sites. |
| A future PR proposes to fold capture invocation into a `narrow_with_capture(...)` helper | Rejected at the spec layer per Gate 1 §5.3. (Already prohibited; PR 4 does not relax this.) |
| A future PR proposes to read corpus state from the narrowing subsystem (e.g., "let's check the corpus to see what we've done before") | Rejected at the spec layer per framing §1.3. The participation-creep grep enforces this mechanically. |
| A future PR proposes to "simplify" the chat handler by removing the named snapshots and reading `tools` directly at the capture site | Rejected per framing §3 (integration-discipline quartet). The destructive `tools = ...` rebinds would lose authoritative truth surfaces; reconstructing them from intermediate state is participation creep through the back door. |
| A future PR proposes a `narrow_with_capture(...)` helper or any pattern that fuses the two arbitration operations with the capture call into one visual statement | Rejected per Gate 1 §5.1 (visual asymmetry). PR 6's lint may eventually catch this mechanically; PR 4 catches it at code review. |
| A future PR proposes to optimize narrowing thresholds based on capture-failure rates, prompt-family frequencies in the corpus, or any other corpus-derived signal | Rejected per framing §1.3 (planner-agreement-frequency tuning is the named threat). The corpus is for *classification of divergence patterns*, not *minimization of divergence count*. |

---

## 9. Cross-references

- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — this spec's
  binding pre-spec contract.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §8.8 — live correlation
  prohibition; same shape as risk 1.3.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern at the
  call site (binding; §4.1 here implements it).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-prohibited
  patterns at the capture call sites (carry through PR 4
  unchanged).
- `forge_bridge/console/handlers.py` (PR 4 modifies) — chat
  handler narrowing path; integration site.
- `forge_bridge/console/_tool_filter.py` (PR 4 verifies via grep)
  — narrowing subsystem; must not import any corpus module except
  the emission path.
- `forge_bridge/console/_step.py` (PR 5 modifies; PR 4 verifies
  via grep) — chain-step narrowing path; same prohibition shape.
- `forge_bridge/corpus/_topology.py` (PR 4 docstring-only
  amendment) — cold-vs-warm topology semantics note (UAT 4.1).
- `tests/corpus/test_pr3_discipline.py` (PR 4 modifies) —
  transitions from forbidden-needles filtering to allowlist mode.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.3 —
  property-preservation discipline; the framing's six carrier
  sentences are an instance.

---

## Resume protocol — what the next session does with this spec

1. **Read the framing first** (`A.5.3.2-PR4-FRAMING.md`). The
   risk-category shift (§0) is the load-bearing context; losing
   it is how the chat-handler integration accidentally grows
   participation features.
2. **Read this spec.** Confirm the four risks → named tests
   mapping (§3); the call-site shape (§4.1); the
   capture-state-cycling fixture (§5); the implementation
   sequencing (§7).
3. **Surface for review** before any code is written. Per the
   established discipline, the spec is reviewed; deviations
   re-open the artifact for explicit re-review, not absorbed
   silently.
4. **Implement** against the named tests in §6, in the sequence
   from §7. The capture-state-cycling fixture is the load-bearing
   verification.
5. **Run the discipline + participation-creep + no-dependency
   tests** before committing. All three must be green.
6. **Commit** with the framing's six carrier sentences in the
   commit message body, alongside any spec-level carriers (e.g.,
   the integration site's adjacent comment block carries them at
   the call site too).

Do not begin drafting the spec without re-reading the framing.
The risk-category shift is the load-bearing context; losing it
is how the chat-handler integration accidentally fuses
observation with arbitration.
