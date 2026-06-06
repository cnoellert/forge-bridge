# Cross-repo findings: state_ws request/reply correlation skew (forge-bridge ↔ forge_core)

**Status:** ROOT CAUSE PINNED · BRIDGE-SIDE FIX LANDED (now-unblock) · DURABLE CONTRACT FIX PROPOSED (tracked). 2026-06-05.
**Repos:** forge-bridge (`forge_bridge/server/`), forge-pipeline (`forge_core/`), forge-contracts (proposal).
**Reported by:** pipeline workstream (Wave-4 round-trip: `forge_core.client.AsyncClient` correlated **zero** replies from the live state_ws; even `ping→pong` timed out). DT grounded the cause across both repos.

## Symptom
`forge_core.client.AsyncClient.request()` never resolves against forge-bridge's state_ws. The receive loop runs, the server **processes and replies**, but the client's pending future is never matched → 2s client timeout. Affects **every message type** (ping has no DB/UUID) and **every client** of that server — not Blender-specific, not the UUID-parse bug.

## Root cause — a wire-envelope correlation-key mismatch (bidirectional)
The two repos disagree on which key carries the request/response correlation id.

| | forge-bridge (server) | forge_core (client) |
|---|---|---|
| Correlation key | **`"id"`** (`forge_bridge/server/protocol.py`, `Message.msg_id = self.get("id")`) | **`"msg_id"`** (`forge_core/server/protocol/messages.py:102`, `self._data.get("msg_id")`); reply match on **`ref_msg_id`** then `msg_id` (`forge_core/client/async_client.py:425-445`) |

It breaks in **both** directions:
```
forge_core → bridge:  {"type":"ping","msg_id":"X"}
                      bridge reads self.get("id") → None  → replies pong(id=None)
bridge → forge_core:  {"type":"pong","id":null}
                      forge_core reads ref_msg_id or self._data["msg_id"] → None → no _pending match → request() hangs
```
Bridge can't read forge_core's request id (looks for `"id"`, finds `"msg_id"`); forge_core can't read bridge's reply id (looks for `"ref_msg_id"`/`"msg_id"`, finds `"id"`). This is a CONTRACT_VERSION-class cross-repo skew (kin to the staged-publish version skew).

## Fix landed now (bridge-side, bilingual) — `forge_bridge/server/protocol.py`
Bridge is the shared server and its protocol is the documented state_ws wire format; **forge_core's `"msg_id"` is baked into forge_core's own server↔client protocol** (the same `Message` serves both), so flipping forge_core would ripple into its internals. The lowest-blast-radius fix makes the **server tolerant**:
1. **Inbound:** `Message.msg_id` reads `self.get("id") or self.get("msg_id")` — accept either correlation key. `is_request` accepts either.
2. **Outbound:** every reply (`ok` / `error` / `pong` / `welcome`) echoes the correlation id under **both `"id"`** (bridge clients) **and `"ref_msg_id"`** (forge_core's primary match key).

Result: forge_core (and any client keying on `msg_id`/`ref_msg_id`) correlates; bridge's own clients (keying on `"id"`) are unchanged. Tested at `tests/test_protocol_builders.py` (dual-key read, ref_msg_id echo, end-to-end envelope round-trip). **No forge_core change required to unblock Wave 4.**

## Durable fix (proposed, tracked — prevents the next skew of this class)
The bilingual server is an unblock, not the end state — it's a tolerance shim, and a tolerance shim documented as "the fix" manufactures future skews. The durable answer: **define the state_ws request/reply envelope in `forge-contracts`** as a published type with ONE canonical correlation key + `contract_version`, and migrate both bridge and forge_core onto it; then retire the bilingual read/echo. This is the same "lift the shared envelope into the contract" move the federation already applies to capabilities/references. Owner: forge-contracts + both consumers. **Do not delete the bilingual shim until both sides speak the contract envelope.**

## Orthogonal (not on this path)
`entity.get` (and `query_dependents`/`query_lineage`/`entity_update`) call `uuid.UUID(<client field>)` unguarded → a malformed id surfaces as `ErrorCode.INTERNAL` (500) instead of `INVALID` (400). Good hygiene to guard (return INVALID), but it is **upstream-unrelated** to the correlation hang and was never the blocker.
