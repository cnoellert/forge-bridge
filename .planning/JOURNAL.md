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


=============================================================================
v1.7 THREAD C / PHASE C.1 — CLOSED                              2026-05-27
=============================================================================

Six Asset MCP tools shipped; Stage 2 leakage-watch clean; 10-test +
1-PR22 pre-existing main-branch debt cluster discovered and seeded
as follow-on. Single day-long cycle: writing-room → spec → Stage 1b
→ implementation → Stage 2 → close, zero role-distinction violations.

WHAT LANDED
-----------
Seed + audit + framing + plan + 8 implementation commits + close
arc, in one continuous cadence:

Planning:
  71acce9  plant Asset first-class-entity seed + open substrate audit
  9f0cdd4  sharpen Asset audit scoping per operator ratification
  3020ae9  Thread C phase framing — Asset operability (R-1..R-10 converged)
  3a361e3  C.1 phase plan — Bridge MCP asset tools (Stage 1b cleared)
  32e8cfb  C.1 plan — sweep-completeness fixups (R-1..R-3)

Implementation (D1..D9 in spec order, byte-for-byte):
  b5e21f7  Status aliases for operator vocabulary parity
  407e5f4  forge_create_asset MCP tool
  3f1caa1  forge_list_assets MCP tool
  92a35d1  forge_get_asset MCP tool
  903d968  forge_update_asset MCP tool
  7a59e81  forge_attach_asset_location MCP tool
  03ee2db  forge_relate_asset MCP tool
  8ea4a40  docs/ASSET.md + VOCABULARY.md cross-link

Close:
  this commit       C.1-CLOSE.md + JOURNAL entry + reliability-debt
                    seed + TROUBLESHOOTING.md launchd-kickstart entry

The room's headline (operator coinage at audit-sharpening):
"Asset is not missing from Bridge. Asset is quiet. Thread C makes it
speak." Six dedicated MCP affordances now exercise the substrate's
already-present Asset infrastructure; the silence is closed.

CLOSE-CURSOR DISCOVERIES
------------------------
Five worth carrying forward (full archaeology in C.1-CLOSE.md):

1. Pre-existing reliability-debt cluster surfaced. C.1's full-suite
   acceptance gate exposed 10 failing tests + 1 PR22 mechanical
   violation that pre-date C.1 (identity-matched against commit
   32e8cfb). Five clusters: console-startup binding, CLI entrypoint,
   flame timeline, ping fixtures, PR22 flame_execute_python (flat-
   signature pattern not in PR22's A/B/C taxonomy). Seeded at
   SEED-MAIN-RELIABILITY-DEBT-V1.7+.md as forward-pressure per
   [[feedback-explicitly-unbound-vs-implicitly-rejected]].

2. Acceptance-gate scope-of-test observation — candidate memory at
   single-instance hold. Gates that reference shared mechanical
   tests inherit the shared surface's health, not just new code's
   compliance. Sibling to [[feedback-distinct-success-criteria-
   per-adjacent-layer]] at gate-language grain.

3. External-daemon-restart operational gap. `fbridge down/up` does
   not own launchd-supervised daemons. The `install_provenance`
   doctor row did exactly what Phase 24.2 engineered it to do —
   caught the snapshot-vs-live asymmetry as first-class observable.
   TROUBLESHOOTING.md launchd-kickstart entry landed alongside this
   close.

4. Stage 2 leakage-watch — clean across all 8 commits. The five
   named substrate-side surfaces (utilities, serializers, shared
   queries, registry helpers, response envelopes) stayed generic.
   Discipline-proof-of-life for the ontology-leakage-watch
   structure.

5. [[feedback-failure-shape-stability-as-disposition-evidence]]
   firing as designed. 10→10 identity-match closed what could have
   been a multi-hour "is C.1 broken?" investigation in minutes.
   Already memory-grade; this is corroboration at a new project
   layer (full-suite integration cluster, not single-intervention
   behavioral falsification).

CANDIDATE-MEMORY LEDGER
-----------------------
One at hold pending second occurrence:

- Acceptance-gate scope-of-test discipline (D-2 above). Single
  instance; carry forward as candidate until a second distinct-
  pressure-surface occurrence.

PROCESS
-------
Writer's-room cadence held without role-distinction violation
across the entire C.1 arc:

- Audit grounded against actual files per
  [[feedback-ground-specs-in-actual-files]] — six layers cited
  with verified file:line anchors.
- Three-step cadence at framing supersession (writing-room
  proposal → explicit room sign-off → code-handoff format) —
  Thread C framing went from writing-room-proposal to
  phase-framing only after Creative + DT + operator ratification
  on the four open scoping questions.
- Stage 1b caught 8 blocking grounding fixes (B-1..B-8) and 3
  substantive room rulings (S-1..S-3) before implementation
  handoff. Creative added four constitutional tightenings (MOL-3
  rationale, MOL-6 doctrine, D1 state-vs-authority, L3 semantic-
  coupling Stage 1b question, ontology-leakage watch).
- Drafter self-violation caught at Stage 1b second pass:
  [[feedback-grep-c-completion-invariant]] failure on the v2
  revision — body updated, manifest didn't sweep alongside (R-1,
  R-2, R-3). The methodology caught the methodology drift; the
  spec promoted clean after the sweep completed.
- Implementation discipline: operator held C.1-CLOSE.md drafting
  appropriately on the strict reading of acceptance gates — the
  writing room owed the classification (load-bearing semantic) on
  what counts as a regression vs corpus-scope archaeology. The
  hand-off was clean once that classification landed.

CARRIED FORWARD
---------------
- Reliability-debt seed (5 clusters) — promotes when CI-green
  becomes load-bearing for a v1.7+ phase OR an explicit cleanup
  motion opens. Two paths named for Cluster 5 (PR22).
- Convenience aggregation pressure watch — Creative's Stage 1b
  forward-looking observation. Now that Asset ontology exists,
  downstream pressure for joins / unified queries / helper
  abstractions / generalized entity handling will arrive. Sibling
  pressure to the ontology-leakage watch but inverted (leakage
  flows substrate-ward; aggregation flows surface-ward). Attend
  to in C.2 and beyond.
- C.2 (Bridge CLI asset surface) — next motion. Operates against
  the same six operations at the operator-friendly Typer subgroup;
  --json mode preserved per P-01; dogfood pass per Thread B B-2.
- C.3 (Projekt Forge consumer proof) — R-10 forcing-criterion
  contract intact; three buckets (latency-bound / atomicity-bound
  / availability-bound), explicit does-NOT-count list. Investigates
  whether projekt-forge needs DBAsset or just commands +
  conventions over Bridge's substrate.

STATE: Thread C / C.1 closed clean. Asset surfaces operational at
the MCP layer. C.2 is the next motion within Thread C; Thread A
proceeds in parallel. Reliability-debt seed parked.
=============================================================================


=============================================================================
2026-06-01 — v1.11 SR.1 CLOSED · cross-team ADR-003 (Door C/C1) ACCEPTED ·
forge-bridge owes Constraint 2 (NEXT MOTION, first thing)
=============================================================================

WHAT LANDED
-----------
- v1.10 Authority Invariance CLOSED (DI.1 dispatch-authority gate +
  DI.2 eligibility arbitration). v1.11 Source-of-Truth Routing / SR.1
  CLOSED + live-verified: sequence-scoped shot reads route to
  flame_get_sequence_segments (console/_source_route.py post-compile
  pass). 2/3 reachable win (R8 path + R10 duration); R9 timewarp =
  capability gap (no tool emits it). main @ 455a60d (pushed, clean).
- Cross-team ADR-003 (forge-pipeline <-> forge-bridge) ACCEPTED —
  Door C / variant C1: chat-initiated mutations traverse the single
  v1.7 ratify chain (AssentRecord); forge-pipeline staged-ops becomes
  a manifest-participating apply-EXECUTOR behind ratify, NOT a second
  authority door. Phase 26 block root cause = a door-mismatch (golden
  path expected chat -> forge_stage_* proposer; chat's mutation door
  is the ratify chain), not a _tool_filter bug.
- Integrity seam = the EXISTING generic commit-node dispatch
  (_step.py:792-866 replays apply_counterpart tool in verify/apply
  modes; generic over MutationManifest, not flame-specific). C2
  (proposer -> async listener) is integrity-incompatible — it falls
  outside the synchronous verify->apply envelope.
- 26-05 MutationManifest integrity contract RATIFIED (DT reviewed vs
  live source; one change-request raised then RETRACTED after tracing
  _step.py:879-887 — the {"drift":true} envelope IS recognized ->
  PLAN_STATE_DRIFT -> mark_failed). 26-06 executors DONE
  (forge_apply_rename / forge_apply_publish, 3-mode discover/verify/
  apply, on forge-pipeline branch claude/document-action-api-ZYmqX,
  unpushed). No forge-bridge files edited — generic contract held.

NEXT MOTION (first thing) — forge-bridge Constraint 2
-----------------------------------------------------
compile_intent() must emit a commit-bearing executor chain
(<executor> + commit) for mutating intents, so they reach
run_compile_branch's preview/ratify branch instead of the DI.1-blocked
bare-flame_rename_shots direct-dispatch path. Keystone that fires C1
end-to-end and unblocks 26-04 (live E2E).
- Mechanism lean: deterministic post-compile transform, sibling of
  SR.1's _source_route + an intent->executor map (rename->forge_apply_
  rename, publish->forge_apply_publish). NOT a prompt change.
- GROUND FIRST (the one unverified item — do NOT assert before
  tracing): does run_compile_branch run the executor's discover at
  PREVIEW time so the operator ratifies the real resolved manifest,
  or is wiring discover-at-preview a Constraint-2 sub-requirement?
  Contract section 2.1 assumes discover-output-IS-preview; the commit
  path stores chain TEXT. Trace preview construction + the existing
  mutation-ratify flow end-to-end before scoping.

METHODOLOGY (the session through-line)
--------------------------------------
The grounding-flip pattern fired ~5x: a load-bearing claim that would
have shaped the work flipped when probed against live source/data
("9 tools" -> 8 & resolves; "builtins pass none" -> 69/69 annotated;
"answerability map must be built" -> _NAMESPACE_PREFIXES already
tokenized; reachable-win 3/3 -> 2/3; the section-2.3 change-request ->
retracted). Operating rule: ground the SPECIFIC claim against live
source before it shapes the work — absence-claims and your own review
assertions especially; trace to the bottom, not the first branch.

CARRIED FORWARD
---------------
- forge-bridge Constraint 2 (above) — the active next motion.
- 26-04 live E2E rerun — blocked on Constraint 2; resumes as a
  ratify-chain rerun against the new executors (non-autonomous,
  live-Flame).
- R9 timewarp — capability gap; needs a segment-effects inspection
  tool (forge-pipeline). R7 — session/project scope.
- /gsd-secure-phase 26 before the forge-pipeline branch merges
  (26-05 STRIDE DT-ratified; 26-06 ships code).

STATE: v1.11 SR.1 closed; cross-team C1 ratified; executor contract +
executors delivered (forge-pipeline side). Ball in forge-bridge's
court for Constraint 2. Live cursor: memory passoff UPDATE 9.
=============================================================================

=============================================================================
2026-06-02 — C2 SHIPPED + CLOSED (Constraint 2) · v1.12 Mutation
Delegation OPENED (phase 1 of 2) · Shape A+ intent-ratification
=============================================================================

WHAT LANDED (main @ 9ecd503, pushed; close docs @ 47574fe)
----------------------------------------------------------
Chat RENAME intents now compile to a commit-bearing executor chain
(flame_rename_shots -> forge_apply_rename <args> -> commit) and reach
preview/AssentRecord/ratify instead of the DI.1 hard-block. Constraint 2
done. Five tasks in one commit (9ecd503):
- T1 console/_executor_route.py — deterministic post-compile rewrite;
  rename-only _EXECUTOR_MAP; 5-clause guard incl. Finding-1
  dispatch_authority(executor_tool); multi-mutation fail-safe.
- T2 hook _chat_compile.py:183 (before graph_contains_commit_node:184),
  execution_tools or tools.
- T3 A+ _commit_count (type-keyed on result type==commit_applied,
  _step.py:889-897) -> count in _apply_complete_body; panel.html renders
  "Renamed N shots." (data + confirmation).
- T4 tests/console/test_c2_executor_routing.py (+163).
- T5 in-chat apply <id> replay aligned onto the reachable surface
  (relocated Finding 2).
Verified bridge-side: suite 2688 -> 2697 (+9), __all__=19, ruff clean,
tree clean, DT sign-off no reservations.

THE DECISION (operator-ratified)
--------------------------------
Shape A+ (intent-ratification) NOW; Shape B (manifest-ratification,
protects the preview->apply Window-2 drift) is the NAMED next motion =
v1.12 phase 2, deliberately NOT smuggled in. Grounding settled the fork
honestly: discover does NOT run at preview (commit path stores chain
TEXT; build_preview_from_steps is lexical) -> a pure-A preview shows no
count, so silent-count-drift is a Shape-B artifact, not an A risk. The
A+ count = len(manifest.resolved_plan), computed bridge-side from the
manifest the commit node holds (robust independent of executor return).

PLAN-CHECK (DT + Creative)
--------------------------
Finding 1 (HIGH) adopted -> T1 enforces the mapped executor's own
mutating authority (G1's one-time annotation check becomes a durable
runtime invariant). Publish EXCLUDED (G2: no ApplyPublishInput <->
PublishSequence arg parity, bare tool unconfirmed) -> own future motion;
"no reshaping" invariant rescoped to rename-proven. Finding 2
traced-to-bottom + RELOCATED: the C2 hook surface is benign (strip-guard
robust to the execution_tools-superset); real exposure was a
pre-existing in-chat apply-replay narrowing C2 was merely first to
exercise -> T5.

METHODOLOGY (the session through-line)
--------------------------------------
Grounding-flip can RELOCATE a finding, not only correct a fact: Finding
2's seam moved (C2 hook -> apply-replay surface), downgraded, spun out
T5. Same pattern fired on a housekeeping claim (DT "2-ahead, 34ff8f7
unpushed" -> grounded: 1-ahead, 34ff8f7 already on origin). And
Creative's read: grounding REDUCED scope (rename-only map, no mode
token, no arg reshaping) = convergence signal, the plan fitting the
system rather than being imposed on it. Candidate amendments parked in
C2-CLOSE.md §Methodology (not yet written to memory files).

CARRIED FORWARD
---------------
- Shape B (manifest-ratification, Window-2) = v1.12 phase 2, named next
  motion. Maturation condition: room judges Window-2 drift unacceptable
  in production.
- 26-04 live E2E — gated on forge-pipeline executors
  (claude/document-action-api-ZYmqX, ~146 ahead, UNPUSHED) being
  pushed + registered. C2 degrades honestly to the DI.1 block until then
  (substrate-before-consumer boundary the plan named).
- Publish executor delegation = its own future motion (own grounding;
  discover mirrors the proposer).
- /gsd-secure-phase 26 before the forge-pipeline executor branch merges.
- R9 timewarp capability tool; R7 session/project scope (from v1.11).

STATE: v1.12 Mutation Delegation OPENED; phase 1 (C2) shipped + closed +
verified bridge-side. main @ 47574fe (pushed, in sync, tree clean).
Live cursor: memory passoff UPDATE 10.
=============================================================================


