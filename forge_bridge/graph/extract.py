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

import re
from dataclasses import dataclass
from typing import Any, ClassVar, Dict

from forge_bridge.graph.ports import PortContract, PortTopology

#: The format-terminal step grammar (#153 slice 2b). Canonical author of the
#: ``format as <class>`` parse, shared by the legacy chain path
#: (``console/_step.py`` re-imports ``extract_format_class`` under its old
#: ``_extract_format_class`` name) and the graph compiler (which recognizes a
#: format terminal and forwards the whole prior result as ``data``). Relocated
#: here — a lower layer than ``console/`` — for the same one-canonical-author
#: reason ``extract_chain_context`` was (slice 2a).
_FORMAT_STEP_RE = re.compile(
    r"\bformat\s+as\s+(?:(?:a|an|the)\s+)?"
    r"(?P<format>email|table|bullets?|bullet[_ -]?list)\b",
    re.IGNORECASE,
)


def is_format_step(step_text: str) -> bool:
    """True when a chain step is a format terminal (``format as <class>``).

    Recognizes the deterministic ``-> format as email`` chain form so the graph
    compiler can route it to the ``format_result`` operator. The bare
    ``format_result`` tool-name form (no format phrase) is not matched here — it
    reaches the operator via first-token dispatch instead.
    """
    return bool(_FORMAT_STEP_RE.search(step_text or ""))


def extract_format_class(step_text: str) -> str | None:
    """Parse the ``format`` class from a format-terminal step, or ``None``.

    Byte-identical to the legacy ``_extract_format_class`` it replaces (the
    legacy name re-imports this). Normalizes ``bullet``/``bullet list``/
    ``bullet_list`` spellings to the canonical ``bullets`` class.
    """
    match = _FORMAT_STEP_RE.search(step_text or "")
    if not match:
        return None
    value = match.group("format").lower().replace("-", "_").replace(" ", "_")
    return "bullets" if value in {"bullet", "bullets", "bullet_list"} else value


def extract_chain_context(result: Any) -> Dict[str, str]:
    """Deterministically extract inherited-context kwargs from a tool result.

    Two orthogonal probes, unioned into the returned dict:

    **Singleton-id probe** (first match wins *among the id keys* — the id keys
    are never unioned with one another):

      1. ``projects`` → ``project_id``
      2. ``shots`` → ``shot_id``
      3. ``versions`` → ``version_id``

    Rules:

      - Only propagate when exactly **one** item exists in the list.
      - Item must be a dict with a non-empty string ``id`` (after strip).
      - Stop at the first qualifying id key.

    **Sequence-name probe** (#153 slice 2a — *additive*, independent of the id
    probe): read ``result["sequence"]`` (falling back to
    ``result["sequence_name"]``) and forward it as ``sequence_name`` when it is a
    non-empty string. This reproduces the legacy ``__previous_result__.sequence``
    backfill (``console/_step.py`` — the extractor's input *is* the previous
    result, so the source key is the same). Faithful to the legacy fold, a single
    step may therefore carry **both** a singleton id *and* ``sequence_name`` (the
    two-key case: e.g. a lone ``shots`` list next to a ``sequence`` key).

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

    context: Dict[str, str] = {}

    # Singleton-id probe: first match wins among the id keys (unchanged from
    # slice 1 — projects > shots > versions, at most one id key emitted).
    project_id = _single_id(result.get("projects"))
    if project_id is not None:
        context["project_id"] = project_id
    else:
        shot_id = _single_id(result.get("shots"))
        if shot_id is not None:
            context["shot_id"] = shot_id
        else:
            version_id = _single_id(result.get("versions"))
            if version_id is not None:
                context["version_id"] = version_id

    # Sequence-name probe (#153 slice 2a): additive and orthogonal to the id
    # probe. Mirror the legacy backfill exactly — ``sequence`` then
    # ``sequence_name``, forwarded only when a non-empty string.
    seq = result.get("sequence") or result.get("sequence_name")
    if isinstance(seq, str) and seq:
        context["sequence_name"] = seq

    return context


@dataclass(frozen=True)
class ExtractContextNode:
    """Emit the inherited-context kwargs an upstream result forwards.

    A value-transform primitive: it consumes an upstream tool result (a
    manifest/dict) and emits a ``{kwarg: value}`` scalars dict, or ``{}`` when
    nothing qualifies. The dict carries at most one singleton id key and, since
    #153 slice 2a, an additive ``sequence_name`` (so a single node may forward
    two keys). The which-key decision lives *inside this visible node*, not in
    the value-blind MCP boundary that merges the dict.

    **Wrap mode (#153 slice 2b).** When ``wrap_key`` is set, the node instead
    re-keys the *whole* upstream result under that single key
    (``{wrap_key: <entire input>}``). This reproduces the legacy
    ``format_result.data = __previous_result__`` whole-payload handoff. Re-keying
    the payload is a transport relabel, not a semantic transform, so it stays the
    same node type / same admission record / same port contract — the mode rides
    in a field, not in the port topology.
    """

    #: When set, emit ``{wrap_key: <whole input>}`` instead of the extracted
    #: singleton kwargs. Compiler-authored via ``config["wrap_key"]``.
    wrap_key: str | None = None

    #: Input accepts a manifest-shaped upstream result; the emitted scalars dict
    #: types back to a manifest via ``infer_topology``. Both are existing
    #: ``PortTopology`` variants — no new port kind (the name rides in the value).
    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.manifest(),),
        PortTopology.manifest(),
    )

    def run(self, data: Any) -> dict[str, Any]:
        if self.wrap_key:
            return {self.wrap_key: data}
        return extract_chain_context(data)
