"""PR30 / PR37 — single chain-step execution (no HTTP, no handler globals).

Moved from ``handlers._execute_chain_step`` so engine and CLI can import without
circular imports from ``handlers``.

A.5.3.2 PR 5 — chain-step capture integration (Shape A guarded import). The
``forge_bridge.corpus`` package is structurally optional at module-load time;
absence is logged and the emission path becomes a no-op. The chat handler's
PR 4 surface uses the same shape (handlers.py:90-115). Per
A.5.3.2-PR5-FRAMING.md §1: "Same topology applies at _step.py module load —
not a separate guarded import, since both modules import emission helpers
from the same forge_bridge.corpus namespace." Symmetric topology, identical
fallback semantics; the duplicate WARNING-on-load is an O(1) cost per
process lifetime.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from forge_bridge.console._tool_filter import deterministic_narrow, filter_tools_by_message
from forge_bridge.mcp.arguments import normalize_tool_args

# A.5.3.2 PR 5 §4.1 — Shape A guarded import for divergence capture.
# Per A.5.3.2-PR5-FRAMING.md §1.4 (inheriting PR 4 framing §1.4):
# "The arbitration layer now expects capture infrastructure to exist."
# That sentence MUST remain false for the lifetime of this architecture.
# If forge_bridge.corpus is structurally absent at module load, fallback
# bindings preserve arbitration completion; capture becomes a no-op.
try:
    from forge_bridge.corpus import (
        divergence_capture_enabled,
        emit_divergence_capture,
    )
except ImportError as _corpus_import_error:
    # Direct getLogger call used intentionally here: this branch
    # executes during module-load-time topology resolution before
    # the module-level logger binding below exists. Same rationale
    # as handlers.py:99-101.
    logging.getLogger(__name__).warning(
        "forge_bridge.corpus is structurally absent at _step load; "
        "divergence-capture disabled for this process lifetime. "
        "(Import-time observation, distinct from "
        "FORGE_BRIDGE_DIVERGENCE_CAPTURE env-driven gating.) "
        "import_error=%s",
        _corpus_import_error,
    )

    def divergence_capture_enabled(*_args, **_kwargs) -> bool:
        return False

    def emit_divergence_capture(*_args, **_kwargs) -> None:
        pass

logger = logging.getLogger(__name__)

_FORMAT_STEP_RE = re.compile(
    r"\bformat\s+as\s+(?:(?:a|an|the)\s+)?"
    r"(?P<format>email|table|bullets?|bullet[_ -]?list)\b",
    re.IGNORECASE,
)


def serialize_forced_tool_result(raw: Any) -> str:
    """Serialize a FastMCP ``call_tool`` return into a string for tracing/context.

    Shared with ``handlers._execute_forced_tool`` — behavior unchanged from the
    original implementation.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        if "result" in raw and isinstance(raw["result"], str):
            return raw["result"]
        return json.dumps(raw, default=str)
    if isinstance(raw, tuple) and len(raw) == 2:
        blocks, structured = raw
        if isinstance(structured, dict) and isinstance(
            structured.get("result"), str
        ):
            return structured["result"]
        raw = blocks
    if isinstance(raw, (list, tuple)):
        parts: list[str] = []
        for block in raw:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
                continue
            dump = getattr(block, "model_dump_json", None)
            if callable(dump):
                try:
                    parts.append(dump())
                    continue
                except Exception:  # noqa: BLE001
                    pass
            parts.append(repr(block))
        return "\n".join(parts) if parts else ""
    return repr(raw)


def _ambiguity_state_for_chain_step(n: int) -> str:
    """Translate narrowing-count to the schema's ``ambiguity_state``
    string at the chain-step surface. Translation-only; no inferential
    logic per the binding constraint in ``A.5.3.2-PR4-SPEC.md`` §4.1.

    Mirrors ``handlers.py::_ambiguity_state_for``; the helpers are NOT
    deduplicated because the chat-handler and chain-step views of
    ``ambiguity_state`` are orthogonal authority surfaces (per
    ``A.5.3.2-PR5-FRAMING.md`` §2.2 architectural protection bullet 3
    + ``A.5.3.2-PR5-SPEC.md`` §4.1 helper-duplication binding).
    Conflating them via shared helper extraction would introduce a
    hidden cross-site coupling that schema-validation shortcuts could
    later exploit. Same translation behavior; independent surface.

    A future PR proposing to extract ``_ambiguity_state_for`` and this
    helper into a shared module is rejected at the spec layer per
    ``A.5.3.2-PR5-SPEC.md`` §8 phase-end conditions.
    """
    return {0: "zero_survivor", 1: "single_survivor"}.get(n, "multi_survivor")


async def execute_chain_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
    step_index: int | str = 0,
) -> dict:
    """Run a single chain step end-to-end.

    Returns a dict in one of two shapes:

      Success: ``{"result": ..., "extracted_context": dict,
                  "tool": <tool_name>, "params": dict}``
      Failure: ``{"error": {"type": ..., "message": ..., ...}}``

    Inherited context merges with explicit step params (PR28); PR32 context for
    the next step comes only from ``extract_chain_context(parsed result)`` inside
    this function's success path.
    """
    from forge_bridge.console._chain_parse import extract_chain_context
    from forge_bridge.console._name_resolve import resolve_name_from_candidates
    from forge_bridge.console._param_extract import extract_explicit_params
    from forge_bridge.console._tool_chain import (
        DISAMBIGUATION_KEY,
        UNRESOLVED_KEY,
        resolve_required_params,
    )

    wire_error = _validate_step_chain_wire(
        step_text=step_text,
        inherited_context=inherited_context,
        step_index=step_index,
    )
    if wire_error is not None:
        return {"error": wire_error}

    graph_outcome = await _maybe_execute_foreach_step(
        step_text=step_text,
        tools=tools,
        mcp=mcp,
        inherited_context=inherited_context,
        step_index=step_index,
    )
    if graph_outcome is not None:
        return graph_outcome

    graph_outcome = _maybe_execute_collect_step(
        step_text=step_text,
        inherited_context=inherited_context,
        step_index=step_index,
    )
    if graph_outcome is not None:
        return graph_outcome

    graph_outcome = await _maybe_execute_commit_step(
        step_text=step_text,
        tools=tools,
        mcp=mcp,
        inherited_context=inherited_context,
        step_index=step_index,
    )
    if graph_outcome is not None:
        return graph_outcome

    graph_outcome = _maybe_execute_if_step(
        step_text=step_text,
        inherited_context=inherited_context,
    )
    if graph_outcome is not None:
        return graph_outcome

    graph_outcome = _maybe_execute_select_step(
        step_text=step_text,
        inherited_context=inherited_context,
    )
    if graph_outcome is not None:
        return graph_outcome

    graph_outcome = _maybe_execute_filter_step(
        step_text=step_text,
        inherited_context=inherited_context,
    )
    if graph_outcome is not None:
        return graph_outcome

    # PR 5 §4.1 — deployment identity snapshot. Per framing §2.1:
    # the chain-step's deployment identity is the caller's view, not
    # the global daemon registry view. Bound at function entry,
    # BEFORE any local interpretation or narrowing activity, so the
    # moment-of-authority truth is preserved regardless of downstream
    # reinterpretation. Authority-surface protection, not local-scope
    # minimization.
    registered_tools = tools

    # PR 5 §4.1 — runtime topology snapshot collapses with deployment
    # identity at this surface. There is no reachability filter here;
    # that filter ran upstream in handlers.py. Per A.5.3.2-PR4-CLOSE.md
    # §3.1 this collapse is named explicitly so it is not silently
    # overloaded across the two call sites.
    tools_post_reachability = tools

    user_params = extract_explicit_params(step_text)
    semantic_params = _extract_semantic_step_params(step_text)

    inherited = inherited_context or {}
    public_inherited = {
        key: value for key, value in inherited.items()
        if not str(key).startswith("__")
    }
    merged: dict = {**public_inherited, **semantic_params, **user_params}
    requested_name = merged.get("project_name")
    resolver_input = {k: v for k, v in merged.items() if k != "project_name"}

    # PR 5 §4.1 — narrower-latency instrumentation. Measurement
    # happens regardless of divergence_capture_enabled() per spec:
    # latency belongs to the arbitration path, not the capture path.
    # Decoupling protects against a later "let's only measure when
    # capturing" simplification that would couple arbitration timing
    # to capture state and weaken the §1.4 no-dependency property.
    narrower_started = time.perf_counter()
    filtered = filter_tools_by_message(tools, step_text)

    # PR 5 §4.1 — arbitration-input snapshot. Captures the post-PR14
    # set BEFORE deterministic_narrow has a chance to collapse it.
    # Used by collapse_occurred derivation (multi-to-single transition
    # diagnostic on the success path).
    tools_post_pr14 = filtered

    if len(filtered) > 1:
        narrowed = deterministic_narrow(filtered, step_text)
        if len(narrowed) < len(filtered):
            filtered = narrowed
    narrower_latency_ms = (time.perf_counter() - narrower_started) * 1000.0

    # ── Capture is emitted after arbitration decisions are finalized
    #    and must not structurally participate in the arbitration
    #    pipeline. (PR 3 spec §0; PR 4 framing §0.)
    #
    #    PR 4 is the controlled introduction of observational
    #    side-effects into live arbitration surfaces. The risk
    #    category has shifted from persistence-substrate risk to
    #    participation-creep risk. (PR 4 framing §0.)
    #
    #    The call site is the source of the three explicit inputs.
    #    The integration layer passes truth. The integration layer
    #    never reconstructs truth. The builder does not discover
    #    runtime state. (PR 4 framing §3.)
    #
    #    Capture emission occurs only after arbitration state is
    #    finalized for the current execution path. Capture records
    #    completed arbitration observations, not provisional
    #    intermediate state. (PR 4 spec §0.)
    #
    #    ── PR 5 specializations ──
    #
    #    PR 5 is the second call site under the integration discipline
    #    PR 4 established. The risk profile is inherited; the surface
    #    geometry is not. (PR 5 framing §0.)
    #
    #    The chain-step's deployment identity is the caller's view,
    #    not the global daemon registry view. (PR 5 framing §0 +
    #    §2.1.)
    #
    #    Ambiguity rejection is an arbitration outcome. Capture must
    #    record it. At this surface, narrower_decision carries the
    #    filtered list verbatim at narrowing finalization — including
    #    zero-match and multi-match rejection paths. pr20_condition_met
    #    is always False and collapse_occurred is False on all
    #    rejection paths. These semantics differ from the chat-handler
    #    case and must not be silently overloaded. (PR 5 framing §2.2.)
    #
    #    Capture is arbitration-aware, not branch-aware. The single
    #    insertion point at narrowing-finalization preserves capture's
    #    relationship to the arbitration event itself, not to its
    #    downstream semantic interpretations. Subsequent failure paths
    #    (e.g., MULTIPLE_PROJECTS) do not re-trigger capture; capture
    #    has already recorded the truthful single-tool narrowing
    #    result. (PR 5 spec §4.1.)

    if divergence_capture_enabled():
        emit_divergence_capture(
            prompt=step_text,
            registered_tools=registered_tools,
            candidate_set_post_reachability=tools_post_reachability,
            candidate_set_post_pr14=tools_post_pr14,
            narrower_decision=filtered,
            pr20_condition_met=False,
            collapse_occurred=(
                len(filtered) == 1 and len(tools_post_pr14) > 1
            ),
            ambiguity_state=_ambiguity_state_for_chain_step(len(filtered)),
            narrower_latency_ms=narrower_latency_ms,
            source="runtime",
        )

    if len(filtered) != 1:
        return {"error": {
            "type": "tool_selection_ambiguous",
            "message": (
                f"Step matched {len(filtered)} tools; chain steps must "
                "select exactly one. Use a more specific verb/noun "
                "(e.g. 'list versions' instead of just 'list')."
            ),
            "candidates": [
                getattr(t, "name", str(t)) for t in filtered[:5]
            ],
        }}
    tool_name = filtered[0].name

    params = await resolve_required_params(
        tool_name, resolver_input, mcp, message=step_text,
    )
    if tool_name == "format_result":
        params = dict(params)
        if "data" not in params and "__previous_result__" in inherited:
            params["data"] = inherited["__previous_result__"]
        if "format" not in params:
            format_class = _extract_format_class(step_text)
            if format_class:
                params["format"] = format_class
    if tool_name in {"flame_rename_shots", "flame_preview_rename"}:
        selected = inherited.get("__filtered_collection__")
        if selected is not None and "selected_segments" not in params:
            params = dict(params)
            params["selected_segments"] = selected

    if DISAMBIGUATION_KEY in params:
        candidates = (params[DISAMBIGUATION_KEY] or {}).get("candidates", []) or []
        resolved_id = (
            resolve_name_from_candidates(requested_name, candidates)
            if requested_name else None
        )
        if not resolved_id:
            return {"error": {
                "type": "MULTIPLE_PROJECTS",
                "message": (
                    "Multiple projects found; specify project_id=<uuid> "
                    "or project_name=<name>."
                ),
                "details": params[DISAMBIGUATION_KEY],
            }}
        params = await resolve_required_params(
            tool_name, {"project_id": resolved_id}, mcp, message=step_text,
        )

    if UNRESOLVED_KEY in params:
        unresolved = params[UNRESOLVED_KEY]
        key = unresolved.get("key")
        if key == "sequence_name":
            prev = inherited.get("__previous_result__")
            if isinstance(prev, dict):
                seq = prev.get("sequence") or prev.get("sequence_name")
                if isinstance(seq, str) and seq:
                    resolver_input["sequence_name"] = seq
                    params = await resolve_required_params(
                        tool_name, resolver_input, mcp, message=step_text,
                    )

    if UNRESOLVED_KEY in params:
        unresolved = params[UNRESOLVED_KEY]
        key = unresolved.get("key")
        message = (
            "Could not resolve sequence name from your query. "
            "Please specify the exact sequence name."
        )
        if key == "reel_name":
            message = (
                "Could not resolve reel name from your query. "
                "Please specify the exact reel name."
            )
        return {"error": {
            "type": "UNRESOLVED_REQUIRED_PARAM",
            "message": message,
            "details": unresolved,
        }}

    try:
        params = normalize_tool_args(tool_name, params, [filtered[0]])
        raw = await mcp.call_tool(tool_name, params)
    except Exception as exc:  # noqa: BLE001
        return {"error": {
            "type": type(exc).__name__,
            "message": str(exc),
        }}

    serialized = serialize_forced_tool_result(raw)

    parsed: Any = serialized
    try:
        decoded = json.loads(serialized)
        parsed = decoded
    except (ValueError, json.JSONDecodeError):
        pass

    return {
        "result": parsed,
        "extracted_context": extract_chain_context(parsed),
        "emitted_topology": _topology_dict_for_value(parsed),
        "tool": tool_name,
        "params": params,
    }


def _validate_step_chain_wire(
    *,
    step_text: str,
    inherited_context: dict,
    step_index: int | str,
) -> dict[str, Any] | None:
    """Validate typed graph ports at the next dispatch edge.

    This is incremental local validation, not chain preflight. It fires only
    when a step declares a typed input contract and a previous result exists.
    """
    from forge_bridge.graph import (
        ChainWireCompatibilityError,
        infer_topology,
        validate_chain_wire,
    )

    inherited_context = inherited_context or {}
    if "__previous_result__" not in inherited_context:
        return None

    contract = _port_contract_for_step(step_text)
    if contract is None:
        return None

    encoded = inherited_context.get("__previous_topology__")
    if isinstance(encoded, dict):
        from forge_bridge.graph import PortTopology

        actual = PortTopology.from_dict(encoded)
    else:
        actual = infer_topology(inherited_context["__previous_result__"])
    try:
        validate_chain_wire(
            step_index=step_index,
            step_text=step_text,
            contract=contract,
            actual=actual,
        )
    except ChainWireCompatibilityError as exc:
        return exc.to_error()
    return None


def _port_contract_for_step(step_text: str):
    from forge_bridge.graph import (
        CollectNode,
        CommitNode,
        FilterNode,
        ForEachNode,
        IfGateNode,
        SelectNode,
        is_collect_step,
        is_commit_step,
        is_filter_step,
        is_foreach_step,
        is_if_step,
        is_select_step,
    )

    if is_foreach_step(step_text):
        return ForEachNode.port_contract
    if is_collect_step(step_text):
        return CollectNode.port_contract
    if is_commit_step(step_text):
        return CommitNode.port_contract
    if is_if_step(step_text):
        return IfGateNode.port_contract
    if is_select_step(step_text):
        return SelectNode.port_contract
    if is_filter_step(step_text):
        return FilterNode.port_contract
    return None


def _topology_dict_for_value(value: Any) -> dict[str, str]:
    from forge_bridge.graph import infer_topology

    return infer_topology(value).to_dict()


def _extract_format_class(step_text: str) -> str | None:
    match = _FORMAT_STEP_RE.search(step_text or "")
    if not match:
        return None
    value = match.group("format").lower().replace("-", "_").replace(" ", "_")
    return "bullets" if value in {"bullet", "bullets", "bullet_list"} else value


def _extract_semantic_step_params(step_text: str) -> dict[str, Any]:
    """Project deterministic resolver entities into chain-step params.

    This is the chain-step instance of the resolver's broader role: entity,
    numeric, format, intent directives, and graph predicates are semantic
    projections, not LLM guesses. Filter and if-gate predicates remain
    graph-node inputs and are consumed before tool selection reaches this path.
    """
    from forge_bridge.llm.resolver import (
        resolve_query_entities,
        resolved_entity_params,
    )

    params = resolved_entity_params(resolve_query_entities(step_text))
    params.pop("filter_predicate", None)
    params.pop("filter_error", None)
    params.pop("if_predicate", None)
    params.pop("if_error", None)
    params.pop("select_identity", None)
    params.pop("select_error", None)
    return params


async def _maybe_execute_foreach_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
    step_index: int | str,
) -> dict | None:
    from forge_bridge.graph import (
        ForeachInputError,
        ForeachParseError,
        ForEachNode,
        PortTopology,
        infer_iteration_item_topology,
        infer_topology,
        is_foreach_step,
        parse_foreach_step,
    )

    if not is_foreach_step(step_text):
        return None

    inherited_context = inherited_context or {}
    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "ForEachNode requires a previous collection result.",
        }}

    try:
        body_step = parse_foreach_step(step_text)
        node = ForEachNode(body_step)
        prior = inherited_context["__previous_result__"]
        items = node.items(prior)
    except (ForeachInputError, ForeachParseError) as exc:
        return {"error": {
            "type": getattr(exc, "code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
        }}

    encoded = inherited_context.get("__previous_topology__")
    collection_topology = (
        PortTopology.from_dict(encoded)
        if isinstance(encoded, dict)
        else infer_topology(prior)
    )

    public_inherited = {
        key: value for key, value in inherited_context.items()
        if not str(key).startswith("__")
    }
    sequence = public_inherited.get("sequence_name")
    if not sequence and isinstance(prior, dict):
        sequence = prior.get("sequence") or prior.get("sequence_name")
    iterations = []
    for iteration_index, item in enumerate(items):
        iteration_payload = node.iteration_payload(prior, item)
        item_topology = infer_iteration_item_topology(
            item=item,
            collection_topology=collection_topology,
        )
        iteration_context = dict(public_inherited)
        if isinstance(sequence, str) and sequence:
            iteration_context["sequence_name"] = sequence
        iteration_context["__previous_result__"] = iteration_payload
        iteration_context["__previous_topology__"] = item_topology.to_dict()
        iteration_context["__filtered_collection__"] = [item]

        outcome = await execute_chain_step(
            step_text=body_step,
            tools=tools,
            mcp=mcp,
            inherited_context=iteration_context,
            step_index=f"{step_index}.{iteration_index}",
        )
        if "error" in outcome:
            error = dict(outcome["error"])
            error["foreach_step_index"] = step_index
            error["iteration_index"] = iteration_index
            error["body_step"] = body_step
            return {"error": error}

        body_result = outcome["result"]
        if not isinstance(body_result, dict):
            body_result = {"value": body_result}
        iterations.append(node.wrap_result(
            index=iteration_index,
            item=item,
            result=body_result,
            emitted_topology=(
                outcome.get("emitted_topology")
                or _topology_dict_for_value(body_result)
            ),
        ))

    result = node.envelope(iterations)
    extracted: dict[str, Any] = {}
    if isinstance(sequence, str) and sequence:
        extracted["sequence_name"] = sequence

    return {
        "result": result,
        "extracted_context": extracted,
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_foreach",
        "params": {"body": body_step},
    }


def _maybe_execute_collect_step(
    *,
    step_text: str,
    inherited_context: dict,
    step_index: int | str,
) -> dict | None:
    from forge_bridge.graph import (
        ChainWireCompatibilityError,
        CollectError,
        CollectNode,
        is_collect_step,
        parse_collect_step,
    )

    if not is_collect_step(step_text):
        return None

    inherited_context = inherited_context or {}
    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "CollectNode requires previous iteration results.",
        }}

    try:
        parse_collect_step(step_text)
        result = CollectNode().run(inherited_context["__previous_result__"])
    except ChainWireCompatibilityError as exc:
        error = exc.to_error()
        error["step_index"] = step_index
        error["step"] = step_text
        return {"error": error}
    except CollectError as exc:
        return {"error": {
            "type": getattr(exc, "code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
        }}

    extracted: dict[str, Any] = {}
    sequence = result.get("sequence") or result.get("sequence_name")
    if isinstance(sequence, str) and sequence:
        extracted["sequence_name"] = sequence

    return {
        "result": result,
        "extracted_context": extracted,
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_collect",
        "params": {},
    }


async def _maybe_execute_commit_step(
    *,
    step_text: str,
    tools: list,
    mcp: Any,
    inherited_context: dict,
    step_index: int | str,
) -> dict | None:
    from forge_bridge.graph import (
        CommitError,
        CommitNode,
        is_commit_step,
        parse_commit_step,
    )
    from forge_bridge.graph.mutation import (
        MutationManifest,
        validate_mutation_manifest,
    )

    if not is_commit_step(step_text):
        return None

    inherited_context = inherited_context or {}
    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "CommitNode requires a previous mutation manifest.",
        }}

    previous = inherited_context["__previous_result__"]
    error = validate_mutation_manifest(previous)
    if error is not None:
        return {"error": CommitError(
            CommitError.MUTATION_MANIFEST_INVALID,
            error.message,
            step_index=step_index,
            step_text=step_text,
        ).to_error()}

    try:
        parse_commit_step(step_text)
        manifest = MutationManifest.from_dict(previous)
    except (CommitError, ValueError) as exc:
        return {"error": CommitError(
            CommitError.MUTATION_MANIFEST_INVALID,
            str(exc),
            step_index=step_index,
            step_text=step_text,
        ).to_error()}

    target_tool = manifest.apply_counterpart["tool"]
    if target_tool not in {getattr(tool, "name", str(tool)) for tool in tools}:
        return {"error": CommitError(
            CommitError.APPLY_COUNTERPART_NOT_DECLARED,
            f"Apply counterpart {target_tool!r} is not declared.",
            step_index=step_index,
            step_text=step_text,
        ).to_error()}

    verify_params = dict(manifest.intent_parameters)
    verify_params.update(manifest.apply_counterpart["parameter_overrides"])
    verify_params["mode"] = "verify"
    verify_params["resolved_plan"] = [
        record.to_dict() for record in manifest.resolved_plan
    ]
    verify_params = normalize_tool_args(target_tool, verify_params, tools)

    try:
        raw = await mcp.call_tool(target_tool, verify_params)
    except Exception as exc:  # noqa: BLE001
        return {"error": {
            "type": type(exc).__name__,
            "message": str(exc),
        }}

    serialized = serialize_forced_tool_result(raw)
    try:
        decoded = json.loads(serialized)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"error": CommitError(
            CommitError.MUTATION_MANIFEST_INVALID,
            f"Verify result is not a mutation manifest: {exc}",
            step_index=step_index,
            step_text=step_text,
        ).to_error()}

    error = validate_mutation_manifest(decoded)
    if error is not None:
        return {"error": CommitError(
            CommitError.MUTATION_MANIFEST_INVALID,
            error.message,
            step_index=step_index,
            step_text=step_text,
        ).to_error()}

    fresh = MutationManifest.from_dict(decoded)
    verification = CommitNode().verify(manifest, fresh)
    if not verification.matched:
        return {"error": CommitError(
            CommitError.PLAN_STATE_DRIFT,
            "Mutation plan no longer matches current state.",
            step_index=step_index,
            step_text=step_text,
            drift_count=verification.drift_count,
            first_drift_index=verification.first_drift_index,
        ).to_error()}

    apply_params = dict(manifest.intent_parameters)
    apply_params.update(manifest.apply_counterpart["parameter_overrides"])
    apply_params["mode"] = "apply"
    apply_params["resolved_plan"] = [
        record.to_dict() for record in manifest.resolved_plan
    ]
    apply_params = normalize_tool_args(target_tool, apply_params, tools)

    try:
        apply_raw = await mcp.call_tool(target_tool, apply_params)
    except Exception as exc:  # noqa: BLE001
        return {"error": {
            "type": type(exc).__name__,
            "message": str(exc),
        }}

    apply_serialized = serialize_forced_tool_result(apply_raw)
    try:
        apply_result = json.loads(apply_serialized)
    except (ValueError, json.JSONDecodeError):
        apply_result = apply_serialized

    if isinstance(apply_result, dict) and apply_result.get("drift") is True:
        return {"error": CommitError(
            CommitError.PLAN_STATE_DRIFT,
            "Mutation plan no longer matches current state.",
            step_index=step_index,
            step_text=step_text,
            drift_count=apply_result.get("drift_count"),
            first_drift_index=apply_result.get("first_drift_index"),
        ).to_error()}

    result = {
        "type": "commit_applied",
        "execution_state": "applied",
        "verified": True,
        "applied": True,
        "message": "applied",
        "count": len(manifest.resolved_plan),
        "apply_result": apply_result,
    }
    return {
        "result": result,
        "extracted_context": {},
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_commit",
        "params": {},
    }


def _maybe_execute_select_step(
    *,
    step_text: str,
    inherited_context: dict,
) -> dict | None:
    from forge_bridge.graph import (
        GraphInputError,
        SelectError,
        SelectIdentity,
        SelectNode,
        is_select_step,
    )
    from forge_bridge.llm.resolver import resolve_query_entities

    if not is_select_step(step_text):
        return None

    inherited_context = inherited_context or {}
    resolved = resolve_query_entities(step_text)
    select_error = resolved.get("select_error")
    if isinstance(select_error, dict) and isinstance(select_error.get("value"), dict):
        return {"error": {
            "type": select_error["value"].get("code", "INVALID_SELECT_IDENTITY"),
            "message": select_error["value"].get("message", "Invalid select identity."),
            "details": select_error["value"],
        }}

    entity = resolved.get("select_identity")
    identity_value = entity.get("value") if isinstance(entity, dict) else None
    if not isinstance(identity_value, dict):
        return {"error": {
            "type": "INVALID_SELECT_IDENTITY",
            "message": "Invalid select identity.",
        }}

    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "SelectNode requires a previous collection or manifest result.",
        }}

    prior = inherited_context["__previous_result__"]
    try:
        identity = SelectIdentity.from_dict(identity_value)
        node = SelectNode(identity)
        result = node.run(prior)
        selected = node.selected_collection(prior)
    except (GraphInputError, SelectError, ValueError) as exc:
        error = {
            "type": getattr(exc, "code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
        }
        details = getattr(exc, "details", None)
        if isinstance(details, dict) and details:
            error["details"] = details
        return {"error": error}

    extracted: dict[str, Any] = {"__filtered_collection__": selected}
    sequence = None
    if isinstance(result, dict):
        sequence = result.get("sequence") or result.get("sequence_name")
    if not sequence and isinstance(prior, dict):
        sequence = prior.get("sequence") or prior.get("sequence_name")
    if isinstance(sequence, str) and sequence:
        extracted["sequence_name"] = sequence

    return {
        "result": result,
        "extracted_context": extracted,
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_select",
        "params": {"identity": identity.to_dict()},
    }


def _maybe_execute_if_step(
    *,
    step_text: str,
    inherited_context: dict,
) -> dict | None:
    from forge_bridge.graph import (
        GraphInputError,
        IfGateNode,
        FilterPredicate,
        is_if_step,
    )
    from forge_bridge.llm.resolver import resolve_query_entities

    if not is_if_step(step_text):
        return None

    inherited_context = inherited_context or {}
    resolved = resolve_query_entities(step_text)
    if_error = resolved.get("if_error")
    if isinstance(if_error, dict) and isinstance(if_error.get("value"), dict):
        return {"error": {
            "type": "UNKNOWN_IF_PREDICATE",
            "message": if_error["value"].get("message", "Unknown if-gate predicate."),
            "details": if_error["value"],
        }}

    entity = resolved.get("if_predicate")
    predicate_value = entity.get("value") if isinstance(entity, dict) else None
    if not isinstance(predicate_value, dict):
        return {"error": {
            "type": "UNKNOWN_IF_PREDICATE",
            "message": "Unknown if-gate predicate.",
        }}

    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "IfGateNode requires a previous execution manifest.",
        }}

    try:
        predicate = FilterPredicate.from_dict(predicate_value)
        result = IfGateNode(predicate).run(inherited_context["__previous_result__"])
    except (GraphInputError, ValueError) as exc:
        return {"error": {
            "type": getattr(exc, "code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
        }}

    extracted: dict[str, Any] = {
        "__if_gate_skip_next__": result.get("execution_state") == "skipped",
    }
    sequence = result.get("sequence") or result.get("sequence_name")
    if isinstance(sequence, str) and sequence:
        extracted["sequence_name"] = sequence

    return {
        "result": result,
        "extracted_context": extracted,
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_if_gate",
        "params": {"predicate": predicate.to_dict()},
    }


def _maybe_execute_filter_step(
    *,
    step_text: str,
    inherited_context: dict,
) -> dict | None:
    from forge_bridge.graph import (
        FilterNode,
        FilterPredicate,
        GraphInputError,
        is_filter_step,
    )
    from forge_bridge.llm.resolver import resolve_query_entities

    if not is_filter_step(step_text):
        return None

    inherited_context = inherited_context or {}
    resolved = resolve_query_entities(step_text)
    filter_error = resolved.get("filter_error")
    if isinstance(filter_error, dict) and isinstance(filter_error.get("value"), dict):
        return {"error": {
            "type": "UNKNOWN_FILTER_PREDICATE",
            "message": filter_error["value"].get("message", "Unknown filter predicate."),
            "details": filter_error["value"],
        }}

    entity = resolved.get("filter_predicate")
    predicate_value = entity.get("value") if isinstance(entity, dict) else None
    if not isinstance(predicate_value, dict):
        return {"error": {
            "type": "UNKNOWN_FILTER_PREDICATE",
            "message": "Unknown filter predicate.",
        }}

    if "__previous_result__" not in inherited_context:
        return {"error": {
            "type": "GRAPH_INPUT_REQUIRED",
            "message": "FilterNode requires a previous enumeration result.",
        }}

    try:
        predicate = FilterPredicate.from_dict(predicate_value)
        node = FilterNode(predicate)
        prior = inherited_context["__previous_result__"]
        result = node.run(prior)
        selected = node.selected_collection(prior)
    except (GraphInputError, ValueError) as exc:
        return {"error": {
            "type": getattr(exc, "code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
        }}

    extracted: dict[str, Any] = {"__filtered_collection__": selected}
    if isinstance(result, dict):
        sequence = result.get("sequence") or result.get("sequence_name")
        if isinstance(sequence, str) and sequence:
            extracted["sequence_name"] = sequence

    return {
        "result": result,
        "extracted_context": extracted,
        "emitted_topology": _topology_dict_for_value(result),
        "tool": "graph_filter",
        "params": {"predicate": predicate.to_dict()},
    }
