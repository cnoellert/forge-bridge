"""forge_bridge.corpus._sources — persistence-layer source-class
governance.

This module defines the persistence-layer governance contract for
``source`` values on observation records. The constant
``KNOWN_SOURCE_VALUES`` is the single source of truth for which
provenance classes are admissible after contextual annotation has
been resolved.

The module is structurally pure: a single frozenset constant + this
governance docstring. No functions, no classes, no imports from any
``forge_bridge.corpus.*`` module. The Layer 1 lint allowlist
(``tests/corpus/test_pr3_discipline.py::_ALLOWLIST``) admits this
file because it is leaf governance — the constant's value is the
artifact, not the protection; the protection is the framing-level
discipline that adding a new source class requires synchronous
update of multiple downstream surfaces.

PR 7 carrier sentences (verbatim, load-bearing — see
``A.5.3.2-PR7-SPEC.md`` §0):

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

Inherited carrier #9 — caller's view of deployment identity (PR 5):

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
  reads source files; it does not import the corpus package. The
  lint's own scope is the same one-directional observational
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

PROTECTED PROPERTY (truth):

  Persisted provenance classes are governed. Adding a new source
  class requires explicit framing-level review plus synchronous
  update of: this constant, reader validation, the contextvar
  resolution path inside ``emit_divergence_capture``, and the
  Gate 4 comparator's partition logic. Mergeability is contingent
  on all four updating in lockstep.

MECHANISM (this file):

  The frozenset constant + this docstring. Future additions to
  the set MUST land alongside the framing-level decision; the
  set's value is the artifact, not the protection.

Carrier #14 is the load-bearing protection against upward
collapse of record-ontology governance into the structural lint.
The lint stays structural (call-site shape, Property C); this
constant is where ontology lives. The two governance surfaces are
physically separated to make the distinction visible — see
``A.5.3.2-GATE-2-FRAMING.md`` §3.4 (gate separation) +
``A.5.3.2-PR7-SPEC.md`` §4.1.

Successor authority surface (Gate 4): the comparator's partition
logic consumes ``KNOWN_SOURCE_VALUES`` to bucket records by
provenance class. New source values land here BEFORE landing in
the comparator; the lockstep contract above protects against
silent ordering drift.
"""
from __future__ import annotations

from typing import Final

KNOWN_SOURCE_VALUES: Final[frozenset[str]] = frozenset({"runtime", "seed"})
