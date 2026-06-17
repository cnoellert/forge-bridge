"""``NodeResult`` — the typed envelope every node emits (M1, bridge-internal).

Mirrors the forge-contracts ``ReferenceResolution`` abstention template
(``status`` + ``reason_code`` + ``message`` + ``candidates``). Per the M1 seam
design it is **minted by the bridge boundary adapter**, never by siblings —
vision/generators keep emitting their native MCP results and the adapter wraps
them. It stays bridge-internal for M1 and promotes to forge-contracts later
without a federation-breaking migration.

Four-variant discriminator. The load-bearing M1 rule: *"is there a usable
output?" is derivable from the discriminator ALONE* — downstream nodes must
never inspect ``output``/``fidelity`` to recover branch semantics.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

#: The four terminal variants. ``ok``/``partial`` carry a usable output;
#: ``abstained``/``error`` do not.
NODE_STATUSES: tuple[str, ...] = ("ok", "partial", "abstained", "error")
_USABLE_STATUSES = frozenset({"ok", "partial"})


@dataclass(frozen=True)
class NodeResult:
    """A node's terminal output on a graph edge."""

    status: str
    run_id: uuid.UUID
    artifact_id: uuid.UUID | None = None
    output: Any = None
    output_topology: dict[str, str] | None = None
    artifact_type: str | None = None  # advisory in M1; contracts validates later
    fidelity: dict[str, Any] | None = None  # present for ``partial``
    reason_code: str | None = None  # machine token (abstained/error); per-register vocab
    message: str | None = None  # human (abstained/error)
    candidates: tuple[Any, ...] = ()  # abstained (à la ReferenceResolution)
    source_artifact_ids: tuple[uuid.UUID, ...] = ()  # forward-only lineage

    def __post_init__(self) -> None:
        if self.status not in NODE_STATUSES:
            raise ValueError(
                f"NodeResult.status {self.status!r} not in {NODE_STATUSES}"
            )

    @property
    def has_usable_output(self) -> bool:
        """Whether a downstream node may consume this output.

        Derivable from the discriminator ALONE — this is the M1 crispness
        invariant. ``ok``/``partial`` → yes; ``abstained``/``error`` → no.
        """
        return self.status in _USABLE_STATUSES
