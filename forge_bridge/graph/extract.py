"""Extract single-key inherited-context kwarg from an upstream tool result.

This is the graph-layer home of the deterministic ``extract_chain_context``
rule that the legacy chain engine folds into downstream tool kwargs at runtime
(`console/_step.py`). Relocating the pure function here — a lower layer than
``console/`` — lets both the legacy path (which re-imports it) and the graph
path (`ExtractContextNode`) share a single canonical author.

``ExtractContextNode`` is the visible graph node that runs the singleton-guarded
which-key decision at runtime and emits a single-key ``{kwarg: value}`` dict as
its typed output. The name rides in the emitted *value*, not the port *type*, so
no new ``PortTopology`` is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict

from forge_bridge.graph.ports import PortContract, PortTopology


def extract_chain_context(result: Any) -> Dict[str, str]:
    """Deterministically extract a single context parameter from a tool result.

    Priority (first match wins — no multi-key merge):

      1. ``projects`` → ``project_id``
      2. ``shots`` → ``shot_id``
      3. ``versions`` → ``version_id``

    Rules:

      - Only propagate when exactly **one** item exists in the list.
      - Item must be a dict with a non-empty string ``id`` (after strip).
      - Return immediately on the first qualifying key; otherwise ``{}``.

    Defensive on input shape: non-dict input returns ``{}``.
    """
    if not isinstance(result, dict):
        return {}

    def _single_id(lst: Any) -> str | None:
        if (
            isinstance(lst, list)
            and len(lst) == 1
            and isinstance(lst[0], dict)
        ):
            _id = lst[0].get("id")
            if isinstance(_id, str) and _id.strip():
                return _id
        return None

    _id = _single_id(result.get("projects"))
    if _id is not None:
        return {"project_id": _id}

    _id = _single_id(result.get("shots"))
    if _id is not None:
        return {"shot_id": _id}

    _id = _single_id(result.get("versions"))
    if _id is not None:
        return {"version_id": _id}

    return {}


@dataclass(frozen=True)
class ExtractContextNode:
    """Emit the single inherited-context kwarg an upstream result forwards.

    A value-transform primitive: it consumes an upstream tool result (a
    manifest/dict) and emits a single-key ``{kwarg: value}`` scalars dict, or
    ``{}`` when nothing qualifies. The which-key decision lives *inside this
    visible node*, not in the value-blind MCP boundary that merges the dict.
    """

    #: Input accepts a manifest-shaped upstream result; the emitted scalars dict
    #: types back to a manifest via ``infer_topology``. Both are existing
    #: ``PortTopology`` variants — no new port kind (the name rides in the value).
    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.manifest(),),
        PortTopology.manifest(),
    )

    def run(self, data: Any) -> dict[str, Any]:
        return extract_chain_context(data)
