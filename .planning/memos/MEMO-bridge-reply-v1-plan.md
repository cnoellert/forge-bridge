# MEMO — forge-bridge (DT) reply: greenscreen→roto v1 — three answers + corrections accepted

**Date:** 2026-06-10
**From:** forge-bridge (DT) · **To:** forge-vision
**Re:** Phase-6 greenscreen→roto primitives — answering the three teed-up questions before the brief dispatches to code
**Companion artifacts:** vision-side build brief `PHASE-6-GREENSCREEN-ROTO-PRIMITIVES.md` (vision repo); bridge composition-seam reference `.planning/VISION-COMPOSITION-SEAM.md` (this repo, merged #45)

---

## Corrections accepted (all four right; one confirmed against the code)

- **Topology is by list-ness + key-name, not cardinality=N.** Confirmed: `_extract_enumeration` finds the collection via `_PREFERRED_COLLECTION_KEYS` + `list[dict]` detection (`forge_bridge/graph/filter.py:91-102, 246-259`). The earlier "cardinality=N" framing in the bridge reply was imprecise; vision's is the real mechanism.
- **Attach is explicit** (`forge_register_publish` + `import_clips`), not automatic — accepted.
- **Chain authoring is bridge-side** — accepted (chat-compile / bridge macro; a consumer may *originate* the request, but the chain logic lives bridge-side).
- **"tag" = comment/name token**, no native Flame keyword API — accepted.

The smaller/cleaner v1 (two operators; `roto_ref` reusing the holdout contract; the flag as the whole routing boundary) is the right shape.

---

## The decisive grounded fact

The filter primitive routes on a **top-level scalar**: `evaluate_predicate` does `value = item.get(predicate.field)` (`filter.py:205`) — a single-level dict lookup, **no nested-path traversal**. A nested Evidence record is therefore invisible to routing. So vision's "surface a top-level `is_greenscreen`, keep the Evidence record nested underneath" isn't just clean — **the code mandates it**. Vision stamps the flag, the bridge routes on it, vision never decides.

---

## Q1 — `is_greenscreen: bool` vs `shot_class == "greenscreen"` → **take `is_greenscreen: bool`**

- The filter routes on a top-level scalar with first-class bool coercion (`_parse_literal` "true"→`True`; `_coerce_comparable` folds bool↔number; `filter.py:262-302`). `filter(is_greenscreen == true)` routes natively.
- Cinematic tagging is **multi-label** ("atomic cinematic components"). A `shot_class` enum forces one mutually-exclusive axis — a shot is greenscreen *and* day-ext *and* handheld. Per-property bools keep each atomic component an independent predicate, congruent with the filter's flat-predicate-AST nature (no nested, no OR; `filter.py:5-6`).
- Abstention stays **per-property** (omit one flag) instead of all-or-nothing (omit the whole `shot_class`).
- Field proliferation (one bool per property) is the real cost — but it's the *correct* shape: atomic components genuinely are many independent flags, and a derived roll-up (`tags[]` / `shot_class`) can be **added** later without removing the bools.

**Routing-form nudge:** author the chain as **`filter(is_greenscreen == true)`, not `is_greenscreen exists`.** If vision ever emits explicit `false` for confident-negatives (vs. omit-on-abstain), `exists` would wrongly match `false` (`false` isn't in the absent set, `filter.py:208`); `== true` is robust to both emission strategies.

## Q2 — attach/tag tail is authored chain-side, NOT vision's call → **confirmed**

`roto_ref` answers one question (produce the soft-alpha matte by-reference) and stops. The tail — `forge_register_publish` (register the matte as a version + location) → `import_clips` / Flame attach → tag via comment/name token — are **bridge-authored chain steps**, executed by the bridge calling forge tools. Vision never decides the attach. Substrate-not-producer exactly: vision = primitive, graph = composition, Flame = consumer.

## Q3 — `roto_ref` distinct tool vs extend `derive_holdout_mattes` → **distinct tool, reuse the contract**

Vision's operator to own, but the architectural lean: **reuse the artifact contract (`DerivedHoldoutsArtifact` → `PlatformLocator.path` + sha256), keep the operator identity distinct.** The composability doctrine is one-operator-one-question; `roto_ref` answers a different question (roto-reference for the greenscreen foreground) than general holdout derivation, even if the output *type* is shared. Overloading `derive_holdout_mattes` with a roto-intent mode pushes a "which mode?" disposition into the operator — exactly the judgment that should live in the consuming (chain) layer, not the primitive.

**Deciding test:** could a chain ever want both in the same graph, or are they always interchangeable? Interchangeable → it's already `roto_ref` under another name; alias + document. Distinguishable-in-a-chain → distinct tool. From here it reads distinguishable.

---

## Green light

Nothing in the brief is structurally blocked on these — dispatch when ready. Q1 fixes the exact output token (`is_greenscreen: bool`, route via `== true`); Q3 settles new-vs-extend before code starts. Both save a rework loop.
