# Chat

The chat endpoint is the natural-language authoring lens over the same chain
substrate used by `fbridge exec`. Chat compiles a user message into validated
chain-step text, previews host-mutating chains, and only applies a previewed
mutation after ratification.

Endpoint: `POST http://localhost:9996/api/v1/chat`

## Request Shape

```json
{
  "messages": [
    {"role": "user", "content": "list shots"}
  ]
}
```

The handler preserves the existing transport envelope and rate limit, then
routes every user turn through the compile stage.

## Read routing (planner flag)

The bare `POST /api/v1/chat` is the **deterministic mutation/ratify surface**:
it compiles a turn into a chain and previews host-mutating chains for
ratification. It is **not** a natural-language *read* router — its deterministic
tool selection mis-handles read queries (e.g. "how many shots in X",
"hello").

Natural-language **reads must opt into the planner path** by sending either:

- query param `?planner_front=true`, or
- header `X-Forge-Planner: v1`

The planner path exposes only read tools, grounds the answer against the store,
and is reads-only by construction. The Console UI sends this flag by default
(`forge-chat.js`), so the in-app read experience already routes correctly; only
raw API consumers need to set it. This split is intentional (#71): the
deterministic path owns mutations and the planner path owns NL reads — they are
not interchangeable.

Mutating operation authoring can opt into the curated operation planner with
`?operation_front=true` or `X-Forge-Operation: v1`. This front currently authors
Flame reel, reel-group, and library creation previews; it never applies them
without ratification.

## Clarification vs capability gap

The planner fronts distinguish missing information from missing capability:

- `clarification_needed` means Bridge supports the request but needs a concrete
  referent or required value before it can proceed.
- `capability_gap` means the requested result is outside the capabilities
  available on that front. Bridge declines without executing a nearby tool,
  broadening the read, or creating an assent record.

Capability-gap responses carry the normalized request and the supported boundary:

```json
{
  "final_text": "I can't rename shots in this operation pass yet. I can create a Flame reel, reel group, or library.",
  "stop_reason": "capability_gap",
  "capability_gap": {
    "requested": "rename shots",
    "supported": ["create_reel", "create_reel_group", "create_library"]
  }
}
```

The reads front uses the same stop reason. Unsupported grouping fields are
classified by Bridge's deterministic reads fence; a model cannot map an unknown
field to a nearby supported grouping and present that substitution as the answer.

## Deterministic list rendering

Pure requests to list every shot name use a validated presentation declaration:

```json
{"kind": "list", "entity": "shot", "field": "name", "scope": "all"}
```

After `forge_list_shots` executes, Bridge validates that the chain contains one
complete shot population and renders the names directly. This skips the second
model narration pass, preserves source order, does not truncate after a sample,
and reports unnamed rows instead of silently dropping them. The response includes
`deterministic_render` evidence with source-step, total, rendered, and missing
counts. Invalid declarations, extra chain evidence, failed reads, or count
mismatches retain the normal narrator fallback.

## Regimes

| Regime | Stop reason | Meaning |
|---|---|---|
| `compiled_non_mutating` | `chain_complete` | The compiled chain has no commit step and was executed immediately. |
| `compiled_mutating_preview` | `preview_emitted` | The compiled chain crosses a host-mutation boundary and produced a preview instead of applying. |
| `chain_aborted` | `chain_aborted` | A compiled or applied chain failed during execution. |
| `compile_error` | `compile_error` | The message could not be compiled into a valid chain. |
| `ratified_apply` | `apply_complete` | A previously ratified graph-intent was applied from storage. |
| planner front | `clarification_needed` | The request is supported but needs another operator answer. |
| planner front | `capability_gap` | The requested read or operation is unavailable; nothing was substituted or executed. |

## Preview Shape

Mutating chains produce a preview and an `AssentRecord` before any host mutation
runs. The operator decides against the `graph_intent_id`.

```json
{
  "preview": {
    "kind": "graph-intent-preview",
    "graph_intent_id": "4bd83c2f1abc",
    "steps": [
      {
        "step_text": "flame_rename_shots dry_run=False",
        "tool_name": "flame_rename_shots",
        "args_preview": {},
        "would_mutate": true
      },
      {
        "step_text": "commit",
        "tool_name": "__commit__",
        "args_preview": {},
        "would_mutate": true
      }
    ],
    "summary": {
      "total_steps": 2,
      "mutating_steps": 2,
      "requires_ratification": true
    }
  },
  "chain": [],
  "stop_reason": "preview_emitted",
  "chat_regime": "compiled_mutating_preview"
}
```

## Apply Grammar

Chat also accepts a narrow apply grammar:

```text
apply <graph_intent_id>
```

The identifier must be 12 lowercase hex characters. Chat apply does not ratify;
it only applies records that are already `ratified`. Use
`fbridge ratify <graph_intent_id>` for the normal operator flow that ratifies
and applies atomically.

## SSE Events

When the request has `Accept: text/event-stream`, chat emits the same regimes
as event taxa:

| Event | Terminal | Meaning |
|---|---:|---|
| `compile_complete` | no | A non-empty chain was compiled before classification. |
| `chain_complete` | yes | Non-mutating chain completed. |
| `preview_emitted` | yes | Mutating preview emitted; no host mutation applied. |
| `apply_complete` | yes | Ratified stored chain applied. |
| `chain_aborted` | yes | Chain execution failed. |
| `compile_error` | yes | Compile failed structurally. |
| `error` | yes | Transport/runtime failure outside compile semantics. |

`event: message` and `event: done` are retired for chat's post-A.1 authority
model. The authority surface is now compile, preview, ratify, apply.

See [RATIFICATION.md](RATIFICATION.md) for the assent record lifecycle and
operator CLI.
