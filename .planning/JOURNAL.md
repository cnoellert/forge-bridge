# forge-bridge — Project Journal

Per-cycle close-out record. Newest entry at the end. Each entry is a
self-contained block: what landed, process notes, what was carried
forward. This file is the running cycle log; it is not the authoritative
cold-resume surface (see the STATE.md note in the first entry's
CARRIED FORWARD).

=============================================================================
PHASE N+ — CLOSED + PUSHED          2026-05-23
=============================================================================

origin/main @ be7a902  (was 533c3d1)  — 35 commits, clean fast-forward
Local = origin, 0/0 parity. Tree clean (AGENTS.md untracked, as throughout).

WHAT LANDED
-----------
One push carried three substrate phases to origin: Phase 25.3 close,
all of Phase N, all of Phase N+.

Phase N+ proper — the commit primitive: substrate's 6th graph primitive,
first domain-applying/host-mutating one. The preview->apply seam. 12
commits, closed b4e1016 (C4 canonical-probe evidence). C4 fired against
the real 30sec 21 sequence, passed both layers (fbridge exec + chat),
real mutation verified, drift-guard held. Three defects surfaced and
fixed across firings (A: dispatch normalization; B: foreach/tool-grain;
C: id()-based resolution non-determinism) — each caught before host
mutation.

Standalone fix — 715a3be: collect trace label anchors on primitive
identity (is_collect_step), not result-shape inference. The render-layer
"get iterations" label gap, flagged across the arc, closed.

Close-cursor cycle — 4 commits + 1 out-of-repo memory landing:
  76e8e1a  §11 register — render-layer label gap -> Landed
  791ad76  Phase N+ close-cursor synthesis (v1.6-PHASE-N-PLUS-CLOSE.md)
  8767269  §constitutional reflow — coined phrases grep-recoverable
  be7a902  plant flame_rename_shots segment-name-collision seed

MEMORY (landed in store, outside repo — verified, not git-tracked)
------------------------------------------------------------------
6 promoted: stage-1b-spec-review, sibling-check-before-fix-scope,
grep-c-completion-invariant, mock-three-tier,
substrate-before-consumer-landing,
substrate-coherence-revealed-in-retrospect.
1 extended: ground-specs-in-actual-files (+4th class:
canonical-probe-text at framing-archaeology grain).
1 amended+promoted: brief-examples-as-behavioral-reference-shapes (bar
deliberately broadened: 2nd distinct-domain recurrence of the shape).
+ 6 MEMORY.md index lines. originSessionId: CLOSE-CURSOR-PHASE-N+.

Also in close doc: 1 constitutional note
(drift-guard-as-determinism-enforcement;
"the seam held every time it mattered"),
2 closure records (evidence-artifact-as-canonical-witness;
Q10(b) bypass+side-effects),
1 seed (SEED-RENAME-SHOTS-SEGMENT-NAME-COLLISION-PHASE-N+.md).

PROCESS
-------
Three-step cadence: 4 cycles in Phase N+ proper + 1 in the close cycle.
Stage 1b caught 3 blockers pre-handoff + 1 grounding correction. Stage 2
caught the §constitutional verbatim-grep defect (escaped Stage 1b + first
Stage 2) -> reflow fixup -> re-verified grep-grade. Every commit verified
twice, independently. Zero role-distinction violations across the arc.
The cycle dogfooded its own promoted patterns — including catching a
defect in a promotion artifact with a pattern that artifact promoted.

CARRIED FORWARD
---------------
- 2 close-cursor candidates, single-instance, held per the ratified bar:
  (a) verbatim-quotation grep-ability — candidate 3rd shape for
      grep-c-completion-invariant;
  (b) promoted-pattern-closes-defect-in-own-promotion-artifact —
      methodology-grain instance of
      substrate-coherence-revealed-in-retrospect.
- STATE.md DISCONTINUITY: .planning/STATE.md is frozen at Phase 24.4
  (2026-05-18). It has no record of Phase 25.x, Phase N, or Phase N+ —
  it stopped advancing a full milestone ago, and the project continued
  without operational collapse. This is not treated as a stale file to
  patch: bringing it current would be retroactive narrative
  reconstruction. The honest record is that 25.x -> N -> N+ lived in
  framing docs, close docs, evidence artifacts, §11 registers, seeds,
  and git history. Open constitutional-room question for a future
  motion: "What is the authoritative cold-resume surface now — and is
  it still meant to be a single file?" STATE.md is paused, not patched,
  pending that ruling.
- ENVIRONMENT: code had an unresolved EPERM block on writes outside the
  repo working tree during this cycle (one root cause, two symptoms:
  .git/index.lock; memory-dir write). Work-items 2/3/4 routed via the
  operator-manual path. Reported resolved at cycle end; unconfirmed
  until code next executes a write.
- §11 register Active scope: empty. Not-addressed retains foreach+
  collect+commit end-to-end demo (needs foreach-natural + manifest-
  emitting body tool; none shipped).

STATE: Phase N+ has nothing outstanding. Both opening threads closed.
Clean seam. DPE count: 18 (held intentionally this cycle).
=============================================================================
=============================================================================
v1.7 ARTIST READINESS — OPENING + THREAD B — CLOSED + PUSHED   2026-05-25
=============================================================================

origin/main @ ae27615  (was b4e1016)  — clean fast-forward, 0/0 parity.
Tree clean (AGENTS.md untracked, as throughout).

WHAT LANDED
-----------
Six motions this cycle. Three planning, one topology audit, two
implementation:

Planning / continuity:
  fb9ca69 + d92ff42  JOURNAL.md created (cycle log; this is entry #2).
    fb9ca69 landed with two defects (sweep-enumeration leaked into file
    content; B1 slug-fix unapplied); d92ff42 the honest fixup. Both kept
    as archaeology.
  6261436 + 80e2d16  Continuity-authority topology motion: freeze headers
    on STATE/RETROSPECTIVE/PROJECT, then CONTINUITY-MAP.md — answers the
    Phase N+ "authoritative cold-resume surface" question: distributed
    continuity substrate, no single cursor.
  52e1b8c  Artist Readiness operator-surface seed planted.
  1ca5a09  Seed promoted to v1.7 milestone framing stub. Names the
    architectural law: substrate self-views are first-class operator
    surfaces, derived not reconstructed.

v1.7 implementation arc — Thread B (exec discoverability):
  0974c5f  B-1: fbridge discover sub-app — registry enumeration. Seven
    commands; primitives enumerate by is_*_step introspection (F1: no
    hardcoded list), locked by a static-source-assertion test.
  ae27615  B-2: Thread B dogfooding pass. Author ran discover against all
    6 primitives + all 62 tools; 12 substrate-self-description fixes
    (3 thin docstrings + 9 missing tool-title annotations); 0 deferred.

Thread B CLOSED — all 3 phase-boundary criteria met: surface enumerates
(B-1); author dogfooded the substrate (B-2 log); revealed weakness fixed
12/12. The architectural law's first full loop: surface built, exercised,
substrate improved where it revealed weakness — exercised, not asserted.
v1.7's opening phase ships.

MEMORY (close-cursor candidate ledger — for promotion this cycle)
-----------------------------------------------------------------
1. pattern-transfer-into-authoring-vs-retrieval — promoted memory fires
   at review, not at authoring. Overdetermined: 10+ instances, peak the
   7-wrap-break milestone-stub round. Recommend promote; consider the
   pre-handoff wrap-scan as formal practice (adopted ad hoc mid-cycle,
   demonstrably worked).
2. verification-instrument-as-contract — enumeration / subject /
   execution-tool must each be verified against the others. 6 within-arc
   instances, 2 in B-2 Stage 2 alone. Overdetermined.
3. classify-don't-chase — corpus-scope instruments surface archival
   imperfections that are not regressions; classification determines
   disposition, not detection. Guards against aesthetic totalization.
4. code-handoff-must-lock-mechanism-not-just-source — B-1 F1: spec named
   the source, not the enumeration mechanism; shortest path would have
   been the doctrine-banned hardcoded list.
5. registry-level-invariant-tests as an enforcement category — no
   static-source-assertion test catches a future title-less tool;
   sibling of B-1's primitive-enumeration contract.
6. docstrings-are-operator-surface-infrastructure — Thread B's permanent
   quality-bar shift: docstrings now partially constitute the operator
   literacy surface, not internal commentary.

PROCESS
-------
Three-step cadence held across all six motions. Stage 1b caught the B-1
F1 mechanism-lock blocker pre-handoff. Stage 2 re-surfaced B-2 against
the live tool (re-ran discover) rather than assuming the edits — the
phase's own loop applied to its own verification. JOURNAL entry #1
(fb9ca69) shipped with defects caught only at Stage 2 — logged honestly,
fixed in d92ff42, both kept.
CADENCE VIOLATION: orchestrator pushed 0974c5f without the operator
sign-off gate — every other push this cycle was operator-executed.
Flagged in-session, logged here, not euphemized.

CARRIED FORWARD
---------------
- 6 close-cursor candidates above — for promotion-to-memory this cycle.
- THREAD A — the v1.7 main arc (chat NL->graph-intent compile stage:
  NL -> graph-intent -> preview -> ratification -> apply). Grounding
  G1/G2/G3 complete, recorded in the milestone framing stub. Phase
  framing not yet drafted — the next motion when the room opens it.
- SEED wrap-breaks in SEED-ARTIST-READINESS-OPERATOR-SURFACES-V1.7+.md:
  pre-existing, NOT reflowed — ruled archival archaeology (classify,
  don't chase). The doctrine lives grep-clean in the milestone stub.
- DEFERRED SUBSTRATE ITEM: foreach+collect+commit end-to-end demo —
  still blocked on a foreach-natural, manifest-emitting body tool.
  Carried from the Phase N+ §11 register, unchanged.
- ENVIRONMENT: code's EPERM block characterized this cycle as
  per-turn-grantable (repo writes work; .git-internal writes need an
  explicit per-turn grant). Worth a standing-access ruling before the
  next execution-heavy cycle.

STATE: Thread B closed, v1.7 opening phase shipped. Clean seam. Thread A
is the milestone's next motion.
=============================================================================

