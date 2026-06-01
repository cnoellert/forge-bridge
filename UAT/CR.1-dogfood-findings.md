# CR.1 Conversational Reads — author-driven dogfood findings (2026-06-01)

Status: **corpus frozen** at 11 reads. This is the CR.1 close-input artifact and the
ranked input to the next milestone's legibility work. It is **not** an artist UAT
(see §7) and makes no artist-comprehension-fidelity claim.

---

## 1. What this is

The first author-driven dogfood of the v1.9 CR.1 conversational-reads answer-pass:
real natural-language reads driven through `POST :9996/api/v1/chat`, escalating from
trivial to mildly compositional, with the comprehension-capture gate on. The goal
(per the v1.9 thesis) was never a passing grade — it was to **generate a real
comprehension-failure corpus** so legibility work can be ranked. It did.

### Build / environment provenance (grounded, not assumed)

- **Daemon source:** loaded from `/Users/cnoellert/GitHub/forge-bridge/forge_bridge`,
  `main @ dab749b`, working tree clean. Behavior confirmed current-code by the
  forced-tool answer-pass firing live (the `a95bf0d` amendment, which exists only on
  current `main`).
- **Caveat (metadata only):** the forge-env `forge_bridge.__version__` reports `1.4.1`
  (stale editable metadata never re-anchored in the forge env; base env `pip show` is
  `1.5.1`). Source path + live amendment behavior both prove the *code* is current;
  the version string is a cosmetic smell, not stale code.
- **Launch:** `:9996` brought up via the stdio-held-open recipe
  (`tail -f /dev/null | python -m forge_bridge mcp stdio`, capture env prepended) —
  the http transport does not co-host `:9996` (the Phase 20.1 gap;
  `SEED-CONSOLE-LAUNCH-DECOUPLING-V1.9+`).
- **Model:** `qwen2.5-coder:14b` (local Ollama, `sensitive=True`).
- **Data:** project `013_13_13_2026_2_1_portofino` (id `2753ec84-…`) on pg `:7533`;
  bus `:9998` up; `graph_store` healthy.
- **Capture gate:** `FORGE_BRIDGE_COMPREHENSION_CAPTURE=1` →
  `~/.forge-bridge/comprehension/comprehension-2026-06-01.jsonl`.

---

## 2. Headline finding — the answer-pass is attached at the wrong seam for the
real failure distribution

CR.1 places the model answer-pass at the `chain_complete` seam: it humanizes a chain
**only when the chain succeeds**. But across these 11 reads, **mildly-complex reads
overwhelmingly fail _upstream_ of that seam** — at intent compilation and tool
resolution — so the humanization layer never runs. v1.9 humanized the one path these
reads do not reach.

This is the single most important corpus signal: **the dominant legibility gap is in
the compile/resolution layer, before the model is ever allowed to speak.** Every tool
that actually *executed* returned correct, well-structured data (iteration `6`, batch
groups, reels). The answer-pass sits downstream of all the failures and cannot rescue
a chain that never completes.

The precise restatement of the operator's verdict ("we've built a substrate that
doesn't communicate"): **the substrate computes correctly; the compile layer cannot
reliably turn an artist's sentence into the right single-tool chain, and when it fails
it leaks raw internals instead of speaking human.** CR.1's answer-pass is
*necessary-but-insufficient* — and aimed at the minority case.

---

## 3. Read ledger (all 11, with wire evidence)

Counts: **11 reads driven · 2 correct · 9 failed · 3 captured to corpus.**

| # | Read | Result (wire) | Shape | Layer |
|---|------|---------------|-------|-------|
| R1 | What batch groups are on the desktop | ✅ correct — `flame_list_batch_groups` → Untitled Batch (open), gen_0460, spike_260430_ddi, spike_260430_e5y | — | — |
| R2 | What reels are on the desktop | ✅ correct — `flame_list_desktop` → WIP_20260408 [Graphics 10c, Legal, Slates, Backup 1seq, Sequences 3seq] | — | — |
| R3 | What is the name of the current desktop | ❌ "The current desktop name is *Untitled Batch*." `flame_list_desktop` returned **no desktop-name field**; model grabbed the first batch group | **fabrication from missing field** (cut-line breach) | answer-pass |
| R4 | What's the name of the current reels group | ❌ MUTATING preview `[flame_get_batch_reels, __commit__]`, `requires_ratification:true` (screenshot 9.44.45) | **read miscompiled as mutation** (`__commit__` injected) | compile |
| R5 | What is the name of the current batch | ❌ MUTATING preview `[flame_list_batch_groups, __commit__]`, `graph_intent_id 82c304791e2e`, `requires_ratification:true` | **read miscompiled as mutation** | compile |
| R6 | What iteration is gen_0460 on? | ❌ `chain_aborted` — `forge_get_batch_iterations` returned `current_iteration:6` ✓, then injected `format_result` failed (`params.format` missing) | **compiler injected a broken extra step; answer was one field away** | compile |
| R7 | List the shots on 30sec_edit 21? | ❌ `MULTIPLE_PROJECTS` — "Multiple projects found. Please specify one." | **ambiguous project context → raw error** (no session scope) | compile/context |
| R8 | What is the path to shot 10 on 30sec_edit 21? | ❌ `chain_aborted` — "Step matched 4 tools… use a more specific verb/noun (e.g. 'list versions' instead of just 'list')" | **resolver paralysis + leaked internal hint** | compile/resolve |
| R9 | Does shot 10 on 30sec_edit 21 have a timewarp? | ❌ same "matched 4 tools" abort | resolver paralysis | compile/resolve |
| R10 | What's the duration of shot 10 on 30sec_edit 21? | ❌ same "matched 4 tools" abort | resolver paralysis | compile/resolve |
| R11 | What's the duration in frames of 30sec_edit 21 | ❌ `tool_forced` → **`flame_set_start_frames`** called empty → `ToolError` (`params.sequence_name` missing) returned **as the answer** | **read compiled to a mutation tool** + raw error stringified as prose | compile + answer-pass |

Screenshots: `UAT/Screenshot 2026-06-01 at 9.44.45 AM.png` (R4 mutation preview),
`UAT/Screenshot 2026-06-01 at 9.45.22 AM.png` (R3 fabricated desktop name).

---

## 4. Failure taxonomy (ranked by frequency × severity)

### Compile/resolution layer — DOMINANT (7 of 9 failures)

1. **Read miscompiled as mutation (R4, R5, R11 — 3×).** The compiler appends a
   `__commit__` step (R4, R5) or forces an outright mutation tool (`flame_set_start_frames`,
   R11) onto reads. This is both a comprehension failure (a question becomes a
   "Ratify & Apply" prompt or a write attempt) **and a doctrine breach** — the
   reads-vs-mutations split CLAUDE.md calls *structural* is being crossed by the
   compiler. Highest severity: a read should never reach the mutating branch.
2. **Resolver paralysis (R8, R9, R10 — 3×).** A compiled step matches N>1 tools; the
   exact-match resolver refuses and surfaces internal guidance ("matched 4 tools; use
   a more specific verb") to the artist. This is the documented
   `pre-orchestration-resolution-paralysis` shape, live on ordinary reads.
3. **Compiler injects broken extra steps (R6 — 1×).** A complete read
   (`forge_get_batch_iterations` → `6`) is killed by an appended `format_result`
   called with a missing required `format` param. The answer existed; the compiler's
   own step aborted the chain.
4. **No session scope (R7 — 1×).** No current-project context, so every project-scoped
   read is ambiguous (`MULTIPLE_PROJECTS`) and answered with a raw error rather than a
   conversational "which project?". The artist must restate scope every turn.

### Answer-pass layer — SECONDARY (2 of 9 failures)

5. **Fabrication from missing field (R3 — 1×).** When the tool result lacks the
   asked-for field, the answer-pass invents a plausible-adjacent value instead of
   saying the field isn't present. Direct breach of the v1.9 cut line: *"MAY NOT
   synthesize facts that do not exist."* Most dangerous *answer-layer* shape —
   confident, wrong, indistinguishable from correct to an artist.
6. **Raw error envelope passed through as prose (R11).** The answer-pass stringified a
   `ToolError` JSON as the human answer — it does not recognize/triage error envelopes.

---

## 5. Corpus-instrument blindspot (a finding about the instrument itself)

Capture writes a record only on `chain_complete` / successful `tool_forced` synthesis.
Result: **of 11 reads, 3 wrote records (R1, R2, R3); 8 wrote nothing** — and the 8
silent reads are *exactly* the compile/resolver/mutation/abort/error failures that
dominate §4. Even R11's `tool_forced` error did not capture.

So the corpus, as built, captures the 2 successes + the 1 fabrication and is **blind
to 8 of 9 failures.** Any ranking driven only by the JSONL corpus will systematically
**under-weight the compile-layer failure class that is the actual problem.** This
artifact (the manual wire ledger in §3) exists precisely because the automated corpus
could not see most of what happened.

Remediation options for the next pass (not actioned here): capture at the
`preview_emitted` / `chain_aborted` / error seams too, with a route/outcome tag — note
this is adjacent to, but distinct from, the known two-path (compile-reaching vs
forced-tool) limitation.

---

## 6. What this is NOT

- **Not a substrate-data problem.** Zero tool/data failures. Every executed tool
  returned correct structured data. Per `project-substrate-to-usability-crossing`,
  these failures are meant to be human/legibility, not architectural — **the crossing
  is working as designed.** The documented trap is "fixing" this in the substrate;
  this pass deliberately did not.
- **Not artist UAT.** This is author-driven. Non-developer artist UAT remains an
  explicit v1.9 carry-forward; CR.1 close must not claim artist-comprehension fidelity
  (`feedback-operational-maturity-not-completeness`).

---

## 7. Ranked input to the next legibility milestone

1. **Stop reads from compiling into the mutating branch** (R4/R5/R11). Highest severity
   — comprehension failure *and* doctrine breach. The read/mutation classifier and the
   `__commit__`/mutation-tool injection on reads are the first thing to harden.
2. **Resolve resolver paralysis for ordinary noun-phrases** (R8/R9/R10). Relax discovery
   / tighten action per `pre-orchestration-resolution-paralysis`; never leak "matched N
   tools" to a human surface.
3. **Move (or duplicate) the legibility seam upstream**, or at minimum humanize the
   compile/resolve/abort/error envelopes — the answer-pass at `chain_complete` cannot
   reach the majority failure path.
4. **Session scope / project context** so project-scoped reads don't dead-end on
   `MULTIPLE_PROJECTS` (R7).
5. **Answer-pass: refuse-on-missing-field + error-envelope triage** (R3, R11) — uphold
   the cut line; never stringify a `ToolError` as an answer.
6. **Fix the corpus instrument** to capture the failure seams (§5).

---

## 8. Reproduction

Daemon up (current code, capture on):

```
FORGE_BRIDGE_COMPREHENSION_CAPTURE=1 FORGE_DB_URL=postgresql+asyncpg://forge:forge@127.0.0.1:7533/forge_bridge sh -c 'tail -f /dev/null | /Users/cnoellert/miniconda3/envs/forge/bin/python -m forge_bridge mcp stdio'
```

Drive a read:

```
curl -s -X POST http://127.0.0.1:9996/api/v1/chat -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"What iteration is gen_0460 on?"}]}'
```

Captured records: `~/.forge-bridge/comprehension/comprehension-2026-06-01.jsonl`.
