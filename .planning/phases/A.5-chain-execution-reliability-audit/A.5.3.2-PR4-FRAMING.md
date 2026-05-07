# A.5.3.2 PR 4 — Framing (registered, not yet drafted)

**Status:** framing registered 2026-05-07 during the post-PR-3
writer's-room pass. **NO spec drafted, NO code written.** This
artifact exists so the next session opens to the right pressure
profile before any drafting begins.

**Predecessors (binding, in order):**

- `A.5.3.2-FRAMING.md` — phase shape, objective lock.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument shape, structural
  invariants, eleven explicit exclusions.
- `A.5.3.2-GATE-1-SPEC.md` — Gate 1 sequencing across six PRs;
  call-site visual-asymmetry pattern (§5.1); architecturally
  prohibited patterns (§5.3).
- `A.5.3.2 PR 1` (commit `ee019be`) — package skeleton.
- `A.5.3.2 PR 2` (commit `a33c135`) — topology + identity.
- `A.5.3.2 PR 3` (commit `a9e3e47`) — capture builder + writer +
  reader; persistence layer ships callable but uncalled.
- `A.5.3.2-PR3-SPEC.md` — orthogonal-truth-surfaces (§5),
  atomic-append discipline (§6.5), corruption locality (§9), the
  six verbatim carrier sentences.

This document is **binding framing** for PR 4. The eventual PR 4
spec must derive from it; the implementation must derive from the
spec. Deviations re-open this artifact for explicit re-review, not
absorbed silently into spec drafting.

---

## 0. The opening framing (verbatim — load-bearing)

> **PR 4 is the controlled introduction of observational
> side-effects into live arbitration surfaces.**

> **The risk category has shifted from persistence-substrate risk
> to participation-creep risk.**

These two sentences travel verbatim from this framing into the
eventual PR 4 spec, the chat-handler integration site's adjacent
comment, and the PR 4 commit message. They are the durable
carriers of architectural intent for PR 4.

PR 1 + PR 2 + PR 3 built the persistence layer. Their risks were
substrate risks: did the writer fingerprint identity correctly?
did the reader localize corruption? did persistence remain
mechanically dumb? **All of those are now closed surfaces.** PR 4's
risks are different in kind: the call site is where the
arbitration pipeline first acquires an observational neighbor, and
the failure mode is participation — the observer subtly becoming
a participant.

Naming this shift early is the framing's load-bearing job. PR 4
inherits the corpus architecture; it does not establish it. The
framing artifact is therefore smaller than PR 3's. But the
risk-category shift cannot be inherited from PR 3 — it has to be
articulated explicitly, because it changes what "dangerous" means
for this PR.

---

## 1. Three risks named explicitly

### 1.1 Visual-asymmetry preservation at the call site

The capture invocation must read as a **separate visual act** from
arbitration. Per Gate 1 spec §5.1, the canonical insertion pattern
is:

```python
filtered = filter_tools_by_message(tools, last_user_text)
narrowed = deterministic_narrow(filtered, last_user_text)

if divergence_capture_enabled():
    emit_divergence_capture(
        prompt=last_user_text,
        registered_tools=tools,                    # §5 deployment identity
        candidate_set_post_reachability=tools,     # §5 runtime topology
        candidate_set_post_pr14=filtered,
        narrower_decision=narrowed,
        # ... remaining contract §3 fields ...
        source="runtime",
    )
```

The blank line and the explicit conditional are part of the
contract, not stylistic preference. Future contributors who attempt
to "tidy up" by folding the two arbitration operations into a
single helper (with capture as a side effect) erode the asymmetry
— that is a spec violation, not a style preference.

**Failure mode if violated:** a future contributor reading the call
site perceives "the narrower decided and we recorded what
happened" as one fused operation. Architectural drift begins at
the reading level before it appears in behavior.

**Architectural protection (carries from Gate 1 §5.3):**

- The narrowing subsystem (`_tool_filter.py`) MUST NOT export an
  observer/listener/callback registration API. (Already prohibited;
  PR 4 does not relax this.)
- A fused `narrow_with_capture(...)` helper that wraps both
  arbitration operations plus capture is prohibited. (Already
  prohibited; PR 4 does not relax this.)
- Capture invocation BEFORE the arbitration decision is finalized
  (e.g., emitting after `filter_tools_by_message` but before
  `deterministic_narrow`) is prohibited. (Already prohibited;
  emission happens after `narrowed` is bound.)

**Lint deferral — locked to PR 6, two combined rationales:**

(a) PR 4 has only one call site. A lint earns its keep when there
are multiple call sites to compare against the canonical pattern;
PR 5 adds the second.

(b) PR 4 is still discovering the stable integration *reading
shape*. Locking visual structure into executable lint too early
risks freezing accidental formatting rather than codifying
intentional structure. The lint design benefits from both PR 4 and
PR 5 as input — exercised integration surfaces, enough operational
reading exposure to distinguish structural choices from incidental
ones.

The second rationale is the stronger long-term argument because
it survives the addition of future call sites. PR 4 ships the
visual-asymmetry pattern as a code-review-only check; PR 6
crystallizes it into executable lint when there's enough evidence
to know what's structural and what's incidental.

---

### 1.2 Capture-call-site state coupling (arbitration invariance)

**This is PR 4's single most important invariant.** The other
risks (1.1, 1.3, 1.4) protect architectural properties; this one
protects **operator-visible behavior**. If arbitration is not
invariant under capture states, every other protection becomes
secondary — the participation boundary has already been crossed
regardless of what the internal architecture claims.

Capture is fire-and-forget, downstream of finalized arbitration.
The arbitration pipeline's externally observable behavior — return
value, latency contribution, side effects, response envelope —
must be **invariant** under all three capture states:

| Capture state | Required invariance |
|---|---|
| **Disabled** (env var unset/falsy) | Arbitration response identical; no extra latency; no observable difference |
| **Enabled + successful** | Arbitration response identical; latency contribution bounded by I-3 (no LLM calls, no network) and the single-syscall write; capture happens AFTER `narrowed` is bound, so no upstream blocking |
| **Enabled + failed** (any I-6 mode) | Arbitration response identical; WARNING logged but envelope unchanged (already pinned by PR 3 failure-invisibility tests at unit level) |

**Failure mode if violated:** branching drift, timing-dependent
divergence, state coupling, conditional arbitration paths, hidden
dependency on capture existence. The chat handler's response
varies based on whether capture happened to fail, whether the env
var was set, whether the corpus directory existed — none of which
should affect what the operator sees. **If operator-visible
behavior changes based on capture state, the participation
boundary has already been crossed regardless of internal
architecture claims.**

**Architectural protection:**

- Capture invocation lives below the `narrowed = ...` line; the
  return value of `emit_divergence_capture` is `None` and unused.
- The env-var read happens only inside `divergence_capture_enabled`
  at the capture call site — never elsewhere in the arbitration
  path. Arbitration must not branch on capture state.
- Per I-6, capture failures already produce no exceptions; PR 4
  extends the test coverage to integration level (chat-handler
  end-to-end, all three capture states, byte-identical response
  envelopes).

**Fixture design — locked:** PR 4 ships a **new
capture-state-cycling fixture** (states: enabled / disabled /
failing / recovering). The architectural concern introduced in PR 4
deserves its own explicit fixture vocabulary. Stretching the
existing chat-handler fixtures to absorb capture-state cycling is
rejected at the spec layer — older fixtures answer different
questions, and conflating them obscures which assertion is
protecting which property.

---

### 1.3 Arbitration-decision feedback through capture (participation creep)

**The protected property is one-directional observational flow.**
The narrower observes nothing about the corpus; the corpus
observes the narrower's decisions. Same prohibition shape as
instrument-contract §8.8 (live correlation collapses observation
into participation).

Concretely prohibited:

- Reading prior corpus records to influence narrowing decisions.
- Adjusting narrower thresholds based on capture-failure rates.
- Using capture latency as a signal about narrower performance.
- Any feedback loop where capture-side data enters the arbitration
  pipeline.
- Any pattern where the narrower's behavior is conditioned — even
  indirectly — on what capture has observed.

**Failure mode if violated:** the boundary blur the framing
forbids. The narrower starts approximating planner reasoning by
training-against-LLM proxy through the corpus. This is the same
threat the instrument contract's §1 articulates
("planner-agreement frequency as an optimization target") — the
corpus exists to *classify* divergence, not to *minimize* it.

**Architectural protection (this is the participation-creep
boundary):**

The protected property is **one-directional observational flow**,
not "don't import this one specific module." The implementation in
PR 4 expresses it as: the narrowing subsystem
(`forge_bridge.console._tool_filter` and the chain-step executor's
narrowing path) imports **zero modules** from `forge_bridge.corpus`
*except* `_capture` (the legitimate emission path). Capture flows
one direction only: arbitration finalizes → capture observes →
corpus persists. The reverse direction — corpus reads back into
arbitration — is the contract violation.

**Forward extension (binding for future PRs):** the prohibition
extends to **any future corpus-read or corpus-analysis modules**,
including but not limited to:

- `reader` (already exists; in scope today)
- `comparator` (Gate 4)
- replay-analysis helpers
- historical lookup helpers
- corpus-derived heuristic surfaces

When such modules land, the participation-creep grep test **must
expand with them**. Otherwise future participation-creep can
bypass the protection simply by introducing new module surfaces
the original grep never anticipated. The grep's invariant is "the
narrowing subsystem imports zero corpus modules except `_capture`"
— that invariant generalizes naturally to new corpus modules; PRs
introducing new corpus surfaces inherit the responsibility to
extend the test.

**Spec confirmation (locked):** the participation-creep grep
becomes an executable test in PR 4 (analogous to the discipline
grep in PR 3, but for the narrowing subsystem). An executable
mechanical guard is worth more than a spec-layer prohibition for
this category of failure mode.

---

### 1.4 Observational side-effects vs observational dependencies

PR 4 permits **observational side-effects.**
PR 4 prohibits **observational dependencies.**

This distinction is critical and lives at the same level as
risks 1.1–1.3.

| Direction | Status |
|---|---|
| **Capture observes arbitration** | Permitted (and is the entire point of PR 4) |
| **Arbitration depends on capture** | **Prohibited** |

Concretely, arbitration must not:

- **require** capture infrastructure to be present
- **expect** capture to be enabled
- **branch** based on capture existence (env-var, file presence,
  reader availability, etc.)
- **rely** on capture-derived state (corpus contents, capture
  history, capture-failure flags)
- **consume** corpus state (reading, statistics, summaries,
  inferences)

**The dangerous future drift this risk names:**

> **"The arbitration layer now expects capture infrastructure to
> exist."**

That sentence must remain false for the lifetime of this
architecture. Capture is a downstream observer of arbitration, not
an upstream dependency of it. If the chat handler stops working
when capture is disabled, broken, or removed, the participation
boundary has already collapsed.

**Architectural protection:**

- The arbitration code path imports nothing from
  `forge_bridge.corpus` (covered by §1.3's grep test for the
  narrowing subsystem; covered by handlers.py's allowlist-bounded
  import staying *purely emissive* in §2).
- The chat handler's success criteria (well-formed response, no
  exception, latency budget) are evaluated independent of capture
  state. The capture-state-cycling fixture (§1.2) exercises this
  directly.
- No conditional logic anywhere in the arbitration pipeline reads
  capture state for a non-emission purpose. The env-var read in
  `divergence_capture_enabled()` is the *only* observational
  dependency that exists, and it is read *at the emission site*
  to decide whether to emit — never elsewhere to decide arbitration.

**Spec recommendation:** add an explicit assertion to the
capture-state-cycling integration test that *removing* the
`forge_bridge.corpus` package entirely (e.g., temporarily aliasing
the import to a sentinel that raises on any access) does not
prevent arbitration from completing successfully. This is the
strongest possible test of the no-dependency property — if
arbitration runs without corpus, the dependency is structurally
absent.

---

## 2. The discipline-grep test transitions to allowlist mode

PR 3's `test_zero_production_imports_outside_corpus` enforced that
no production code path imports `forge_bridge.corpus`. PR 4
deliberately relaxes this — by adding `handlers.py` (chat handler)
to an allowlist. The asymmetry doesn't disappear; **it gets
bounded.**

The architecture should truthfully acknowledge what has changed:
**`handlers.py` is now an intentionally permitted observational
emission surface.** That truthful acknowledgment is healthier than
pretending the asymmetry still literally means "zero imports."
Bounded asymmetry, named explicitly, is more durable than literal
asymmetry maintained by ignoring real integration.

**Allowlist-mode contract:**

- The test continues to walk the production tree.
- Files matching the allowlist (initially: `console/handlers.py`)
  are permitted to import `forge_bridge.corpus`.
- Files not on the allowlist still produce zero imports.
- The allowlist is explicit and reviewable; growth requires spec
  amendment.
- Allowlisted files are still subject to §1.3's prohibition: their
  imports may include the emission path (`_capture` /
  `divergence_capture_enabled` / `emit_divergence_capture`) but
  must not include reader / comparator / replay-analysis surfaces.
  The allowlist relaxes "does this file import `forge_bridge.corpus`
  at all"; it does not relax "what is this file allowed to use the
  corpus for."

**Other paths to make the discipline-grep test pass are rejected
at the spec layer:**

- **Mocking the import out** — if a future PR proposes patching
  the test to ignore `handlers.py` via mock, that is rejected. The
  whole point is mechanical visibility; mocking erodes it.
- **Removing the test** — if a future PR proposes "this test was
  PR-3-specific, let's delete it now that PR 4 has landed," that
  is rejected. The bounded asymmetry is what protects against
  participation creep at unrelated call sites.
- **Inverting the test** — testing only that `handlers.py` *does*
  import the corpus (positive assertion) rather than continuing to
  enforce the negative across the rest of the tree, is rejected.

PR 5's chain-step integration adds `console/_step.py` to the
allowlist. Each PR explicitly extends the allowlist by exactly one
named entry. Growth is reviewable at the spec layer.

**Recommendation for PR 4 spec:** replace `_FORBIDDEN_NEEDLES`
filtering with an allowlist parameter. The test's failure message
should name the allowlist explicitly so future contributors
understand the boundary.

---

## 3. Disciplines inherited from PR 3 (carry without re-articulation)

These disciplines carry through PR 4 unchanged and must be
**preserved aggressively**. They are the boundary that prevents
PR 4's call-site integration from becoming a wedge for future
participation creep.

**The integration layer's binding posture (verbatim, load-bearing):**

- **The call site is the source of the three explicit inputs.**
- **The integration layer passes truth.**
- **The integration layer never reconstructs truth.**
- **The builder does not discover runtime state.**

These four sentences travel into the PR 4 spec's call-site section
and the chat-handler integration site's adjacent comment block.
They are the durable carriers of the integration discipline,
analogous to PR 3's §6.5 / §9 sentences for persistence.

**Why "passes truth, never reconstructs truth" is load-bearing:**

The chat handler holds the authoritative registered tool set, the
authoritative pre-filter candidate set, the authoritative
arbitration inputs and outputs. PR 4's job is to pass those
through to `emit_divergence_capture` *as the call site already
holds them* — not to reconstruct them, not to reformulate them,
not to derive them from intermediate state. Any reconstruction is
a vector for participation creep: derivation requires assumption,
assumption requires interpretation, interpretation puts
arbitration-shaped logic adjacent to the capture site.

**Specific disciplines that carry from PR 3 / Gate 1:**

- **§5 orthogonal truth surfaces.** PR 4 is the call site that
  *supplies* the three explicit inputs. The chat handler must
  pass `registered_tools` (deployment identity) distinct from
  `candidate_set_post_reachability` (runtime topology) distinct
  from arbitration inputs (`candidate_set_post_pr14`,
  `narrower_decision`, `pr20_fired`, `collapse_occurred`,
  `ambiguity_state`). The orthogonal truth surfaces remain
  explicit call-site responsibilities — the chat handler holds
  the full registered tool set before any filtering, so it is the
  authoritative source for deployment identity.
- **§6.5 atomic-append discipline.** Already enforced inside the
  writer; PR 4 does not interact with the persistence layer
  beyond the public emit call. Do not introduce buffering,
  batching, or queue-and-flush patterns in the call site — they
  would re-create exactly the corruption windows §6.5 prohibits.
- **I-7 corruption locality.** Reader behavior; PR 4 does not
  invoke the reader. The participation-creep grep (§1.3)
  structurally prevents this from changing.
- **PR 3 carrier sentences.** Travel into the chat-handler
  integration site's adjacent comment block where the call lands.
  The "Capture is emitted after arbitration decisions are
  finalized" sentence is the most likely candidate, since it
  applies directly to the call-site contract. The orthogonal-
  truth-surfaces pair (§5 of PR 3 spec) also belong here because
  the integration site is exactly where those parameters get
  populated.

The PR 4 framing's own carriers (the two opening sentences in §0
plus the integration-discipline quartet above) are additive —
they document PR 4's specific risk profile, which PR 3's carriers
do not address.

---

## 4. UAT findings — scope decisions for PR 4

Two findings surfaced during PR 3 review that affect — or do not
affect — PR 4 scope. Recording them here so the spec doesn't have
to re-derive the routing.

### 4.1 Cold-vs-warm topology semantics (in scope, small)

`forge_bridge/corpus/_topology.py::snapshot_topology` reads the
`_tool_filter._cache` directly. Cold-cache state renders as
`reachable: false` because no probe has occurred. The current
docstring articulates this implicitly ("Unknown / unreachable
state is itself truthful Layer 1 data"); the UAT signal is that a
small explicit note distinguishing cold-cache-not-yet-probed from
actually-unreachable would harden the documentation against
future readers misinterpreting the snapshot.

**Routing:** docstring-level addition only. Lands alongside PR 4
or as a tiny separate commit before PR 4. **No code change.**
No carrier sentence change.

### 4.2 Stray-header-mid-file warning sharpness (deferred)

The reader's `validate_capture_record` rejection of a stray header
appearing mid-file produces a generic "missing required top-level
keys" WARNING. Sharpening this to "stray header mid-file" would
improve operator legibility but adds reader-side classification
logic that the spec §9.3 deliberately constrained ("reader does
NOT yield malformed-sentinel records, does NOT expose a skip
count, does NOT attempt repair").

**Routing:** defer to PR 6 polish or a v1.5.x patch. **Not in PR 4
scope.** Adding it to PR 4 would dilute the participation-creep
focus.

If a future contributor surfaces the same UAT finding, redirect
here.

---

## 5. Surface-before-implementation discipline (carries from PR 3)

The PR 3 surface-before-implementation discipline carries through
PR 4:

1. **This framing artifact** (registered now, this commit).
2. **PR 4 spec** (`A.5.3.2-PR4-SPEC.md`) — drafted from this
   framing in the next session. Surfaces for review before any
   code lands.
3. **Implementation** — derived from the spec. Surfaces for review
   before staging.
4. **Atomic merge** — PR 4 ships as one coherent integration
   landing. Implementation pacing may vary; review pacing may
   vary; merge cadence does not.

The user's pacing clause from PR 3 still applies: pausing at
structural seams (call-site shape, allowlist mechanism, test
fixtures) is explicitly acceptable. Partial surfacing is
review-only, not mergeable. PR 4's mergeability contract:
chat-handler call site + allowlist update + integration tests +
participation-creep grep test land together or not at all.

---

## 6. What PR 4 is NOT

- **Not the chain-step integration.** PR 5 covers `console/_step.py`.
  PR 4 + PR 5 are split deliberately so the chat-handler call site
  gets focused review attention; the chain-step site adds
  the second allowlist entry and the second integration-test
  bundle without re-litigating the call-site shape.
- **Not the seed corpus drive.** Gate 2 (a future spec) drives the
  fixture-based seed prompts. PR 4 only enables the runtime probe
  at the chat handler.
- **Not the comparator.** Gate 4. Not in Gate 1 scope at all.
- **Not feature work.** PR 4 ships the integration that turns on
  Layer 1 capture in production. Operator-visible behavior change:
  none, until `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` is set.

---

## 7. Resume protocol

When the next session opens:

1. **Read this framing first** before drafting anything. The
   risk-category shift (§0) is the load-bearing context; losing it
   is how the chat-handler integration accidentally grows
   participation features.
2. **Draft `A.5.3.2-PR4-SPEC.md`** from this framing. The spec
   sequences the implementation and resolves the deferrals named
   above (visual-asymmetry lint mode, integration-test design,
   participation-creep grep mechanism, allowlist parameter shape).
3. **Surface the spec for review** per the established discipline.
4. **Then implement** against the spec.
5. **Commit** with the framing's two opening sentences in the
   commit message body.

Do not begin drafting the spec without re-reading this framing.
The risk-category shift is the load-bearing context; losing it is
how the chat-handler integration accidentally fuses observation
with arbitration.

---

## 8. Cross-references

- `A.5.3.2-FRAMING.md` § "Threat articulation" — the
  planner-agreement-frequency failure mode that participation
  creep would re-introduce.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` §8.8 — live correlation
  prohibition; same prohibition shape as risk 1.3 above.
- `A.5.3.2-GATE-1-SPEC.md` §5.1 — visual-asymmetry pattern
  (carries verbatim into PR 4's call-site implementation).
- `A.5.3.2-GATE-1-SPEC.md` §5.3 — three architecturally-prohibited
  patterns at the capture call sites.
- `A.5.3.2-PR3-SPEC.md` §10 — discipline-grep test mechanism that
  PR 4 transitions to allowlist mode.
- `A.5.3.2-PR3-SPEC.md` §5 — orthogonal truth surfaces that the
  call site supplies as explicit inputs.
- `SEED-RELIABILITY-PHASE-METHODOLOGY-V1.6+.md` § 2.3 —
  property-preservation discipline; the §0 carrier sentences are
  an instance.
