"""forge_bridge.corpus._topology — topology snapshot helper (PR 2 stub).

Wraps the existing reachability cache from
``forge_bridge.console._tool_filter`` and extends it to surface LLM-
provider availability. The output matches the Layer 1 schema's
topology block (per contract §3).

PR 1 status: stub. Implementation lands in PR 2 (identity + topology
helpers).
"""
from __future__ import annotations

from typing import Any


def snapshot_topology() -> dict[str, Any]:
    """Return a topology dict matching the Layer 1 schema's topology block.

    PR 1 stub: raises NotImplementedError. Implementation lands in
    PR 2.
    """
    raise NotImplementedError(
        "snapshot_topology lands in PR 2 (identity + topology helpers)."
    )
