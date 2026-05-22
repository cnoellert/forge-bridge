# SEED — Apply-Path Enforcement (Phase N++)

Phase N+ persisted the direct-apply path: flame_rename_shots in apply
mode is reachable both through the commit primitive (preview -> manifest
-> verify -> apply) and directly (dry_run=False, no commit).

The deferred question: should domain mutation be reachable ONLY through
the commit primitive? Enforcing that makes the preview->apply seam
architecturally mandatory — direct tool-apply at the LLM-router and
chat-handler surfaces would route through commit.

Touches: the LLM router's invocation of mutating tools, the chat
handler's tool dispatch, possibly the fbridge CLI run path. Framing-
domain change outside Phase N+'s scope (the commit primitive and the
manifest contract).

Related deferred item: foreach-aggregated commit. Phase N+ ships
direct-call commit only; under foreach, per-iteration intent_parameters
vary and collect's scalar-variance reconciliation drops the field, so
the aggregate manifest fails validation by design. A second-consumer
phase that wants foreach-aggregated commit must resolve where foreach-
level intent is carried (chain layer, not tool emission).

Structural shape preserved for a future phase to take deliberately.
