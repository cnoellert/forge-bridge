---
name: SEED-FLAME-CHAT-FOUNDRY-V1.6+
description: Add a second Flame right-click menu item ("Forge: Ask...") that hits /api/v1/chat instead of /api/v1/exec. Conceptually framed as the foundry where new node types are authored — the surface where the LLM extends the registry, with staged-ops approval gating what enters.
type: forward-looking-feature
planted_during: Architecture conversation 2026-05-04 — PR40-42 consolidation aftermath, re: deterministic-vs-generative dual-mode surfaces and the missing LLM-from-Flame entry point
trigger_when: v1.6 milestone opens OR deterministic dialog has been used in production for ≥2 weeks (vocabulary friction notes accumulated) OR a workflow gap is hit that requires a new tool that doesn't yet exist
---

# SEED-FLAME-CHAT-FOUNDRY-V1.6+: LLM entry point in Flame as node-foundry surface

## Idea

Add a parallel right-click menu item in Flame ("Forge: Ask...") alongside the existing deterministic exec dialog. Same minimal UI shape — free-text entry, enter to submit, response rendered in a small Qt surface — but POSTs to `/api/v1/chat` instead of `/api/v1/exec`. This is the LLM-driven path: the artist asks for something, the model gets it with the tool registry available, decides what to do, and may call existing tools, may synthesize new ones, may iterate.

Conceptually, frame the surface explicitly as a *foundry* (per SEED-NODE-SCHEMATIC-V1.6+). The deterministic dialog is the keyboard interface to the existing schematic — power users compose known nodes. The Ask dialog is where new node types are authored. The two surfaces serve different needs and reinforce that division of cognitive load: deterministic = use what exists, generative = grow what exists.

## Why This Matters

Currently there is no LLM access from inside Flame. The deterministic right-click dialog (just verified working end-to-end post-PR42, commit 6e3239d) handles known operations. But when the artist hits a gap — a workflow that no existing tool covers, an awkward sequence done three times in a week, a new external format that needs ingesting — there's no path forward from inside Flame except "open a terminal and chat with the bridge another way."

That breaks the core bootstrap loop. Without an LLM entry point in Flame, the registry can't grow from the surface where artists actually work. The deterministic path can use what exists, but nothing creates new vocabulary from inside Flame. The system can only get better at things it already knows about.

The Ask dialog closes the loop: the artist hits a gap, asks the foundry to fill it, the LLM proposes a tool, staged-ops gates approval, and once approved the tool enters the registry. From then on, the deterministic path uses it like any other primitive. The artist's daily workflow grows the system's vocabulary without leaving Flame.

This is also where the v1.4 FB-C staged-operations infrastructure gets its first real artist-facing consumer. It's been waiting for one.

## Boundaries

In scope (when this seed activates):
- Second right-click menu item ("Forge: Ask..." or similar label).
- Free-text entry, enter to submit, threaded HTTP call to `/api/v1/chat`.
- Response rendered in a small Qt surface (modal dialog or non-modal docked widget — choice made at plan time).
- Response shape distinguishes:
  - **Direct answer** — the model responded conversationally, no tool action taken.
  - **Tool execution result** — the model called an existing registered tool and returned its result.
  - **Proposed tool** — the model wants to synthesize and register a new tool; needs human approval before it enters the registry.
  - **Synthesized + approved + executed** — full bootstrap-loop completion, end-to-end.
- Threading is mandatory. LLM calls are 2-30s; synchronous urlopen on Flame's UI thread is unacceptable. Pattern: worker thread + Qt signal on completion.
- A doctor affordance — the dialog should show "Forge: connected" or surface a clear error path when the daemon is unreachable. Same shape as the equivalent affordance for the deterministic dialog.
- System prompt biased toward "synthesize a tool for this if one doesn't exist" rather than "give a conversational answer." The system grows when tools are made, not when chat happens.

Out of scope (initial):
- Persistent chat panel with conversation history (separate effort if it earns its keep — see existing chat seeds).
- Full schematic rendering of the graph or of synthesized nodes (covered by SEED-NODE-SCHEMATIC-V1.6+).
- Multi-turn conversational state in the dialog (one-shot first; multi-turn is later).
- Inline editing of synthesized tool code before approval (review-and-approve only first cut).
- Voice input, speech recognition, or other input modalities.

## Bootstrap Loop Completion

The Ask dialog completes a loop that's been partial for months. End-to-end:

1. Artist invokes deterministic dialog with a command.
2. Deterministic path resolves and runs. (PR15-29 work — verified post-PR42.) ✓
3. If deterministic resolution fails (no matching tool, ambiguous, missing required parameter), the failure surface offers "Try asking instead?" — handoff to the foundry.
4. Ask dialog passes the original intent to `/api/v1/chat`.
5. LLM either finds an existing tool (rare, since deterministic just failed), or proposes a new tool to synthesize.
6. Synthesizer writes the tool under quarantine. (existing v1.0 infra.) ✓
7. Staged-ops surface presents the proposed tool to the artist. Approve or reject.
8. If approved, tool enters the registry. (existing v1.0 infra + v1.4 staged-ops.) ✓
9. Tool executes; result returns to the artist.
10. Next time the artist invokes the deterministic dialog with similar intent, the new tool resolves and runs immediately.

The system grew. The artist stayed in Flame the whole time. The LLM did its job and got out of the way.

## When This Seed Activates

Any of:
1. **v1.6 milestone opens** — natural sequencing after v1.5 Legibility ships.
2. **Deterministic dialog has accumulated ≥2 weeks of production use** — vocabulary friction notes from real artist usage tell us where the gaps are. Premature foundry work without that data risks building the wrong synthesis prompts.
3. **A specific workflow gap is hit** — if Chris (or any artist) finds themselves typing the same awkward sequence repeatedly and wishing for a tool that doesn't exist, that's the moment to wire the foundry. The first real synthesized tool is more valuable than another speculative seed.
4. **Producer/external surface needs LLM access** — if a Slack bot or other-surface conversation reignites and demands LLM access, the Flame foundry is the correct internal proving ground first.

## Breadcrumbs

Code references (current as of 2026-05-04):
- `forge_bridge/server.py` — `/api/v1/chat` endpoint (LLM-driven path, FB-D).
- `forge_bridge/llm/router.py` — `complete_with_tools()` is the agentic loop the chat endpoint drives.
- `forge_bridge/learning/synthesizer.py` — tool synthesis under quarantine.
- `forge_bridge/learning/storage.py` — staged operations / proposed-tool persistence.
- `flame_hooks/forge_bridge/` — existing right-click dialog (just unblocked post-PR42, commit 6e3239d); the Ask dialog is a parallel sibling here.
- `forge_bridge/flame/integration.py` — `run_command_from_flame()` is the deterministic-path adapter; the foundry adapter is `run_chat_from_flame()` or similar.
- v1.4 FB-C staged operations — the gate that lets proposed tools reach the registry.
- v1.4 FB-C `LLMLoopBudgetExceeded` — the chat call has hard timeouts; the dialog must surface them clearly.
- `docs/learnings/single-runtime-pr40-42.md` — context on why the foundry adapter uses stdlib `urllib.request`, not httpx, in Flame's bundled Python.

Existing chat-related seeds that are *not* this:
- `SEED-CHAT-PERSIST-HISTORY-V1.5+` — about chat conversation persistence; relevant if the dialog later grows into a persistent panel.
- `SEED-CHAT-STREAMING-V1.4.x` — about token streaming; relevant for response rendering.
- `SEED-CHAT-TOOL-ALLOWLIST-V1.5` — about scoping which tools the LLM can call.
- `SEED-CHAT-PARTIAL-OUTPUT-V1.5` — about progressive rendering during tool calls.

This seed is a *consumer surface* for those internal features; the seeds above are internal mechanisms.

## Open Questions (for v1.6+ planning)

- **Default mode bias.** Should the chat endpoint's system prompt explicitly reward "I'll synthesize a tool for this" over "here's a one-shot answer"? Probably yes — the system grows when tools are made, while conversational answers are ephemeral. But this is a prompt-engineering decision worth being deliberate about; over-biasing produces tool spam, under-biasing produces a chatbot.
- **Approval surface shape.** Where does staged-ops approval render? Inside the dialog as a follow-up panel? In a separate browser window via the schematic? In Flame's existing UI somehow? This intersects with SEED-NODE-SCHEMATIC and probably wants resolution there first — pending operations as ghost nodes is the natural answer.
- **Threading library.** Qt's `QThread` + signals, `QtConcurrent.run`, or a plain `threading.Thread` that emits a Qt signal on completion? Flame's bundled Python and Qt version constrain this; resolve at plan time.
- **Failure handoff from deterministic to foundry.** When the deterministic dialog fails to resolve, should it auto-redirect to the Ask dialog with the original input pre-filled? Or just offer a "Try asking instead?" button? The latter is probably right — preserves intent without surprising the user.
- **Synthesized tool naming.** Does the LLM name the tool, or does the artist? Does the artist see the name before approval and have a chance to rename it? Naming matters for vocabulary clarity (the same forcing function as SEED-NODE-SCHEMATIC's vocabulary pressure).
- **Context capture.** Like the deterministic dialog, the Ask dialog needs Flame-side context (selected clip, current batch, etc.) when relevant. Is the context passed identically to both endpoints, or does the Ask path get a richer/different shape?

## Why Plant Now

The architectural prerequisites all landed in v1.0-v1.4: the synthesizer (v1.0), the LLM router with safety guards (v1.4 FB-C), staged operations (v1.4 FB-C), the chat endpoint (v1.4 FB-D), and now a working deterministic Flame dialog (PR42 + commit 6e3239d, just verified). Every component the foundry needs already exists. The only missing piece is the surface — a parallel right-click menu item paralleling the dialog that just got working.

The framing — Ask dialog as foundry, deterministic dialog as keyboard, schematic as canvas — emerged in the same conversation that produced SEED-NODE-SCHEMATIC. Capturing it now means v1.6 planning has both the schematic vision and the immediate surface-level entry point ready to plan against, with the conceptual relationship between them already articulated.

This is the surface that closes the bootstrap loop. Without it, bridge can only get better at things it already knows about. With it, the registry grows from artist intent, in artist context, with artist approval. That's the durable claim — not "AI does VFX," but "the system learns the operations its users care about, with users in control of what gets learned."
