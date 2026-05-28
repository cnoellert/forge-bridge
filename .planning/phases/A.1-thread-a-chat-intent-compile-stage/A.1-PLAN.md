---
milestone: v1.7
thread: A
phase: A.1
phase_name: Chat intent-compile stage — the compile + preview surface
status: phase-plan
drafted: 2026-05-27
revised: 2026-05-27 (v3 — Stage 1b normalization pass: F-1 outer wait_for line corrected (:1721 → :1711), F-2 tests/graph/ enumeration extended (4 → 7 files), F-3a SSE done-payload consumer lines corrected (:1166/:1140 → :1165/:1142), F-4 file-manifest IFFs lifted to definitive rulings, F-5 discuss artifact body synced to ratified state — no architectural change; v2 retained: B-1..B-12 sweep + S-1 (delete handler-side dead paths) + S-2 (UAT-iterable prompt wording) + S-3 (Path b explicit local guard) + sub-question (a) (tool_enforced/tool_forced=False for envelope continuity) + Creative refinements applied. Sweep-expectation invariant: future `grep :1166\|:1140` against this file returns exactly 1 hit on THIS archaeology line — not drift; intentional preservation of the superseded coordinate system. Per Creative Stage 1b 2026-05-27.)
type: phase-plan
derives_from: .planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-DISCUSS-QUESTIONS.md
governing_rulings: R-A1.1 (compile method) + R-A1.2 (commit-node classifier) + R-A1.3 (preview wire shape) + R-A1.4 (insertion point) + R-A1.5 (chat-side terminal taxa)
artifact_role: code-handoff — implementation hands off against this spec after Stage 1b verification clears
review_state: awaiting-stage-1b-verification
---

# A.1 — Chat intent-compile stage

> **What this artifact is.** The code-handoff phase plan for A.1, the
> opening phase of Thread A (v1.7 milestone's main arc). It locks
> the compile primitive's signature, the commit-node classifier's
> contract, the preview wire shape, the chat-side terminal taxa
> family, the JSON/SSE dual-transport integration, the handler-side
> dead-path deletions, the test plan, and the file change manifest.
> Implementation hands off against this spec after Stage 1b
> verification clears (DT seat).
>
> **What this artifact is not.** Not implementation. Not a partial
> draft to be filled during execution. The contracts below are the
> spec; deviation requires a spec amendment, not implementation-time
> discretion.

## Scope

A.1 ships the compile + preview surface of Thread A's
NL → compile → canonical graph → execution substrate → host arc.
Specifically:

- A new `LLMRouter.compile_intent(...)` text-completion method —
  additive sibling to `complete_with_tools(...)`, not a replacement.
- A new `CompileError` family in `forge_bridge/llm/router.py`
  (sibling to `LLMToolError` family; one base + five concrete taxa
  = six classes total).
- A substrate utility `graph_contains_commit_node(steps)` walking
  compiled chain-step text against `graph/commit.py:is_commit_step`.
- A new `console/_chat_compile.py` module owning the
  compile → classify → preview/execute branch — shared helper
  callable from both JSON and SSE chat paths.
- Integration at the `chat_handler` JSON path (handlers.py:1712)
  AND `_chat_sse_response` (handlers.py:1025) — both paths replace
  `router.complete_with_tools(...)` with the compile-branch helper.
- A new preview wire shape: `preview` field on the JSON envelope +
  `event: graph_intent_preview` SSE event taxon.
- Five new chat-side terminal SSE event taxa:
  `compile_complete` / `preview_emitted` / `chain_complete` /
  `chain_aborted` / `compile_error`.
- **Deletion of consumer-side dead paths** in `chat_handler` and
  `_chat_sse_response` (S-1 ruling 2026-05-27): the Phase 24.4
  termination branches, the `_on_message` callback +
  `event: message` taxon, the `enforced_system` construction +
  threading, and the `_build_orchestration_terminated_body`
  handler-private helper. Reversibility lives in git history, not
  in zombie scaffolding.

Per the discuss artifact: A.1 is the **compile + preview** surface.
A.2 ships ratification + enforced apply (assent as substrate
record, commit.verify extended to check assent, CLI ratify surface).
A.3 is hardening — surfaced once A.1/A.2 land.

Per `[[feedback-substrate-not-producer]]` (twice over): A.1 adds
substrate primitives (compile_intent, classifier, preview shape) and
consumer wiring (chat handler) on top. Other callers of
`complete_with_tools(...)` (none in production today; test consumers
only) remain reachable in the legacy agentic regime; chat moves to
compiled regimes 2/3 (THREAD-A-FRAMING.md §"Coexistence
architecture"). **Coexistence is upheld at the ROUTER substrate
level; consumer-side dead paths are deleted.**

## Substrate inventory (grounded; do not duplicate)

Verified 2026-05-27 against current `main` (`1d7afc8`):

- **LLMRouter.acomplete** — `forge_bridge/llm/router.py:377`,
  signature `acomplete(prompt, sensitive=True, system=None,
  temperature=0.1) -> str`. Routes to `_async_local(:1181)` when
  `sensitive=True` (Ollama via OpenAI-compat shim) or
  `_async_cloud(:1201)` when `sensitive=False` (Anthropic).
  **Compile uses the same `_async_local` / `_async_cloud`
  primitives directly** (per S-3 Path b ruling) — same sensitive
  flag, same `system=` override semantics. Does NOT delegate to
  `acomplete()` body.
- **LLMRouter.complete_with_tools** — `forge_bridge/llm/router.py:422`.
  The Phase 24.4 agentic executor. **Untouched by A.1**; remains the
  legacy-agentic substrate primitive (test consumers only post-A.1,
  per B-7 verification — zero production non-chat callers).
- **LLMToolError family** — `forge_bridge/llm/router.py:188-258`.
  Public exception block: `LLMLoopBudgetExceeded(:202)` /
  `RecursiveToolLoopError(:224)` / `LLMToolError(:242)`. Sibling
  placement convention for `CompileError` family — define alongside,
  consistent with the FB-C D-16 module-cohesion precedent.
- **_in_tool_loop ContextVar** — `forge_bridge/llm/router.py:319`.
  Re-instantiated locally in `compile_intent` body per S-3 (Path b).
- **chat_handler** — `forge_bridge/console/handlers.py:1206`.
  Rate-limit (:1241), body validation (:1257-1373 approx), tool
  list assembly + reachability filter (PR-pre-14), macros short-circuit
  (:1427-1462), `->`-chain dispatch (PR30; :1486-1520), PR14
  message-pre-filter (:1529), PR15 enforced-system construction
  (:1600-1607 — **DELETED by A.1 per S-1**), PR20 forced-execute
  short-circuit (:1623-1640), Accept-header SSE branch (:1687), JSON
  path `complete_with_tools` call (:1712 — **REPLACED by A.1**),
  Phase 24.4 termination branch (:1797-1818 — **DELETED by A.1 per
  S-1**), PR15 output validation (:1826), success envelope (:1852).
- **_chat_sse_response** — `forge_bridge/console/handlers.py:953`.
  Phase 24.3 SSE streaming response. The inner `_run_loop` (:1021)
  calls `router.complete_with_tools(...)` at **:1025** (verified
  via grep; v1's :1024 reference was a one-line drift) with
  `message_callback=_on_message` for history-grows streaming.
  **Body REPLACED by A.1; signature shrinks (enforced_system,
  tool_enforced_flag kwargs deleted per S-1).** Phase 24.4
  orchestration-terminated branch (:1109-1145) + `_on_message`
  callback definition (:1018-1020) + `event: message` emission
  (:1019) + `event: done` emission (:1159-1168) — **ALL DELETED
  by A.1 per S-1**. The `event: error` transport-error taxon
  (:1045-1108 emit sites) — **PRESERVED unchanged** (transport
  errors still fire post-A.1).
- **_build_orchestration_terminated_body** —
  `forge_bridge/console/handlers.py:889-950`. **DELETED by A.1 per
  S-1** — handler-private helper consumed only by the two Phase
  24.4 branches that A.1 deletes.
- **_format_sse_event** — `forge_bridge/console/handlers.py:879`.
  Single-line JSON `data:` payload, blank-line frame terminator.
  Used verbatim for all new SSE taxa.
- **run_chain_steps** — `forge_bridge/console/_engine.py:14`.
  Signature `run_chain_steps(*, steps: list[str], tools: list,
  mcp, request_id, client_ip, started) -> dict`. Sequential,
  abort-on-first-error. Returns the PR31 unified envelope
  `{status, request_id, chain, error}`. **This IS the post-compile
  executor** — Gap #3 grounding. No new executor component.
- **_execute_chain (the PR30 wrapper)** —
  `forge_bridge/console/handlers.py:797`. Builds JSONResponse around
  `run_chain_steps` output. A.1's compile-branch helper follows the
  same body-then-envelope pattern.
- **commit.is_commit_step** — `forge_bridge/graph/commit.py:67`,
  signature `is_commit_step(text: str) -> bool`. Tests for bare
  `commit` keyword (case-insensitive, whitespace-tolerant). **The
  load-bearing primitive** A.1's classifier folds over.
- **commit.parse_commit_step** — `forge_bridge/graph/commit.py:72`.
  Stricter validator that raises `CommitError("NOT_COMMIT_STEP")`
  if not a commit step. Not called from A.1 — A.1's classifier
  uses the lighter `is_commit_step` predicate.
- **MutationManifest + MutationManifestError** —
  `forge_bridge/graph/mutation.py:28-101`. Not touched by A.1; the
  substrate already exists. A.1's compile-branch never constructs
  or validates manifests — those flow through tools per Q3
  composition.
- **parse_chain** — `forge_bridge/console/_chain_parse.py:58`,
  signature `parse_chain(message: str) -> List[str]`. Splits on
  literal `->` separator. **Reused** in A.1's preview-shape
  derivation (for per-step tool_name extraction).
- **build_enforcement_system_prompt** —
  `forge_bridge/console/_tool_enforcement.py` (PR15). **Module
  remains; chat_handler stops calling it.** Per S-1 + L7: zero
  production non-chat callers exist; the handler-side `enforced_system`
  construction at :1604 is deleted. The `build_enforcement_system_prompt`
  module function itself is preserved for any future restoration;
  but its only chat-side consumer is the two `complete_with_tools`
  call sites A.1 replaces, so the variable construction is dead
  consumer code per S-1.
- **filter_tools_by_message + deterministic_narrow** —
  `forge_bridge/console/_tool_filter.py` (PR14 + PR21). Untouched
  by A.1; compile inherits the same narrowed tool set the
  executor would have received.
- **expand_macro + resolve_query_entities + enrich_messages_with_resolved_entities**
  — `forge_bridge/console/_macros.py:expand_macro` (called at
  handlers.py:1464), `_name_resolve.py:resolve_query_entities`
  (called at :1465 with resolved-params builder at :1466), and
  `_name_resolve.py:enrich_messages_with_resolved_entities`
  (called at :1473). All **untouched by A.1**; compile_intent
  receives the enriched `messages_for_llm` (post macro + entity +
  enrichment), not raw `messages`. See B-3 / L5 closing paragraph.
- **emit_divergence_capture** —
  `forge_bridge/console/handlers.py:1580-1598` (PR4 §5). Untouched
  by A.1; compile_intent runs downstream of this capture.

The substrate is ready. A.1 adds compile + preview operator surfaces
over it AND deletes the now-orphaned handler-side dead paths from
the legacy-agentic chat path.

## Locks

Locks are the load-bearing contract anchors Stage 1b verifies. Any
deviation from these requires a spec amendment, not
implementation-time discretion.

### L1 — Compile primitive signature

**`router.compile_intent(...)` is additive on `LLMRouter`. The
signature and semantics below are the contract.**

```python
async def compile_intent(
    self,
    prompt: str,
    tools: list,
    *,
    sensitive: bool = True,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_seconds: float = 30.0,
) -> list[str]:
    """Compile NL into a deterministic chain-step list.

    Text-completion primitive — single LLM call, no tool loop. Routes
    via the same sensitive→local / non-sensitive→cloud primitives
    acomplete() uses (_async_local / _async_cloud) BUT does NOT
    delegate to acomplete() — applies the same _in_tool_loop entry
    guard re-instantiated locally per S-3 ruling. Parses the model
    response into list[str] chain-step text validated against
    parse_chain() syntax.

    Args:
        prompt:      The user message / NL intent.
        tools:       Registered tool surface (post-PR14 narrowing).
                     Tool descriptions are formatted into the compile
                     prompt; the caller does NOT need to call any
                     adapter prep.
        sensitive:   True → Ollama (local); False → Anthropic (cloud).
                     Verbatim from acomplete() routing.
        system:      Compile-specific system prompt. If None, falls
                     back to a built-in compile prompt that does NOT
                     inherit self.system_prompt and does NOT include
                     PR15's enforcement language. Caller may pass an
                     override; the override REPLACES (does not stack
                     on) the built-in compile prompt.
        temperature: Sampling temperature. Default 0.1 for
                     deterministic compile output.
        max_seconds: Wall-clock cap on the single LLM call. Default
                     30s. Caller wraps with its own asyncio.wait_for
                     if a different budget is required.

    Returns:
        list[str] — chain-step text, one entry per step, validated
        against parse_chain() shape. Empty list is a structural
        outcome (raises CompileUnresolvableIntent, never returned).

    Raises:
        CompileUnresolvableIntent: LLM produced no recognizable
            graph-intent (empty / no parseable content).
        CompileInvalidChainShape: LLM output couldn't parse to
            list[str] chain steps (e.g., invalid `->` separator
            usage, syntactically malformed).
        CompileToolUnknown: Graph references a tool name not in
            the registered `tools` list.
        CompileSeamViolation: (architectural anchor) compile
            produced host-mutation step without a paired commit
            step. Substrate-impossible today per R-A1.2's
            preview-only short-circuit; the taxon exists so the
            invariant is named in the public surface.
        CompileBudgetExceeded: Wall-clock cap fired before the LLM
            returned. Wraps the underlying asyncio.TimeoutError.
        RecursiveToolLoopError: Called from within an outer
            complete_with_tools() — _in_tool_loop ContextVar is True.
            Per S-3: this guard is re-instantiated LOCALLY as the
            first executable statement in compile_intent's body, NOT
            inherited by composition through acomplete().
    """
```

**Naming convention:** the method is `compile_intent` (verb-object).
Mirrors the discuss artifact R-A1.1. The return type is `list[str]`
(not a structured graph object) per Q2 grounding —
graph-intent IS validated chain-step text, the same substrate-shape
exec produces.

**Per S-3 (Path b explicit local guard).** `compile_intent`'s body
MUST include as its first executable statement:

```python
if _in_tool_loop.get():
    raise RecursiveToolLoopError(
        "compile_intent() called from within complete_with_tools() — "
        "recursive LLM call blocked. See LLMTOOL-07 / D-12..D-14 "
        "and S-3 ruling (Stage 1b 2026-05-27)."
    )
```

Rationale: control-flow invariants are local to the orchestration
surface that depends on them. Per
`[[feedback-orchestrator-control-flow-not-meaning]]`. Otherwise
acomplete's body changes silently change compile semantics
(hidden-inheritance-seam shape per Creative's Stage 1b coinage).

### L2 — CompileError family

**The CompileError family is one base class + five concrete taxa =
six classes total. Placement: sibling to `LLMLoopBudgetExceeded` /
`RecursiveToolLoopError` / `LLMToolError` block in
`router.py:188-258`.**

```python
class CompileError(RuntimeError):
    """Base for all compile-stage structural failures.

    Caught by chat_handler (and any future compile consumer) and
    mapped to HTTP status:
      CompileUnresolvableIntent  → 422 (model could not produce a graph)
      CompileInvalidChainShape   → 422 (output malformed)
      CompileToolUnknown         → 422 (graph references unknown tool)
      CompileSeamViolation       → 500 (substrate invariant violated)
      CompileBudgetExceeded      → 504 (wall-clock cap fired)

    Per discuss artifact FC-4: sweep-completeness at spec time, not
    implementation time. All five concrete taxa are defined here; no
    taxon invented during implementation.
    """


class CompileUnresolvableIntent(CompileError):
    """LLM produced no recognizable graph-intent.

    Attributes:
        raw_response: The model's raw text (truncated to 2KB if
                      longer). Diagnostic only — preview surface
                      may render this as compile diagnostic per
                      Gap #1.
    """


class CompileInvalidChainShape(CompileError):
    """LLM output couldn't parse to list[str] chain steps.

    Attributes:
        raw_response: As CompileUnresolvableIntent.
        parse_error:  String describing the parse failure
                      (e.g., "empty step at index 2",
                       "malformed -> separator").
    """


class CompileToolUnknown(CompileError):
    """Compiled graph references a tool name not in the registered set.

    Attributes:
        unknown_tool: The unknown tool name string.
        step_index:   Index of the offending step (0-based).
        step_text:    The offending step's text.
    """


class CompileSeamViolation(CompileError):
    """Architectural anchor — compiled graph produced host-mutation
    without a paired commit step.

    Substrate-impossible today per R-A1.2's preview-only short-circuit:
    if the graph contains ANY commit-step, it routes to preview-only;
    if it contains zero commit-steps, no mutation is executed. The
    taxon exists so the invariant is named in the public surface and
    a future regression that introduces a host-mutation path bypassing
    R-A1.2 lands a distinct, named error class.

    Attributes:
        offending_step_text:  The host-mutation step that lacks a paired commit.
        offending_step_index: Index of the offending step.
    """


class CompileBudgetExceeded(CompileError):
    """Wall-clock cap fired before compile_intent's LLM call returned.

    Attributes:
        max_seconds: The cap value that fired.
        elapsed_s:   Wall-clock seconds elapsed when the cap fired.
    """
```

**Anti-scope:** no `CompileError` is exported via `forge_bridge.__all__`.
The compile family is internal to `forge_bridge.llm`; chat_handler
imports the names directly from `forge_bridge.llm.router`. Preserves
the 19-symbol public surface invariant.

### L3 — Commit-node classifier

**`graph_contains_commit_node(steps)` is the substrate utility. It
walks `list[str]` chain steps and returns True iff any step is a
commit-step per `commit.is_commit_step`.**

Placement: `forge_bridge/graph/commit.py`, appended after the
existing `is_commit_step` / `parse_commit_step` block (after line
82), before the `CommitVerification` dataclass at line 85.

```python
def graph_contains_commit_node(steps: list[str]) -> bool:
    """True iff any step in the chain is a commit step.

    Substrate-grounded classifier for R-A1.2's preview-only routing:
      - zero commit nodes  → executable via run_chain_steps
      - one+ commit nodes  → preview-only (A.1 stub for A.2's ratify)

    Folds over commit.is_commit_step (which already encodes the
    `commit` keyword grammar). No new commit-detection logic in A.1 —
    this is composition over the existing primitive.
    """
    return any(is_commit_step(step) for step in steps)
```

**Per-step classification (for the preview shape's `would_mutate`
field) uses `is_commit_step(step_text)` directly.** A commit step IS
the authority-transition node; it is the substrate-honest
single-step indicator. Non-commit steps may or may not call mutation
tools, but the **chain-level** decision is what R-A1.2 cares about,
and the **step-level** flag exposes the commit-step itself in the
preview. Both are folds over the same primitive.

### L4 — Preview wire shape

**The preview JSON envelope + SSE event payload share an identical
schema. Both surfaces emit the same dict shape — only the transport
differs.**

```python
preview = {
    "kind": "graph-intent-preview",
    "steps": [
        {
            "step_text":    str,    # verbatim chain-step text
            "tool_name":    str,    # parsed first token; "__commit__"
                                    #   for commit-steps
            "args_preview": dict,   # parsed args from the step text
            "would_mutate": bool,   # True iff is_commit_step(step_text)
        },
        # ...one entry per step in compile_intent's output...
    ],
    "summary": {
        "total_steps":            int,   # len(steps)
        "mutating_steps":         int,   # count of steps with
                                          #   would_mutate=True
        "requires_ratification":  bool,  # mutating_steps > 0
    },
}
```

**Wire shape locations:**

- JSON envelope — new top-level `preview` field on the
  `chat_handler` JSON response. `null` for regime-2 (executable, no
  preview short-circuit); populated dict for regime-3 (preview-only
  short-circuit per R-A1.2).
- SSE event — `event: graph_intent_preview` taxon. The `data:`
  payload is `{preview: {...}}` (the same dict shape, wrapped in a
  one-key envelope to mirror existing `data:` patterns).

**`tool_name` parsing.** Use the existing step-parse utility:
`step_text.split(maxsplit=1)[0]` for the first token; if
`is_commit_step(step_text)` returns True, override to the literal
string `"__commit__"`. The `__commit__` sentinel avoids ambiguity
with hypothetical tools named `commit`.

**`args_preview` parsing.** Use `forge_bridge.console._param_extract`
(the PR28 deterministic extractor) for each step. The same
extractor PR20's forced-execute path uses; consistency with the
existing chat dispatch substrate.

### L5 — Insertion point preserves all live preamble; deletes orphaned dead paths

**A.1 replaces ONLY the two `router.complete_with_tools(...)` call
sites in `console/handlers.py` — JSON path at :1712 and SSE path at
:1025. All live PR-numbered preamble is preserved unchanged. Dead
paths orphaned by the replacement (Phase 24.4 termination branches,
_on_message callback, enforced_system construction, event: done
emission) are DELETED per S-1 ruling.**

| Preamble surface | Line(s) | A.1 disposition |
|---|---|---|
| Rate-limit (D-13/CHAT-01) | 1241 | unchanged |
| Body validation (D-02) | 1257-1373 | unchanged |
| Tool list + reachability filter (PR4 §5) | 1368-1407 | unchanged |
| Macros short-circuit | 1427-1462 | unchanged — non-LLM path |
| `->`-chain dispatch (PR30) | 1486-1520 | unchanged — exact-compile path |
| PR14 message-pre-filter | 1529 | unchanged — see L6 semantic-shift note |
| PR21 deterministic narrow | 1554-1559 | unchanged |
| PR15 enforced-system construction | 1600-1607 | **DELETED per S-1 / L7** |
| PR20 forced-execute | 1623-1640 | unchanged — see L8 disposition |
| Empty-tools guard | 1650 | unchanged |
| Accept-header SSE branch | 1687 | unchanged — both branches integrate |
| **JSON path LLM dispatch** | **1712** | **REPLACED** — `compile_intent` + branch helper |
| Phase 24.4 termination branch (JSON path) | 1797-1818 | **DELETED per S-1 / L9** |
| PR15 output validation | 1826 | **DELETED per S-1** (only consumed model-emitted text; the new regime-2/3 paths do not produce model text) |
| JSON success envelope | 1852 | RESHAPED per D4 (new envelope fields per L4 / L9) |
| `_build_orchestration_terminated_body` helper | 889-950 | **DELETED per S-1** (handler-private; only consumed by deleted branches) |
| `_chat_sse_response` `_on_message` callback definition | 1018-1020 | **DELETED per S-1** (consumed only by deleted message_callback arg) |
| `_chat_sse_response` `event: message` emission | 1019 | **DELETED per S-1** (callback-driven) |
| `_chat_sse_response` `enforced_system` kwarg | 958 (signature) + 1029 (call site) | **DELETED per S-1** |
| `_chat_sse_response` `tool_enforced_flag` kwarg | 967 (signature) | **DELETED per S-1** (replaced with inline `False` in regime-2/3 payloads per sub-question (a)) |
| **SSE path LLM dispatch** | **1025 (inside `_chat_sse_response`)** | **REPLACED** — same branch helper |
| `_chat_sse_response` Phase 24.4 termination branch | 1109-1145 | **DELETED per S-1 / L9** |
| `_chat_sse_response` `event: done` emission | 1159-1168 | **DELETED per S-1** (replaced by regime-specific terminal events per L9) |
| `_chat_sse_response` `event: error` transport-error emission | 1045-1108 (catch blocks) | **PRESERVED unchanged** (transport/runtime errors still fire) |
| `_format_sse_event` helper | 879 | unchanged — used by all new taxa |

**Non-PR-numbered live preamble — also unchanged.** Per B-3 sweep
completeness:

`expand_macro` at :1464, `resolve_query_entities` at :1465,
`enrich_messages_with_resolved_entities` at :1473, `divergence_capture`
emission at :1580-1598, and the `tool_call_count_in` tally at :1675
(if retained — see B-11 sub-note in v2 process) are similarly
unchanged. **Mechanically: `compile_intent` operates on
`messages_for_llm` (the enriched messages produced after macro
expansion, entity resolution, and enrichment), NOT on the raw
`messages` from the request body.** This is the load-bearing
execution-shape claim B-3 surfaces — implementers must not
inadvertently pass raw `messages` to compile.

### L6 — PR14 semantic-role-shift note

**PR14's code is byte-equivalent post-A.1. Its semantic role shifts
upstream by one stage.**

- Pre-A.1: PR14 narrows the tool space the EXECUTOR sees → the LLM
  picks tool calls from the narrowed space.
- Post-A.1: PR14 narrows the tool space the COMPILER sees → the
  LLM composes a graph from the narrowed space.

Both reduce the LLM's decision space per
`[[feedback-pre-orchestration-resolution-paralysis]]`. The
load-bearing surface moves; the code does not. Per discuss artifact
Stage 1b carve-out #8: this note exists so a Stage 1b reviewer does
not catch "PR14 looks the same but means something different now"
as drift. The drift is named; PR14 stays.

### L7 — PR15 system prompt disposition (Path A — override) + handler-side construction deleted

**`compile_intent` takes an optional `system=` override and the chat
handler passes a compile-specific prompt. PR15's
`build_enforcement_system_prompt(...)` is NOT inherited. The
handler-side `enforced_system` construction at :1604 (and threading
through `_chat_sse_response` at :958 / :1029 / :1693) is DELETED
per S-1.**

Rationale per discuss artifact R-A1.4 carve-out 1 + S-1 + B-7:

- PR15's enforcement language is built FOR the executor's tool-call
  determinism — "use tools as primary modality, force HARD-TOOL
  when one survivor." Compile is text-completion, not tool-call.
  The model produces chain-step TEXT, not function calls. PR15's
  enforcement is semantically wrong for the compile call.
- `compile_intent`'s built-in fallback prompt (used when caller
  passes `system=None`) encodes compile-specific instructions:
  available tool catalogue, chain syntax (`->` separator, no inline
  natural language between steps), and the `commit` keyword's
  authority semantics.
- The chat handler builds a compile system prompt via a new helper
  `build_compile_system_prompt(tools)` (in `console/_chat_compile.py`)
  and passes it explicitly: `compile_intent(prompt=..., tools=tools,
  system=compile_sys)`.
- **B-7 verification (DT Stage 1b 2026-05-27):** zero production
  non-chat callers of `complete_with_tools` exist. The handler-side
  `enforced_system` variable has no remaining consumer post-A.1.
  Preserving it would be dead consumer scaffolding, not substrate
  preservation. Per Creative's refinement (S-1 ruling):
  **"preservation buys ambiguity, not reversibility."** Reversibility
  lives in git history.

**`build_enforcement_system_prompt` module function itself is
preserved** (it lives in `_tool_enforcement.py` and is module-level
substrate-shape — A.1 does not delete the module). What A.1 deletes
is the chat-handler's invocation of it. If A.1 is ever reverted, a
single git-restore of the chat-handler dispatch + a single re-add
of the variable reconstructs the executor path.

### L8 — PR20 forced-execute disposition (Ruling A)

**PR20 stays as a deterministic pre-compile shortcut. It does NOT
route through `compile_intent`.**

Rationale per discuss artifact R-A1.4 carve-out 2:

- PR20 is non-LLM; compile is LLM. They serve different surfaces.
- The three coexistence-architecture regimes (THREAD-A-FRAMING.md
  §"Coexistence architecture") describe **chat's LLM-bound dispatch
  surface**. PR20 is upstream of all three — a deterministic
  short-circuit that bypasses LLM dispatch entirely when the
  PR14-filtered set collapses to exactly one tool.
- If the forced tool is a mutation tool (e.g., `flame_rename_shots`),
  the mutation seam lives on the TOOL substrate (per Q3 grounding
  in THREAD-A-FRAMING.md). PR20's forced invocation goes through
  the tool's existing preview/apply mode — chat does not need to
  interpose a graph-intent stage between PR20 and the tool.
- A "degenerate compile" routing (one-step graph-intent → run_chain_steps)
  is defensible but introduces a 4th LLM-bound regime (forced-tool
  via inferential preamble) for no architectural gain. Held off.

**A.1's three chat regimes are LLM-bound; PR20 is a pre-LLM
deterministic short-circuit alongside the three.** Stage 1b
reviewers should read the regime enumeration as LLM-bound dispatch,
not system-wide.

### L9 — Chat-side terminal taxa (new) + handler-side Phase 24.4 termination DELETED

**Per R-A1.5: Phase 24.4's three taxa (`done` /
`orchestration_terminated` / `error`) stay untouched in
`complete_with_tools` (`router.py:988, :1018`). Chat's SSE path
under A.1 emits a NEW taxa family at the chat-handler level. The
chat-handler-side Phase 24.4 termination consumption (both the JSON
branch at :1797-1818 and the SSE branch at :1109-1145) is DELETED
per S-1, because the K=2 trigger no longer fires from the chat
path post-A.1.**

The K=2 trigger and its taxa describe the EXECUTOR's terminal
states. Under A.1, chat no longer calls the executor for the
inferential path — the trigger doesn't fire FROM CHAT. The
executor's emission code stays intact in `router.py` for any other
caller. Chat's SSE taxa family becomes additive at the chat surface,
not a rename of router-side taxa.

| Chat-side terminal taxon | Intermediate vs terminal | Fires when | JSON-path analogue |
|---|---|---|---|
| `event: compile_complete` | intermediate | `compile_intent` returns a non-empty graph-intent before classification | not in JSON envelope; intermediate event only |
| `event: preview_emitted` | terminal | regime-3 short-circuit: graph contains commit node; preview returned, no execution | top-level `preview` field populated + `stop_reason="preview_emitted"` |
| `event: chain_complete` | terminal | regime-2: `run_chain_steps` finished cleanly (zero commit nodes path) | `stop_reason="chain_complete"` + `chain` array populated |
| `event: chain_aborted` | terminal | regime-2: a step in the chain failed; chain halted | `status="error"` envelope + `error.code="CHAIN_STEP_FAILED"` (matches existing `_engine.py:65` shape) |
| `event: compile_error` | terminal | `CompileError` raised during compile_intent | `error.code="compile_*"` envelope with the specific taxon as suffix |

**SSE event payload shapes (per B-1: `final_text` field is OMITTED
in regime-2 / regime-3 terminal payloads — match handlers.py:929-933
convention; including empty string would create ambiguity with
model-emitted empty responses):**

```
event: compile_complete
data: {"request_id": "...", "steps_count": N}

event: preview_emitted
data: {"preview": {...L4 shape...}, "stop_reason": "preview_emitted",
       "request_id": "...", "tools_available": N, "tools_filtered": M,
       "tool_enforced": false, "tool_forced": false}
       # final_text OMITTED per B-1

event: chain_complete
data: {"chain": [...], "stop_reason": "chain_complete",
       "request_id": "...", "tools_available": N, "tools_filtered": M,
       "tool_enforced": false, "tool_forced": false}
       # final_text OMITTED per B-1

event: chain_aborted
data: {"chain": [...partial...], "error": {"code": "CHAIN_STEP_FAILED",
       "message": "...", "step_index": N, "original_error": {...}},
       "stop_reason": "chain_aborted", "request_id": "..."}

event: compile_error
data: {"error": {"code": "compile_unresolvable_intent" |
                          "compile_invalid_chain_shape" |
                          "compile_tool_unknown" |
                          "compile_seam_violation" |
                          "compile_budget_exceeded",
                 "message": "...", "details": {...taxon-specific...}},
       "stop_reason": "compile_error", "request_id": "..."}
```

**`event: error` transport-error taxon (handlers.py:1045-1108
emit sites) is PRESERVED with unchanged semantics.**
Transport/runtime errors (timeout, rate-limit, unhandled exception,
LLMLoopBudgetExceeded inherited via compile budget,
LLMToolError, RecursiveToolLoopError) continue to emit
`event: error`. The new `compile_error` taxon is specific to
structural compile failures, NOT a rename. Distinct surfaces per
`[[feedback-description-layer-multi-register-surface]]` — different
registers reach different behaviors.

**Per sub-question (a) ruling (operator 2026-05-27):** the
`tool_enforced` and `tool_forced` fields ARE retained in regime-2
and regime-3 envelopes (always emitted as `false`) for
response-shape continuity. Existing wrapper parsers
(`forge_bridge/llm/call_wrapper.py` and any downstream consumer)
read these fields; preserving them as `false` is a zero-cost
backwards-shape guarantee. A future motion may replace with a
single `chat_regime` field per MOL-6; that is a separate
spec-amendment surface, not an A.1 deliverable.

### Minor locks

- **MOL-1. Compile prompt template — structurally locked, wording
  UAT-iterable.** `console/_chat_compile.py` owns
  `build_compile_system_prompt(tools)` which formats the available
  tool surface into compile instructions. The template is
  implementation-detail; the contract is: (a) tool catalogue
  rendered with name + description per tool, (b) chain syntax
  named (literal `->` separator), (c) `commit` keyword's
  authority-transition role named, (d) NO PR15 enforcement
  language inherited. Test contract verifies (a)-(d) are present
  in the produced prompt; exact wording is not locked.

  > **Per S-2 ruling (Creative + DT 2026-05-27).** The compile
  > prompt's exact wording is expected to iterate during operator
  > UAT (D7 acceptance items #7-8). Spec locks structural
  > properties (a)-(d); wording is operator-tunable post-landing.
  > A revision to the prompt wording does NOT require a spec
  > amendment.
  >
  > **The architecture is the law. The wording is tuning.**
  > (Creative coinage, Stage 1b 2026-05-27.)
  >
  > Locking wording would treat prompt prose as constitutional
  > law; it isn't. Heads off future writing-room churn over
  > prompt-prose nits.

- **MOL-2. Compile budget defaults.** `compile_intent`'s
  `max_seconds=30.0` default. Chat handler does NOT override —
  passes through. The outer 125s wait_for at chat handler
  (handlers.py:1711 pre-A.1; recomputed at the new compile-branch
  call site) wraps compile + run_chain_steps combined; compile's
  30s budget leaves ~90s for execution.
- **MOL-3. `final_text` field is OMITTED from regime-2 and regime-3
  JSON responses.** Per B-1 (Creative + DT Stage 1b 2026-05-27;
  the most important single catch in the review):

  > **NOT included: `final_text`.** Matches handlers.py:929-933
  > existing convention: *"The orchestrator does not produce
  > conversational text in this case. Including an empty string
  > would create ambiguity with model-emitted empty responses
  > (which are a different failure mode, not the same shape).
  > Omission is unambiguous."*

  Regime-2 `chain_complete` JSON: `final_text` field is omitted
  entirely (NOT empty string).
  Regime-3 `preview_emitted` JSON: `final_text` field is omitted
  entirely.
  Regime-error JSON: `final_text` field is omitted (the error
  envelope is the body, not a content payload).

  The SSE payload tables in L9 follow this convention — the
  `final_text` field does not appear in `chain_complete` /
  `preview_emitted` / `chain_aborted` / `compile_error` /
  `compile_complete` event payloads.

  Implementer must NOT include `final_text: ""` "for parity" —
  that re-introduces the exact semantic ambiguity the existing
  convention solved. Per
  `[[feedback-orchestrator-control-flow-not-meaning]]`: omission
  encodes orchestration-decided semantics distinctly from
  model-emitted semantics.

- **MOL-4. Preview-only regime returns HTTP 200.** A
  `preview_emitted` JSON response is HTTP 200 (it is a structural
  success — the compile completed and routed to preview
  correctly), with `preview` populated and `chain` empty.
  Distinct from `compile_error` (HTTP 4xx/5xx per L2 mapping
  table).
- **MOL-5. No new public exports.** `forge_bridge.__all__` stays
  at 19. `compile_intent`, `CompileError` family,
  `graph_contains_commit_node`, and `build_compile_system_prompt`
  are all module-private to their respective packages and reached
  via direct imports from chat-handler internals.
- **MOL-6. Chat regime telemetry log line.** Every chat response
  logs a `chat_regime=` field naming the regime that fired:
  `compiled_non_mutating` (regime 2) /
  `compiled_mutating_preview` (regime 3) /
  `compile_error` / `transport_error`. Legacy `legacy_agentic` is
  NOT a chat-side regime post-A.1 (per S-1: chat no longer
  dispatches through `complete_with_tools`); it is only meaningful
  for non-chat callers and therefore not part of the chat
  telemetry vocabulary. Operationalizes the
  THREAD-A-FRAMING.md coexistence-architecture enumeration in
  observable telemetry per
  `[[feedback-provenance-precedes-behavioral-interpretation]]`.
- **MOL-7. `ollama-compile` log line extension for compile.** Phase
  24.1's `ollama-turn` structured log line at `_adapters.py:send_turn`
  is for `complete_with_tools` calls. compile_intent does NOT
  share that path — it uses `_async_local`. Add a sibling
  structured log line `ollama-compile` at the compile call site
  (router.py compile_intent body) capturing
  `model + cache_prefix_hash + prompt_tokens + completion_tokens +
  duration_ms` per `[[feedback-provenance-precedes-behavioral-interpretation]]`
  + FC-2 grounding. Cold prefix is an expected first-invocation
  cost; the log line makes it observable.
- **MOL-8. Test fixtures mock the LLM, not the substrate.**
  `compile_intent` tests use MagicMock or AsyncMock on
  `_async_local` / `_async_cloud` directly, mirroring the
  client-builder MagicMock pattern at
  `tests/llm/test_complete_with_tools.py:70-82` (per B-5 — the
  v1 `_MockOpenAI` / `_MockAnthropic` citation was a memory-shaped
  fixture hallucination; corrected here). The compile→branch →
  run_chain_steps integration tests in `tests/console/` use the
  same approach for the compile portion + an in-memory MCP for
  the chain execution portion.
- **MOL-9. Cross-thread isolation.** A.1 modifies only the
  surfaces listed in the file change manifest below. Thread C
  surfaces (`forge_bridge/mcp/tools.py`,
  `forge_bridge/mcp/registry.py`,
  `forge_bridge/core/vocabulary.py`) are untouched. The
  asset-operability work + the compile-stage work proceed in
  parallel without substrate overlap.

## Deliverables

Spec order matches expected commit sequence. Implementation hands
off in this order; commits land in roughly D1..D8 cadence.

### D1 — `compile_intent` method + `CompileError` family on `LLMRouter`

**File:** `forge_bridge/llm/router.py`

**Substrate-first landing per `[[feedback-substrate-before-consumer-landing]]`.**
The primitive lands and is tested on its own commit; consumer
adoption (chat handler) rides later.

**Changes:**

1. Add the `CompileError` family (one base class + five concrete
   taxa = six classes total) immediately after the existing
   `LLMToolError` block (after line 258), before the
   `_OrchestrationTerminated` private signal class at line 276.
2. Add the `compile_intent` method to `LLMRouter`, placed after
   `acomplete` (line 420) and before `complete_with_tools` (line 422).
3. **Per S-3 (Path b explicit local guard):** `compile_intent`'s
   body MUST include as its first executable statement:
   ```python
   if _in_tool_loop.get():
       raise RecursiveToolLoopError(
           "compile_intent() called from within complete_with_tools() — "
           "recursive LLM call blocked. See LLMTOOL-07 / D-12..D-14 "
           "and S-3 ruling (Stage 1b 2026-05-27)."
       )
   ```
   Compile does NOT delegate to `acomplete()` — it calls
   `_async_local` / `_async_cloud` directly and re-instantiates the
   guard locally. Per
   `[[feedback-orchestrator-control-flow-not-meaning]]`.
4. Add a module-private `_parse_compile_output(raw, tools) -> list[str]`
   helper that walks the raw LLM text and produces validated
   chain-step list. Raises the appropriate `CompileError` taxon.

**Acceptance:**

- `compile_intent("list shots", tools=[...], sensitive=True)`
  returns `list[str]` when the mocked LLM produces a valid `->`-separated
  string.
- Empty mocked-LLM output raises `CompileUnresolvableIntent`.
- Malformed mocked output (`"foo -> -> bar"`) raises
  `CompileInvalidChainShape`.
- Output referencing `{"tool_name": "nonexistent_tool"}` raises
  `CompileToolUnknown` with `unknown_tool="nonexistent_tool"`.
- Mocked-LLM `asyncio.TimeoutError` wraps to `CompileBudgetExceeded`.
- `compile_intent` called from within `complete_with_tools` raises
  `RecursiveToolLoopError` (the LOCAL guard fires; not via
  composition through `acomplete`).
- `compile_intent` does NOT modify `_in_tool_loop` ContextVar — it
  is not a loop; nested compile_intent calls are permitted (and
  harmless because the guard tests, doesn't set).
- `compile_intent` with `system=None` produces an LLM call whose
  system prompt does NOT contain PR15's HARD-TOOL enforcement text
  (verified by inspecting the mock's recorded `messages` argument).
- `compile_intent` does NOT call `await self.acomplete(...)`
  internally (verified by spy on `LLMRouter.acomplete`).

### D2 — `graph_contains_commit_node` substrate utility

**File:** `forge_bridge/graph/commit.py`

**Changes:**

1. Append `graph_contains_commit_node(steps: list[str]) -> bool`
   per L3 contract. Place after the existing
   `is_commit_step` / `parse_commit_step` block (after line 82),
   before the `CommitVerification` dataclass at line 85.

**Acceptance:**

- `graph_contains_commit_node([])` returns `False`.
- `graph_contains_commit_node(["list shots"])` returns `False`.
- `graph_contains_commit_node(["flame_rename_shots dry_run=False", "commit"])` returns `True`.
- `graph_contains_commit_node(["commit"])` returns `True`.
- Case-insensitive: `graph_contains_commit_node(["COMMIT"])` returns `True`.

### D3 — `console/_chat_compile.py` branch helper module

**File:** `forge_bridge/console/_chat_compile.py` (new)

**Module owns the compile → classify → preview/execute branch.**
Callable from both JSON and SSE chat paths; returns a structured
dict either path can wrap in its native envelope.

**Exports:**

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class CompileBranchOutcome:
    """Structured outcome of the compile-branch helper.

    Carries enough state for either transport (JSON or SSE) to
    construct its native envelope without re-deriving anything.

    Fields:
        regime:      "compiled_non_mutating" | "compiled_mutating_preview"
                   | "compile_error" | "chain_aborted"
        steps:       The list[str] chain-step text compile produced.
                     Empty on compile_error.
        preview:     The L4 preview dict if regime is
                     "compiled_mutating_preview"; None otherwise.
        chain_body:  The run_chain_steps return dict if regime is
                     "compiled_non_mutating" or "chain_aborted";
                     None otherwise.
        compile_error: The CompileError instance if regime is
                       "compile_error"; None otherwise.
    """
    regime: str
    steps: list[str]
    preview: Optional[dict]
    chain_body: Optional[dict]
    compile_error: Optional[Any]


def build_compile_system_prompt(tools: list) -> str:
    """Format the compile system prompt from the registered tool
    surface. See MOL-1 contract.
    """


async def run_compile_branch(
    *,
    router: Any,
    user_prompt: str,
    tools: list,
    mcp: Any,
    request_id: str,
    client_ip: str,
    started: float,
    compile_system: Optional[str] = None,
) -> CompileBranchOutcome:
    """Compile → classify → preview-or-execute branch.

    1. Builds compile system prompt (if not provided).
    2. Calls router.compile_intent(...) — catches CompileError taxa.
    3. Classifies via graph_contains_commit_node.
    4. Either:
       (a) Builds preview dict + returns CompileBranchOutcome(
           regime="compiled_mutating_preview", ...).
       (b) Calls run_chain_steps(...) + returns CompileBranchOutcome(
           regime="compiled_non_mutating" | "chain_aborted", ...).
    """


def build_preview_from_steps(steps: list[str]) -> dict:
    """Construct the L4 preview shape from compiled chain steps.

    Per-step tool_name + args_preview parsing uses the existing
    _param_extract.extract_explicit_params primitive (consistency
    with PR20).
    """
```

**Acceptance:**

- `build_compile_system_prompt([])` produces a prompt with the
  empty-tool-set sentinel and the chain syntax description.
- `build_compile_system_prompt([tool1, tool2])` produces a prompt
  containing both tool names + descriptions + the `commit`
  keyword section.
- `build_preview_from_steps(["list shots"])` returns
  `{kind, steps: [{step_text: "list shots", tool_name: "list",
  args_preview: {}, would_mutate: False}],
  summary: {total_steps: 1, mutating_steps: 0,
  requires_ratification: False}}`.
- `build_preview_from_steps(["flame_rename_shots dry_run=False",
  "commit"])` produces `requires_ratification=True`,
  `mutating_steps=1`, and the second step has `tool_name="__commit__"`,
  `would_mutate=True`.
- `run_compile_branch` with mocked compile returning
  `["list shots"]` produces `regime="compiled_non_mutating"`
  + populates `chain_body` with the `run_chain_steps` envelope.
- `run_compile_branch` with mocked compile returning
  `["flame_rename_shots dry_run=False", "commit"]` produces
  `regime="compiled_mutating_preview"` + populates `preview`
  + leaves `chain_body=None` (no execution).
- `run_compile_branch` with `compile_intent` raising
  `CompileUnresolvableIntent` produces `regime="compile_error"`
  + `compile_error` populated.

### D4 — JSON path integration in `chat_handler` (REPLACES call + DELETES dead paths)

**File:** `forge_bridge/console/handlers.py`

**Changes:**

1. **DELETE** `_build_orchestration_terminated_body` helper at
   :889-950 (handler-private; only consumed by the deleted Phase
   24.4 branches).
2. **DELETE** the `enforced_system` construction at :1604 + the
   `tool_enforced_flag` line at :1607 IFF `tool_enforced_flag` is
   not consumed by PR20 short-circuit. **Verify:**
   `tool_enforced_flag` is consumed by `_execute_forced_tool` at
   :1638 (PR20). Therefore `tool_enforced_flag` STAYS (PR20 still
   needs it); only `enforced_system` is deleted.
3. **DELETE** the Phase 24.4 termination branch at :1797-1818.
4. **DELETE** the PR15 output validation at :1826 (it operated on
   model-emitted `final_text`; A.1's regimes do not produce
   model-emitted text).
5. **REPLACE** the `complete_with_tools` call at :1712 (and its
   surrounding `try/except` block) with a call to
   `run_compile_branch(...)` from D3. The handler builds the
   compile system prompt locally:
   `compile_system = build_compile_system_prompt(tools)`.
6. **RESHAPE** the JSON success envelope at :1852 to one of the
   four new regime-specific shapes:
   - `compiled_non_mutating` → HTTP 200 JSON envelope:
     ```python
     {
       "chain": outcome.chain_body["chain"],
       "stop_reason": "chain_complete",
       "request_id": request_id,
       "tools_available": tools_available_count,
       "tools_filtered": tools_filtered_count,
       "tool_enforced": False,    # per sub-question (a)
       "tool_forced": False,      # per sub-question (a)
       "preview": None,
       # NO final_text per MOL-3 / B-1
     }
     ```
   - `compiled_mutating_preview` → HTTP 200 JSON envelope:
     ```python
     {
       "preview": outcome.preview,
       "chain": [],
       "stop_reason": "preview_emitted",
       "request_id": request_id,
       "tools_available": tools_available_count,
       "tools_filtered": tools_filtered_count,
       "tool_enforced": False,    # per sub-question (a)
       "tool_forced": False,      # per sub-question (a)
       # NO final_text per MOL-3 / B-1
     }
     ```
   - `chain_aborted` → HTTP 400 with body shaped per
     `_engine.py:64-77` (the existing
     `CHAIN_STEP_FAILED` envelope), adding
     `stop_reason="chain_aborted"`.
   - `compile_error` → HTTP 422 (or 504 for `CompileBudgetExceeded`;
     500 for `CompileSeamViolation` per L2 mapping table) via
     `_chat_error(...)` with structured `details` carrying the
     taxon-specific attributes.

**Acceptance:**

- End-to-end test (`tests/console/test_chat_compile_branch.py`)
  with mocked compile + real in-memory MCP exercises regime-2
  full path; response carries `chain` array + `tool_enforced=false`
  + `tool_forced=false` + NO `final_text` field.
- End-to-end test exercises regime-3 preview-only path; response
  carries `preview` populated + `chain=[]` + NO `final_text` field.
- Compile error → 422 with structured `details` carrying
  `unknown_tool` (for `CompileToolUnknown`) or `raw_response`
  (for `CompileUnresolvableIntent`).
- `CompileBudgetExceeded` → 504. `CompileSeamViolation` → 500.
- Existing `test_chat_handler.py` tests still pass (macros,
  `->`-chain, PR20 forced-execute paths all untouched).
- Grep verification: `complete_with_tools` does NOT appear in
  `handlers.py` post-A.1 except optionally in a comment naming the
  historical insertion point.
- Grep verification: `_build_orchestration_terminated_body` does
  NOT appear in `handlers.py` post-A.1.

### D5 — SSE path integration in `_chat_sse_response` (REPLACES call + DELETES dead paths)

**File:** `forge_bridge/console/handlers.py`

**Changes:**

1. **SHRINK** `_chat_sse_response` signature: delete the
   `enforced_system: str` kwarg at :958. Delete the
   `tool_enforced_flag: bool` kwarg if it is only consumed by the
   now-deleted `event: done` payload at :1165 and the deleted
   Phase 24.4 termination payload at :1142. **Verify:**
   `tool_enforced_flag` is consumed at :1165 (SSE done payload) and
   :1142 (SSE termination call); both are deleted; therefore
   `tool_enforced_flag` kwarg is also deleted.
   Inline `False` in the new event payloads per sub-question (a).
   Update the call site at :1693 to match the shrunken signature.
2. **DELETE** the `_on_message` callback definition at :1018-1020
   and the `event: message` emission inside it. Compile is not a
   loop; no per-message streaming.
3. **REPLACE** the `complete_with_tools` call at :1025 (inside
   `_run_loop`) with a call to `run_compile_branch(...)` from D3.
   The `message_callback=_on_message` parameter is REMOVED.
4. **DELETE** the Phase 24.4 termination branch at :1109-1145
   (consumed Phase 24.4 envelope; not reachable post-A.1).
5. **DELETE** the `event: done` emission at :1159-1168 (replaced
   by regime-specific terminal events per L9).
6. **DELETE** the PR15 output validation at :1097-1107 (operated
   on model-emitted text).
7. **REPLACE** the post-call branching with the five new
   chat-side taxa per L9:
   - Emit `event: compile_complete` BEFORE classification when
     `run_compile_branch` produces a non-error
     `outcome.steps` (the intermediate event makes compile-stage
     completion observable in real time per
     `[[feedback-provenance-precedes-behavioral-interpretation]]`).
   - `outcome.regime == "compiled_non_mutating"` →
     emit `event: chain_complete` per L9 payload.
   - `outcome.regime == "compiled_mutating_preview"` →
     emit `event: preview_emitted` per L9 payload.
   - `outcome.regime == "chain_aborted"` →
     emit `event: chain_aborted` per L9 payload.
   - `outcome.regime == "compile_error"` →
     emit `event: compile_error` per L9 payload.
8. **PRESERVE** transport-error taxon (`event: error`) unchanged
   — all existing exception handlers (asyncio.TimeoutError,
   LLMLoopBudgetExceeded inherited via compile budget,
   RecursiveToolLoopError, LLMToolError, unhandled Exception)
   continue to emit `event: error` per the existing catch-block
   patterns at :1045-1108.

**Acceptance:**

- SSE end-to-end test (`tests/console/test_chat_compile_sse.py`)
  for regime-2: SSE stream produces
  `event: compile_complete` → `event: chain_complete`. No
  `event: message` emitted. No `event: done` emitted.
- SSE regime-3 test: stream produces
  `event: compile_complete` → `event: preview_emitted`.
- SSE regime compile-error test: stream produces
  `event: compile_error` with appropriate `error.code` matching
  the taxon (e.g., `compile_unresolvable_intent`).
- SSE regime chain-aborted test: stream produces
  `event: compile_complete` → `event: chain_aborted`.
- Cross-transport parity test: same input → JSON path and SSE
  path produce semantically equivalent terminal state (same
  preview dict / same chain array / same error code). Phase 24.3
  invariant restated.
- Grep verification: `_on_message`, `message_callback`,
  `event: message`, `event: done`, `_OrchestrationTerminated`
  do NOT appear in `handlers.py` post-A.1.

### D6 — `ollama-compile` log line + `chat_regime=` telemetry

**Files:** `forge_bridge/llm/router.py` (compile_intent body) +
`forge_bridge/console/handlers.py` (chat success/error log lines).

**Changes:**

1. In `compile_intent`'s body, after the underlying `_async_local`
   / `_async_cloud` call returns (success or raises), emit a
   `logger.info` structured line:
   ```
   ollama-compile model=%s prompt_tokens=%d completion_tokens=%d
       duration_ms=%d cache_prefix_hash=%s status=%s
   ```
   `cache_prefix_hash` is a stable hash of the system prompt +
   first user-message prefix (the cache key Ollama uses). Per
   MOL-7 + `[[feedback-provenance-precedes-behavioral-interpretation]]`.
2. In chat handler JSON path, extend the existing success log
   line at :1845 with `chat_regime=%s` field. Same in the SSE
   path success log at :1153 (which now logs `chat_regime` per
   the new regime-specific event emission).
3. Existing log lines for transport-error / timeout /
   loop-budget remain unchanged — they fire below the compile
   stage and the regime is `transport_error`.

**Acceptance:**

- Log line inspection in `test_compile_intent.py` confirms
  `ollama-compile` lines fire on every compile call.
- Log line inspection in `test_chat_compile_branch.py` confirms
  `chat_regime=compiled_non_mutating` / `compiled_mutating_preview`
  / `compile_error` fires on each regime's path.
- `chat_regime=legacy_agentic` does NOT appear in any chat-side
  log line post-A.1 (per MOL-6).

### D7 — Tests

**Files:**

- `tests/llm/test_compile_intent.py` (new) — D1 substrate tests.
- `tests/console/test_chat_compile_branch.py` (new) — D3/D4
  integration tests (JSON path).
- `tests/console/test_chat_compile_sse.py` (new) — D5 SSE-path
  tests. Sibling shape to `test_chat_handler_sse.py`.
- `tests/graph/test_commit_classifier.py` (new) — D2 substrate
  tests. **`tests/graph/` directory exists** (verified 2026-05-27:
  contains `test_commit.py`, `test_filter.py`,
  `test_foreach_collect.py`, `test_if_gate.py`, `test_mutation.py`,
  `test_ports.py`, `test_select.py` — 7 files total); no
  `__init__.py` needed (per B-8 — pytest discovers without it).

**Fixture grounding per `[[feedback-fixture-shape-mirrors-production]]`:**

- `compile_intent` tests use **MagicMock or AsyncMock on
  `_async_local` / `_async_cloud` directly**, mirroring the
  client-builder MagicMock pattern at
  `tests/llm/test_complete_with_tools.py:70-82` (per B-5 — v1's
  `_MockOpenAI` / `_MockAnthropic` citation was a memory-shaped
  fixture hallucination per Creative's Stage 1b coinage; corrected
  here). Do NOT mock the `parse_chain` parser or the
  `_parse_compile_output` helper — exercising the parsing path is
  the load-bearing assertion.
- `chat_compile_branch` tests use the fixture pattern at
  **`tests/console/test_chat_handler_sse.py:83-131`** (per B-6 —
  v1's `make_test_app()` / `conftest.py:_LOCATE` citation was a
  memory-shaped fixture hallucination; corrected here):
  `make_client` fixture + `_make_test_tool` helper at :83 +
  `_build_streaming_mock_router` helper at :96. **Implementer
  picks one:** (a) import these helpers from
  `test_chat_handler_sse.py`, or (b) duplicate them inline in the
  new test file. Pick one; do not invent a new fixture.
- SSE tests use the same `make_client` fixture with
  `Accept: text/event-stream` and parse the streamed events
  manually (matching `tests/console/test_chat_handler_sse.py`
  parsing pattern).

**Coverage matrix:**

| Test ID | Coverage |
|---|---|
| `test_compile_intent_parses_valid_chain` | D1 happy path |
| `test_compile_intent_raises_unresolvable_intent_on_empty` | D1 / L2 |
| `test_compile_intent_raises_invalid_chain_shape` | D1 / L2 |
| `test_compile_intent_raises_tool_unknown` | D1 / L2 |
| `test_compile_intent_raises_budget_exceeded` | D1 / L2 |
| `test_compile_intent_local_guard_fires_in_outer_tool_loop` | D1 / S-3 — guard is LOCAL not composed via acomplete |
| `test_compile_intent_does_not_call_acomplete` | D1 / S-3 — verify spy on LLMRouter.acomplete shows zero calls |
| `test_compile_intent_system_override_replaces_default` | L1 / L7 |
| `test_compile_intent_system_none_omits_pr15_language` | L7 |
| `test_compile_intent_emits_ollama_compile_log_line` | D6 / MOL-7 |
| `test_graph_contains_commit_node_empty_returns_false` | D2 |
| `test_graph_contains_commit_node_no_commit_returns_false` | D2 |
| `test_graph_contains_commit_node_with_commit_returns_true` | D2 / L3 |
| `test_graph_contains_commit_node_case_insensitive` | D2 |
| `test_build_compile_system_prompt_renders_tool_catalogue` | MOL-1 |
| `test_build_compile_system_prompt_names_chain_syntax` | MOL-1 |
| `test_build_compile_system_prompt_names_commit_keyword` | MOL-1 |
| `test_build_compile_system_prompt_omits_pr15_enforcement_language` | L7 |
| `test_build_preview_from_steps_zero_commit_nodes` | L4 |
| `test_build_preview_from_steps_one_commit_node` | L4 |
| `test_build_preview_from_steps_commit_tool_name_sentinel` | L4 (__commit__) |
| `test_run_compile_branch_regime_2_routes_to_run_chain_steps` | D3 |
| `test_run_compile_branch_regime_3_returns_preview_only` | D3 / R-A1.2 |
| `test_run_compile_branch_chain_aborted_on_step_failure` | D3 |
| `test_run_compile_branch_compile_error_surface` | D3 |
| `test_chat_handler_json_regime_2_full_path` | D4 |
| `test_chat_handler_json_regime_2_omits_final_text` | D4 / MOL-3 / B-1 |
| `test_chat_handler_json_regime_2_emits_tool_enforced_false` | D4 / sub-q (a) |
| `test_chat_handler_json_regime_3_full_path` | D4 |
| `test_chat_handler_json_regime_3_omits_final_text` | D4 / MOL-3 / B-1 |
| `test_chat_handler_json_compile_error_422` | D4 / L2 |
| `test_chat_handler_json_compile_budget_504` | D4 / L2 |
| `test_chat_handler_json_compile_seam_violation_500` | D4 / L2 |
| `test_chat_handler_json_chat_regime_telemetry_log` | D6 |
| `test_chat_handler_json_preserves_pr14_pr20_pr30_short_circuits` | L5 (preamble preservation) |
| `test_chat_handler_json_no_complete_with_tools_grep` | D4 / S-1 — verify deletion |
| `test_chat_handler_json_no_build_orchestration_terminated_body_grep` | D4 / S-1 — verify deletion |
| `test_chat_handler_sse_regime_2_event_sequence` | D5 |
| `test_chat_handler_sse_regime_3_event_sequence` | D5 |
| `test_chat_handler_sse_compile_error_event` | D5 / L9 |
| `test_chat_handler_sse_chain_aborted_event` | D5 / L9 |
| `test_chat_handler_sse_compile_complete_intermediate_event` | D5 |
| `test_chat_handler_sse_transport_error_event_unchanged` | D5 (existing taxon preserved) |
| `test_chat_handler_sse_no_event_message_grep` | D5 / S-1 — verify deletion |
| `test_chat_handler_sse_no_event_done_grep` | D5 / S-1 — verify deletion |
| `test_chat_compile_json_sse_terminal_state_parity` | D5 cross-transport parity |
| `test_chat_handler_does_not_break_existing_macros` | L5 regression |
| `test_chat_handler_does_not_break_existing_arrow_chain` | L5 regression |
| `test_chat_handler_does_not_break_existing_pr20_short_circuit` | L5 / L8 regression |
| `test_chat_handler_handles_enriched_messages` | B-3 / L5 — compile_intent receives messages_for_llm (post macro + entity + enrichment) |

**Implementation notes for tests:**

- `tests/llm/test_compile_intent.py` mocks
  `_async_local` / `_async_cloud` per MOL-8 (corrected fixture
  pattern per B-5).
- `tests/console/test_chat_compile_branch.py` reuses the fixture
  pattern from `tests/console/test_chat_handler_sse.py:83-131`
  per B-6 corrected citation. **Implementer picks one:** import
  helpers across the test module boundary OR duplicate inline.
  Pick one; do not invent.
- Cross-transport parity test: drive the same input through both
  JSON and SSE paths; assert preview dict equality (for regime 3)
  + chain array equality (for regime 2) + error code equality
  (for compile error).
- Regression tests for L5 preamble preservation: drive
  `list macros`, a `->`-chain message, and a PR20 single-tool
  collapse — assert these short-circuit paths fire BEFORE compile
  and produce their existing responses unchanged.
- The "grep" tests (`test_chat_handler_json_no_*_grep`,
  `test_chat_handler_sse_no_*_grep`) parse handlers.py source
  text and assert specific identifiers do NOT appear. Tests
  encode the S-1 deletion contract structurally; future
  regressions that re-introduce dead paths fail mechanically.

### D8 — Phase close cursor

**File:** `.planning/phases/A.1-thread-a-chat-intent-compile-stage/A.1-CLOSE.md`
(written at phase close, not at implementation handoff).

Mirrors C.1-CLOSE.md shape: archaeology, gate-evidence,
methodology-ledger candidates, carried-forward items for A.2.

## Test plan

Acceptance gate for A.1 implementation:

1. All tests in D7 pass.
2. Existing chat test suite passes unchanged
   (`tests/console/test_chat_handler.py`,
   `tests/console/test_chat_handler_sse.py`,
   `tests/console/test_pr30_chain.py`,
   `tests/console/test_pr33_macros.py`,
   `tests/console/test_pr40_exec.py`).
3. `tests/llm/test_complete_with_tools.py` passes unchanged —
   the legacy-agentic executor is untouched.
4. `tests/console/test_chat_history_handler.py` passes unchanged.
5. PR22 mechanical compliance: no new MCP tools registered; the
   mechanical contract test is unaffected. Verify by running
   `tests/test_tool_contract_enforcement.py` — should report the
   same passing-count as pre-A.1.
6. `fbridge doctor` passes unchanged.
7. Live smoke test: `fbridge chat "list projects"` produces a
   `chain_complete` response with the project list (regime-2 wet
   end-to-end). Per S-2: compile prompt wording iterates during
   this UAT pass; spec amendments NOT required for wording
   adjustments.
8. Live smoke test: `fbridge chat "rename shots in 30sec 21 with
   suffix _v002 -> commit"` produces a `preview_emitted` response
   with the preview dict populated (regime-3 wet end-to-end). Per
   FC-3: operator-facing UAT — the operator will dogfood this
   surface and a sparse list-of-strings preview will fail
   acceptance.

## Doc plan

Acceptance gate for A.1 docs:

1. **Create `docs/CHAT.md` (new file — verified absent
   2026-05-27 per B-9).** Sections:
   - The compile-stage architecture (NL → compile → graph →
     execution substrate → host).
   - The three chat regimes (compiled_non_mutating /
     compiled_mutating_preview / compile_error) — chat-scoped per
     THREAD-A-FRAMING.md §"Coexistence architecture".
   - The preview JSON envelope shape (L4).
   - The five SSE event taxa (L9).
   - The CompileError taxonomy (L2).
   - Cross-link to `THREAD-A-FRAMING.md` and
     `A.1-DISCUSS-QUESTIONS.md` for archaeology depth.
2. No `docs/VOCABULARY.md` change — A.1 introduces no new
   canonical vocabulary terms (graph-intent IS the existing chain
   substrate per Q2; commit IS the existing graph primitive per
   Q3).

## File change manifest

**New files (6 files):**

- `forge_bridge/console/_chat_compile.py` — branch helper module
  (D3)
- `tests/llm/test_compile_intent.py` (D7)
- `tests/console/test_chat_compile_branch.py` (D7)
- `tests/console/test_chat_compile_sse.py` (D7)
- `tests/graph/test_commit_classifier.py` (D7)
- `docs/CHAT.md` (D9 — verified absent 2026-05-27 per B-9)

**Modified files (3 files):**

- `forge_bridge/llm/router.py` — add `CompileError` family (six
  classes) + `compile_intent` method (with S-3 local guard) +
  `_parse_compile_output` helper + `ollama-compile` log line (D1, D6)
- `forge_bridge/graph/commit.py` — add `graph_contains_commit_node`
  (D2)
- `forge_bridge/console/handlers.py` — REPLACE two
  `complete_with_tools` call sites (:1712 JSON, :1025 SSE) with
  `run_compile_branch` calls; emit new SSE taxa per L9; add
  `chat_regime=` telemetry per D6; **DELETE** consumer-side dead
  paths per S-1:
    - `_build_orchestration_terminated_body` helper (:889-950)
    - `_on_message` callback definition (:1018-1020)
    - `event: message` emission (:1019)
    - Phase 24.4 termination branch in `_chat_sse_response`
      (:1109-1145)
    - `event: done` emission (:1159-1168)
    - PR15 output validation in `_chat_sse_response` (:1097-1107)
    - `enforced_system` construction (:1604)
    - `enforced_system` kwarg from `_chat_sse_response` signature
      (:958)
    - `enforced_system` argument from call site (:1029, :1693)
    - `tool_enforced_flag` kwarg from `_chat_sse_response`
      signature (:967) — **DELETED** (sweep grounded at D5 step 1:
      consumed at :1165 + :1142, both deleted; regime payloads emit
      `tool_enforced: false` inline per sub-question (a))
    - `tool_call_count_in` kwarg from `_chat_sse_response`
      signature (:964) — **KEPT** (sweep grounded at D6 step 2:
      consumed at :1131 — DELETED — and :1157 — PRESERVED in the
      reshaped SSE success log line that now also emits
      `chat_regime=`; kwarg therefore retains a surviving consumer)
    - Phase 24.4 termination branch in JSON path (:1797-1818)
    - PR15 output validation in JSON path (:1826)

**Files NOT modified (20 files strictly NOT modified + 2 partial-preservation sub-claims about modified files = 22 enumerated entries):**

- `forge_bridge/llm/router.py` `complete_with_tools` body —
  Phase 24.4 K=2 trigger, OllamaToolAdapter dispatch, terminal
  taxa emission. Legacy-agentic substrate preserved for non-chat
  callers (test consumers only post-A.1).
- `forge_bridge/llm/_adapters.py` — Anthropic + Ollama tool
  adapters.
- `forge_bridge/llm/_sanitize.py` — tool result sanitization.
- `forge_bridge/llm/health.py` — LLM health resource registration.
- `forge_bridge/llm/resolver.py` — entity resolver.
- `forge_bridge/llm/call_wrapper.py` — chat wrapper / trace
  summary. **Verify** `tool_enforced` / `tool_forced` fields are
  parsed by this wrapper post-A.1 (sub-question (a) preservation
  is for THIS module's parser primarily).
- `forge_bridge/console/_tool_enforcement.py` — PR15 enforcement
  prompt builder. Module preserved; chat-handler invocation deleted
  per L7 + S-1.
- `forge_bridge/console/_tool_filter.py` — PR14 / PR21 narrowing.
  Semantic role shifts per L6; code unchanged.
- `forge_bridge/console/_chain_parse.py` — PR30 `->`-parser.
  Reused by D3; not modified.
- `forge_bridge/console/_param_extract.py` — PR28 deterministic
  extractor. Reused by D3 for per-step `args_preview`; not
  modified.
- `forge_bridge/console/_engine.py` — `run_chain_steps` IS the
  post-compile executor (Gap #3); used as-is.
- `forge_bridge/console/_macros.py` — `expand_macro` + macro list/delete.
- `forge_bridge/console/_step.py` — single-step execution primitive.
- `forge_bridge/console/_rate_limit.py` — IP-keyed rate limit.
- `forge_bridge/console/_memory.py` — chat memory.
- `forge_bridge/console/_constants.py` — chat-handler constants.
- `forge_bridge/console/_name_resolve.py` — entity name resolution.
- `forge_bridge/console/_tool_chain.py` — tool-chain helpers.
- `forge_bridge/graph/commit.py` — `is_commit_step`,
  `parse_commit_step`, `CommitError`, `CommitVerification`,
  `CommitNode` — all unchanged; D2 only appends the new utility
  function.
- `forge_bridge/graph/mutation.py` — `MutationManifest`,
  `MutationManifestError`, `validate_mutation_manifest` — all
  unchanged. A.1 does not construct or validate manifests.
- `forge_bridge/__init__.py` — public `__all__` stays at 19 per
  MOL-5.
- `pyproject.toml` — no version bump (A.1 is patch-equivalent
  additive surface inside v1.7's milestone arc).

## Implementation guidance — coexistence-architecture watch + deletion verification

Per THREAD-A-FRAMING.md §"Coexistence architecture": post-A.1 the
system has three chat regimes + the legacy-agentic substrate
(router-side primitive, no production consumers) + PR20
deterministic short-circuit. **Coexistence is upheld at the
ROUTER substrate level. Consumer-side dead paths are deleted per
S-1.**

> **Per Creative's S-1 ruling (Stage 1b 2026-05-27):**
> "Preservation buys ambiguity, not reversibility." Git history is
> the reversibility layer; zombie handler code is not.
>
> **The correct read of
> `[[feedback-substrate-coherence-revealed-retrospect]]`** is
> *"preserve primitives whose downstream consumers are plausibly
> unresolved"*. After A.1, the handler-side dead paths have NO
> remaining execution path — they are not "latent substrate"; they
> are dead consumer scaffolding.

### What to PRESERVE (router substrate)

- **`complete_with_tools` body in `router.py`** (Phase 24.4 K=2
  trigger, terminal taxa, `OrchestrationTerminationEnvelope`,
  `_OrchestrationTerminated` signal class, K-fold canonical
  recurrence logic). Has active test consumers
  (`tests/llm/test_complete_with_tools.py`, etc.); substrate
  primitive.
- **`_in_tool_loop` ContextVar in `router.py`**. Used by both
  `complete_with_tools` (sets) and now `compile_intent` (tests, per
  S-3 local guard).
- **`build_enforcement_system_prompt` module function in
  `_tool_enforcement.py`**. Module-level substrate; only the
  chat-handler invocation of it is deleted.

### What to DELETE (consumer-side dead paths)

Enumerated in the file change manifest under `handlers.py`
modifications. The deletions are surgical and limited to the
handler-private surfaces that lose their only consumer when
`complete_with_tools` calls are replaced.

### Stage 2 prompt (for the implementation-review pass after commits land)

Re-grep the following identifiers across modified files. Verify:

| Identifier | Allowed locations post-A.1 | Forbidden locations |
|---|---|---|
| `complete_with_tools` | `router.py` (definition), test files | `handlers.py` (except optional historical comment) |
| `compile_intent` | `router.py`, `_chat_compile.py`, new test files | — |
| `CompileError` (and subclasses) | `router.py`, `_chat_compile.py`, `handlers.py` (catches), new test files | — |
| `graph_contains_commit_node` | `commit.py`, `_chat_compile.py`, new test files | — |
| `chat_regime=` | `handlers.py` success/error log lines | — |
| `compiled_non_mutating` | `_chat_compile.py` regime field literal, test assertions, log values | — |
| `compiled_mutating_preview` | `_chat_compile.py` regime field literal, test assertions, log values | — |
| `_on_message` | nowhere in `handlers.py` | `handlers.py` (verifies S-1 deletion) |
| `message_callback` | `router.py` (still a parameter for non-chat callers), `_adapters.py` | `handlers.py` (verifies S-1 deletion) |
| `event: message` | nowhere | `handlers.py` (verifies S-1 deletion) |
| `event: done` | nowhere | `handlers.py` (verifies S-1 deletion) |
| `_OrchestrationTerminated` | `router.py` (definition), router-internal usage | `handlers.py` (verifies S-1 deletion) |
| `_build_orchestration_terminated_body` | nowhere | `handlers.py` (verifies S-1 deletion) |
| `enforced_system` | `_tool_enforcement.py` (module function preserved), legacy callers if any | `handlers.py` (verifies S-1 deletion of the variable / kwarg) |

The discipline: **A.1's job is to add the compiled regimes AND
delete the dead consumer scaffolding when the executor call sites
are replaced. Stage 1b verifies the grep-table mechanically.**

## Dependencies and sequencing

- **Blocks:** A.2 (ratification + enforced apply) — A.2's
  consumer-CLI assent surface writes against the preview-id that
  A.1's preview emits, and A.2's `commit.verify()` extension
  reads what A.1's compile branch routed to preview-only. A.2
  cannot start until A.1's preview shape is locked.
- **Blocked by:** Nothing. The substrate is ready (THREAD-A-FRAMING.md
  grounding verified 2026-05-27).
- **Parallel with:** Thread C (C.2 Bridge CLI asset surface, C.3
  projekt-forge consumer proof). No substrate overlap per MOL-9.
- **A.2 inherits forward-looking caveat:** FC-5 (check-location
  AT the commit node, not pre-execute gate). A.1 does NOT
  implement assent checking; A.2's substrate work attaches the
  check INSIDE `run_chain_steps`' commit-node handling.

## Stage 1b checklist

Items DT (or substitute reviewer) should verify before this spec
clears for implementation handoff:

- [ ] **Locks L1-L9 are mutually consistent and exhaustive.** Any
  scope question that could surface during implementation has an
  answer in a Lock or a Minor Lock — or it's explicitly out of
  scope.
- [ ] **L1 signature matches discuss artifact R-A1.1 + S-3 ruling.**
  `compile_intent` is additive on `LLMRouter`, text-completion,
  returns `list[str]`, applies `_in_tool_loop` guard LOCALLY as
  first statement (Path b).
- [ ] **L2 error family is sweep-complete.** One base + five
  concrete taxa = six classes total (count normalized per B-12).
- [ ] **L3 classifier folds over an existing primitive.** No new
  commit-detection logic.
- [ ] **L4 preview shape is wire-locked.** Field names + types +
  the `__commit__` sentinel + the `summary` block — all named
  explicitly.
- [ ] **L5 preamble preservation is comprehensive (per B-3 sweep).**
  Every PR-numbered AND non-PR-numbered preamble surface is named
  in the disposition table; deletions are explicitly listed;
  `compile_intent` operates on `messages_for_llm` not `messages`
  (mechanically named).
- [ ] **L5 line numbers are correct (per B-2 sweep).** SSE call
  site is `:1025` (not `:1024`) throughout.
- [ ] **L6 PR14 semantic-shift note is in the plan body.**
  (Stage 1b carve-out #8.)
- [ ] **L7 PR15 ruling rationale is honest (per B-7).** No
  fictional "non-chat callers" claim; `enforced_system` deleted
  per S-1; only the module function in `_tool_enforcement.py`
  preserved.
- [ ] **L8 PR20 ruling is named.**
- [ ] **L9 chat-side taxa are wire-locked + transport-error taxon
  preserved.** Five new taxa + the retained `event: error` taxon.
  Payload shapes specified for each. `final_text` OMITTED from
  regime-2 / regime-3 payloads per B-1.
- [ ] **MOL-1 acknowledges UAT-iteration of prompt wording (per S-2).**
- [ ] **MOL-3 inverts v1's empty-string-final_text claim (per B-1).**
  `final_text` is OMITTED entirely from regime-2 / regime-3 JSON
  responses. The most important catch of the Stage 1b review.
- [ ] **D1 / D2 / D3 / D4 / D5 / D7 fixture citations are
  grounded (per B-5, B-6).** No `_MockOpenAI` /
  `_MockAnthropic` (don't exist); no `make_test_app()` /
  `conftest.py:_LOCATE` (don't exist). Corrected to actual
  fixture pattern citations.
- [ ] **D7 / `tests/graph/__init__.py` not in new-files list
  (per B-8).** Directory exists; pytest discovers without
  `__init__.py`.
- [ ] **D9 / `docs/CHAT.md` unconditional in doc plan
  (per B-9).** Verified absent; not a conditional create.
- [ ] **Discuss artifact frontmatter updated (per B-10).**
  `review_state: operator-ratified-2026-05-27`.
- [ ] **File change manifest is complete + count normalized (per B-11).**
  6 new files. 3 modified files. 20 files strictly NOT modified +
  2 partial-preservation sub-claims = 22 enumerated entries in the
  NOT-modified section.
- [ ] **CompileError class count normalized (per B-12).** "One
  base + five concrete = six classes total" consistently across
  L2 / D1.
- [ ] **D3 / D4 / D5 dual-transport plumbing is non-bifurcated.**
  Both JSON and SSE paths call the same `run_compile_branch`
  helper.
- [ ] **MOL-5 — `forge_bridge.__all__` stays at 19.**
- [ ] **MOL-9 cross-thread isolation verifiable.** Thread C
  surfaces untouched.
- [ ] **Test matrix coverage matches the L/MOL surface + S-1
  deletions.** Each Lock and load-bearing Minor Lock has at
  least one named test row in D7. S-1 deletions have grep tests
  encoding the deletion contract structurally.
- [ ] **No backwards-incompatible response changes for retained
  fields (sub-question (a)).** `tool_enforced` and `tool_forced`
  remain in regime-2 / regime-3 envelopes as `false`.
  Wrapper-side parsers (`forge_bridge/llm/call_wrapper.py` and
  downstream) continue to read these fields.
- [ ] **Per-layer success criteria attached to native layer per
  `[[feedback-distinct-success-criteria-per-adjacent-layer]]`.**
  Compile primitive, branch helper, chat handler — each layer's
  criteria are local.
- [ ] **Coexistence-architecture watch is operational** with the
  delete-vs-preserve split named explicitly. Stage 2 grep table
  encodes verification.
- [ ] **A.2 forward-looking caveat (FC-5) is captured.**

## Status

**Phase plan v2, awaiting Stage 1b verification.** Revised
2026-05-27 from v1 after DT Stage 1b synthesis (12 B-grade
grounding fixes + 3 S-grade room rulings + 4 D-grade
drafter-discretion confirmations + 8 carve-out dispositions) and
operator + Creative room convergence (S-1 delete handler-side dead
paths; S-2 UAT-iterable prompt wording; S-3 Path b explicit local
guard; sub-question (a) `tool_enforced` / `tool_forced` envelope
continuity).

**Stage 1b methodology note (carry to A.1 close):** v1's grounding
errors (B-5, B-6, B-7) were concentrated in test-fixture and
non-chat-caller claims cited from memory without contemporaneous
verification. Per Creative's Stage 1b coinage,
"**memory-shaped fixture hallucination**" — *structurally
plausible, stylistically consistent, not actually grounded
in-tree*. Within-cycle 2nd-instance evidence of
`[[feedback-fixture-shape-mirrors-production]]` at the
fixture-citation-in-spec surface (vs the prior test-fixture-mirrors-production
surface); promotion candidate at A.1 close. Methodology
self-referential: the review-stage instrument caught the drafter
drift, same pattern as C.1's drafter-self-violation at the
sweep-completeness surface.

**Next motion.** Stage 1b verification pass (DT seat) against:
- The plan body (this artifact)
- Current main (`1d7afc8`)
- The discuss artifact (now `operator-ratified-2026-05-27`)
- v1 → v2 diff (verifying B-1..B-12 + S-1/S-2/S-3 + sub-q (a)
  applied)

If green-clean: implementation hands off in D1..D8 order. If
revisions needed: v3 draft.

**Anti-scope binding.** Per
`[[feedback-anti-scope-discipline-under-pressure]]`: when
mid-implementation partial-failure surfaces become visible, the
implementer does NOT introduce prompt hacks / routing tricks /
narrowing tweaks / orchestrator-side synthesis. Compile is the
named architectural transition; failure shapes are observable
through the five `CompileError` taxa; the policy boundary is
clear. Per
`[[feedback-orchestrator-control-flow-not-meaning]]`: compile owns
its own guard contract locally (S-3 Path b); compile_intent does
not synthesize or impersonate the model.
