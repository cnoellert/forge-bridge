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
