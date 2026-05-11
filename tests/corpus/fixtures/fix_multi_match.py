"""Seed fixture — multi-match ambiguity-rejection narrowing
outcome at the chat-handler observation surface.

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

This fixture exercises the multi-match ambiguity-rejection
narrowing outcome at the chat-handler observation surface per
carrier #10. The prompt ``"list"`` (single-step shape; does NOT
fire chain-step arbitration) drives ``chat_handler``'s
arbitration pipeline against the PR 9 controlled reachable-tool
set (see ``test_pr9_fixture_integration.py`` monkeypatch
strategy + ``A.5.3.2-PR9-SPEC.md`` §4.5). The pipeline yields:

  - **PR14 keyword filter** returns 2 tools:
    ``forge_list_projects`` (token "list" matches) and
    ``flame_list_libraries`` (token "list" matches). Both are
    other-match (single-token overlap).
  - **PR21 deterministic_narrow** cannot collapse: both tools
    tie at max-overlap=1 ("list"); no domain-priority pair
    fires (the closed list ``(("version", "project"),)`` does
    not include "list"); Rule 3 raw-token tie-breaker also
    finds no asymmetry — both tools have identical raw-token
    overlap with the message. Survivor set is unchanged.
  - **Observation record**: ``narrower_decision = [
    "forge_list_projects", "flame_list_libraries"]`` verbatim
    (PR14 input order preserved through PR21); ``pr20_condition_met
    == False`` (tools_filtered_count > 1); ``collapse_occurred
    == False`` (no multi-to-single transition).
  - **Expectation record**: ``expected_narrow =
    ["forge_list_projects", "flame_list_libraries"]`` matches
    arbitration's actual outcome verbatim (list-equality, not
    set-equality — carrier #10's "filtered list verbatim"
    language requires ordering preservation). Zero divergence;
    Gate 4 comparator will agree.

The arbitration trace recorded above is archaeology-grade per
``feedback_counts_are_archaeology_grade.md``. Future contributors
diagnosing multi-match regressions can verify against the trace
recorded here + the Step 2 commit body.

PR 9 governing sentence (framing-artifact-scoped):

  PR 9 proves topology, not infrastructure.

This fixture is data + one orchestration call only — no
helpers, no factories, no parametrization. Per cleanup-pressure-
resistance class member #9 (fixture-surface-data-discipline;
``A.5.3.2-PR9-FRAMING.md`` §6.1).
"""
from __future__ import annotations

FIXTURE: dict = {
    "fixture_id": "fix-pr9-multi-match",
    "prompt": "list",
    "expected_narrow": ["forge_list_projects", "flame_list_libraries"],
}
