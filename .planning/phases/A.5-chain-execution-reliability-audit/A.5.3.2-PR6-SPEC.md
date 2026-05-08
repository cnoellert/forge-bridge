# A.5.3.2 PR 6 — Spec (visual-asymmetry executable lint backstop)

**Status:** drafted 2026-05-08 (post-PR-5-close session). Derived
from `A.5.3.2-PR6-FRAMING.md` (this commit). The framing is the
binding pre-spec contract; this spec is the implementation
contract derived from it.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  visual-asymmetry pattern (§5.1); helper signature (§5.2);
  architecturally prohibited patterns (§5.3).
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology + identity.
- `A.5.3.2 PR 3` (commit `a9e3e47`) — capture builder + writer +
  reader.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5);
  atomic-append (§6.5); discipline grep (§10).
- `A.5.3.2 PR 4` (commit `614750a`) — chat-handler integration
  (Layer 1 + Layer 2 + first canonical-shape call site).
- `A.5.3.2-PR4-FRAMING.md` (commit `2281baf`) — risk-category
  shift; integration-discipline quartet.
- `A.5.3.2-PR4-SPEC.md` (commit `b84a8c8`) — chat-handler
  integration contract.
- `A.5.3.2-PR4-CLOSE.md` (commit `fab26cb`) — durable archival
  state PR 5 inherited.
- `A.5.3.2 PR 5` (commit `0cd915d`) — chain-step integration
  (second canonical-shape call site).
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; arbitration-aware-not-branch-aware (Rejection 4
  origin).
- `A.5.3.2-PR5-SPEC.md` (commit `42336c3`) — chain-step
  integration; helper-duplication binding.
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherits. **Mandatory predecessor read.**
- **`A.5.3.2-PR6-FRAMING.md`** (this commit) — binding pre-spec
  contract; resolves discovery-vs-allowlist (§3.2), hybrid AST +
  text validation (§4.3), Property D visual grammar lock (§4.1),
  NARROWING_FUNCTION_NAMES maintenance surface (§4.2 Rejection 2),
  Layer-3-only scope discipline (§4.2 Rejection 3 + §5).

**Successor (NOT this spec):** Gate 2 framing (seed corpus drive).
Gate 1 closes when PR 6 closes; Gate 2 framing drafts after Gate 1
closure.

---

## 0. Crystallizing sentences (verbatim — load-bearing)

Thirteen carrier sentences travel verbatim into:

1. The lint module's docstring at
   `tests/corpus/test_pr6_visual_asymmetry.py`.
2. The PR 6 commit message body.
3. The lint's failure messages (where applicable per the per-
   rejection-criterion mapping in §6.4).

Eleven inherit verbatim from PR 4 + PR 5; two are additive PR 6
carriers introduced by the framing.

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

**Inherited from PR 5 (verbatim):**

> **PR 5 is the second call site under the integration discipline
> PR 4 established. The risk profile is inherited; the surface
> geometry is not.**

> **The chain-step's deployment identity is the caller's view, not
> the global daemon registry view.**

> **Ambiguity rejection is an arbitration outcome. Capture must
> record it. At this surface, `narrower_decision` carries the
> filtered list verbatim at narrowing finalization — including
> zero-match and multi-match rejection paths. `pr20_condition_met`
> is always False and `collapse_occurred` is False on all
> rejection paths. These semantics differ from the chat-handler
> case and must not be silently overloaded.**

> **No-dependency coverage at the chain-step surface must be
> measured, not inferred. The existing probe drives only the
> chat-handler single-step path; PR 5 owns the responsibility to
> extend coverage to the chain-step path empirically.**

**Additive — PR 6 structural-backstop framing (framing §0):**

> **PR 6 is the structural backstop for the visual-asymmetry
> pattern. The lint validates shape, not content; structure, not
> interpretation. Carrier content is the room's job; field
> validation is the helper signature's job; the lint validates the
> visual asymmetry between arbitration and observation.**

**Additive — PR 6 observation-not-participation framing (framing
§0 + §3.2):**

> **The lint operates by observation, not by participation. It
> reads source files; it does not import the corpus package. The
> lint's own scope is the same one-directional observational flow
> the call sites enforce.**

A reader who encounters PR 6's lint module without reading the
full spec should encounter these sentences first. The eleven
inherited carriers establish the integration discipline and the
surface geometry asymmetry; the two PR 6 carriers establish the
backstop's scope and the lint's own posture. Neither set
substitutes for the other.

---

## 1. Real job + success condition

**Real job:** *"Transition the visual-asymmetry pattern (Gate 1
§5.1) from a code-review-only check into mechanically enforced
CI. Validate every present and future call site to
`emit_divergence_capture(...)` against the canonical shape
(Properties A-D). Reject the four prohibited deviations
(Rejections 1, 2, 4 explicitly; Rejection 3 as a consequence of
the local-shape properties holding). Preserve the visual signal
that distinguishes arbitration from observation, because semantic
preservation without visual preservation is the specific erosion
mode PR 6 exists to prevent."*

The lint's two operational responsibilities at this surface:

- **Discover candidate call sites** by walking the production
  tree (`forge_bridge/`, excluding `corpus/` and tests/) and
  finding every `Call(func=Name('emit_divergence_capture'))`
  AST node. Per framing §3.2, discovery answers *where calls
  actually exist*; the allowlist answers *where imports may
  exist*; both are needed.
- **Validate each discovered call site** against Properties A-D
  (acceptance criteria) and reject the deviations enumerated in
  §6.3 (Rejections 1, 2, 4 with explicit detection logic;
  Rejection 3 as a named consequence with no separate analysis
  pass).

Plus one helper-internal check (framing §4.4) on
`forge_bridge/corpus/_capture.py::emit_divergence_capture`: the
helper itself must NOT internally call
`divergence_capture_enabled()` to silently no-op. This locks the
gate's location at the call site rather than inside the helper
(Gate 1 §5.3 first prohibited pattern, helper-internal layer).

**Success condition:** *"PR 6 ships a single test module
(`tests/corpus/test_pr6_visual_asymmetry.py`) that walks the
production tree, validates every discovered emit call site
against the canonical shape, validates the helper-internal
gate-absence property, validates its own no-corpus-import
posture, and passes against the current main. The lint fires
expected failures under each of the four bite-verification
scratches at production call sites; reverting each scratch
restores green. Synthetic-source rejection tests exercise each
property and rejection criterion under the lint's parser
without mutating production code."*

**Operator-visible behavior change:** none. PR 6 is test-side
infrastructure; production code is not modified.

---

## 2. Scope

**In scope:**

- **New test module** —
  `tests/corpus/test_pr6_visual_asymmetry.py`. Contains:
  - The `NARROWING_FUNCTION_NAMES` maintenance surface
    (framing §4.2 Rejection 2).
  - AST helpers (discovery, enclosing-If finder, guard-shape
    validator, narrowing-call detector).
  - Text-introspection helpers (blank-line counter, comment-
    block opener detector).
  - Property A-D validators.
  - Rejection 1, 2, 4 detection logic.
  - The helper-internal gate-absence check.
  - Synthetic-source rejection tests (one per property +
    rejection criterion).
  - The production-tree umbrella test.
  - The lint-self-no-corpus-import meta-test.
- **No production code changes.** PR 6 introduces no edits to
  `forge_bridge/` source files. The lint validates what's there;
  it does not motivate restructuring.
- **No allowlist changes.** `test_pr3_discipline.py::_ALLOWLIST`
  stays at two entries (handlers.py + _step.py). The lint is a
  test-side mechanism.
- **No participation-creep grep changes.**
  `test_pr4_participation_creep.py::_NARROWING_SUBSYSTEM` stays
  unchanged; the grep continues to bite at the import boundary
  while PR 6 bites at the call-site shape boundary.
- **No fixture changes.** `tests/corpus/_pr4_helpers.py` is
  closed for extension by PR 6; the lint reads source files and
  needs no integration-style construction helpers.

**Out of scope (deferred per framing):**

- **A new call site.** Two are sufficient for the lint's
  earnability; a third is Gate 2/4 work. (Framing §8 + CLOSE
  §3.4.)
- **Refactoring either existing call site.** The lint validates
  what's there; if incarnation surfaces a place where the
  canonical pattern would read more clearly with a small
  adjustment, that adjustment routes to a separate v1.5.x
  patch. (Framing §8.)
- **Carrier-content validation.** Carrier text presence and
  byte-identicality are validated by the flattening pipeline
  (PR 4 step 6). The lint does NOT verify what the carrier
  says; it verifies the carrier block exists in the right
  place. (Framing §2.2.)
- **Field-count or field-name validation in the emission call.**
  That is the helper signature's job (Gate 1 §5.2). The lint
  validates only `source="runtime"` because that is *structural*
  (PR 3 schema enum), not *content*. (Framing §2.2.)
- **A standalone "Rejection 3" co-location analysis pass.** Per
  framing §4.2 Rejection 3 + §5: cross-module fused-helper drift
  is caught at Layers 1 + 2; in-function fused-helper drift is
  caught as a *consequence* of Properties A-D + Rejections 1, 2,
  4 holding. PR 6 does NOT acquire module-graph traversal,
  dependency-flow analysis, or cross-file fusion detection
  responsibilities. (Framing §2.3 + §4.2 + §5.)
- **A schema bump.** v1 schema continues unchanged.
- **A fifth `capture_state_cycling` state.** Closed for extension
  at the spec layer (PR 5 framing §1; carries to PR 6 unchanged).
- **Stray-header sharpness from PR 3 UAT.** Per framing §4.5:
  decision deferred to incarnation; default route is v1.5.x
  patch unless the lint touches `_reader.py` for some reason
  (it does not). **Confirmed at spec layer: routes to v1.5.x
  patch.** Not in PR 6.
- **Third-party dependencies (libcst, parso, asttokens).** Out
  of scope for v1.5 Legibility per CLAUDE.md (no new external
  libraries). Stdlib `ast` + line-by-line `source.splitlines()`
  text introspection is sufficient.

If the spec begins drifting toward "while we're here, let's
also..." or "this would be a good time to refactor X," **stop
and re-scope.** PR 6's framing is narrow by design; expansions
re-open the framing.

---

## 3. The four risks → named tests

PR 6 is a verification mechanism, not an integration. The risk
table maps differently from PR 4/PR 5 because the operational
surface is the lint itself, not a new call site.

| # | Risk | Named test (this PR) |
|---|---|---|
| **6.1** | Lint over-fits incidental formatting (the PR 4 framing §1.1 deferral rationale: "locking visual structure into executable lint too early risks freezing accidental formatting") | The synthetic-source rejection tests (§6.4) cover the rejection criteria; Property D shape-preserving flexibility tests (§6.4 D.3) verify that 0-blank-line variants and internal-section-break variants are ACCEPTED. The two operational call sites + the synthetic shape-preserving variants give input diversity to distinguish structural from incidental. |
| **6.2** | Lint under-fits — accepts a deviation it should reject | Synthetic-source rejection tests (§6.4) for each Rejection criterion + each Property failure mode. Each test constructs a synthetic source string, runs the lint over it, and asserts the lint fires with a specific failure-mode identifier. |
| **6.3** | Lint becomes a participation-creep vector itself (acquires `forge_bridge.corpus` import or reaches for module-graph analysis) | `test_lint_imports_no_corpus_modules` — meta-test that asserts `tests/corpus/test_pr6_visual_asymmetry.py` itself does not import `forge_bridge.corpus` in any form. Plus the §4.2 Rejection 3 framing's "stop and re-scope" guard at the spec layer; the lint's own AST does not reach across files. |
| **6.4** | Maintenance-surface erosion — a future narrowing rename silently disables Rejection 2 | Documentation discipline at `NARROWING_FUNCTION_NAMES` definition site + the constant's docstring + the lint module docstring (§5.2.1). The constant IS the operational mechanism; the protected property is the truth. The constant's update is part of any narrowing-rename mergeability contract. (No mechanical test for this — the property is *that the constant stays current*, which is a maintenance discipline, not an automatable invariant.) |

Plus the PR 3/PR 4/PR 5 existing structural tests continue to
pass unchanged:

- `test_pr3_discipline.py::test_zero_production_imports_outside_corpus`
  — Layer 1 (file-level allowlist).
- `test_pr4_participation_creep.py::test_narrowing_subsystem_imports_zero_corpus_modules_except_capture`
  — Layer 2 (import-symbol allowlist).
- `test_pr4_no_dependency.py::test_arbitration_completes_when_corpus_unavailable[<state>]`
  — no-dependency invariant.
- All four chain-step / chat-handler integration tests under all
  capture states.

---

## 4. Module surface

### 4.1 The lint module

**Location:** `tests/corpus/test_pr6_visual_asymmetry.py`.

**Module docstring (verbatim layout — locks the carriers'
entry-point):**

```
"""Layer 3 — call-site shape (visual-asymmetry executable lint).

Validates the canonical visual-asymmetry pattern at every call
site invoking ``emit_divergence_capture(...)`` in the production
tree. Joins ``test_pr3_discipline.py`` (Layer 1 — file-level
allowlist) and ``test_pr4_participation_creep.py`` (Layer 2 —
import-symbol allowlist) as the third layer of forge-bridge's
structural-test discipline.

Per A.5.3.2-PR6-FRAMING.md §2.3 — the three layers are non-
redundant AND non-overlapping. PR 6 owns Layer 3 only; cross-
module fused-helper drift is caught at Layers 1 + 2.

Carrier sentences (eleven inherited from PR 4 + PR 5; two
additive at PR 6):

    PR 4 is the controlled introduction of observational side-
    effects into live arbitration surfaces.

    The risk category has shifted from persistence-substrate
    risk to participation-creep risk.

    The call site is the source of the three explicit inputs.

    The integration layer passes truth.

    The integration layer never reconstructs truth.

    The builder does not discover runtime state.

    Capture emission occurs only after arbitration state is
    finalized for the current execution path. Capture records
    completed arbitration observations, not provisional
    intermediate state.

    PR 5 is the second call site under the integration
    discipline PR 4 established. The risk profile is inherited;
    the surface geometry is not.

    The chain-step's deployment identity is the caller's view,
    not the global daemon registry view.

    Ambiguity rejection is an arbitration outcome. Capture must
    record it. ...

    No-dependency coverage at the chain-step surface must be
    measured, not inferred. ...

    PR 6 is the structural backstop for the visual-asymmetry
    pattern. The lint validates shape, not content; structure,
    not interpretation. Carrier content is the room's job;
    field validation is the helper signature's job; the lint
    validates the visual asymmetry between arbitration and
    observation.

    The lint operates by observation, not by participation. It
    reads source files; it does not import the corpus package.
    The lint's own scope is the same one-directional
    observational flow the call sites enforce.

See A.5.3.2-PR6-FRAMING.md and A.5.3.2-PR6-SPEC.md for the
full scope. Failure messages quote the relevant Gate 1 §5.3
prohibition + the relevant PR 5 establishing language for each
rejection criterion (§6.4 of the spec).
"""
```

The full text of all eleven inherited carriers is reproduced in
the docstring. The two PR 6 additive carriers close the docstring.
This is the lint's load-bearing self-documentation; future
contributors reading the file encounter the canonical pattern's
*intent* before reading the validation logic.

**Imports:**

```python
from __future__ import annotations

import ast
import re
from pathlib import Path

import forge_bridge
```

**Forbidden imports** (asserted by `test_lint_imports_no_corpus_modules`,
§6.5.3):

- `forge_bridge.corpus` in any form. The lint reads source files;
  it does not import what it validates.
- Third-party AST tools (`libcst`, `parso`, `asttokens`). Stdlib
  `ast` + line-by-line text introspection is sufficient.

### 4.2 The maintenance surface — `NARROWING_FUNCTION_NAMES`

```python
# Maintenance surface for Rejection 2 (pre-finalization emission).
#
# Protected property (the truth):
#
#     "No additional narrowing operation may occur downstream of
#     finalized arbitration capture."
#
# This constant is the current OPERATIONAL MECHANISM for
# identifying narrowing operations. It is NOT the protected
# property itself.
#
# Renaming or refactoring the narrowing implementations REQUIRES
# a synchronized update to this set. A future PR that renames
# ``filter_tools_by_message`` to (e.g.)
# ``filter_by_message_intent`` without updating this constant
# would silently disable the Rejection 2 enforcement while
# leaving the lint structurally green.
#
# The constant's update is part of any narrowing-rename
# mergeability contract. Reviewers reading a narrowing-rename PR
# must verify this set updates synchronously; the discipline
# carries at the spec layer (A.5.3.2-PR6-FRAMING.md §4.2
# Rejection 2 + this spec §3 risk 6.4).
NARROWING_FUNCTION_NAMES: frozenset[str] = frozenset({
    "filter_tools_by_message",
    "deterministic_narrow",
})
```

**Binding constraints (locked at this spec):**

1. The constant is a `frozenset[str]`, not a list/tuple. Set
   membership is the operational test (`call_name in
   NARROWING_FUNCTION_NAMES`); `frozenset` makes immutability
   explicit and the lookup O(1).
2. The comment block at the constant's definition site MUST
   distinguish *protected property* from *operational
   mechanism*. The framing §4.2 Rejection 2 distinction is
   load-bearing; if the comment block does not document it,
   future contributors will conflate the two and treat the
   constant as the rule.
3. The lint module docstring (§4.1) AND the failure-message
   text for Rejection 2 (§6.4) MUST quote the protected
   property, not the constant's contents. The constant is *how*
   the lint detects; the property is *what* the lint protects.
4. Renaming or expanding the constant requires spec amendment
   (this spec). Adding a third name is itself a forward-narrowing
   maintenance discipline; that addition is in scope when a
   third narrowing implementation lands.

### 4.3 The helper-internal check

**Location:** same module
(`tests/corpus/test_pr6_visual_asymmetry.py`).

**Implementation:**

```python
def test_emit_helper_does_not_internally_call_gate():
    """Validate that ``emit_divergence_capture`` does not
    internally call ``divergence_capture_enabled()`` (silent-
    no-op-on-disabled prohibited pattern).

    Per A.5.3.2-GATE-1-SPEC.md §5.3 first prohibited pattern:
    the gate must live at the call site, not inside the helper.
    A helper that internally checks the gate would visually
    fuse arbitration and observation by hiding the gate from
    the call site, eroding the §5.1 visual asymmetry.

    This check is co-located with the call-site shape lint
    because both protect the same architectural commitment
    (the gate's location at the call site) at different layers
    (call site vs. helper-internal).
    """
    capture_module = (
        Path(forge_bridge.__file__).parent / "corpus" / "_capture.py"
    )
    source = capture_module.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Locate the emit_divergence_capture function definition.
    emit_def: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.FunctionDef)
            and node.name == "emit_divergence_capture"):
            emit_def = node
            break
    assert emit_def is not None, (
        f"emit_divergence_capture definition not found in {capture_module}"
    )

    # Walk the function body for any Call to divergence_capture_enabled.
    offenders: list[int] = []
    for sub in ast.walk(emit_def):
        if (isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "divergence_capture_enabled"):
            offenders.append(sub.lineno)

    assert not offenders, (
        "Gate-inside-helper prohibition violated: "
        "emit_divergence_capture internally calls "
        "divergence_capture_enabled() at line(s) "
        f"{offenders} of {capture_module}.\n"
        "\n"
        "Per A.5.3.2-GATE-1-SPEC.md §5.3 first prohibited "
        "pattern: the gate must live at the call site, not "
        "inside the helper. The visual-asymmetry pattern "
        "(§5.1) requires the `if divergence_capture_enabled():` "
        "guard to be visible at the call site so future "
        "contributors perceive observation as optional and "
        "gated. Folding the gate inside the helper would "
        "visually fuse arbitration and observation, hiding "
        "the gate from the call site.\n"
        "\n"
        "If a future PR genuinely requires helper-internal "
        "gate logic, that requires spec amendment "
        "(A.5.3.2-PR6-SPEC.md §4.3) — not silent absorption."
    )
```

The check is structurally narrow: parse one file, find one
function, walk its body, assert one negative property. ~20 LOC
of test code; ~30 LOC including the failure message that quotes
the relevant Gate 1 §5.3 prohibition.

### 4.4 The lint's AST + text helpers

**Five helper functions** (private to the test module — names
prefixed with `_`):

```python
def _walk_production_tree() -> Iterator[Path]:
    """Yield .py files in forge_bridge/, excluding corpus/ and tests/."""
    package_root = Path(forge_bridge.__file__).parent
    corpus_subtree = package_root / "corpus"
    for py in package_root.rglob("*.py"):
        try:
            py.relative_to(corpus_subtree)
            continue
        except ValueError:
            pass
        yield py


def _find_emit_call_sites(
    tree: ast.AST,
) -> list[
    tuple[
        ast.FunctionDef | ast.AsyncFunctionDef,
        ast.Call,
    ]
]:
    """Walk ``tree`` and return ``(enclosing_function, emit_call)``
    pairs for every ``emit_divergence_capture(...)`` invocation.

    **Ownership is attached at the discovery surface** — the
    enclosing function is captured at the moment the call is
    identified, not reconstructed later via a downstream parent-
    walk inference helper. This aligns with the PR 4/5 moment-of-
    authority lineage: structural truth lives at the discovery
    point, not in inference helpers that reconstruct it after the
    fact.

    A NodeVisitor maintains a function stack so the innermost
    enclosing FunctionDef is captured per emit call. Calls that
    appear at module scope (no enclosing function) are NOT
    surfaced as call sites — the canonical pattern lives inside
    a function by definition (the call sites at handlers.py and
    _step.py are both inside async function bodies).
    """
    sites: list[
        tuple[
            ast.FunctionDef | ast.AsyncFunctionDef,
            ast.Call,
        ]
    ] = []

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._stack: list[
                ast.FunctionDef | ast.AsyncFunctionDef
            ] = []

        def visit_FunctionDef(
            self, node: ast.FunctionDef,
        ) -> None:
            self._stack.append(node)
            self.generic_visit(node)
            self._stack.pop()

        def visit_AsyncFunctionDef(
            self, node: ast.AsyncFunctionDef,
        ) -> None:
            self._stack.append(node)
            self.generic_visit(node)
            self._stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            if (isinstance(node.func, ast.Name)
                and node.func.id == "emit_divergence_capture"
                and self._stack):
                sites.append((self._stack[-1], node))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return sites


def _enclosing_if(tree: ast.AST, target: ast.Call) -> ast.If | None:
    """Return the If statement whose body directly contains target.

    Returns None if the target is not directly contained by an If
    body (e.g., bare call at function scope, or nested deeper).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and stmt.value is target:
                    return node
    return None


def _is_canonical_guard_test(test: ast.expr) -> bool:
    """True iff ``test`` is exactly Call(Name('divergence_capture_enabled'))
    with no args, no keywords, no boolean operators.
    """
    return (
        isinstance(test, ast.Call)
        and isinstance(test.func, ast.Name)
        and test.func.id == "divergence_capture_enabled"
        and not test.args
        and not test.keywords
    )


def _narrowing_call_lines(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[int]:
    """Return line numbers of narrowing-function calls within
    ``function``.

    A call counts if its callee Name's id is in
    NARROWING_FUNCTION_NAMES. The maintenance surface is the
    operational mechanism per §4.2.

    Helper signature expresses actual authority surface — the
    enclosing function — and nothing else. No ``tree`` parameter:
    the search domain IS the function body, not the surrounding
    module. Helper signatures express actual authority surfaces,
    not hypothetical future usage (PR 4/5 truth-vs-mechanism
    discipline).
    """
    return [
        sub.lineno for sub in ast.walk(function)
        if (isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id in NARROWING_FUNCTION_NAMES)
    ]
```

**Three text-introspection helpers:**

```python
_SEPARATOR_PREFIX: str = "# ──"
_BLANK_LINE_RE = re.compile(r"^\s*$")
_COMMENT_LINE_RE = re.compile(r"^\s*#")


def _blank_line_count_above(
    source_lines: list[str], guard_line_index: int,
) -> int:
    """Count contiguous blank lines immediately above ``guard_line_index``.

    ``source_lines`` is zero-indexed; ``guard_line_index`` is the
    zero-indexed line of the ``if divergence_capture_enabled():``
    statement. Returns the count of blank lines walking upward
    from ``guard_line_index - 1`` until a non-blank line is hit.
    """
    count = 0
    i = guard_line_index - 1
    while i >= 0 and _BLANK_LINE_RE.match(source_lines[i]):
        count += 1
        i -= 1
    return count


def _comment_block_above(
    source_lines: list[str], guard_line_index: int,
) -> tuple[int, int] | None:
    """Return (start_idx, end_idx) of the contiguous comment block
    above the blank-line gap, or None if no comment block exists.

    Both indices are zero-indexed and inclusive. The block starts
    at the first comment line walking downward from above the gap
    and ends at the last comment line directly above the gap.
    """
    # Skip the blank-line gap.
    i = guard_line_index - 1
    while i >= 0 and _BLANK_LINE_RE.match(source_lines[i]):
        i -= 1
    if i < 0 or not _COMMENT_LINE_RE.match(source_lines[i]):
        return None
    end = i
    while i >= 0 and _COMMENT_LINE_RE.match(source_lines[i]):
        i -= 1
    start = i + 1
    return (start, end)


def _opens_with_separator(
    source_lines: list[str], block_start_idx: int,
) -> bool:
    """True iff the comment line at ``block_start_idx`` begins with
    the canonical visual separator (per Property D.2).

    Allowing leading whitespace before the ``#`` so indented
    comment blocks are accepted.
    """
    line = source_lines[block_start_idx]
    stripped = line.lstrip()
    return stripped.startswith(_SEPARATOR_PREFIX)
```

These helpers compose into the per-property validators (§5).

### 4.5 What the lint deliberately does NOT do

Per framing §2.2 + §4.2 Rejection 3 + §5, the lint deliberately
does NOT:

- **Read or import any corpus module.** Pure file-system + AST
  + text introspection. (Enforced mechanically by §6.5.3.)
- **Walk module dependency graphs.** No "find every function
  that imports X" or "trace where Y is called from." That is
  Layer 1's responsibility (file-level allowlist) at a coarser
  granularity.
- **Detect cross-file fused helpers.** A `narrow_and_capture`
  helper defined in `_tool_filter.py` and called from
  `handlers.py` is caught at Layer 2 (the helper imports
  `divergence_capture_enabled`, which `_tool_filter.py` is not
  permitted to import). PR 6 does NOT duplicate this coverage.
- **Validate carrier text content.** No grep for specific
  carrier sentences. The flattening pipeline (PR 4 step 6)
  validates byte-identical-as-text presence; the lint validates
  the *structural placement* of the carrier block.
- **Validate field count, field names, or field order.** Helper
  signature's job (Gate 1 §5.2). The lint validates only
  `source="runtime"` (Property C).
- **Lock blank-line counts beyond the 0-or-1 range.** Property
  D.1 explicitly permits 0-or-1; 2+ rejects. Locking "exactly 1"
  would freeze formatting trivia.
- **Lock specific indentation widths.** Properties read line
  prefixes via `lstrip()`; widths vary by surrounding scope and
  must not lock.

If a synthetic-source rejection test or a production-tree
umbrella test surfaces a need for one of these, **stop and re-
scope.** The framing's binding decisions are made at framing
review; spec drafting respects them.

---

## 5. Property + rejection validators (the lint's core logic)

The validators compose Properties A-D and Rejections 1, 2, 4
into a single per-call-site validation pass. Rejection 3 is NOT
a separate validator — per framing §4.2 + §5, it is the named
*consequence* of Properties A-D + Rejections 1, 2, 4 holding.

### 5.1 The umbrella validator

```python
@dataclass(frozen=True)
class _CallSiteFailure:
    file: Path
    lineno: int
    failure_id: str  # e.g., "property_a", "rejection_2", "property_d_1"
    detail: str


def _validate_call_site(
    file: Path,
    source_lines: list[str],
    tree: ast.AST,
    enclosing_function: ast.FunctionDef | ast.AsyncFunctionDef,
    call: ast.Call,
) -> list[_CallSiteFailure]:
    """Validate one ``emit_divergence_capture(...)`` call against the
    canonical pattern. Return a list of failures (empty list = pass).

    Failures accumulate; a single call site can fire multiple
    properties (e.g., a fused-helper scratch fires Property D AND
    Rejection 1 simultaneously). Aggregating failures gives the
    operator a complete picture of the canonical-pattern
    violation, not a halt-on-first-failure that obscures
    secondary breakage.
    """
    failures: list[_CallSiteFailure] = []

    # Property A — guarded invocation.
    if_stmt = _enclosing_if(tree, call)
    if if_stmt is None:
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_a",
            detail=(
                "emit_divergence_capture call is not directly "
                "enclosed by an `if divergence_capture_enabled():` "
                "block (Rejection 1 — gate inside helper)."
            ),
        ))
        # If unguarded, Properties B-D and Rejections 2/4 cannot be
        # evaluated against an if statement that does not exist.
        # Aggregate what we can; bail out of guard-dependent checks.
        return failures

    # Rejection 4 — branch-state gating.
    if not _is_canonical_guard_test(if_stmt.test):
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="rejection_4",
            detail=(
                "Guard's test expression is not exactly "
                "`divergence_capture_enabled()` — gate combined "
                "with branch state via boolean operator or "
                "modified-call-shape."
            ),
        ))

    # Property B — single-statement body.
    if len(if_stmt.body) != 1:
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="property_b",
            detail=(
                f"Guard body contains {len(if_stmt.body)} "
                "statements; canonical pattern requires exactly "
                "one (the emit_divergence_capture call)."
            ),
        ))

    # Property C — keyword-only invocation with source="runtime".
    if call.args:
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_c_positional",
            detail=(
                f"Call has {len(call.args)} positional argument(s); "
                "canonical pattern requires keyword-only arguments."
            ),
        ))
    source_keyword = next(
        (kw for kw in call.keywords if kw.arg == "source"), None,
    )
    if source_keyword is None:
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_c_source_missing",
            detail="Call missing required `source=` keyword.",
        ))
    elif not (
        isinstance(source_keyword.value, ast.Constant)
        and source_keyword.value.value == "runtime"
    ):
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_c_source_value",
            detail=(
                "Call's `source=` keyword is not the literal "
                "string \"runtime\" — schema enum violation."
            ),
        ))

    # Property D — visual grammar (separator → carrier → guard → emission).
    failures.extend(
        _validate_visual_grammar(file, source_lines, if_stmt)
    )

    # Rejection 2 — pre-finalization emission.
    narrowing_lines = _narrowing_call_lines(enclosing_function)
    after_emission = [
        ln for ln in narrowing_lines if ln > if_stmt.end_lineno
    ]
    if after_emission:
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="rejection_2",
            detail=(
                "Protected property violated: no additional "
                "narrowing operation may occur downstream of "
                "finalized arbitration capture. Narrowing "
                f"calls (in NARROWING_FUNCTION_NAMES) at "
                f"line(s) {after_emission} appear after "
                f"emission at line {if_stmt.lineno} in "
                f"{enclosing_function.name}."
            ),
        ))

    return failures
```

**Aggregation rationale:** the validator collects failures rather
than halting at the first. The fused-helper bite-verification
scratch (framing §5 row 3) demonstrates the value: a single
scratch fires Property A + Property D simultaneously, and the
operator sees both failures in the lint output. A halt-on-first
implementation would surface only the first failure and obscure
the structural shape of the breakage.

**Property A short-circuit:** the one exception. If Property A
fails (no enclosing guarded If), Properties B + Rejection 4 +
Property D + Rejection 2 cannot be meaningfully evaluated — they
all reference `if_stmt` which does not exist. The validator
records the Property A failure and returns; downstream properties
are not evaluated. This is the only short-circuit; all other
properties accumulate.

### 5.2 The visual-grammar validator (Property D)

```python
def _validate_visual_grammar(
    file: Path,
    source_lines: list[str],
    if_stmt: ast.If,
) -> list[_CallSiteFailure]:
    """Validate Property D — the four-element grammar:
    separator → carrier block → guard → emission.

    ``if_stmt.lineno`` is one-indexed; convert to zero-indexed for
    list indexing. The guard line itself is at ``if_stmt.lineno - 1``.
    """
    failures: list[_CallSiteFailure] = []
    guard_idx = if_stmt.lineno - 1  # zero-indexed

    # D.1 — blank line semantics (0 or 1 permitted; 2+ rejects).
    blank_count = _blank_line_count_above(source_lines, guard_idx)
    if blank_count > 1:
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="property_d_1",
            detail=(
                f"{blank_count} blank lines between carrier "
                "comment block and guard; canonical pattern "
                "permits 0 or 1. Visual adjacency between "
                "observation block and guard is part of the "
                "canonical shape."
            ),
        ))

    # D.2 — separator placement (block must open with `# ──`).
    block = _comment_block_above(source_lines, guard_idx)
    if block is None:
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="property_d_block_missing",
            detail=(
                "No carrier comment block found above the guard. "
                "Canonical pattern requires a contiguous comment "
                "block (separator → carrier → guard → emission)."
            ),
        ))
    else:
        block_start, _block_end = block
        if not _opens_with_separator(source_lines, block_start):
            failures.append(_CallSiteFailure(
                file=file, lineno=block_start + 1,  # one-indexed
                failure_id="property_d_2",
                detail=(
                    "Carrier comment block does not open with the "
                    f"canonical visual separator '{_SEPARATOR_PREFIX}'. "
                    "The separator must be the opening line of the "
                    "block (Property D.2 lock); presence elsewhere "
                    "in the block is insufficient. The separator "
                    "announces entry into observational asymmetry "
                    "space."
                ),
            ))

    return failures
```

**D.3 — shape-preserving flexibility:** validated by *acceptance*
tests (§6.4 Property D.3 row), not by a separate rejection
validator. The framing §4.1 D.3 vocabulary distinguishes shape-
preserving variation (acceptable, no failure) from shape-eroding
variation (D.1 + D.2 reject). The validators implement this
boundary via what they DO check (D.1, D.2) and what they don't
check (variable names, exact comment count, internal section
breaks).

### 5.3 What the validators do NOT check

- **Carrier text content.** No `grep` for carrier sentences.
  The flattening pipeline (PR 4 step 6) handles byte-identical
  presence.
- **Field names or values beyond `source="runtime"`.** Helper
  signature's job.
- **Variable names of snapshot variables.** `tools` (handlers.py)
  vs. `filtered` (_step.py); both accepted.
- **Ordering of fields in the emission call.** Helper signature
  is keyword-only; order is irrelevant.
- **Number of comment lines in the carrier block.** As long as
  the block is contiguous, opens with the separator, and is
  immediately above the 0-or-1-blank-line gap.
- **Internal section breaks within the carrier block** (e.g.,
  `── PR 5 specializations ──` lines). They are pure-comment
  lines and do not break the block's contiguity.

---

## 6. Test plan

All tests live in `tests/corpus/test_pr6_visual_asymmetry.py`.

### 6.1 Test inventory

| # | Test name | Type | What it validates |
|---|---|---|---|
| 1 | `test_visual_asymmetry_at_all_call_sites` | umbrella, production tree | Walks `forge_bridge/` (per §4.4), discovers every `emit_divergence_capture` call, runs `_validate_call_site` (§5.1) on each, asserts zero failures. |
| 2 | `test_emit_helper_does_not_internally_call_gate` | helper-internal | Per §4.3 — `emit_divergence_capture` in `_capture.py` does not internally call `divergence_capture_enabled`. |
| 3 | `test_lint_imports_no_corpus_modules` | meta | The lint module itself does not import `forge_bridge.corpus`. (§6.5.3.) |
| 4 | `test_lint_rejects_unguarded_emit` | synthetic, Property A / Rejection 1 | Constructs a synthetic source string with bare `emit_divergence_capture(...)` (no guard); asserts validator emits `failure_id="property_a"`. |
| 5 | `test_lint_rejects_branch_state_gate` | synthetic, Rejection 4 | Synthetic source with `if divergence_capture_enabled() and len(filtered) == 1:`; asserts `failure_id="rejection_4"`. |
| 6 | `test_lint_rejects_multi_statement_guard_body` | synthetic, Property B | Synthetic guard body with two statements; asserts `failure_id="property_b"`. |
| 7 | `test_lint_rejects_positional_args` | synthetic, Property C | Synthetic call with one positional arg; asserts `failure_id="property_c_positional"`. |
| 8 | `test_lint_rejects_missing_source_keyword` | synthetic, Property C | Synthetic call without `source=` kwarg; asserts `failure_id="property_c_source_missing"`. |
| 9 | `test_lint_rejects_wrong_source_value` | synthetic, Property C | Synthetic call with `source="seed"`; asserts `failure_id="property_c_source_value"`. |
| 10 | `test_lint_rejects_two_blank_lines_above_guard` | synthetic, Property D.1 | Synthetic source with 2 blank lines between block and guard; asserts `failure_id="property_d_1"`. |
| 11 | `test_lint_rejects_separator_mid_block` | synthetic, Property D.2 | Synthetic source with `# ──` appearing on line 3 of the block instead of opening; asserts `failure_id="property_d_2"`. |
| 12 | `test_lint_rejects_no_carrier_block` | synthetic, Property D | Synthetic source with the guard immediately following code (no comment block); asserts `failure_id="property_d_block_missing"`. |
| 13 | `test_lint_rejects_pre_finalization_emission` | synthetic, Rejection 2 | Synthetic source with `filter_tools_by_message(...)` AFTER the guard block (within the same function); asserts `failure_id="rejection_2"`. |
| 14 | `test_lint_accepts_zero_blank_lines_above_guard` | synthetic, Property D.1 acceptance | Synthetic source with 0 blank lines between block and guard; asserts validator returns empty failure list (shape-preserving flexibility). |
| 15 | `test_lint_accepts_internal_section_break` | synthetic, Property D.3 acceptance | Synthetic source with `── PR N specializations ──` mid-block (mirroring `_step.py`'s actual structure); asserts validator returns empty failure list. |
| 16 | `test_lint_accepts_chat_handler_pattern` | regression, real source | Validator runs on `handlers.py:1166-1203` snippet (extracted at test time via line-range read); asserts empty failure list. Locks the current `handlers.py` shape as canonical. |
| 17 | `test_lint_accepts_chain_step_pattern` | regression, real source | Validator runs on `_step.py:188-247` snippet; asserts empty failure list. Locks the current `_step.py` shape as canonical. |

**17 tests total.** ~14-17 new pytest IDs in the new file
depending on parametrization. The numbers map to:

- 1 production-tree umbrella test (test 1).
- 1 helper-internal test (test 2).
- 1 lint-self meta-test (test 3).
- 10 synthetic-source rejection tests (tests 4-13).
- 2 synthetic-source acceptance tests (tests 14-15).
- 2 real-source regression tests (tests 16-17).

### 6.2 Synthetic-source helper

```python
def _validate_source(source: str) -> list[_CallSiteFailure]:
    """Parse ``source`` and run ``_validate_call_site`` on every
    ``(enclosing_function, emit_call)`` pair surfaced by
    ``_find_emit_call_sites``.

    Returns the aggregated failure list. Used by synthetic-source
    rejection + acceptance tests to exercise the validator
    without mutating production code.

    The synthetic source typically defines a single top-level
    function containing the emission call; the discovery surface
    captures ownership at the moment of identification so the
    helper does not need to know the function's name.
    """
    tree = ast.parse(source)
    source_lines = source.splitlines()

    failures: list[_CallSiteFailure] = []
    for enclosing_function, call in _find_emit_call_sites(tree):
        failures.extend(_validate_call_site(
            file=Path("<synthetic>"),
            source_lines=source_lines,
            tree=tree,
            enclosing_function=enclosing_function,
            call=call,
        ))
    return failures
```

### 6.3 Synthetic source examples

Each rejection test constructs a minimal synthetic source. Below
are representative examples; the spec locks the shape, the
incarnation may adjust formatting details (whitespace, exact
field count) so long as the test exercises the named property.

**Test 4 — unguarded emit (Property A):**

```python
SYNTHETIC = """\
def f():
    emit_divergence_capture(
        prompt="hi",
        registered_tools=[],
        candidate_set_post_reachability=[],
        candidate_set_post_pr14=[],
        narrower_decision=[],
        pr20_condition_met=False,
        collapse_occurred=False,
        ambiguity_state="zero_survivor",
        narrower_latency_ms=0.0,
        source="runtime",
    )
"""
failures = _validate_source(SYNTHETIC)
assert any(f.failure_id == "property_a" for f in failures)
```

**Test 5 — branch-state gate (Rejection 4):**

```python
SYNTHETIC = """\
def f():
    # ── Capture is emitted after arbitration decisions are finalized.
    if divergence_capture_enabled() and len(filtered) == 1:
        emit_divergence_capture(
            prompt="hi", registered_tools=[],
            candidate_set_post_reachability=[],
            candidate_set_post_pr14=[],
            narrower_decision=[],
            pr20_condition_met=False, collapse_occurred=False,
            ambiguity_state="single_survivor",
            narrower_latency_ms=0.0, source="runtime",
        )
"""
failures = _validate_source(SYNTHETIC)
assert any(f.failure_id == "rejection_4" for f in failures)
```

**Test 13 — pre-finalization emission (Rejection 2):**

```python
SYNTHETIC = """\
def f():
    # ── Capture is emitted after arbitration decisions are finalized.
    if divergence_capture_enabled():
        emit_divergence_capture(
            prompt="hi", registered_tools=[],
            candidate_set_post_reachability=[],
            candidate_set_post_pr14=[],
            narrower_decision=[],
            pr20_condition_met=False, collapse_occurred=False,
            ambiguity_state="zero_survivor",
            narrower_latency_ms=0.0, source="runtime",
        )
    # narrowing AFTER emission — Rejection 2 fires.
    filtered = filter_tools_by_message(tools, "hi")
"""
failures = _validate_source(SYNTHETIC)
assert any(f.failure_id == "rejection_2" for f in failures)
```

**Test 15 — internal section break is shape-preserving (D.3 acceptance):**

```python
SYNTHETIC = """\
def f():
    # ── Capture is emitted after arbitration decisions are finalized.
    #
    #    ── PR 5 specializations ──
    #
    #    PR 5 carriers...
    if divergence_capture_enabled():
        emit_divergence_capture(
            prompt="hi", registered_tools=[],
            candidate_set_post_reachability=[],
            candidate_set_post_pr14=[],
            narrower_decision=[],
            pr20_condition_met=False, collapse_occurred=False,
            ambiguity_state="zero_survivor",
            narrower_latency_ms=0.0, source="runtime",
        )
"""
failures = _validate_source(SYNTHETIC)
assert failures == []
```

The remaining synthetic tests follow the same pattern. Spec
captures intent; incarnation captures the exact synthetic source
strings.

### 6.4 Failure-message contract (binding per framing §2.4)

Each rejection's failure message MUST quote the relevant
architectural commitment. The lint is the room's mechanical
memory; failure messages explain *why* the shape matters, not
just *what* is wrong.

| Failure id | Message must quote |
|---|---|
| `property_a` | Gate 1 §5.3 first prohibited pattern (gate-inside-helper) |
| `property_b` | Gate 1 §5.1 single-statement-body part of the canonical pattern |
| `property_c_positional` | Gate 1 §5.2 helper signature (keyword-only) |
| `property_c_source_missing` | Gate 1 §5.2 helper signature; PR 3 schema enum |
| `property_c_source_value` | PR 3 schema enum (`source` ∈ `{"runtime", "seed", ...}`); the value `"runtime"` is the call-site contract |
| `property_d_1` | Framing §4.1 D.1 (0-or-1 blank lines lock); §4.1 D.3 shape-eroding-flexibility vocabulary |
| `property_d_2` | Framing §4.1 D.2 (separator placement lock); the separator's meaning ("observation begins here") |
| `property_d_block_missing` | Framing §4.1 visual-grammar lock (separator → carrier → guard → emission) |
| `rejection_2` | The protected property verbatim ("No additional narrowing operation may occur downstream of finalized arbitration capture") + a note that NARROWING_FUNCTION_NAMES is the operational mechanism, not the truth |
| `rejection_4` | Gate 1 §5.3 (no third prohibition explicitly, but the §5.1 visual asymmetry + PR 5 spec §4.1 arbitration-aware-not-branch-aware language) |

The umbrella production-tree test's aggregated failure message
prepends the framing §0 carriers (the two PR 6 additive carriers)
so the operator reading a CI failure encounters the lint's
posture before the per-call-site failures.

### 6.5 What stays untouched

- `tests/corpus/test_pr3_discipline.py` — Layer 1; unchanged.
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2;
  unchanged.
- `tests/corpus/test_pr4_no_dependency.py` — no-dependency;
  unchanged.
- `tests/corpus/test_pr4_chat_handler_integration.py` — PR 4
  integration bundle; unchanged.
- `tests/corpus/test_pr5_chain_step_integration.py` — PR 5
  integration bundle; unchanged.
- `tests/corpus/_pr4_helpers.py` — fixture and assertion
  helpers; unchanged.
- `tests/corpus/conftest.py` — unchanged.
- All `forge_bridge/` source files — unchanged. Per §2 in scope:
  no production code edits.

### 6.5.3 The lint-self meta-test

```python
def test_lint_imports_no_corpus_modules():
    """The lint itself does not import ``forge_bridge.corpus`` in
    any form. Per A.5.3.2-PR6-FRAMING.md §0 carrier:

        The lint operates by observation, not by participation.
        It reads source files; it does not import the corpus
        package. The lint's own scope is the same one-directional
        observational flow the call sites enforce.

    The same principle the call sites enforce at the production
    tree applies to the lint itself: observation does not
    participate.
    """
    lint_path = Path(__file__)  # tests/corpus/test_pr6_visual_asymmetry.py
    text = lint_path.read_text(encoding="utf-8")

    forbidden = (
        "from forge_bridge.corpus",
        "import forge_bridge.corpus",
    )
    offenders: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue  # Doc references in comments are fine.
        for needle in forbidden:
            if needle in line:
                offenders.append((lineno, stripped))
                break

    assert offenders == [], (
        "Lint participation-creep violated: "
        f"tests/corpus/test_pr6_visual_asymmetry.py imports "
        "forge_bridge.corpus.\n"
        "\n"
        "Per A.5.3.2-PR6-FRAMING.md §0 + §3.2: the lint reads "
        "source files; it does not import what it validates. "
        "Importing the corpus package would put the lint into "
        "the same participation-creep risk surface that the "
        "production allowlist + grep tests already protect "
        "against — and would force the lint module to be added "
        "to ``test_pr3_discipline.py::_ALLOWLIST``, eroding "
        "the bounded-asymmetry's meaning.\n"
        "\n"
        f"Offenders:\n"
        + "\n".join(f"  line {n}: {l}" for n, l in offenders)
    )
```

### 6.6 Test count delta

PR 6 adds:

- **17 new pytest IDs** in `tests/corpus/test_pr6_visual_asymmetry.py`
  (per §6.1 inventory).
- **0 modifications** to any existing test file.

Final count target (forge env, Python 3.11):

- 131 (post-PR-5 baseline) + 17 (new file) = **148 corpus tests
  pass.** Same 4 pre-existing failures (stdio_cleanliness ×2,
  typer_entrypoint ×2 — confirmed unrelated to A.5).

Final count target (forge-bridge env, Python 3.12):

- 125 (post-PR-5 baseline) + 17 (new file) = **142 corpus tests
  pass.** The new file does NOT need jinja2 (no chat-handler
  app construction); the file-skip count remains at 2.

---

## 7. Implementation sequence

The framing §7 cadence-matches-work-depth rule applies:

- **Light-touch review** for plumbing — module skeleton, AST/text
  helpers, NARROWING_FUNCTION_NAMES constant, lint-self meta-
  test.
- **Full three-round review** for the validation logic and the
  bite-verification scratches — the `_validate_call_site`
  + `_validate_visual_grammar` machinery is the participation-
  creep boundary work; the synthetic-source rejection tests are
  load-bearing falsifiability proofs.

The natural sequencing (mirrors PR 5's ten-step shape, adapted
to PR 6's narrower scope):

0. **Schema decision: no bump.** PR 6 explicitly does NOT modify
   the schema. Decision recorded in this spec (§2 out-of-scope)
   and surfaces in the PR 6 commit message body. **No code
   change.** Verification: `git diff` of `forge_bridge/corpus/_schema.py`
   is empty at PR 6 close.

1. **Polish step (reserved).** PR 4 step 1 was the cold-vs-warm
   topology docstring polish. PR 5 step 1 was a no-op. PR 6 step
   1 is reserved for any analogous polish surfaced during spec
   drafting; this spec surfaces none. **Step 1 is a no-op for
   PR 6.** Skipped.

2. **Lint module skeleton.** Create
   `tests/corpus/test_pr6_visual_asymmetry.py` with:
   - The full module docstring (§4.1 verbatim — eleven inherited
     carriers + two PR 6 additive carriers).
   - Imports (`ast`, `re`, `pathlib.Path`, `forge_bridge`).
   - The `NARROWING_FUNCTION_NAMES` frozenset + its load-bearing
     comment block (§4.2).
   - Stub functions for the AST and text helpers (§4.4) — bodies
     are `pass` or `raise NotImplementedError("step 3+")`.
   - The `_CallSiteFailure` dataclass (§5.1).
   - The `_SEPARATOR_PREFIX`, `_BLANK_LINE_RE`, `_COMMENT_LINE_RE`
     module-level constants (§4.4).
   **Light-touch review.** Verification: file exists, imports
   succeed, `pytest --collect-only` finds the file.

3. **AST + text helpers (full bodies).** Implement
   `_walk_production_tree`, `_find_emit_call_sites`,
   `_enclosing_if`, `_is_canonical_guard_test`,
   `_narrowing_call_lines`, `_blank_line_count_above`,
   `_comment_block_above`, `_opens_with_separator` per §4.4.
   `_find_emit_call_sites` returns
   `(enclosing_function, emit_call)` pairs — ownership captured
   at the discovery surface, not reconstructed via downstream
   parent-walk inference. `_narrowing_call_lines` takes only
   the enclosing function (no `tree` parameter); the search
   domain IS the function body. **Light-touch review** — each
   helper is mechanical and small.

4. **Validation logic.** Implement `_validate_call_site` (§5.1)
   and `_validate_visual_grammar` (§5.2). Aggregating failures
   discipline (§5.1 paragraph "Aggregation rationale") locked at
   incarnation. **Full three-round review** — this is the lint's
   load-bearing logic.

5. **Synthetic-source rejection tests** (§6.3). Tests 4-13 plus
   acceptance tests 14-15. Each test:
   - Defines its synthetic source as a triple-quoted module
     constant.
   - Calls `_validate_source` (§6.2).
   - Asserts the expected `failure_id` (rejection tests) OR
     empty failures (acceptance tests).
   **Full three-round review** — synthetic tests prove the
   lint's falsifiability. Reviewers verify the failure assertion
   matches the framing's named property/rejection.

6. **Real-source regression tests** (§6.1 tests 16-17). Read
   `forge_bridge/console/handlers.py:1166-1203` and
   `forge_bridge/console/_step.py:188-247` at test time, run the
   validator on each, assert empty failure list. **Full three-
   round review** — locks the current main as canonical.

7. **Helper-internal check** (§4.3 + §6.1 test 2). Validate
   `emit_divergence_capture` in `_capture.py` does not internally
   call `divergence_capture_enabled`. **Light-touch review** —
   structurally narrow, single-file check.

8. **Production-tree umbrella test** (§6.1 test 1). Walk
   `forge_bridge/`, validate every discovered emit call, assert
   zero aggregated failures. **Light-touch review** — composes
   the helpers + validators from steps 3-4 over the real tree.

9. **Lint-self meta-test** (§6.5.3 + §6.1 test 3). Asserts the
   lint module itself does not import `forge_bridge.corpus`.
   **Light-touch review.**

10. **Bite-verification scratches** (framing §5). Operator
    drives:
    - Apply scratch 1 (remove guard at handlers.py:1185) → run
      the lint → expected fire of `property_a` → revert →
      expected pass.
    - Apply scratch 2 (move emission block before
      `filter_tools_by_message` at handlers.py:1134) → expected
      fire of `rejection_2` → revert.
    - Apply scratch 3 (introduce `narrow_and_capture` helper at
      handlers.py replacing the canonical block) → expected
      fire of `property_a` AND `property_d_block_missing` (per
      framing §5 row 3) → revert.
    - Apply scratch 4 (modify guard at _step.py:233 to add
      `and len(filtered) == 1`) → expected fire of `rejection_4`
      → revert.
    Each scratch + observation + revert is recorded in the PR 6
    close artifact's bite-verification section. **No scratch
    lands in main.** This step is operator-driven and is the
    falsifiability proof; it does not produce a commit.

11. **Run full suite + verify counts.** Both envs (forge 3.11
    and forge-bridge 3.12). Confirm:
    - **148 corpus tests pass in forge env** (131 baseline + 17
      new file IDs).
    - **142 corpus tests pass in forge-bridge env** (125
      baseline + 17 new file IDs).
    - Same 4 pre-existing failures (stdio_cleanliness ×2,
      typer_entrypoint ×2).
    - Chat-handler tests (`tests/console/test_chat_handler.py`)
      — 50/50 unchanged.
    - PR 4 + PR 5 integration tests under all four capture
      states pass unchanged.

12. **Surface for review** (writer's-room cadence). Steps 4 + 5
    + 6 receive full three-round review; surrounding steps run
    light-touch.

**Natural pause points** (per framing §7 pacing clause):

- Between step 3 and step 4 — verifies the AST/text helpers
  in isolation before the validator's aggregation logic layers
  on top. A small probe (`python -c "from
  test_pr6_visual_asymmetry import _walk_production_tree;
  print(list(_walk_production_tree()))"`) confirms discovery
  works before the validator is invoked.
- Between step 6 and step 7 — verifies the validator passes
  against current main before the helper-internal check +
  umbrella test layer their full assertion machinery on top.
- Between step 9 and step 10 — verifies the lint test suite
  passes green before bite-verification scratches start
  introducing intentional failures.

A smaller pause point may surface between step 0 and step 2 if
the schema-decision verification surfaces any unexpected diff.

---

## 8. Phase-end conditions for PR 6

| Trigger | Response |
|---|---|
| All 17 new tests pass + production-tree umbrella test passes against current main + helper-internal check passes + lint-self meta-test passes + all four bite-verification scratches fire the expected failure_id when applied and pass when reverted | PR 6 closes; Gate 1 closes; Gate 2 framing drafts. |
| `test_visual_asymmetry_at_all_call_sites` regresses on a future PR | Hard CI failure; the canonical pattern has been violated at one or more call sites. The aggregated failure message names which Properties/Rejections fired; review surfaces the framing-level violation and routes the offender (a) revert the offending change, OR (b) spec amendment if the change is genuinely needed. |
| `test_emit_helper_does_not_internally_call_gate` regresses on a future PR | Hard CI failure; the gate-inside-helper prohibition has been violated at the helper layer. Reject at CI; review surfaces Gate 1 §5.3 first prohibited pattern. |
| `test_lint_imports_no_corpus_modules` regresses on a future PR | The lint has acquired a corpus dependency; the framing §0 carrier "the lint operates by observation, not by participation" has been violated. Reject at CI; review surfaces the framing's discipline. |
| A future PR proposes to add a fifth Property (E, F, ...) or a fifth Rejection (5, 6, ...) | Spec amendment required (this spec). The four properties + four rejections (with Rejection 3 as consequence, not standalone) are framing-locked at §4.1 + §4.2; expanding the validator's scope re-opens the framing. |
| A future PR proposes to remove `NARROWING_FUNCTION_NAMES` and replace it with a positive-condition lint ("narrowing must come before emission") | Rejected at the spec layer per framing §4.2 Rejection 2. The negative property is mechanically narrow and resists drift; a positive condition would couple the lint to the specific shape of the arbitration pipeline. |
| A future PR proposes to make the lint walk module dependency graphs to detect cross-file fused helpers | Rejected at the spec layer per framing §4.2 Rejection 3 + §5. PR 6 owns Layer 3 only. Cross-module fused-helper drift is caught at Layers 1 + 2; adding redundant coverage in Layer 3 is itself a participation-creep risk for the lint. If the existing layers genuinely have a coverage gap, the response is to extend Layer 1 or Layer 2's allowlist/grep, not to expand Layer 3's scope. |
| A future PR proposes to add a `narrow_with_capture(...)` helper or any other arbitration-and-emission fusion | Rejected at the spec layer per Gate 1 §5.3 + framing §4.2 Rejection 3. The fused-helper prohibition is a named architectural commitment; the lint's enforcement of it via Properties A-D + Rejections 1, 2, 4 does NOT need a separate "fusion check" to be effective. |
| A future PR proposes to validate carrier text content (grep for specific carrier sentences) | Rejected at the spec layer per framing §2.2. The flattening pipeline (PR 4 step 6) validates byte-identicality at the text level; the lint validates structural placement. Doubling the coverage would create a maintenance vector (every carrier-rewording PR would update both). |
| A future PR proposes to lock blank-line counts to "exactly 1" (removing the 0-or-1 flexibility) | Rejected at the spec layer per framing §4.1 D.1 + D.3. "Exactly 1" elevates formatting trivia into invariant status; the 0-or-1 range preserves visual adjacency without locking. |
| A future PR proposes to re-deferral-stage the visual-asymmetry lint ("we don't actually need this; the human reviewers can catch it") | Rejected at the spec layer per framing §2.4. The lint is the room's mechanical memory; reviewer attention is finite and turnover is real. The framing §2.4 rationale is binding. |

---

## 9. Cross-references

- `A.5.3.2-PR6-FRAMING.md` (this commit) — this spec's binding
  pre-spec contract; resolves discovery (§3.2), hybrid AST + text
  validation (§4.3), Property D visual grammar lock (§4.1),
  NARROWING_FUNCTION_NAMES maintenance surface (§4.2 Rejection 2),
  Layer-3-only scope discipline (§4.2 Rejection 3 + §5).
- `A.5.3.2-PR5-CLOSE.md` (commit `b8f522e`) — durable archival
  state PR 6 inherits; §1 establishes; §2 inheritance; §3
  changes; §4 queued future work; §5 methodology observations.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (binding for Properties A-D acceptance criteria).
- `A.5.3.2-GATE-1-SPEC.md` §5.2 — helper signature (binding for
  Property C `source="runtime"` validation; the lint does NOT
  re-validate fields beyond `source`).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-
  prohibited patterns (binding for Rejections 1, 2, 3; PR 5 spec
  §4.1 adds Rejection 4).
- `A.5.3.2-PR4-FRAMING.md` §1.1 — visual-asymmetry deferral
  rationale; expiry condition (two operational call sites)
  satisfied at PR 6 entry.
- `A.5.3.2-PR4-FRAMING.md` §3 — integration-discipline quartet;
  carriers travel into the lint module docstring.
- `A.5.3.2-PR4-SPEC.md` §0 — finalized-state contract; binding
  for Rejection 2 (pre-finalization emission).
- `A.5.3.2-PR5-FRAMING.md` (commit `2ae187a`) — surface geometry
  asymmetry; PR 5's four additive carriers travel into the lint
  module docstring alongside PR 4's seven.
- `A.5.3.2-PR5-SPEC.md` §4.1 — arbitration-aware-not-branch-
  aware framing; binding for Rejection 4.
- `A.5.3.2-PR3-SPEC.md` §10 — discipline grep mechanism;
  inspiration for the structural-test pattern PR 6 extends to
  Layer 3.
- `forge_bridge/console/handlers.py:1166-1203` — chat-handler
  integration site; first lint regression input (test 16).
- `forge_bridge/console/_step.py:188-247` — chain-step integration
  site; second lint regression input (test 17).
- `forge_bridge/corpus/_capture.py::emit_divergence_capture` —
  helper definition; subject to the §4.3 helper-internal check
  (test 2).
- `tests/corpus/test_pr3_discipline.py` — Layer 1 (file-level
  allowlist); unchanged at PR 6.
- `tests/corpus/test_pr4_participation_creep.py` — Layer 2
  (import-symbol allowlist); unchanged at PR 6.
- `tests/corpus/test_pr6_visual_asymmetry.py` — Layer 3 (call-
  site shape; **PR 6 creates this file**).
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` — promotion
  candidate for the three-layer structural-test discipline
  observation (framing §2.3) and the truth-vs-mechanism
  distinction (framing §4.2 Rejection 2 + spec §4.2).
- `SEED-PYTHON-3.13-MIGRATION-V1.5+.md` — migration trajectory,
  queued behind Gate 1.

---

## Resume protocol — what the next session does with this spec

1. **Read the framing first** (`A.5.3.2-PR6-FRAMING.md`). The
   five binding decisions (§3.2 discovery, §4.1 visual grammar,
   §4.2 maintenance surface, §4.2 Rejection 3 Layer-3-only
   scope, §4.3 hybrid validation) are the load-bearing context;
   skipping them is how the lint accidentally collapses scope
   or acquires global-coupling-analysis responsibilities.
2. **Read this spec.** Confirm the four risks → named tests
   mapping (§3); the lint module surface (§4); the validator
   logic (§5); the test inventory (§6.1); the failure-message
   contract (§6.4); the implementation sequencing (§7); the
   phase-end conditions (§8).
3. **Surface for review** before any code is written. Per the
   established discipline, the spec is reviewed; deviations
   re-open the artifact for explicit re-review, not absorbed
   silently.
4. **Implement** against the test inventory in §6.1, in the
   sequence from §7. Steps 4 + 5 + 6 receive full three-round
   review; surrounding plumbing runs light-touch.
5. **Run the existing structural tests** (Layer 1 + Layer 2 +
   no-dependency + integration bundles) before committing each
   step. All must remain green at every step boundary; the lint
   only adds Layer 3, it does not modify Layers 1 or 2.
6. **Drive the bite-verification scratches** at step 10. Each
   scratch + revert is recorded in the PR 6 close artifact's
   bite-verification section; no scratch lands in main.
7. **Commit** with the thirteen carrier sentences distributed
   across the lint module docstring (§4.1 lays them out
   verbatim) and the PR 6 commit message body.
8. **Close PR 6 with `A.5.3.2-PR6-CLOSE.md`** following the PR 5
   close artifact's structure. **Gate 1 closes when PR 6
   closes.** The close artifact reseeds the room for Gate 2
   framing.

Do not begin implementing without re-reading the framing. The
NARROWING_FUNCTION_NAMES truth-vs-mechanism distinction (framing
§4.2 + spec §4.2) and the Layer-3-only scope discipline (framing
§4.2 Rejection 3 + spec §5 + §8 phase-end) are the most likely
sites of silent drift if the framing is short-circuited.
