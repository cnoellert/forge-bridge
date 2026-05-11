"""Seed fixture — no-keyword-match full-capability-fallback
narrowing outcome at the chat-handler observation surface.

Renamed per ``A.5.3.2-PR9-SPEC.md`` §4.7 amendment 2026-05-11
(was ``fix_zero_match.py`` pre-amendment). The chat-handler
narrowing pipeline cannot produce ``narrower_decision == []`` —
the PR14 "no capability loss" fallback returns the full
reachable tool set verbatim when zero keywords match. Carrier
#10's "zero-match" language is chain-step-specific and does
NOT regenerate at chat-handler.

PR 9 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR9-SPEC.md`` §0).

PR 8 carrier #15 — chat-handler-only seeding scope (LANDS AT
TOP per relevance-by-file ordering; PR 9 fixtures are
structurally scoped to the chat-handler observation surface,
making carrier #15 the most-relevant inherited governance):

  PR 8 seeds the chat-handler observation surface only.
  Chain-step seeding is explicitly deferred because handlers.py
  and _step.py produce semantically distinct observation
  records. Cross-surface expectation semantics require a
  dedicated framing pass before implementation proceeds.

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

Binding framing clarification — call-site-owned arbitration
inputs (Gate 2):

  Arbitration-state fields remain call-site-owned explicit
  inputs. Dispatch provenance is contextual metadata derived at
  emission time and does not participate in arbitration
  semantics.

Fixture purpose:

This fixture exercises the chat-handler-surface no-keyword-match
full-capability-fallback narrowing outcome. The prompt
``"what time is it"`` (single-step shape; does NOT fire chain-
step arbitration) contains zero keyword tokens that match any
tool name's tokens in the PR 9 controlled reachable-tool set.
The pipeline yields:

  - **PR14 keyword filter** returns the FULL reachable set (4
    tools): ``forge_ping``, ``forge_list_projects``,
    ``flame_list_libraries``, ``flame_render_status``. PR14's
    "no capability loss" fallback fires (``_tool_filter.py:320–321``):
    "If nothing matches, the full ``tools`` list is returned
    unchanged so we never lose capability."
  - **PR21 deterministic_narrow** does not reduce: input size
    > 1 but max-overlap is 0 ("no signal, leave the candidate
    set untouched" per PR21 stop conditions in
    ``_tool_filter.py``). Survivor set is unchanged.
  - **Observation record**: ``narrower_decision`` = the full
    controlled reachable set verbatim (4 tools, PR14 input
    order); ``pr20_condition_met == False`` (tools_filtered_count
    > 1); ``collapse_occurred == False`` (``tools_post_pr14 ==
    tools`` — no multi-to-single transition).
  - **Expectation record**: ``expected_narrow = []`` is the
    fixture-author's **aspirational claim** ("I expect no
    narrowing — zero survivors after keyword filtering"). The
    chat-handler topology preserves full capability instead;
    the divergence between aspirational ``[]`` and observed
    full-list IS the demonstrable Gate 4 comparator-unblock
    proof.

The aspirational ``expected_narrow = []`` is structurally valid
per ``emit_seed_expectation``'s contract
(``forge_bridge/corpus/_seed.py:259–264``) — the empty list
expresses "expected zero-survivor narrowing for this prompt" as
a valid expectation, not a missing field. The divergence from
arbitration's actual production is the test's load-bearing
property, not a fixture authoring error.

The arbitration trace recorded above is archaeology-grade per
``feedback_counts_are_archaeology_grade.md``. Future contributors
diagnosing no-keyword-match regressions can verify against the
trace recorded here + the Step 2 commit body. The fixture's
divergent expectation IS intentional and is the load-bearing
Gate 4 unblock proof — do NOT "fix" the divergence by aligning
``expected_narrow`` with the observed outcome.

Authored/observed divergence framing:

  This fixture intentionally encodes an authored/observed
  divergence.

  The authored expectation declares:

    expected_narrow = []

  The observed chat-handler behavior instead preserves the full
  reachable tool set via PR14's "no capability loss" fallback.

  The divergence is intentional and operationally valuable: it
  proves the companion-record topology can represent authored
  expectation separately from observed arbitration outcome,
  which is the Gate 4 comparator-unblock condition this fixture
  exists to exercise.

PR 9 governing sentence (framing-artifact-scoped):

  PR 9 proves topology, not infrastructure.

This fixture is data + one orchestration call only — no
helpers, no factories, no parametrization. Per cleanup-pressure-
resistance class member #9 (fixture-surface-data-discipline;
``A.5.3.2-PR9-FRAMING.md`` §6.1).
"""
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr9-no-keyword-match",
    "prompt": "what time is it",
    "expected_narrow": [],
}
