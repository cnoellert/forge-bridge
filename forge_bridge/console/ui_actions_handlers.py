"""/ui/actions/* — renderer #2 of the ``fbridge exec`` verb registry (web forms).

The CLI interactive shell was renderer #1; this is the same DATA (``cli/verbs.py``
``REGISTRY``) rendered as Console forms. Verb logic is NOT reimplemented here —
the delta builders, the trust-boundary ``parse_value``, the single canonical
``GraphSpec`` author (``_build_mutation_spec``), the no-assent preview
(``_preview_mutation``) and the stage producer
(``preview_editorial_delta_for_ratification``) are all reused from the CLI /
orchestration paths.

STAGE-ONLY (load-bearing): the browser PREVIEWS and STAGES a proposed
graph-intent only. It NEVER applies or mutates on click — there is no apply
endpoint here. Ratification stays the operator's act via the EXISTING CA.1
ratify affordance on the Chat view. This view ends at "staged → here is the
graph_intent_id, go ratify it".

Heavy imports (cli.interactive / orchestration / store) stay function-local so
this module imports cheaply and without the pipeline plugin installed — mirrors
the ui_handlers.py lazy-import contract.
"""
from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from forge_bridge.cli import verbs as _verbs

logger = logging.getLogger(__name__)

# ponytail: this renderer reaches into cli.interactive's PRIVATE, renderer-neutral
# helpers (_segments / _build_mutation_spec / _preview_mutation / _humanize) — they
# return DATA with zero Rich/print/prompt side-effects, so reuse is safe at n=2
# renderers (CLI + web). EXTRACTION TRIGGER: renderer #3. At that point lift those
# four into a renderer-neutral module (cli/verbs.py or a new composition/exec_core)
# and have all renderers import from there, so the neutral logic no longer lives
# inside one renderer (CLI). Not done now — premature for n=2.


def _verb_view(verb: Any) -> dict[str, Any]:
    """The renderer-facing projection of a Verb (no behaviour, just labels)."""
    return {
        "name": verb.name,
        "label": verb.label,
        "summary": verb.summary,
        "value_label": verb.value_label,
        "value_kind": verb.value_kind,
        # number input for numeric verbs — int AND offset (trim is a SIGNED
        # relative count: negatives extend, so NO min=0 for offset); text
        # otherwise (e.g. rename).
        "input_type": "number" if verb.value_kind in ("int", "offset") else "text",
    }


def _fragment_error(request: Request, message: str, status: int = 200) -> HTMLResponse:
    """De-blank guard for htmx fragment endpoints — an error-card, never blank.

    Status defaults to 200 so htmx still swaps the message into the target
    (htmx ignores 4xx/5xx bodies by default); validation rejects ride this path.
    """
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/error_fragment.html",
        {"message": message},
        status_code=status,
    )


def _page_error(request: Request, message: str, status: int) -> HTMLResponse:
    """Full-page de-blank guard (extends shell.html → keeps the health-strip)."""
    return request.app.state.templates.TemplateResponse(
        request,
        "errors/not_found.html",
        {"message": message, "active_view": "actions"},
        status_code=status,
    )


# -- Full-page views ---------------------------------------------------------

async def ui_actions_index_handler(request: Request) -> HTMLResponse:
    """GET /ui/actions — the verb roster as cards (renderer of REGISTRY)."""
    verbs = [_verb_view(v) for v in _verbs.list_verbs()]
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/list.html",
        {"active_view": "actions", "verbs": verbs},
    )


async def ui_actions_form_handler(request: Request) -> HTMLResponse:
    """GET /ui/actions/{verb} — the form for one verb (sequence → segment → value)."""
    name = request.path_params["verb"]
    verb = _verbs.REGISTRY.get(name)
    if verb is None:
        return _page_error(request, f"No action named {name!r}.", 404)
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/form.html",
        {"active_view": "actions", "verb": _verb_view(verb)},
    )


# -- htmx fragments ----------------------------------------------------------

async def ui_actions_segments_fragment(request: Request) -> HTMLResponse:
    """GET /ui/fragments/actions-segments?verb=&sequence= — the live segment picker.

    Fetches the live timeline exactly as the CLI does (``_segments`` →
    ``flame_get_sequence_segments``). Degrades gracefully: an unreachable
    daemon/Flame or an empty timeline renders a clear message, never a blank.
    """
    name = request.query_params.get("verb", "")
    sequence = (request.query_params.get("sequence") or "").strip()
    verb = _verbs.REGISTRY.get(name)
    if verb is None:
        return _fragment_error(request, "Unknown action.")
    if not sequence:
        return _fragment_error(request, "Enter a sequence name first.")
    try:
        from forge_bridge.cli.interactive import _segments
        segs = await _segments(sequence)
    except Exception as exc:  # noqa: BLE001 — degrade, never blank/traceback
        logger.warning(
            "ui_actions_segments_fragment fetch failed: %s",
            type(exc).__name__, exc_info=True,
        )
        return _fragment_error(
            request,
            f"Could not reach the live timeline for {sequence!r} — "
            "is the sequence open in Flame and the daemon running?",
        )
    if not segs:
        return _fragment_error(
            request,
            f"No segments found on {sequence!r}. Open the sequence in Flame, then reload.",
        )
    rows = [
        {
            "index": i,
            "seg_name": s.get("seg_name"),
            "track_idx": s.get("track_idx"),
            "current": s.get(verb.current_key),
        }
        for i, s in enumerate(segs, 1)
    ]
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/segments.html",
        {"verb": _verb_view(verb), "sequence": sequence, "segments": rows},
    )


async def _resolve_target(
    request: Request, verb: Any, form: Any
) -> tuple[dict[str, Any] | None, HTMLResponse | None]:
    """Shared validation for preview + stage — one trust boundary, no dup logic.

    Re-fetches the live timeline (same as the CLI) and indexes the picked
    segment, then parses the value through ``verbs.parse_value``. Returns
    ``(payload, None)`` on success or ``(None, error_fragment)``.
    """
    sequence = (form.get("sequence") or "").strip()
    seg_index_raw = (form.get("segment_index") or "").strip()
    value_raw = form.get("value")
    if not sequence:
        return None, _fragment_error(request, "Sequence is required.")
    try:
        idx = int(seg_index_raw)
    except (TypeError, ValueError):
        return None, _fragment_error(request, "Pick a segment.")
    try:
        from forge_bridge.cli.interactive import _segments
        segs = await _segments(sequence)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_resolve_target segment fetch failed: %s",
            type(exc).__name__, exc_info=True,
        )
        return None, _fragment_error(
            request,
            f"Could not reach the live timeline for {sequence!r} — is Flame open?",
        )
    if not (1 <= idx <= len(segs)):
        return None, _fragment_error(
            request, "That segment is no longer on the timeline — reload the picker."
        )
    seg = segs[idx - 1]
    value, perr = _verbs.parse_value(verb, value_raw or "")
    if perr is not None:
        return None, _fragment_error(request, perr, status=400)
    current = seg.get(verb.current_key)
    if _verbs.is_unchanged(verb, value, current):
        return None, _fragment_error(request, "Value unchanged — nothing to do.", status=400)
    # Trim verbs: host-side range guard AFTER the value parses and the segment is
    # resolved, BEFORE staging anything. Surfaces the plain-language reason exactly
    # like a parse error (no-op for non-trim verbs — validate_trim returns None).
    trim_reason = _verbs.validate_trim(verb, value, seg)
    if trim_reason is not None:
        return None, _fragment_error(request, trim_reason, status=400)
    return (
        {"sequence": sequence, "seg": seg, "index": idx, "value": value, "current": current},
        None,
    )


async def ui_actions_preview_handler(request: Request) -> HTMLResponse:
    """POST /ui/actions/{verb}/preview — domain-language preview (NO assent, NO apply)."""
    name = request.path_params["verb"]
    verb = _verbs.REGISTRY.get(name)
    if verb is None:
        return _fragment_error(request, "Unknown action.")
    form = await request.form()
    payload, err = await _resolve_target(request, verb, form)
    if err is not None:
        return err
    assert payload is not None
    try:
        from forge_bridge.cli.interactive import _humanize, _preview_mutation
        held, perr = await _preview_mutation(
            verb, payload["sequence"], payload["seg"], {verb.value_field: payload["value"]}
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ui_actions_preview_handler preview failed: %s",
            type(exc).__name__, exc_info=True,
        )
        return _fragment_error(
            request, "Preview failed — the engine could not resolve this change."
        )
    if perr is not None:
        return _fragment_error(request, f"Can't do that — {_humanize(perr[1])}", status=400)
    plan = held.get("resolved_plan") or []
    # artist-legible one-liner; offset verbs never leak an absolute frame.
    change_summary = _verbs.describe_change(verb, payload["current"], payload["value"])
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/preview.html",
        {
            "verb": _verb_view(verb),
            "sequence": payload["sequence"],
            "segment_index": payload["index"],
            "seg_name": payload["seg"].get("seg_name"),
            "current": payload["current"],
            "new_value": payload["value"],
            "change_summary": change_summary,
            "plan_count": len(plan),
            # raw value carried verbatim so Stage re-runs the exact same path
            "value_raw": form.get("value") or "",
        },
    )


async def ui_actions_stage_handler(request: Request) -> HTMLResponse:
    """POST /ui/actions/{verb}/stage — persist a PROPOSED graph-intent for ratification.

    Reuses the single canonical spec author (``_build_mutation_spec``) and the
    proven stage producer (``preview_editorial_delta_for_ratification``). NO
    apply, NO assent — assent stays the ratifier's act on the Chat view's CA.1
    affordance. Returns the ``graph_intent_id`` and the ratify handoff.
    """
    name = request.path_params["verb"]
    verb = _verbs.REGISTRY.get(name)
    if verb is None:
        return _fragment_error(request, "Unknown action.")
    session_factory = request.app.state.session_factory
    if session_factory is None:
        return _fragment_error(
            request, "Staging is unavailable — the console has no database session."
        )
    form = await request.form()
    payload, err = await _resolve_target(request, verb, form)
    if err is not None:
        return err
    assert payload is not None
    seg_name = payload["seg"].get("seg_name")
    try:
        from forge_bridge.cli.interactive import _build_mutation_spec
        from forge_bridge.orchestration.apply_editorial_delta import (
            preview_editorial_delta_for_ratification,
        )
        spec = _build_mutation_spec(
            verb, payload["sequence"], payload["seg"], {verb.value_field: payload["value"]}
        )
        staged = await preview_editorial_delta_for_ratification(
            spec,
            session_factory=session_factory,
            display=f"{verb.name} {seg_name} -> {payload['value']}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ui_actions_stage_handler stage failed: %s",
            type(exc).__name__, exc_info=True,
        )
        return _fragment_error(request, "Staging failed — nothing was applied.")
    change_summary = _verbs.describe_change(verb, payload["current"], payload["value"])
    return request.app.state.templates.TemplateResponse(
        request,
        "actions/staged.html",
        {
            "verb": _verb_view(verb),
            "graph_intent_id": staged.get("graph_intent_id"),
            "seg_name": seg_name,
            "current": payload["current"],
            "new_value": payload["value"],
            "change_summary": change_summary,
        },
    )
