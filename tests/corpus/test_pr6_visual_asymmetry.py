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
    record it. At this surface, narrower_decision carries the
    filtered list verbatim at narrowing finalization — including
    zero-match and multi-match rejection paths. pr20_condition_met
    is always False and collapse_occurred is False on all
    rejection paths. These semantics differ from the chat-handler
    case and must not be silently overloaded.

    No-dependency coverage at the chain-step surface must be
    measured, not inferred. The existing probe drives only the
    chat-handler single-step path; PR 5 owns the responsibility
    to extend coverage to the chain-step path empirically.

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
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import forge_bridge


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
# Rejection 2 + A.5.3.2-PR6-SPEC.md §3 risk 6.4).
NARROWING_FUNCTION_NAMES: frozenset[str] = frozenset({
    "filter_tools_by_message",
    "deterministic_narrow",
})


_SEPARATOR_PREFIX: str = "# ──"
_BLANK_LINE_RE = re.compile(r"^\s*$")
_COMMENT_LINE_RE = re.compile(r"^\s*#")


@dataclass(frozen=True)
class _CallSiteFailure:
    """One canonical-pattern violation at one call site.

    ``failure_id`` is a stable, machine-readable identifier
    (e.g., ``"property_a"``, ``"rejection_2"``,
    ``"property_d_1"``) that synthetic-source rejection tests
    assert against. ``detail`` is the human-readable failure
    message that quotes the relevant architectural commitment
    per the §6.4 failure-message contract.
    """
    file: Path
    lineno: int
    failure_id: str
    detail: str


# ---------------------------------------------------------------------------
# AST + text helpers (per A.5.3.2-PR6-SPEC.md §4.4).
# ---------------------------------------------------------------------------

def _walk_production_tree() -> Iterator[Path]:
    """Yield .py files in forge_bridge/, excluding corpus/.

    The lint walks the production tree to discover candidate call
    sites for ``emit_divergence_capture(...)``. The corpus subtree
    itself is excluded — it defines the helper, it does not invoke
    it. Tests under ``tests/`` are not part of the production tree.
    """
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
) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.Call]]:
    """Walk ``tree`` and return ``(enclosing_function, emit_call)``
    pairs for every ``emit_divergence_capture(...)`` invocation.

    Ownership is attached at the discovery surface — the enclosing
    function is captured at the moment the call is identified, not
    reconstructed later via a downstream parent-walk inference
    helper. This aligns with the PR 4/5 moment-of-authority
    lineage: structural truth lives at the discovery point, not in
    inference helpers that reconstruct it after the fact.

    A NodeVisitor maintains a function stack so the innermost
    enclosing FunctionDef is captured per emit call. Calls that
    appear at module scope (no enclosing function) are NOT
    surfaced — the canonical pattern lives inside a function by
    definition.
    """
    sites: list[
        tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.Call]
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
    """Return the If statement whose body directly contains
    ``target``'s expression statement.

    Returns None if ``target`` is not directly contained by an If
    body (e.g., a bare call at function scope, or a call nested
    inside a deeper expression).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and stmt.value is target:
                    return node
    return None


def _is_canonical_guard_test(test: ast.expr) -> bool:
    """True iff ``test`` is exactly
    ``Call(Name('divergence_capture_enabled'))`` with no args, no
    keywords, no boolean operators.

    Patterns like ``divergence_capture_enabled() and len(filtered)
    == 1`` (BoolOp) are rejected here — Property A's canonical
    guard shape is the bare zero-arg call, not any larger boolean
    expression that happens to include it.
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
    NARROWING_FUNCTION_NAMES (the operational mechanism per §4.2).
    The constant is *how* the lint detects narrowing; the
    protected property is *that* no narrowing occurs downstream of
    finalized arbitration capture.

    Helper signature expresses actual authority surface — the
    enclosing function — and nothing else. The search domain IS
    the function body.
    """
    return [
        sub.lineno for sub in ast.walk(function)
        if (isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id in NARROWING_FUNCTION_NAMES)
    ]


def _blank_line_count_above(
    source_lines: list[str], guard_line_index: int,
) -> int:
    """Count contiguous blank lines immediately above
    ``guard_line_index``.

    ``source_lines`` is zero-indexed; ``guard_line_index`` is the
    zero-indexed line of the ``if divergence_capture_enabled():``
    statement. Walks upward from ``guard_line_index - 1`` until a
    non-blank line is hit; returns the count of blank lines
    traversed.
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
    """Return ``(start_idx, end_idx)`` of the contiguous comment
    block above the blank-line gap, or None if no comment block
    exists.

    Both indices are zero-indexed and inclusive. The block ends at
    the last comment line directly above the gap and begins at the
    first comment line walking upward from there. Pure-comment
    lines (lines whose first non-whitespace character is ``#``)
    constitute the block.
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

    Leading whitespace before the ``#`` is allowed so indented
    comment blocks (the call sites' actual shape) are accepted.
    """
    line = source_lines[block_start_idx]
    stripped = line.lstrip()
    return stripped.startswith(_SEPARATOR_PREFIX)


# ---------------------------------------------------------------------------
# Validation logic (per A.5.3.2-PR6-SPEC.md §5).
# ---------------------------------------------------------------------------
#
# The validators compose Properties A-D and Rejections 1, 2, 4
# into a single per-call-site validation pass. Rejection 3 is NOT
# a separate validator — per A.5.3.2-PR6-FRAMING.md §4.2 + §5, it
# is the named *consequence* of Properties A-D + Rejections 1, 2,
# 4 holding. PR 6 owns Layer 3 only; cross-module fused-helper
# drift is caught at Layers 1 + 2.
#
# Aggregation rationale: failures accumulate rather than
# halt-on-first. A single fused-helper scratch fires Property A +
# Property D simultaneously; the operator should see both
# failures in the lint output, not just the first. The single
# exception is the Property A short-circuit — if the call has no
# enclosing guarded If, downstream property checks reference an
# `if_stmt` that does not exist; the validator records the
# Property A failure and returns.

# Failure-message preludes — quoted in each per-rejection detail
# so the operator reading a CI failure encounters the
# architectural commitment, not just a structural mismatch
# (per A.5.3.2-PR6-FRAMING.md §2.4: "the lint is the room's
# mechanical memory").

_PROPERTY_A_PRELUDE = (
    "Per A.5.3.2-GATE-1-SPEC.md §5.3 first prohibited pattern: "
    "the gate must live at the call site, not inside the helper. "
    "The visual-asymmetry pattern (§5.1) requires the "
    "`if divergence_capture_enabled():` guard to be visible at "
    "the call site so future contributors perceive observation "
    "as optional and gated."
)

_PROPERTY_B_PRELUDE = (
    "Per A.5.3.2-GATE-1-SPEC.md §5.1 canonical pattern: the "
    "guard's body contains exactly one statement — the "
    "`emit_divergence_capture(...)` call. Additional statements "
    "would visually fuse capture with surrounding logic and "
    "erode the asymmetry between observation and arbitration."
)

_PROPERTY_C_PRELUDE = (
    "Per A.5.3.2-GATE-1-SPEC.md §5.2 helper signature: the call "
    "is keyword-only with `source=\"runtime\"` (PR 3 schema "
    "enum). The lint validates only the structural enum value; "
    "field count, names, and order are the helper signature's "
    "job."
)

_PROPERTY_D_1_PRELUDE = (
    "Per A.5.3.2-PR6-FRAMING.md §4.1 D.1 (visual grammar lock): "
    "0 or 1 blank lines permitted between the carrier comment "
    "block and the guard. Locking 'exactly 1' would elevate "
    "formatting trivia into invariant status; permitting 2+ "
    "would erode adjacency entirely. The 0-or-1 range is "
    "shape-preserving flexibility; 2+ is shape-eroding."
)

_PROPERTY_D_2_PRELUDE = (
    "Per A.5.3.2-PR6-FRAMING.md §4.1 D.2 (separator placement "
    "lock): the canonical visual separator must be the OPENING "
    "line of the comment block. Presence elsewhere in the block "
    "is insufficient — the separator's specific position carries "
    "the meaning 'observation begins here, distinct from "
    "arbitration above'; that meaning evaporates if the "
    "separator can drift within the block."
)

_PROPERTY_D_BLOCK_MISSING_PRELUDE = (
    "Per A.5.3.2-PR6-FRAMING.md §4.1 D (visual grammar lock): "
    "the canonical pattern is separator → carrier block → guard "
    "→ emission. A guard without a preceding carrier block has "
    "no observational header; future readers would not perceive "
    "this code as 'observation, distinct from arbitration'."
)

_REJECTION_2_PRELUDE = (
    "Protected property violated: \"No additional narrowing "
    "operation may occur downstream of finalized arbitration "
    "capture.\" "
    "(NARROWING_FUNCTION_NAMES is the operational mechanism for "
    "identifying narrowing calls — NOT the protected property "
    "itself. Per A.5.3.2-PR6-FRAMING.md §4.2 Rejection 2: the "
    "constant is *how* the lint detects; the property is *what* "
    "the lint protects.) "
    "Per A.5.3.2-GATE-1-SPEC.md §5.3 third prohibited pattern: "
    "capture is a record OF the decision, not an observer "
    "INSIDE the decision pipeline."
)

_REJECTION_4_PRELUDE = (
    "Per A.5.3.2-PR5-SPEC.md §4.1 (arbitration-aware, not "
    "branch-aware): emission is gated on "
    "`divergence_capture_enabled()`, NOT on success/failure "
    "branches. The single insertion point preserves capture's "
    "relationship to the arbitration event itself, not to its "
    "downstream semantic interpretations. A guard that combines "
    "the gate with branch state via boolean operator collapses "
    "this distinction."
)


def _validate_visual_grammar(
    file: Path,
    source_lines: list[str],
    if_stmt: ast.If,
) -> list[_CallSiteFailure]:
    """Validate Property D — the four-element visual grammar:
    separator → carrier block → guard → emission.

    ``if_stmt.lineno`` is one-indexed (Python AST convention);
    convert to zero-indexed for source_lines list indexing. The
    guard line itself is at ``if_stmt.lineno - 1``.
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
                "permits 0 or 1.\n\n"
                + _PROPERTY_D_1_PRELUDE
            ),
        ))

    # D.2 — separator placement (block must open with `# ──`).
    block = _comment_block_above(source_lines, guard_idx)
    if block is None:
        failures.append(_CallSiteFailure(
            file=file, lineno=if_stmt.lineno,
            failure_id="property_d_block_missing",
            detail=(
                "No carrier comment block found above the "
                "guard.\n\n"
                + _PROPERTY_D_BLOCK_MISSING_PRELUDE
            ),
        ))
    else:
        block_start, _block_end = block
        if not _opens_with_separator(source_lines, block_start):
            failures.append(_CallSiteFailure(
                file=file, lineno=block_start + 1,  # one-indexed
                failure_id="property_d_2",
                detail=(
                    "Carrier comment block does not open with "
                    f"the canonical visual separator "
                    f"'{_SEPARATOR_PREFIX}'.\n\n"
                    + _PROPERTY_D_2_PRELUDE
                ),
            ))

    return failures


def _validate_call_site(
    file: Path,
    source_lines: list[str],
    tree: ast.AST,
    enclosing_function: ast.FunctionDef | ast.AsyncFunctionDef,
    call: ast.Call,
) -> list[_CallSiteFailure]:
    """Validate one ``emit_divergence_capture(...)`` call against
    the canonical pattern. Return a list of failures (empty list =
    pass).

    Failures accumulate; a single call site can fire multiple
    properties simultaneously. The Property A short-circuit is
    the one exception — if no enclosing guarded If exists,
    downstream property checks reference an `if_stmt` that does
    not exist, so the validator records the Property A failure
    and returns.
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
                "block (Rejection 1 — gate inside helper).\n\n"
                + _PROPERTY_A_PRELUDE
            ),
        ))
        # If unguarded, Properties B/C/D and Rejections 2/4 cannot
        # be evaluated against an if statement that does not exist.
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
                "modified-call-shape.\n\n"
                + _REJECTION_4_PRELUDE
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
                "one (the emit_divergence_capture call).\n\n"
                + _PROPERTY_B_PRELUDE
            ),
        ))

    # Property C — keyword-only invocation with source="runtime".
    if call.args:
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_c_positional",
            detail=(
                f"Call has {len(call.args)} positional "
                "argument(s); canonical pattern requires "
                "keyword-only arguments.\n\n"
                + _PROPERTY_C_PRELUDE
            ),
        ))
    source_keyword = next(
        (kw for kw in call.keywords if kw.arg == "source"), None,
    )
    if source_keyword is None:
        failures.append(_CallSiteFailure(
            file=file, lineno=call.lineno,
            failure_id="property_c_source_missing",
            detail=(
                "Call missing required `source=` keyword.\n\n"
                + _PROPERTY_C_PRELUDE
            ),
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
                "string \"runtime\" — schema enum violation.\n\n"
                + _PROPERTY_C_PRELUDE
            ),
        ))

    # Property D — visual grammar.
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
                f"Narrowing calls (in NARROWING_FUNCTION_NAMES) "
                f"at line(s) {after_emission} appear after "
                f"emission at line {if_stmt.lineno} in "
                f"`{enclosing_function.name}`.\n\n"
                + _REJECTION_2_PRELUDE
            ),
        ))

    return failures


# ---------------------------------------------------------------------------
# Synthetic-source helper + tests (per A.5.3.2-PR6-SPEC.md §6.2 + §6.3).
# ---------------------------------------------------------------------------

def _validate_source(source: str) -> list[_CallSiteFailure]:
    """Parse ``source`` and run ``_validate_call_site`` on every
    ``(enclosing_function, emit_call)`` pair surfaced by
    ``_find_emit_call_sites``.

    Used by synthetic-source rejection + acceptance tests to
    exercise the validator without mutating production code.
    Ownership comes from the discovery surface — the helper does
    not need to know the function's name.
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


def _failure_ids(failures: list[_CallSiteFailure]) -> set[str]:
    """Return the set of distinct ``failure_id`` values in
    ``failures``. Used by rejection tests to assert the lint fires
    the named property/rejection without locking on count or
    line numbers (which are incarnation-specific).
    """
    return {f.failure_id for f in failures}


# ----- Rejection tests (one per failure_id) --------------------------------


def test_lint_rejects_unguarded_emit():
    """Property A — ``emit_divergence_capture`` called without an
    enclosing ``if divergence_capture_enabled():`` guard. Per
    A.5.3.2-GATE-1-SPEC.md §5.3 first prohibited pattern.
    """
    synthetic = (
        "def f():\n"
        "    emit_divergence_capture(\n"
        '        prompt="hi", source="runtime",\n'
        "    )\n"
    )
    assert "property_a" in _failure_ids(_validate_source(synthetic))


def test_lint_rejects_branch_state_gate():
    """Rejection 4 — guard combines ``divergence_capture_enabled()``
    with branch state via boolean operator. Per A.5.3.2-PR5-SPEC.md
    §4.1: capture is arbitration-aware, not branch-aware.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled() and len(filtered) == 1:\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert "rejection_4" in _failure_ids(_validate_source(synthetic))


def test_lint_rejects_multi_statement_guard_body():
    """Property B — guard body contains more than one statement.
    Per A.5.3.2-GATE-1-SPEC.md §5.1 canonical pattern: the body
    is exactly the ``emit_divergence_capture(...)`` call.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
        "        x = 1  # second statement — Property B fires\n"
    )
    assert "property_b" in _failure_ids(_validate_source(synthetic))


def test_lint_rejects_positional_args():
    """Property C — call uses positional arguments. Per
    A.5.3.2-GATE-1-SPEC.md §5.2 helper signature: keyword-only.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            "hi", source="runtime",\n'
        "        )\n"
    )
    assert "property_c_positional" in _failure_ids(
        _validate_source(synthetic),
    )


def test_lint_rejects_missing_source_keyword():
    """Property C — call missing required ``source=`` keyword.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi",\n'
        "        )\n"
    )
    assert "property_c_source_missing" in _failure_ids(
        _validate_source(synthetic),
    )


def test_lint_rejects_wrong_source_value():
    """Property C — ``source=`` keyword's literal value is not
    ``"runtime"``. Per PR 3 schema enum: at this layer the call-
    site contract is exactly ``source="runtime"``.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="seed",\n'
        "        )\n"
    )
    assert "property_c_source_value" in _failure_ids(
        _validate_source(synthetic),
    )


def test_lint_rejects_two_blank_lines_above_guard():
    """Property D.1 — 2+ blank lines between carrier comment block
    and guard. Per A.5.3.2-PR6-FRAMING.md §4.1 D.1: the canonical
    pattern permits 0 or 1 blank lines; 2+ is shape-eroding
    flexibility.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "\n"
        "\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert "property_d_1" in _failure_ids(_validate_source(synthetic))


def test_lint_rejects_separator_mid_block():
    """Property D.2 — canonical visual separator does not appear
    on the OPENING line of the carrier comment block. Per
    A.5.3.2-PR6-FRAMING.md §4.1 D.2: presence elsewhere is
    insufficient.
    """
    synthetic = (
        "def f():\n"
        "    # not the separator opening\n"
        "    # ── separator landed mid-block instead\n"
        "    # more carrier text\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert "property_d_2" in _failure_ids(_validate_source(synthetic))


def test_lint_rejects_no_carrier_block():
    """Property D — guard immediately follows code with no carrier
    comment block. Per A.5.3.2-PR6-FRAMING.md §4.1 D: the
    canonical grammar is separator → carrier → guard → emission.
    """
    synthetic = (
        "def f():\n"
        "    x = 1\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert "property_d_block_missing" in _failure_ids(
        _validate_source(synthetic),
    )


def test_lint_rejects_pre_finalization_emission():
    """Rejection 2 — narrowing call appears AFTER the
    ``emit_divergence_capture`` block within the same function.
    Per A.5.3.2-GATE-1-SPEC.md §5.3 third prohibited pattern:
    capture is a record OF the decision, not an observer INSIDE
    the decision pipeline.

    The protected property — "No additional narrowing operation
    may occur downstream of finalized arbitration capture" — is
    the truth; NARROWING_FUNCTION_NAMES is the operational
    mechanism (per A.5.3.2-PR6-FRAMING.md §4.2 Rejection 2).
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
        "    filtered = filter_tools_by_message(tools, 'hi')\n"
    )
    assert "rejection_2" in _failure_ids(_validate_source(synthetic))


# ----- Acceptance tests (shape-preserving flexibility) ---------------------


def test_lint_accepts_zero_blank_lines_above_guard():
    """Property D.1 acceptance — 0 blank lines between carrier
    comment block and guard. Per A.5.3.2-PR6-FRAMING.md §4.1 D.1:
    the 0-or-1 range is shape-preserving flexibility; locking
    "exactly 1" would elevate formatting trivia into invariant
    status.
    """
    synthetic = (
        "def f():\n"
        "    # ── header\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert _validate_source(synthetic) == []


def test_lint_accepts_internal_section_break():
    """Property D.3 acceptance — internal ``── PR N specializations
    ──`` separator appears mid-block (mirroring _step.py's actual
    structure). The carrier block remains contiguous; the OPENING
    separator is preserved at the block's top. Per
    A.5.3.2-PR6-FRAMING.md §4.1 D.3: this is shape-preserving
    flexibility, not shape-eroding.
    """
    synthetic = (
        "def f():\n"
        "    # ── Capture is emitted after arbitration finalized\n"
        "    #\n"
        "    #    ── PR 5 specializations ──\n"
        "    #\n"
        "    #    further carrier text\n"
        "    if divergence_capture_enabled():\n"
        "        emit_divergence_capture(\n"
        '            prompt="hi", source="runtime",\n'
        "        )\n"
    )
    assert _validate_source(synthetic) == []


# ---------------------------------------------------------------------------
# Real-source regression tests (per A.5.3.2-PR6-SPEC.md §6.1 tests 16-17).
# ---------------------------------------------------------------------------
#
# These tests lock the current handlers.py + _step.py call-site
# shapes as canonical. They run the validator over the actual
# production source (NOT a synthetic snippet) and assert empty
# failure list.
#
# A future PR that mutates the canonical pattern at either site
# fires a structural assertion here BEFORE the umbrella test
# (step 8) catches it across the whole tree, giving the operator
# a more focused failure message.
#
# Test scope is the FILE, not a line range — the validator
# discovers emit calls via _find_emit_call_sites; we filter to
# the named function so changes to surrounding code do not
# accidentally turn this test green by routing through a
# different surface.


def _validate_production_file_function(
    file_relative: str, function_name: str,
) -> list[_CallSiteFailure]:
    """Read ``file_relative`` (relative to forge_bridge/), parse,
    discover emit call sites, filter to those whose enclosing
    function matches ``function_name``, validate each, return the
    aggregated failure list.
    """
    package_root = Path(forge_bridge.__file__).parent
    target = package_root / file_relative
    source = target.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    tree = ast.parse(source)

    failures: list[_CallSiteFailure] = []
    for enclosing_function, call in _find_emit_call_sites(tree):
        if enclosing_function.name != function_name:
            continue
        failures.extend(_validate_call_site(
            file=target,
            source_lines=source_lines,
            tree=tree,
            enclosing_function=enclosing_function,
            call=call,
        ))
    return failures


def test_lint_accepts_chat_handler_pattern():
    """Locks ``forge_bridge/console/handlers.py::chat_handler``'s
    canonical shape as accepted. PR 4 step 6 landing.

    A failure here means a future PR has mutated the chat-
    handler's emit call site shape away from the canonical
    pattern. Per A.5.3.2-PR6-SPEC.md §8 phase-end conditions:
    review surfaces which Property/Rejection fired and routes
    the offender (revert the change OR spec amendment if the
    change is genuinely needed).
    """
    failures = _validate_production_file_function(
        "console/handlers.py", "chat_handler",
    )
    assert failures == [], (
        "chat_handler call-site shape regression:\n"
        + "\n".join(
            f"  {f.failure_id} at {f.file.name}:{f.lineno}\n"
            f"    {f.detail}"
            for f in failures
        )
    )


def test_lint_accepts_chain_step_pattern():
    """Locks ``forge_bridge/console/_step.py::execute_chain_step``'s
    canonical shape as accepted. PR 5 step 6 landing.

    A failure here means a future PR has mutated the chain-step
    emit call site shape away from the canonical pattern. The
    site differs from chat_handler in field semantics
    (pr20_condition_met=False; ambiguity rejection captures the
    filtered list verbatim) but the structural shape is
    identical — Property D's separator → carrier → guard →
    emission grammar applies symmetrically.
    """
    failures = _validate_production_file_function(
        "console/_step.py", "execute_chain_step",
    )
    assert failures == [], (
        "execute_chain_step call-site shape regression:\n"
        + "\n".join(
            f"  {f.failure_id} at {f.file.name}:{f.lineno}\n"
            f"    {f.detail}"
            for f in failures
        )
    )
