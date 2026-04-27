"""
forge_bridge.mcp.registry — Namespace enforcement and source tagging for MCP tools.

Every tool registration (builtins, synthesized, user-taught) routes through this
module. It enforces the flame_*/forge_*/synth_* prefix rules and attaches
_source metadata to every registered tool.

Public API:
    register_tool(mcp, fn, name, source, annotations=None)
    register_tools(mcp, fns, prefix="", source="user-taught")
    register_builtins(mcp)
    invoke_tool(name, args) -> str   # FB-C LLMTOOL-03 default tool executor

Constants:
    _VALID_PREFIXES         — all accepted prefixes
    _SYNTH_RESERVED_PREFIXES — prefixes only the synthesis pipeline may use
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from forge_bridge.learning.sanitize import apply_size_budget

logger = logging.getLogger(__name__)

# Prefixes exclusively owned by the synthesis pipeline.
# Static (builtin / user-taught) registrations are blocked from using these.
_SYNTH_RESERVED_PREFIXES: frozenset[str] = frozenset({"synth_"})

# All valid prefixes for this server.
_VALID_PREFIXES: frozenset[str] = frozenset({"flame_", "forge_", "synth_"})


def _validate_name(name: str, source: str) -> None:
    """Raise ValueError if *name* violates namespace rules for *source*.

    Rules:
        1. Every tool name must start with one of the _VALID_PREFIXES.
        2. Only source="synthesized" may register under _SYNTH_RESERVED_PREFIXES.
    """
    if not any(name.startswith(p) for p in _VALID_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} must start with flame_, forge_, or synth_. "
            f"Got source={source!r}."
        )
    if source != "synthesized" and any(name.startswith(p) for p in _SYNTH_RESERVED_PREFIXES):
        raise ValueError(
            f"Tool name {name!r} uses a reserved synth_ prefix. "
            "Only the synthesis pipeline may register under synth_."
        )


def register_tool(
    mcp: FastMCP,
    fn: Callable[..., Any],
    name: str,
    source: str,
    annotations: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> None:
    """Register a single tool with namespace enforcement and source tagging.

    Args:
        mcp:         The live FastMCP instance to register against.
        fn:          The callable to register as an MCP tool.
        name:        Tool name — must start with flame_, forge_, or synth_.
        source:      One of "builtin", "synthesized", or "user-taught".
        annotations: Optional MCP tool annotations dict (readOnlyHint, etc.).
                     For source="synthesized", readOnlyHint defaults to False
                     per PROV-04 (synthesized tools call bridge.execute()).
        provenance:  Optional dict of shape {"tags": [...], "meta": {...}}
                     produced by the watcher's _read_sidecar helper.
                     Only forge-bridge/* namespaced meta keys are forwarded
                     to mcp.add_tool (defense-in-depth against key injection).

    Raises:
        ValueError: If name violates namespace rules for the given source.
    """
    _validate_name(name, source)

    # Build the merged meta dict. _source is the v1.0 contract (Phase 2);
    # forge-bridge/* keys are the v1.2 PROV-02 contract layered on top.
    merged_meta: dict[str, Any] = {"_source": source}
    if provenance is not None:
        # Defense-in-depth (WR-01): enforce PROV-03 size budget at the write
        # boundary, regardless of whether the watcher already ran it. A non-
        # watcher caller (plugin, test, future synthesizer shortcut) cannot
        # push unbounded meta bytes or tag counts onto the MCP wire this way.
        # Per-tag content sanitization (_sanitize_tag) is NOT re-applied here
        # because the watcher already sanitized and prepended the literal
        # "synthesized" filter tag — re-running it would redact that literal.
        # Content sanitization is the caller's contract at READ time; the
        # write boundary enforces only size/shape.
        budgeted = apply_size_budget({
            "tags": provenance.get("tags") or [],
            "meta": provenance.get("meta") or {},
        })
        prov_meta = budgeted["meta"]
        for k, v in prov_meta.items():
            if k.startswith("forge-bridge/"):
                merged_meta[k] = v
        tags = budgeted["tags"]
        if tags:
            merged_meta["forge-bridge/tags"] = list(tags)

    # PROV-04 safety baseline: every synthesized tool gets readOnlyHint=False
    # unless the caller explicitly set it. Synthesized tools call
    # bridge.execute() which runs arbitrary Python inside Flame — MCP clients
    # MUST NOT auto-approve them. Builtin tools keep their original hints.
    effective_annotations: dict[str, Any] | None
    if annotations is not None:
        effective_annotations = dict(annotations)
    else:
        effective_annotations = None
    if source == "synthesized":
        if effective_annotations is None:
            effective_annotations = {}
        effective_annotations.setdefault("readOnlyHint", False)

    mcp.add_tool(
        fn,
        name=name,
        annotations=effective_annotations,
        meta=merged_meta,
    )


def register_tools(
    mcp: FastMCP,
    fns: list[Callable[..., Any]],
    prefix: str = "",
    source: str = "user-taught",
) -> None:
    """Register multiple tools under a shared prefix and source tag.

    Public API for downstream consumers (e.g. projekt-forge).

    Usage (before mcp.run()):
        from forge_bridge.mcp import register_tools, get_mcp
        register_tools(get_mcp(), [my_fn1, my_fn2], prefix="forge_")

    Note: Must be called before mcp.run(). Tools registered after run() will
    not appear in the client's tool list until the client reconnects (no
    ToolListChangedNotification is sent by this function).

    Raises:
        RuntimeError: If called after mcp.run() has started. All tool
                      registration must happen before the server starts.

    Args:
        mcp:    The live FastMCP instance.
        fns:    List of callables to register.
        prefix: Prefix prepended to each fn.__name__ to form the tool name.
        source: Source tag for all tools in this batch.
    """
    # Lazy import avoids the server.py -> registry.py -> server.py cycle.
    # Accessing _server_started through the module captures the *current*
    # value, not a stale snapshot (see RESEARCH.md R-5).
    import forge_bridge.mcp.server as _server
    if _server._server_started:
        raise RuntimeError(
            "register_tools() cannot be called after the MCP server has started. "
            "Register all tools before calling mcp.run()."
        )

    for fn in fns:
        name = f"{prefix}{fn.__name__}" if prefix else fn.__name__
        register_tool(mcp, fn, name=name, source=source)


async def invoke_tool(name: str, args: dict) -> str:
    """Default tool executor for LLMRouter.complete_with_tools (FB-C LLMTOOL).

    Looks up `name` against the live FastMCP tool registry (the canonical
    singleton owned by forge_bridge.mcp.server.mcp), invokes it with `args`,
    and returns the result as a string.

    Per FB-C D-20: signature is async (tool_name: str, args: dict) -> str.
    Per FB-C D-21: this function is the DEFAULT executor when the caller of
    complete_with_tools(...) does not pass `tool_executor=...`. The coordinator
    lazy-imports it via:

        if tool_executor is None:
            from forge_bridge.mcp.registry import invoke_tool
            tool_executor = invoke_tool

    The coordinator is responsible for:
      - Sanitizing the returned string via _sanitize_tool_result (plan 15-04).
      - Truncating to _TOOL_RESULT_MAX_BYTES (plan 15-04).
      - Wrapping any exception this function raises as is_error=True
        ToolCallResult (per LLMTOOL-03 acceptance — the coordinator catches
        Exception, surfaces back to the LLM, loop continues).

    Args:
        name: Tool name (must match a registered MCP tool — flame_*, forge_*,
              or synth_* per registry namespace rules).
        args: Tool arguments dict (JSON-shaped).

    Returns:
        Tool result as a string. Result-shape handling:
          - String result → returned verbatim.
          - Dict / list result → returned as json.dumps(result, default=str).
          - FastMCP ContentBlock list (the actual call_tool return type) →
            joined text from each text-typed block.
          - Other types → str(result).

    Raises:
        KeyError: If `name` is not a registered tool. Message includes the
                  attempted name + a sorted list of available tools so the
                  coordinator can surface the hallucinated-tool-name structured
                  error to the LLM per research §4.3.
        Exception: Tool-internal exceptions propagate unmodified to the caller.
                   The coordinator wraps them as is_error=True ToolCallResult
                   (LLMTOOL-03 acceptance — one bad tool does not abort the
                   session).
    """
    # Lazy import — same anti-cycle pattern as register_tools (line 165).
    # Accessing the FastMCP singleton through the module captures the *current*
    # value, not a stale snapshot.
    import forge_bridge.mcp.server as _server
    mcp = _server.mcp

    # Hallucinated-name detection — KeyError with available-tools hint per
    # research §4.3. Use list_tools() (the public FastMCP API) rather than
    # poking _tool_manager._tools directly.
    available = await mcp.list_tools()
    available_names = sorted(t.name for t in available)
    if name not in available_names:
        raise KeyError(
            f"tool {name!r} is not registered. "
            f"Available tools: {', '.join(available_names) or '(none)'}"
        )

    # Invoke via the public FastMCP API. call_tool returns list[ContentBlock]
    # per the MCP protocol — for text-typed tools (forge-bridge's surface)
    # the first block's .text attribute carries the result.
    raw = await mcp.call_tool(name, arguments=args)

    return _stringify_tool_result(raw)


def _stringify_tool_result(raw: Any) -> str:
    """Coerce a FastMCP call_tool return value into a string.

    Handles four shapes the FastMCP protocol may produce:
      1. list of ContentBlock with .text — concatenate the text fields.
      2. plain str — return verbatim.
      3. dict / list — json.dumps with default=str (handles non-JSON-serializable
         values like UUIDs and datetimes via their str() representation).
      4. anything else — str(raw).

    Coordinator (plan 15-08) sanitizes + truncates the returned string via
    _sanitize_tool_result before feeding back to the LLM.
    """
    # Case 1: FastMCP list[ContentBlock] (the canonical call_tool return type).
    if isinstance(raw, list):
        # Inspect first element shape to disambiguate from a tool that
        # legitimately returned a list (e.g., list of shot ids).
        if raw and hasattr(raw[0], "text"):
            return "".join(getattr(block, "text", "") or "" for block in raw)
        # Plain list returned by the tool — JSON-stringify.
        return json.dumps(raw, default=str)

    # Case 2: plain string.
    if isinstance(raw, str):
        return raw

    # Case 3: dict.
    if isinstance(raw, dict):
        return json.dumps(raw, default=str)

    # Case 4: fallback.
    return str(raw)


def register_builtins(mcp: FastMCP) -> None:
    """Register all builtin flame_* and forge_* tools.

    This function is called by server.py at import time and routes every
    builtin tool registration through register_tool(), enforcing namespace
    rules and attaching source='builtin' metadata to all tools.
    """

    # ── forge-bridge tools (pipeline state) ──────────────────────
    from forge_bridge.mcp import tools

    register_tool(
        mcp, tools.ping,
        name="forge_ping",
        source="builtin",
        annotations={
            "title": "Check forge-bridge connection",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.list_projects,
        name="forge_list_projects",
        source="builtin",
        annotations={
            "title": "List all pipeline projects",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_project,
        name="forge_get_project",
        source="builtin",
        annotations={
            "title": "Get project details",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.create_project,
        name="forge_create_project",
        source="builtin",
        annotations={
            "title": "Create a new project",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
        },
    )

    register_tool(
        mcp, tools.list_shots,
        name="forge_list_shots",
        source="builtin",
        annotations={
            "title": "List shots in a project",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_shot,
        name="forge_get_shot",
        source="builtin",
        annotations={
            "title": "Get shot details with stack",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.create_shot,
        name="forge_create_shot",
        source="builtin",
        annotations={
            "title": "Create a shot with stack and layers",
            "readOnlyHint": False,
            "idempotentHint": False,
        },
    )

    register_tool(
        mcp, tools.update_shot_status,
        name="forge_update_shot_status",
        source="builtin",
        annotations={
            "title": "Update shot status",
            "readOnlyHint": False,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.list_versions,
        name="forge_list_versions",
        source="builtin",
        annotations={
            "title": "List versions for a shot",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_shot_stack,
        name="forge_get_shot_stack",
        source="builtin",
        annotations={
            "title": "Get all layers in a shot's stack",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_dependents,
        name="forge_get_dependents",
        source="builtin",
        annotations={
            "title": "Get entities that depend on this one",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.list_roles,
        name="forge_list_roles",
        source="builtin",
        annotations={
            "title": "List all registered roles",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_events,
        name="forge_get_events",
        source="builtin",
        annotations={
            "title": "Get recent pipeline events",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    # ── Forge publish workflow tools ──────────────────────────────

    register_tool(
        mcp, tools.check_shots,
        name="forge_check_shots",
        source="builtin",
        annotations={
            "title": "Pre-publish preflight — check if shots exist",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.register_publish,
        name="forge_register_publish",
        source="builtin",
        annotations={
            "title": "Register a published component in forge-bridge",
            "readOnlyHint": False,
        },
    )

    register_tool(
        mcp, tools.snapshot_timeline,
        name="flame_snapshot_timeline",
        source="builtin",
        annotations={
            "title": "Snapshot Flame timeline — all sequences and segments",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.list_published_plates,
        name="forge_list_published_plates",
        source="builtin",
        annotations={
            "title": "List published video plates from the forge-bridge registry",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_shot_versions,
        name="forge_get_shot_versions",
        source="builtin",
        annotations={
            "title": "Get all published plate versions for a specific shot",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.get_shot_lineage,
        name="forge_get_shot_lineage",
        source="builtin",
        annotations={
            "title": "Get full publish lineage for a shot — versions, media, verification status",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.blast_radius,
        name="forge_blast_radius",
        source="builtin",
        annotations={
            "title": "Find what depends on a media entity — impact analysis for republishes",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    register_tool(
        mcp, tools.list_media,
        name="forge_list_media",
        source="builtin",
        annotations={
            "title": "List media entities with status filter — find unverified or failed plates",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    # ── Flame HTTP bridge tools ───────────────────────────────────

    try:
        from forge_bridge.tools import project as flame_project
        from forge_bridge.tools import timeline as flame_timeline
        from forge_bridge.tools import batch as flame_batch
        from forge_bridge.tools import utility as flame_utility
        from forge_bridge.tools import publish as flame_publish
        from forge_bridge.tools import reconform as flame_reconform
        from forge_bridge.tools import switch_grade as flame_switch_grade_mod

        # ── Project & Workspace ──────────────────────────────────

        register_tool(mcp, flame_utility.ping, name="flame_ping", source="builtin",
                      annotations={"readOnlyHint": True})

        register_tool(mcp, flame_project.get_project, name="flame_get_project", source="builtin",
                      annotations={"readOnlyHint": True})

        register_tool(mcp, flame_project.list_libraries, name="flame_list_libraries", source="builtin",
                      annotations={"readOnlyHint": True})

        register_tool(mcp, flame_project.list_desktop, name="flame_list_desktop", source="builtin",
                      annotations={"readOnlyHint": True})

        register_tool(mcp, flame_project.find_media, name="flame_find_media", source="builtin",
                      annotations={"readOnlyHint": True})

        register_tool(
            mcp, flame_project.get_context,
            name="flame_context",
            source="builtin",
            annotations={
                "title": "Get current Flame context — project, workspace, desktop, all reel contents",
                "readOnlyHint": True,
                "idempotentHint": True,
            },
        )

        # ── Timeline ─────────────────────────────────────────────

        register_tool(
            mcp, flame_timeline.get_sequence_segments,
            name="flame_get_sequence_segments",
            source="builtin",
            annotations={"title": "Get all segments with FORGE metadata", "readOnlyHint": True},
        )

        register_tool(
            mcp, flame_timeline.preview_rename,
            name="flame_preview_rename",
            source="builtin",
            annotations={"title": "Preview rename without changes", "readOnlyHint": True, "idempotentHint": True},
        )

        register_tool(
            mcp, flame_timeline.rename_shots,
            name="flame_rename_shots",
            source="builtin",
            annotations={"title": "Rename shots and segments on a sequence", "readOnlyHint": False},
        )

        register_tool(
            mcp, flame_timeline.preview_start_frames,
            name="flame_preview_start_frames",
            source="builtin",
            annotations={"title": "Preview start frame assignments", "readOnlyHint": True, "idempotentHint": True},
        )

        register_tool(
            mcp, flame_timeline.set_start_frames,
            name="flame_set_start_frames",
            source="builtin",
            annotations={"title": "Set composite start frames on a sequence", "readOnlyHint": False},
        )

        register_tool(
            mcp, flame_timeline.set_segment_attribute,
            name="flame_set_segment_attribute",
            source="builtin",
            annotations={"title": "Set an attribute on a single segment", "readOnlyHint": False},
        )

        register_tool(
            mcp, flame_timeline.disconnect_segments,
            name="flame_disconnect_segments",
            source="builtin",
            annotations={
                "title": "Disconnect Segments from Source Media",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.inspect_sequence_versions,
            name="flame_inspect_sequence_versions",
            source="builtin",
            annotations={
                "title": "Inspect Sequence Versions",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.create_version,
            name="flame_create_version",
            source="builtin",
            annotations={
                "title": "Create Sequence Version",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.reconstruct_track,
            name="flame_reconstruct_track",
            source="builtin",
            annotations={
                "title": "Reconstruct Track from Segments",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.clone_version,
            name="flame_clone_version",
            source="builtin",
            annotations={
                "title": "Clone Sequence Version",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.replace_segment_media,
            name="flame_replace_segment_media",
            source="builtin",
            annotations={
                "title": "Replace Segment Media",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.scan_roles,
            name="flame_scan_roles",
            source="builtin",
            annotations={
                "title": "Scan Track Roles",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_timeline.assign_roles,
            name="flame_assign_roles",
            source="builtin",
            annotations={
                "title": "Assign Roles to Tracks",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        # ── Batch ─────────────────────────────────────────────────

        register_tool(
            mcp, flame_batch.inspect_batch_xml,
            name="flame_inspect_batch_xml",
            source="builtin",
            annotations={
                "title": "Inspect Batch XML",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_batch.prune_batch_xml,
            name="flame_prune_batch_xml",
            source="builtin",
            annotations={
                "title": "Prune Batch XML",
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        # ── Reconform ─────────────────────────────────────────────

        register_tool(
            mcp, flame_reconform.reconform_sequence,
            name="flame_reconform_sequence",
            source="builtin",
            annotations={
                "title": "Reconform Sequence",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        )

        # ── Grade ─────────────────────────────────────────────────

        register_tool(
            mcp, flame_switch_grade_mod.switch_grade,
            name="flame_switch_grade",
            source="builtin",
            annotations={
                "title": "Switch Grade on Shot",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_switch_grade_mod.query_alternatives,
            name="flame_query_alternatives",
            source="builtin",
            annotations={
                "title": "Query Grade Alternatives",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        # ── Publish ───────────────────────────────────────────────

        register_tool(
            mcp, flame_publish.rename_segments,
            name="flame_rename_segments",
            source="builtin",
            annotations={
                "title": "Rename Segments on Sequence",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )

        register_tool(
            mcp, flame_publish.publish_sequence,
            name="flame_publish_sequence",
            source="builtin",
            annotations={
                "title": "Publish Sequence",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": True,
            },
        )

        register_tool(
            mcp, flame_publish.assemble_published_sequence,
            name="flame_assemble_published_sequence",
            source="builtin",
            annotations={
                "title": "Assemble Published Sequence",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        )

    except ImportError:
        import logging
        logging.getLogger(__name__).warning(
            "Flame HTTP bridge tools not available — forge_bridge.tools not found"
        )

    # ── LLM Resources ─────────────────────────────────────────────
    from forge_bridge.llm.health import register_llm_resources
    register_llm_resources(mcp)
