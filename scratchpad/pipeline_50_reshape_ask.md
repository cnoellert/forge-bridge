# #50 reshape — make ingest's `data` BE the EditState (path C)

Bridge + operator decided the `edit_state` seam = **path C** (executor NOT thawed; `from_port` reserved for proven multi-output). For C to work, ingest's operation `data` must be directly consumable as `apply_steps.state`.

**Current #50 shape:** `data = {"edit_state": <EditState dict>, "flame_sequence_ingest": <evidence>}`

**Why it doesn't wire:** Bridge's executor passes the **whole** upstream `data` down the edge (`executor.py:114-115` maps `to_port → whole NodeResult`; `from_port` is not consulted, and honoring it would thaw the byte-stable executor — deliberately deferred). So `ingest --(state)--> apply_steps` would hand `apply_steps.state` the wrapper `{edit_state, flame_sequence_ingest}`, and `EditState.from_dict` chokes.

**Reshape (tiny follow-up):** make ingest's `OperationResult.data` **be** the EditState payload — exactly the dict `EditState.from_dict` consumes, nothing else nested in `data`. Move the `flame_sequence_ingest` evidence (provenance, active_sequence_id, selected_version, project/bin/media diagnostics) onto a **non-edge** surface: `OperationResult.logs` / lineage / a dedicated evidence field — anywhere off the graph-routed `data`. Evidence stays recorded; it's just not a graph edge today (nothing consumes it as one — n=0).

**Bridge-facing contract:** `OperationResult.data == EditState.to_dict()` (round-trips through `EditState.from_dict`). That's the whole contract.

**Reserve note:** when a real graph consumer of evidence appears (a node/edge that reads it) **plus** a 2nd/3rd multi-output seam, we revisit declared-port executor semantics (`from_port`) as a deliberate, constraint-tested executor change — not before.

**Bridge side under C** = one admission row for `traffik.flame_sequence.ingest_edit_state` (`dispatch_kind="operation"`, `no_state_mutation=True`, `idempotent_result=True`), staged with the vertical. No executor/boundary change.
