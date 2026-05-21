"""forge-bridge chat — testable CLI surface over the blessed `/api/v1/chat`.

Sends a single user message to ``http://<console_host>:<console_port>/api/v1/chat``
(the same endpoint the Artist Console UI uses) and renders the timeout /
retry / response-timing messaging from ``llm.call_wrapper``.

The terminal step's operator-meaningful output IS the chat answer.
Prior chain steps are execution plumbing. The CLI render layer
exists to surface the terminal step's operator-meaningful output
in the form most useful to the operator, not to expose execution
structure.

This is *not* a parallel chat path — it consumes the same shared endpoint
and therefore benefits from any improvements made there.
"""
from __future__ import annotations

import json
import sys
from typing import Annotated, Optional

import typer

from forge_bridge import config
from forge_bridge.llm import call_wrapper

# Exit codes
_EXIT_OK = 0
_EXIT_FAIL = 1
_EXIT_UNREACHABLE = 2
_EXIT_TIMEOUT = 3

_KIND_TO_EXIT = {
    "connection": _EXIT_UNREACHABLE,
    "timeout": _EXIT_TIMEOUT,
    "invalid_response": _EXIT_FAIL,
}
_FORMAT_RESULT_EGRESS_WARNING = (
    "format_result sends condensed data to Anthropic cloud model. "
    "Ensure ANTHROPIC_API_KEY is set and data-egress policy permits."
)
_warned_egress = False


def chat_cmd(
    message: Annotated[
        str,
        typer.Argument(help="Message to send to the LLM."),
    ],
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Per-request timeout in seconds."),
    ] = call_wrapper.DEFAULT_TIMEOUT_SECONDS,
    retries: Annotated[
        int,
        typer.Option("--retries", help="Automatic retries on timeout (0 = none)."),
    ] = call_wrapper.DEFAULT_RETRIES,
    backoff: Annotated[
        float,
        typer.Option("--backoff", help="Seconds to wait before each retry."),
    ] = call_wrapper.DEFAULT_BACKOFF_SECONDS,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help=(
                "Dump full chain JSON after completion. "
                "For debugging chain composition or step output."
            ),
        ),
    ] = False,
    trace: Annotated[
        bool,
        typer.Option(
            "--trace",
            help=(
                "Show per-step summaries during chain execution. "
                "For monitoring long-running chains. Output to stderr."
            ),
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress messages."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit a stable JSON envelope to stdout."),
    ] = False,
) -> None:
    """Send a message to the chat endpoint with timeout + retry usability."""
    url = f"{config.console_url()}/api/v1/chat"
    payload = {"messages": [{"role": "user", "content": message}]}

    # P-01 stdout purity: default chat output is the operator answer only.
    # Retry/progress chatter would corrupt pipe targets such as formatted CSV.
    reporter = None

    result = call_wrapper.call_with_retry(
        url, payload,
        timeout=timeout, retries=retries, backoff_seconds=backoff,
        reporter=reporter,
    )

    if as_json:
        sys.stdout.write(
            json.dumps({
                "ok": result.ok,
                "data": result.data,
                "error": None if result.ok else {
                    "kind": result.error_kind,
                    "message": result.error_message,
                    "fix": result.fix,
                },
                "attempts": result.attempts,
                "elapsed_seconds": round(result.elapsed_seconds, 3),
                "timeline": result.timeline,
                "trace": result.trace,
            }) + "\n"
        )
        raise typer.Exit(
            code=_EXIT_OK if result.ok else _KIND_TO_EXIT.get(result.error_kind, _EXIT_FAIL)
        )

    if not result.ok:
        if trace:
            _write_trace_block(result.trace)
            meta = _extract_metadata(result.data)
            sys.stderr.write(
                f"[chat] FAILED kind={result.error_kind}  "
                f"elapsed={result.elapsed_seconds:.2f}s  "
                f"attempts={result.attempts}/{retries + 1}  "
                f"model={meta.get('model', '?')}  "
                f"tools={_format_tools(meta, result)}\n"
            )
        sys.stderr.write(
            f"forge-bridge chat: {result.error_kind}: {result.error_message}\n"
        )
        if result.fix:
            sys.stderr.write(f"fix: {result.fix}\n")
        raise typer.Exit(code=_KIND_TO_EXIT.get(result.error_kind, _EXIT_FAIL))

    if verbose:
        if trace:
            _write_chain_trace(result.data)
            _write_trace_block(result.trace)
        sys.stdout.write(
            json.dumps(result.data, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        raise typer.Exit(code=_EXIT_OK)

    # Phase 24.5: orchestration_terminated is its own consumer taxon.
    # Detect BEFORE _extract_reply runs — otherwise the K-th tool
    # result's content gets rendered as if the model authored it, which
    # is the consumer-side analog of the impersonation 24.4 ruled out at
    # the orchestrator (framing §10.1 item 9). The termination IS the
    # result of this chat call; render the envelope verbatim per the
    # §4 contract (provenance / trigger / reason / iterations /
    # accumulated_results) without paraphrase or synthesis.
    if _is_orchestration_terminated(result.data):
        _render_orchestration_terminated(result.data, trace, retries, result)
        raise typer.Exit(code=_EXIT_OK)

    if trace:
        _write_chain_trace(result.data)
        _write_trace_block(result.trace)
    output = _render_operator_output(result.data)
    sys.stdout.write(output + ("\n" if output and not output.endswith("\n") else ""))


def _render_operator_output(data: Optional[dict]) -> str:
    """Project chat data into the operator-facing default stdout surface."""
    if _is_chain_envelope(data):
        assert isinstance(data, dict)
        if data.get("status") == "error":
            return _render_structured_error(data.get("error"))
        chain = data.get("chain")
        if not isinstance(chain, list) or not chain:
            return ""
        for entry in chain:
            if not isinstance(entry, dict):
                continue
            error = entry.get("error")
            if error:
                return _render_structured_error(error)
            result = entry.get("result")
            if isinstance(result, dict) and _looks_like_structured_error(result):
                return _render_structured_error(result)
            if entry.get("status") == "error":
                return _render_structured_error(entry)
        terminal = chain[-1] if isinstance(chain[-1], dict) else {}
        output = _project_terminal_result(
            terminal.get("result"),
            is_format_result=terminal.get("tool") == "format_result",
        )
        return output

    if isinstance(data, dict) and data.get("status") == "error":
        return _render_structured_error(data.get("error"))

    reply = _extract_reply(data)
    if reply is not None:
        return reply

    return _project_terminal_result(data, is_format_result=False)


def _project_terminal_result(value: object, *, is_format_result: bool) -> str:
    if is_format_result:
        _write_format_result_egress_warning_once()
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if _looks_like_structured_error(value):
            return _render_structured_error(value)
        if _looks_like_mutation_result(value):
            return _render_mutation_result(value)
        collection_key, collection = _find_collection(value)
        if collection_key and collection is not None:
            return _render_enumeration(collection)
        return _render_inspection(value)
    if isinstance(value, list):
        return _render_enumeration(value)
    if value is None:
        return ""
    return str(value)


def _write_format_result_egress_warning_once() -> None:
    global _warned_egress
    if _warned_egress:
        return
    _warned_egress = True
    sys.stderr.write(_FORMAT_RESULT_EGRESS_WARNING + "\n")


def _looks_like_structured_error(value: dict) -> bool:
    return any(key in value for key in ("error", "code", "message", "type")) and (
        "error" in value or "original_error" in value or value.get("status") == "error"
    )


def _render_structured_error(error: object) -> str:
    if not isinstance(error, dict):
        return f"Error: {error}"
    original = error.get("original_error")
    if isinstance(original, dict):
        error = original
    code = error.get("code") or error.get("type") or error.get("error") or "unknown_error"
    message = error.get("message") or error.get("detail") or error.get("reason")
    lines = [f"Error: {code}"]
    if message:
        lines.append(str(message))
    details = error.get("details")
    if isinstance(details, dict):
        advice = details.get("message") or details.get("advice")
        if advice and advice != message:
            lines.append(str(advice))
    return "\n".join(lines)


def _looks_like_mutation_result(value: dict) -> bool:
    mutation_keys = {
        "renamed",
        "skipped",
        "applied",
        "errors",
        "shots_assigned",
        "propagated",
        "deleted",
        "disconnected",
        "opened",
        "dry_run",
        "proposed_changes",
    }
    return bool(mutation_keys & set(value))


def _render_mutation_result(value: dict) -> str:
    preferred = [
        "renamed",
        "skipped",
        "applied",
        "errors",
        "shots_assigned",
        "propagated",
        "deleted",
        "disconnected",
        "opened",
        "count",
    ]
    parts = []
    for key in preferred:
        item = value.get(key)
        if isinstance(item, (int, float, str)) and not isinstance(item, bool):
            parts.append(f"{key}={item}")
        elif isinstance(item, list):
            parts.append(f"{key}={len(item)}")
    lines = [" ".join(parts) if parts else _render_inspection(value)]
    changes = value.get("changes") or value.get("proposed_changes")
    if isinstance(changes, list) and changes:
        names = [
            _first_string(change, ("new", "proposed", "shot_name", "name"))
            for change in changes
            if isinstance(change, dict)
        ]
        names = [name for name in names if name]
        if names:
            lines.append(f"{names[0]} ... {names[-1]}" if len(names) > 1 else names[0])
    return "\n".join(lines)


def _find_collection(value: dict) -> tuple[str | None, list | None]:
    for key in (
        "segments",
        "clips",
        "reels",
        "items",
        "iterations",
        "nodes",
        "projects",
        "shots",
        "versions",
        "results",
    ):
        item = value.get(key)
        if isinstance(item, list):
            return key, item
    return None, None


def _render_enumeration(items: list) -> str:
    lines = []
    for item in items:
        if isinstance(item, dict):
            lines.append(_render_enumeration_item(item))
        else:
            lines.append(str(item))
    return "\n".join(lines)


def _render_enumeration_item(item: dict) -> str:
    name = _first_string(
        item,
        ("name", "sequence", "sequence_name", "shot_name", "seg_name", "source_name", "node_name"),
    ) or "(unnamed)"
    fields = []
    type_value = item.get("type") or item.get("role")
    if type_value:
        fields.append(str(type_value))
    duration = item.get("duration")
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        fields.append(f"{duration:g} frames")
    if isinstance(item.get("track_count"), int):
        fields.append(f"{item['track_count']} tracks")
    elif isinstance(item.get("track_idx"), int):
        fields.append(f"track {item['track_idx']}")
    if isinstance(item.get("is_open"), bool):
        fields.append("open" if item["is_open"] else "closed")
    return f"{name}  ({', '.join(fields)})" if fields else name


def _render_inspection(value: dict) -> str:
    lines = []
    for key, item in value.items():
        if str(key).startswith("_"):
            continue
        lines.append(f"{key:<12} {_format_scalar_for_operator(item)}")
    return "\n".join(lines)


def _format_scalar_for_operator(value: object) -> str:
    if isinstance(value, dict):
        return f"{len(value)} fields"
    if isinstance(value, list):
        return f"{len(value)} items"
    return str(value)


def _first_string(mapping: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _is_chain_envelope(data: object) -> bool:
    return isinstance(data, dict) and isinstance(data.get("chain"), list) and "status" in data


def _write_chain_trace(data: Optional[dict]) -> None:
    if not _is_chain_envelope(data):
        return
    assert isinstance(data, dict)
    chain = data.get("chain") or []
    total = len(chain)
    for index, entry in enumerate(chain, start=1):
        if not isinstance(entry, dict):
            continue
        rendered = _maybe_render_foreach_step(entry, index, total)
        if rendered is not None:
            sys.stderr.write(rendered + "\n")
            continue
        rendered = _maybe_render_gate_step(entry, index, total)
        if rendered is not None:
            sys.stderr.write(rendered + "\n")
            continue
        label = _trace_step_label(str(entry.get("step") or ""), entry.get("result"))
        summary = _brief_result_summary(entry.get("result"))
        sys.stderr.write(f"[{index}/{total}] {label} → {summary}\n")


def _maybe_render_foreach_step(entry: dict, index: int, total: int) -> str | None:
    from forge_bridge.graph import is_foreach_step

    step = str(entry.get("step") or "")
    if not is_foreach_step(step):
        return None

    result = entry.get("result")
    if not isinstance(result, dict):
        return None

    iterations = result.get("iterations")
    if not isinstance(iterations, list):
        return None

    foreach_meta = result.get("foreach")
    body_step = ""
    if isinstance(foreach_meta, dict):
        body = foreach_meta.get("body")
        if isinstance(body, str):
            body_step = body

    parent = f"[{index}/{total}] {step.strip()} → {len(iterations)} iterations"
    lines = [parent]
    for iteration in iterations:
        if not isinstance(iteration, dict):
            continue
        iteration_index = iteration.get("index")
        iteration_result = iteration.get("result")
        label = _trace_step_label(body_step, iteration_result)
        summary = _brief_result_summary(iteration_result)
        lines.append(f"  [{index}.{iteration_index}] {label} → {summary}")
    return "\n".join(lines)


def _maybe_render_gate_step(entry: dict, index: int, total: int) -> str | None:
    result = entry.get("result")
    if not isinstance(result, dict):
        return None

    if "skipped_step" in result:
        label = _trace_step_label(str(entry.get("step") or ""), result)
        return f"[{index}/{total}] {label} → suppressed by upstream gate"

    gate = result.get("if_gate")
    step = str(entry.get("step") or "")
    if isinstance(gate, dict) and step.lstrip().lower().startswith("if"):
        predicate = gate.get("predicate")
        predicate_echo = _format_if_predicate(predicate if isinstance(predicate, dict) else {})
        decision = (
            "matched (gate open)"
            if gate.get("matched")
            else "unmatched (gate closed)"
        )
        return f"[{index}/{total}] {predicate_echo} → {decision}"

    return None


def _format_if_predicate(predicate: dict) -> str:
    field = str(predicate.get("field") or "predicate")
    operator = predicate.get("operator")
    value = predicate.get("value")
    if operator and value is not None:
        return f"if({field} {operator} {value})"
    if operator:
        return f"if({field} {operator})"
    return f"if({field})"


def _trace_step_label(step: str, result: object) -> str:
    lowered = step.lower()
    if "filter" in lowered or lowered.startswith("where") or lowered.startswith("only"):
        return step.strip()
    if "format" in lowered:
        for name in ("table", "email", "bullets", "bullet list"):
            if name in lowered:
                return f"format {name.replace('bullet list', 'bullets')}"
        return "format"
    if "rename" in lowered:
        return "rename shots"
    if "segment" in lowered:
        return "get sequence segments"
    if isinstance(result, dict):
        key, _ = _find_collection(result)
        if key:
            return f"get {key}"
    return step.strip() or "step"


def _brief_result_summary(value: object) -> str:
    if isinstance(value, str):
        return "rendered"
    if isinstance(value, dict):
        if _looks_like_mutation_result(value):
            keys = [
                f"{key}={value[key]}"
                for key in ("renamed", "skipped", "applied", "count")
                if isinstance(value.get(key), int)
            ]
            return " ".join(keys) if keys else "mutation result"
        key, collection = _find_collection(value)
        if collection is not None:
            before = value.get("_input_count")
            after = len(collection)
            if isinstance(before, int):
                return f"{before} → {after} items"
            suffix = ""
            frame_rate = value.get("frame_rate")
            if frame_rate:
                suffix = f" ({frame_rate})"
            return f"{after} {key}{suffix}"
    if isinstance(value, list):
        return f"{len(value)} items"
    return "done"


def _write_trace_block(trace: dict) -> None:
    """Render the structured trace as a short, ordered narrative on stderr.

    Reads only the trace shape produced by ``call_wrapper`` (PR11). No
    derivation from ``timeline``.
    """
    if not isinstance(trace, dict):
        return
    events = trace.get("events")
    if not isinstance(events, list) or not events:
        return
    lines = ["[trace]"]
    for ev in events:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        if kind == "attempt":
            n = ev.get("attempt", "?")
            res = ev.get("result", "?")
            dur = ev.get("duration", 0.0)
            lines.append(f"attempt {n} → {res} ({_fmt_seconds(dur)})")
        elif kind == "backoff":
            lines.append(f"backoff → {_fmt_seconds(ev.get('duration', 0.0))}")
        # summary is rendered as the closing total line below.
    total = trace.get("total_elapsed", 0.0)
    lines.append(f"total → {_fmt_seconds(total)}")
    sys.stderr.write("\n".join(lines) + "\n")


def _fmt_seconds(value: object) -> str:
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return "?s"


def _format_tools(meta: dict, result) -> str:
    """Render the verbose ``tools=N`` / ``tools=N (X.Ys)`` field.

    Prefer values reported by the chat endpoint (in ``meta``). For failure
    paths the response body is usually absent — fall back to the last attempt
    event's ``tool_calls`` / ``tool_duration``, which PR13-B sets to 0/None
    on skipped attempts so the operator sees ``tools=0`` instead of
    ``tools=?``. Elide the parenthesized duration when no measurement exists.
    """
    tool_calls = meta.get("tool_calls")
    tool_duration = meta.get("tool_duration")

    if tool_calls is None or tool_duration is None:
        events = (getattr(result, "trace", None) or {}).get("events") or []
        last_attempt = next(
            (e for e in reversed(events)
             if isinstance(e, dict) and e.get("kind") == "attempt"),
            None,
        )
        if isinstance(last_attempt, dict):
            if tool_calls is None:
                tc = last_attempt.get("tool_calls")
                if isinstance(tc, list):
                    tool_calls = len(tc)
                elif isinstance(tc, int):
                    tool_calls = tc
            if tool_duration is None:
                tool_duration = last_attempt.get("tool_duration")

    count = tool_calls if isinstance(tool_calls, int) else "?"
    if isinstance(tool_duration, (int, float)) and not isinstance(tool_duration, bool):
        return f"{count} ({float(tool_duration):.1f}s)"
    return f"{count}"


# ---------------------------------------------------------------------------
# Phase 24.5: orchestration_terminated consumer projection
#
# Both the detection (_is_orchestration_terminated) and the rendering
# (_render_orchestration_terminated) operate against the verbatim envelope
# emitted by forge_bridge/console/handlers.py:_build_orchestration_terminated_body
# (handlers.py:879-895). No paraphrase, no synthesis — the consumer is a
# projection of the envelope, not a re-author of its semantics.
#
# Discipline question used during implementation:
#   "Does this render preserve provenance?"
# If the answer becomes blurry, the consumer is drifting toward semantic
# impersonation (framing §10.1 item 9).
# ---------------------------------------------------------------------------

_ORCHESTRATION_TERMINATED_STOP_REASON = "orchestration_terminated"


def _is_orchestration_terminated(data: Optional[dict]) -> bool:
    """True if the envelope encodes an orchestrator-decided termination.

    Detected via the top-level ``stop_reason`` field, set by
    ``forge_bridge/console/handlers.py:_build_orchestration_terminated_body``.
    """
    if not isinstance(data, dict):
        return False
    return data.get("stop_reason") == _ORCHESTRATION_TERMINATED_STOP_REASON


def _render_orchestration_terminated(
    data: dict,
    trace: bool,
    retries: int,
    result,
) -> None:
    """Render the orchestration_terminated envelope as a structured block.

    Projects the consumer-contract five facts to stdout per Phase 24.5
    framing §4:

      1. Provenance (the ``[orchestration termination]`` taxon prefix)
      2. Trigger (``termination.trigger`` verbatim)
      3. Reason (``termination.reason`` verbatim — author at orchestrator)
      4. Iterations (``termination.iterations``)
      5. Accumulated results (full ordered list so operator sees the
         recurrence pattern; each entry shows tool_name + iter +
         args_hash + result_hash + content)

    Does NOT extract or paraphrase any ``content`` field as if it were
    the model's reply (framing §10.1 item 9).
    """
    term = data.get("termination") if isinstance(data, dict) else None
    if not isinstance(term, dict):
        term = {}

    trigger = term.get("trigger", "?")
    reason = term.get("reason", "(reason field absent)")
    iterations = term.get("iterations", "?")
    accumulated = term.get("accumulated_results")
    if not isinstance(accumulated, list):
        accumulated = []

    lines = [
        "[orchestration termination]",
        f"  trigger:     {trigger}",
        f"  reason:      {reason}",
        f"  iterations:  {iterations}",
    ]

    if accumulated:
        lines.append(f"  canonical results ({len(accumulated)} successful):")
        for i, entry in enumerate(accumulated, start=1):
            if not isinstance(entry, dict):
                lines.append(f"    {i}. <malformed entry>")
                continue
            tool_name = entry.get("tool_name", "?")
            iter_num = entry.get("iter", "?")
            args_hash = entry.get("args_hash", "?")
            result_hash = entry.get("result_hash", "?")
            content = entry.get("content", "")
            lines.append(f"    {i}. {tool_name} [iter={iter_num}]")
            lines.append(f"       args_hash:   {args_hash}")
            lines.append(f"       result_hash: {result_hash}")
            if isinstance(content, str) and content:
                content_lines = content.splitlines() or [content]
                lines.append("       content:")
                for cl in content_lines:
                    lines.append(f"         | {cl}")
            else:
                lines.append("       content:     (empty)")
    else:
        lines.append("  canonical results: (none)")

    sys.stdout.write("\n".join(lines) + "\n")

    if trace:
        _write_trace_block(result.trace)
        meta = _extract_metadata(data)
        sys.stderr.write(
            f"[chat] orchestration_terminated  "
            f"elapsed={result.elapsed_seconds:.2f}s  "
            f"attempts={result.attempts}/{retries + 1}  "
            f"model={meta.get('model', '?')}  "
            f"provider={meta.get('provider', '?')}  "
            f"tools={_format_tools(meta, result)}\n"
        )


def _extract_reply(data: Optional[dict]) -> str | None:
    """Pull a renderable text reply out of the chat response."""
    if not isinstance(data, dict):
        return None
    for key in ("response", "reply", "text", "content", "message"):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    messages = data.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, str):
                return content
    return None


def _extract_metadata(data: Optional[dict]) -> dict:
    if not isinstance(data, dict):
        return {}
    # PR10 verbose: surface tool_calls if the chat handler reports them.
    # PR13-B: also surface tool_duration; coerce tool_calls to a count or None.
    tool_calls = data.get("tool_calls")
    tool_duration = data.get("tool_duration")

    if isinstance(tool_calls, list):
        tool_calls = len(tool_calls)
    elif not isinstance(tool_calls, int):
        tool_calls = None

    return {
        "model": data.get("model"),
        "provider": data.get("provider") or data.get("backend"),
        "iterations": data.get("iterations"),
        "tool_calls": tool_calls,
        "tool_duration": tool_duration,
    }
