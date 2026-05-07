"""forge_bridge.corpus._topology — topology snapshot helper.

Returns a dict matching the Layer 1 schema's ``topology`` block (see
``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 and ``_schema.py``).

Preserved invariants (carry through any future change to this module):

  1. **Descriptive, not evaluative.** Capture only reachable/
     unreachable, configured/available, identity/version, routing
     state. Do NOT capture: healthy, preferred, recommended,
     fallback-worthy. Evaluative fields propagate semantic weight
     that belongs in Layer 2.

  2. **Observational, not semantic.** Read existing reachability
     state. Do not compute compatibility grades, equivalence
     classes, drift scoring — those are Layer 2 derived judgments.

  3. **No lazy runtime side effects.** Must not initialize providers,
     warm clients, allocate transports, touch arbitration state,
     spawn background tasks, or mutate caches into warm-state
     preparation. Capture observes existing state; capture never
     causes state.

  4. **Loud asymmetry preserved.** Topology working without writes
     is correct. The writer remains deferred to PR 3 specifically
     because the architectural pressure to fuse observation with
     persistence is highest at this moment.

Implementation approach:

  - For ``flame_bridge``: read ``forge_bridge.console._tool_filter._cache``
    directly. If the cache has an entry (the reachability filter has
    probed in the last 5s), use the cached value. If not — *do not
    probe* — report ``reachable: false``. Unprobed-and-unreachable
    are observationally equivalent at Layer 1.
  - For ``ollama_local`` and ``anthropic``: no cache exists, so
    ``reachable: false`` always (until/unless a future probe is
    added in a different PR). ``configured`` is read from env (no
    side effect — env var read is observational).
  - ``identity: None`` for all backends in this PR. Identity is
    provider-specific (e.g., model digest, API version) and would
    require probing to discover; that work is Layer 2's classifier
    territory, not Layer 1's observation.

Unknown / unreachable state is itself truthful Layer 1 data. This
module does not throw, synthesize defaults, silently omit providers,
retry implicitly, or "heal" topology. The caller observes whatever
truth the cache and env hold at the moment of snapshot.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def snapshot_topology() -> dict[str, Any]:
    """Return a topology dict matching the Layer 1 schema's topology block.

    The returned dict is suitable for direct embedding under the
    ``topology`` key of a Layer 1 record. Schema validation against
    ``_schema.validate_capture_record`` is the integration point.

    Reads existing state. Never probes. Never initializes. Never
    spawns. Idempotent: repeated calls are operationally
    indistinguishable except for ``probed_at`` freshness.
    """
    # NOTE: Direct read of the private _cache attribute. We deliberately
    # do NOT call _get_backend_reachability(): that function probes on
    # cache miss, which is a runtime side effect this module is
    # forbidden from causing.
    from forge_bridge.console._tool_filter import _cache as _flame_cache

    flame_entry = _flame_cache.get("flame_bridge")
    flame_reachable = bool(flame_entry[0]) if flame_entry is not None else False

    ollama_url = os.environ.get(
        "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1",
    )
    anthropic_configured = bool(os.environ.get("ANTHROPIC_API_KEY"))

    return {
        "probed_at": datetime.now(tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "backends": {
            "flame_bridge": {
                "configured": True,
                "reachable": flame_reachable,
                "identity": None,
                "host": "127.0.0.1",
                "port": 9999,
            },
            "ollama_local": {
                "configured": True,
                "reachable": False,
                "identity": None,
                "url": ollama_url,
            },
            "anthropic": {
                "configured": anthropic_configured,
                "reachable": False,
                "identity": None,
            },
        },
    }
