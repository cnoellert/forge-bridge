# Ratification

Ratification is the authority boundary for chat-authored host mutation. Chat may
infer intent, but it may not apply a host mutation until the operator ratifies
the previewed graph-intent.

## Flow

1. Chat compiles a user request into chain-step text.
2. If the chain contains a `commit` step, chat stores an `AssentRecord` with a
   content-addressed `graph_intent_id`.
3. Chat returns a preview with that `graph_intent_id`; no host mutation runs.
4. The operator ratifies the graph-intent.
5. forge-bridge applies the exact chain stored in the `AssentRecord`.
6. The record becomes `applied` or `failed`.

No recompile happens during apply. The chain that runs is the chain the operator
previewed.

## CLI

```bash
fbridge ratify 4bd83c2f1abc
fbridge ratify 4bd83c2f1abc --actor jdoe
fbridge ratify 4bd83c2f1abc --json
```

`fbridge ratify` calls `POST /api/v1/ratify` with
`{"graph_intent_id": "...", "actor": "..."}`. The endpoint ratifies and applies
atomically.

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Apply succeeded. |
| 1 | Validation or apply failed. Inspect the error envelope. |
| 2 | Console daemon unreachable. Start it with `fbridge up`. |

## Chat Apply

Chat accepts:

```text
apply <graph_intent_id>
```

This path applies an already-ratified record. It does not perform the ratify
transition. It exists so chat can drive the apply half through the same
store-and-replay substrate.

## Audit Events

The `AssentRecordRepo` writes four audit event types:

| Event | Meaning |
|---|---|
| `assent.proposed` | A previewable graph-intent was stored. |
| `assent.ratified` | An operator recorded assent. |
| `assent.applied` | The stored chain applied successfully. |
| `assent.failed` | Apply failed after ratification. |

## Failure Envelopes

Common error codes:

| Code | Meaning |
|---|---|
| `validation_error` | Bad graph-intent id format or empty actor. |
| `assent_record_not_found` | No `AssentRecord` exists for that graph-intent id. |
| `assent_illegal_state` | The record is already applied, failed, or otherwise not ratifiable/applicable. |
| `drift_invalid` | Commit verification found plan drift. |
| `chain_aborted` | A chain step failed during apply. |
| `daemon_unreachable` | The CLI could not reach the console daemon. |

## Relationship To Staged Operations

`AssentRecord` is not `staged_operation`. A staged operation is an approval
queue for a producer-owned operation: approval is bookkeeping and the producer
executes its own domain. An `AssentRecord` is chat's ratification substrate for
a compiled graph-intent: it stores the exact chain previewed by the operator and
replays that chain only after assent.

See [CHAT.md](CHAT.md) for the chat regimes and SSE event taxa.
