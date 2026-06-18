# M2 Slice 1 — Fix-Back Brief (post-DT/Creative verify)

**Date:** 2026-06-18 · **Status:** pass-to-code (remediation) · **Branch:** `feat/m2-slice1-unified-dispatch` (append fix-back commits).
**Parents:** [[M2-SLICE-1-SEAM-DESIGN]] · [[M2-SLICE-1-PASS-TO-CODE]] · framing [[M2-PARITY-AND-CUTOVER-FRAMING]].

## Verdict context

Slice 1 was DT+Creative verified against the live branch. **The hard structural seams are honored** — `executor.py` byte-untouched, abort-as-orchestration (`AbortOnFirstErrorDispatch`), one-table fail-closed dispatch, `resolved_class` added, 40 green / `__all__` 19 / ruff clean. **Three fix-back items + one defer**, all converged with the room. This is **one fix-back pass before merge** over `compare.py` + `admission.py` + a fixture; the Seam B doc amendment is already done (Orch).

The pattern the verify found: *structure faithful, safety-semantics thinned and masked by deterministic toy fixtures.* The fixes restore the safety-semantics. **Do not let the slice close as "parity proven" until FB1 lands** — "40 green" currently carries more confidence than the harness earns.

---

## FB1 (headline) — surgical volatile normalizer + real-capture fixture

**Why:** `compare.py` does raw equality on `terminal_output`; it passes only because the test's `_FakeMCP` returns deterministic toy payloads. Without a normalizer, `compare_strategy_for` is **unsound**: it picks `double_exec` for roto on `idempotent=True`, but roto is **idempotent-result / volatile-envelope** — two identical-input calls return different provenance uuids, so raw compare fails. The normalizer is the precondition that makes `double_exec` valid, not polish.

**The captures are real and on the branch** (DT, this session — re-pulled from the live tool, not transcribed):
- `tests/composition/fixtures/roto_ref_gs_010_call_a.json`, `…_call_b.json` — two same-input roto runs.
- greenscreen captures already persisted (Phase 2, `test_m1_boundary_contract.py`).

**The normalizer spec is empirical (derived from the two-call diff — implement exactly, do not guess):**

- **STRIP / canonicalize (volatile — differ across the two identical-input calls):**
  `content_hash` · `artifact.artifact_id` · `artifact.sequence_locator.path` · `artifact_refs[].artifact_id` · `artifact_refs[].locator` · `graph_event_id` · top-level `request_id`.
- **PRESERVE (stable — idempotency-proving; stripping these blinds the compare):**
  `artifact.media_content_sha256` (the output-matte sha — byte-identical `19ffdc03…` across both calls = roto's idempotence, *proven*) · `derived_from.media_content_sha256` · `artifact_refs[].payload_id` · `derivation_run.request_id` · all structural fields.

**Two non-obvious requirements the capture forces:**
1. **Surgical, not blanket:** strip provenance uuids but **PRESERVE the content-shas.** `media_content_sha256` is the *signal* (a real matte divergence must fail the compare); `artifact_id` is the *noise*. Strip the sha and you'd pass two different mattes as equal.
2. **`sequence_locator.path` and `artifact_refs[].locator` embed the artifact_id** (`…/roto_<artifact_id>/…`). A field-level delete misses them — these need **uuid-canonicalization inside the string**, not field deletion. A naive normalizer still diverges here.

**The test (strictly stronger than record-replay):** inject `call_a` and `call_b` (divergent provenance, identical matte sha) and assert the normalizer collapses them to **equal**. Identical bytes would never exercise the normalizer; divergent-provenance/identical-matte does. This retires the toy-fake problem and is the captured-not-assembled discipline (same as the Phase-2 error-key fix).

**Honest scope note (state it in the harness docstring):** a *live* round-trip (both paths hitting the daemon) is inherently **slice-5** work. What slice 1 proves now is the **real-shape, real-volatility compare** (inject the two captures, assert normalized-equal). The normalizer lands now regardless — it's what makes `double_exec` sound.

---

## FB2 — structure the four admission declarations + relabel roto as a make

Two facets of one fix (the admission table currently launders a make and a read as identical):

**FB2a — structure all four criteria as bools (fail-closed on omission).** Today only `idempotent` is structured; `synchronous` / `returns_reference` / `no_state_mutation` are folded into a free-text `declaration`, so registration mechanically requires only idempotence — S1-B's "assert the declaration" is ¼ true. Make all four structured fields that **fail closed if any is omitted at construction**:
- `synchronous` · `returns_reference` · `no_state_mutation` · **`idempotent_result`** (rename from `idempotent` — disambiguate from *envelope-determinism*; this is the exact conflation FB1's headline turned on, and `compare_strategy_for` keys off it).
- **Honesty caveat (name them as declarations, not facts):** bridge cannot *verify* "no_state_mutation" of a sibling tool — these are **declared properties whose truth is sibling-contractual** ([[project_federation_facts_judgment_spine]]), verified for real when #86's specimen lands. Doc them as such; don't imply behavioral verification.
- Add the **S1-B negative test**: constructing/registering an admission record with a missing declaration **raises** (fail-closed).

**FB2b — relabel roto (provenance-corruption fix, do regardless).** roto is currently `resolved_class="mcp.read_perception"` — identical to greenscreen — recording a **make as a read** in the `resolved_class` audit trail this slice just added. DT's capture *proves* roto is a make: it writes a `DerivedHoldoutsArtifact` EXR (`artifact.sequence_locator.path`), which greenscreen never produces. Relabel:
- roto → `resolved_class="mcp.synchronous_make"` (or `mcp.reference_make` — pick one, keep it consistent with Seam A's "reference-producing synchronous operator" vocabulary). `dispatch_kind` stays `"mcp"` (same mechanism).
- greenscreen stays a read-class.
- **Payoff:** once structured + relabeled, the two get visibly different profiles (roto: `returns_reference=True`, make-class; greenscreen: read-class) — the table stops laundering them. FB2a and FB2b are the same fix seen twice.

---

## FB3 — Seam B doc amendment (DONE — Orch)

Ratified the stricter design: assent flows through the dispatch closure; the executor never references assent at all. Framing-doc Seam B updated (wording + enforcement + redline-resolution line). The slice-1 guard (`test_m2_executor_invariants.py`, total assent-token ban scoped to `executor.py`) is **kept as-is** — do not loosen it. No code change in this item; slice-3's author threads assent via the closure, never an executor param.

---

## FB5 (defer — track, do not build) — corpus persistence

`PARITY_CASES` as a static in-code tuple is fine for slice 1. The atomic-append JSONL log only matters when corpus-wide compare gates cutover (slice 6). **Tracking note for when it lands:** follow the atomic-append-JSONL + versioned-schema pattern (same discipline as the CR.1 comprehension corpus), at `~/.forge-bridge/parity/specimens.jsonl` per the original brief. Flag it; don't block merge.

---

## Acceptance (slice-1 exit gate, post-fix)

- **FB1:** normalizer collapses `call_a`/`call_b` (divergent provenance, identical matte) to equal; the greenscreen→filter→roto compare passes *through the normalizer* on real-shape captures (not toy fakes). `media_content_sha256` is preserved (a mutated-matte negative diverges).
- **FB2:** all four admission declarations structured + fail-closed negative green; roto profile = make-class + `returns_reference=True`; greenscreen = read-class.
- Executor grep-invariant still green (unchanged). `__all__` still 19. ruff clean. Full suite green.

## Instructions for code

1. **Same branch** (`feat/m2-slice1-unified-dispatch`); append atomic fix-back commits (one per FB item).
2. **Load the persisted captures** (`tests/composition/fixtures/roto_ref_gs_010_call_{a,b}.json`) — do **not** hand-author a "realistic" dict; that recreates the toy-fake problem with more keys.
3. **Normalizer:** implement the empirical strip-set exactly; **preserve content-shas**; **uuid-canonicalize the locator paths** (don't field-delete them).
4. **Rename `idempotent` → `idempotent_result`** across `admission.py` + `compare.py` (`compare_strategy_for`) + tests.
5. **Report back:** the normalizer-collapse test result, the post-fix admission profiles (roto vs greenscreen), the suite count, and `len(forge_bridge.__all__)`.
