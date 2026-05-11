"""forge_bridge.corpus._seed — seed driver + authored-expectation
helper.

This module is the seed-driver authority surface for Gate 2. It
houses two public-from-corpus helpers — ``emit_seed_expectation``
and ``drive_seed_fixture`` — that author declared expectations and
orchestrate single-fixture invocations through the chat-handler
arbitration pipeline. The module is consumed by PR 9 fixtures and
by future Gate 4 comparator regression tests; PR 8 ships zero
production call sites.

This module is a corpus-adjacent orchestration surface whose
purpose is to drive the live arbitration surface in-process. It
is the exception surface — not a generalized corpus → console
direction. No other corpus module may acquire a
``forge_bridge.console`` import without framing-level review (see
``A.5.3.2-PR8-SPEC.md`` §2 out-of-scope #13).

This module is a SKELETON at PR 8 Step 1. The three functions
(``emit_seed_expectation``, ``_invoke_chat_handler_in_process``,
``drive_seed_fixture``) carry their full docstrings + signatures
but raise ``NotImplementedError`` at this step. Bodies land at
Steps 3 + 4 per ``A.5.3.2-PR8-SPEC.md`` §6.

PR 8 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR8-SPEC.md`` §0):

PR 8 carrier #15 — chat-handler-only seeding scope (LANDS AT TOP
PER FRAMING §3.2 RELEVANCE-BY-FILE ORDERING):

  PR 8 seeds the chat-handler observation surface only. Chain-step
  seeding is explicitly deferred because handlers.py and _step.py
  produce semantically distinct observation records. Cross-surface
  expectation semantics require a dedicated framing pass before
  implementation proceeds.

Inherited carriers #1–#2 — risk-category shift (PR 4):

  PR 4 is the controlled introduction of observational
  side-effects into live arbitration surfaces.

  The risk category has shifted from persistence-substrate risk
  to participation-creep risk.

Inherited carriers #3–#6 — integration-discipline quartet (PR 4):

  The call site is the source of the three explicit inputs.

  The integration layer passes truth.

  The integration layer never reconstructs truth.

  The builder does not discover runtime state.

Inherited carrier #7 — finalized-state contract (PR 4):

  Capture emission occurs only after arbitration state is
  finalized for the current execution path. Capture records
  completed arbitration observations, not provisional
  intermediate state.

Inherited carrier #8 — risk-inheritance + surface-geometry
distinction (PR 5):

  PR 5 is the second call site under the integration discipline
  PR 4 established. The risk profile is inherited; the surface
  geometry is not.

Inherited carrier #9 — caller's view of deployment identity
(PR 5):

  The chain-step's deployment identity is the caller's view, not
  the global daemon registry view.

Inherited carrier #10 — ambiguity-as-arbitration-outcome (PR 5):

  Ambiguity rejection is an arbitration outcome. Capture must
  record it. At this surface, ``narrower_decision`` carries the
  filtered list verbatim at narrowing finalization — including
  zero-match and multi-match rejection paths.
  ``pr20_condition_met`` is always False and ``collapse_occurred``
  is False on all rejection paths. These semantics differ from
  the chat-handler case and must not be silently overloaded.

Inherited carrier #11 — measured-not-inferred coverage (PR 5):

  No-dependency coverage at the chain-step surface must be
  measured, not inferred. The existing probe drives only the
  chat-handler single-step path; PR 5 owns the responsibility
  to extend coverage to the chain-step path empirically.

Inherited carrier #12 — structural-backstop framing (PR 6):

  PR 6 is the structural backstop for the visual-asymmetry
  pattern. The lint validates shape, not content; structure, not
  interpretation. Carrier content is the room's job; field
  validation is the helper signature's job; the lint validates
  the visual asymmetry between arbitration and observation.

Inherited carrier #13 — observation-not-participation framing
(PR 6):

  The lint operates by observation, not by participation. It
  reads source files; it does not import the corpus package.
  The lint's own scope is the same one-directional observational
  flow the call sites enforce.

Inherited carrier #14 — declared epistemic class vs. persisted
provenance (Gate 2):

  Property C governs the epistemic class declared at the
  observation boundary. KNOWN_SOURCE_VALUES governs persisted
  provenance classes after contextual annotation has been
  resolved.

Binding framing clarification — call-site-owned arbitration inputs
(Gate 2):

  Arbitration-state fields remain call-site-owned explicit
  inputs. Dispatch provenance is contextual metadata derived at
  emission time and does not participate in arbitration
  semantics.

PR 8-local binding — companion records as truth-partitioning
(member #7 protection, scope-local to this module +
emit_seed_expectation):

  A unified "richer" record appears mechanically simpler because
  it collapses authored expectation and observed arbitration
  into one persistence surface. The simplification is false: it
  destroys falsifiability by allowing expectation and
  observation to co-author the same artifact.

  Operationally: observation records and expectation records are
  persisted as separate records in the same date-partitioned
  JSONL file, distinguished by record_kind, joined later by
  Gate 4's comparator on fixture_id. The schema validator
  rejects records carrying record_kind="expectation" and a
  source field at the persistence boundary; this module's
  helpers preserve the partition by construction
  (emit_seed_expectation persists record_kind="expectation"
  with no source field; emit_divergence_capture persists
  record_kind="observation" with source ∈ KNOWN_SOURCE_VALUES).

PR 8-local binding — emit_seed_expectation as semantics-not-
topology (member #8 protection, scope-local to this module +
emit_seed_expectation):

  Inlining persistence into emit_seed_expectation appears
  symmetrical with emit_divergence_capture but silently
  transfers persistence-topology authority into a semantics-
  scoped helper. The separation is protected because authored
  expectation and persistence topology are intentionally
  distinct authority surfaces.

  Operationally: emit_seed_expectation builds the expectation
  record dict and delegates persistence to
  _persist_expectation_record (the PR 7 seam). It does NOT call
  _resolve_corpus_dir, _make_header, _serialize_line, or any
  direct file I/O surface. The PR-8-local participation
  discipline test
  (tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS
  + AST walker) enforces mechanically. The participation
  contract is semantic, not cardinal — the bright line is
  rejection of persistence-topology authority, not enforcement
  of an exact symbol count.

PR-8-internal three-way authority partition (see
``A.5.3.2-PR8-SPEC.md`` §4.1.5.1):

This module implements a sub-partition of Gate 2 framing's
§3.4 third gate-level authority surface (authored expectation),
splitting it into three PR-8-internal authority surfaces:

  - Authored expectation semantics → emit_seed_expectation
      (the truth claim: "this is what the fixture-author
       declares the arbitration outcome should be")
  - Orchestration semantics → drive_seed_fixture
      (the invocation contract: "this is how a single fixture
       is exercised through the chat-handler pipeline")
  - Persistence topology → _persist_expectation_record
      (the PR 7 seam: "this is how a record is written to disk
       under atomic-append + I-6")

The three surfaces are intentionally distinct authority classes.
Future cleanup PRs proposing to collapse them are rejected at
the spec layer (see ``A.5.3.2-PR8-SPEC.md`` §7 phase-end
conditions).

This module implements the seed-driver portion of Gate 2 framing's
three-authority-surface partitioning (§3.4):

  - Observation surface (PR 7): emit_divergence_capture +
    contextvar resolution path. Unchanged by PR 8.
  - Dispatch provenance surface (PR 7): seed_dispatch_scope +
    _DispatchContext. Unchanged by PR 8 (this module CONSUMES
    the scope; it does not modify it).
  - Authored expectation surface (PR 8 — THIS MODULE):
    emit_seed_expectation + drive_seed_fixture +
    _invoke_chat_handler_in_process.

See ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 for the canonical
record shape, ``A.5.3.2-GATE-2-FRAMING.md`` §3.4–§5.7 for the
gate-level architecture, and ``A.5.3.2-PR8-FRAMING.md`` for the
PR-level binding decisions this module operationalizes.
"""
from __future__ import annotations


def emit_seed_expectation(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Persist an authored expectation record for a seed fixture.

    PR 8 SEMANTICS-NOT-TOPOLOGY GUARD (verbatim, load-bearing —
    see ``A.5.3.2-PR8-SPEC.md`` §0 PR 8-local binding statement
    #2):

      Inlining persistence into emit_seed_expectation appears
      symmetrical with emit_divergence_capture but silently
      transfers persistence-topology authority into a semantics-
      scoped helper. The separation is protected because
      authored expectation and persistence topology are
      intentionally distinct authority surfaces.

    Future contributors must not inline
    ``_persist_expectation_record``'s body into this helper,
    must not call ``_resolve_corpus_dir`` or any direct file I/O
    surface from this helper, and must not add a ``source``
    parameter or any arbitration-state parameter to this
    helper's signature. The cleanup-pressure-resistance class
    member #8 (``A.5.3.2-PR8-FRAMING.md`` §6.2) names the
    architectural protection; the PR-8-local participation
    discipline test
    (``tests/corpus/test_pr8_seed_surface.py::_SEED_PERMITTED_IMPORTS``)
    enforces mechanically.

    Args:
        fixture_id: REQUIRED keyword-only. The seed fixture
            identifier the expectation describes. Persisted as
            the ``fixture_id`` field on the expectation record.
        prompt: REQUIRED keyword-only. The single-step prompt
            text the fixture exercises. Persisted as the
            ``prompt`` field.
        expected_narrow: REQUIRED keyword-only. The list of tool
            names the fixture-author declares the narrowing
            decision should produce. Possibly empty (the empty
            list is a valid expectation — it expresses
            "expected zero-survivor narrowing for this prompt").
            Persisted as the ``expected_narrow`` field.

    Returns:
        ``None``. Failure-invisibility per I-6: any exception
        from record construction, schema validation (inside
        ``_persist_expectation_record``), or persistence is
        caught and logged at WARNING; nothing propagates.
        Defense in depth — ``_persist_expectation_record``
        already wraps its body in I-6 internally; this helper's
        outer wrap is the belt-and-suspenders posture matching
        the corpus convention.
    """
    raise NotImplementedError(
        "emit_seed_expectation body lands at PR 8 Step 3 — see "
        "A.5.3.2-PR8-SPEC.md §6 Step 3 + §4.1.3."
    )


async def _invoke_chat_handler_in_process(prompt: str) -> None:
    """Invoke chat_handler with a minimal in-process Request.

    Private async helper carrying four architectural seam roles:

      1. Sync → async bridge. The sync driver
         (``drive_seed_fixture``) reaches the async handler via
         ``asyncio.run`` invoking this helper.
      2. Request-envelope reconstruction seam. The minimal
         Starlette Request is constructed here (ASGI scope dict
         + injected body bytes). The reconstruction wraps truth
         in the chat-handler protocol envelope; it does not
         reconstruct arbitration truth (carrier #6 preserved).
      3. Corpus → console exception seam. The function-scoped
         ``from forge_bridge.console.handlers import chat_handler``
         lives here. The exception's effective scope is the
         helper's invocation, not ``_seed.py``'s import time.
      4. Carrier #15 enforcement seam. The chat-handler-only
         scope is the helper's single concern; tests patch this
         helper's target (``forge_bridge.console.handlers.chat_handler``,
         the source namespace) to assert chain-step is never
         invoked during seeded driver executions.

    Carrier #15 governs (verbatim, see module docstring): PR 8
    seeds the chat-handler observation surface only.

    Carrier #6 preserved (integration layer passes truth, not
    transport): the prompt + minimal protocol envelope (a
    single-user-message body) IS the chat-handler arbitration
    surface. The Request object is the protocol envelope, not
    arbitration truth; building it is wrapping the truth, not
    reconstructing it. The handler's internal arbitration
    logic — narrowing, tool dispatch, observation emission at
    handlers.py:1185 — is what the seed driver exercises.

    Args:
        prompt: The single-step prompt text. Wrapped in the
            canonical D-02 messages body shape:
            ``{"messages": [{"role": "user", "content": prompt}]}``.

    Returns:
        ``None``. The JSONResponse from chat_handler is
        intentionally ignored — the observation emission fires
        inside chat_handler's body BEFORE the response is built
        (per the existing call site at handlers.py:1185). The
        seed driver's interest is in the emission, not the
        response.
    """
    raise NotImplementedError(
        "_invoke_chat_handler_in_process body lands at PR 8 "
        "Step 4 — see A.5.3.2-PR8-SPEC.md §6 Step 4 + §4.1.4."
    )


def drive_seed_fixture(
    *,
    fixture_id: str,
    prompt: str,
    expected_narrow: list[str],
) -> None:
    """Drive one seed fixture through the chat-handler arbitration
    pipeline.

    Builds and persists the authored expectation, opens
    ``seed_dispatch_scope``, invokes ``chat_handler`` in-process
    (via ``_invoke_chat_handler_in_process``), exits the scope.

    PR 8 CARRIER #15 — chat-handler-only seeding scope (verbatim,
    load-bearing — see ``A.5.3.2-PR8-SPEC.md`` §0):

      PR 8 seeds the chat-handler observation surface only.
      Chain-step seeding is explicitly deferred because
      handlers.py and _step.py produce semantically distinct
      observation records. Cross-surface expectation semantics
      require a dedicated framing pass before implementation
      proceeds.

    A future contributor proposing to drive ``_step.py:233`` from
    this function must produce a framing artifact defining
    cross-surface expectation semantics BEFORE proposing
    implementation. Implementation-first chain-step seeding is
    rejected at the spec layer per
    ``A.5.3.2-PR8-SPEC.md`` §2 out-of-scope #1 + §7
    (phase-end-conditions rejection table).

    PR 8 ORCHESTRATION-NOT-AUTHORING GUARD (verbatim, load-
    bearing — see ``A.5.3.2-PR8-SPEC.md`` §4.1.5.1 + §6 Step 4):

      drive_seed_fixture is an orchestration surface, not an
      expectation-authoring surface.

    The driver delegates expectation construction to
    ``emit_seed_expectation``; it does NOT build the expectation
    record dict directly. Inlining the construction would
    collapse the helper/driver authority partitioning (one of
    the three PR-8-internal authority surfaces — see module
    docstring's three-way authority partition section). The
    delegation is structurally load-bearing, not stylistic.

    Args:
        fixture_id: REQUIRED keyword-only. The seed fixture
            identifier. Forwarded to ``emit_seed_expectation``
            and to ``seed_dispatch_scope``.
        prompt: REQUIRED keyword-only. The single-step prompt
            text. Forwarded to ``emit_seed_expectation`` and to
            ``_invoke_chat_handler_in_process``.
        expected_narrow: REQUIRED keyword-only. The list of tool
            names the fixture-author declares the narrowing
            decision should produce. Forwarded to
            ``emit_seed_expectation``.

    Returns:
        ``None``. The driver does not surface the chat_handler
        response or any observation outcome — the seed driver's
        interest is in the emission side-effect (the observation
        record that fires inside chat_handler), not the response.
    """
    raise NotImplementedError(
        "drive_seed_fixture body lands at PR 8 Step 4 — see "
        "A.5.3.2-PR8-SPEC.md §6 Step 4 + §4.1.5."
    )
