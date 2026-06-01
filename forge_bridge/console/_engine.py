"""PR31 / PR37 — shared multi-step chain engine (dict contract, injectable mcp)."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from forge_bridge.console._step import execute_chain_step
from forge_bridge.graph import infer_topology

from forge_bridge.core.assent import AssentRecord

logger = logging.getLogger(__name__)


async def run_chain_steps(
    *,
    steps: list[str],
    tools: list,
    mcp: Any,
    request_id: str,
    client_ip: str,
    started: float,
    assent_record: Optional[AssentRecord] = None,
) -> dict:
    """Sequentially execute chain steps. Abort on first error.

    Returns the PR31 JSON body dict (not JSONResponse). Context between steps
    uses only ``extracted_context`` from each step outcome (PR32).
    """
    chain_trace: list[dict] = []
    context: dict = {}

    for step_idx, step_text in enumerate(steps):
        if context.pop("__if_gate_skip_next__", False):
            prior = context.get("__previous_result__")
            skipped_manifest = dict(prior) if isinstance(prior, dict) else {}
            skipped_manifest["execution_state"] = "skipped"
            skipped_manifest["skipped_step"] = step_text
            chain_trace.append({
                "step": step_text,
                "result": skipped_manifest,
            })
            context = {
                "__previous_result__": skipped_manifest,
                "__previous_topology__": infer_topology(skipped_manifest).to_dict(),
            }
            continue

        outcome = await execute_chain_step(
            step_text=step_text,
            tools=tools,
            mcp=mcp,
            inherited_context=context,
            step_index=step_idx,
            assent_record=assent_record,
        )

        if "error" in outcome:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "chain_step_failed request_id=%s client_ip=%s "
                "step_index=%d steps_total=%d wall_clock_ms=%d "
                "error_type=%s",
                request_id, client_ip, step_idx, len(steps), elapsed_ms,
                outcome["error"].get("type", "unknown"),
            )
            return {
                "status": "error",
                "request_id": request_id,
                "chain": chain_trace,
                "error": {
                    "code": "CHAIN_STEP_FAILED",
                    "message": (
                        f"Chain step {step_idx} failed; subsequent "
                        "steps were not executed."
                    ),
                    "step_index": step_idx,
                    "original_error": outcome["error"],
                },
            }

        chain_trace.append({
            "step": step_text,
            "result": outcome["result"],
        })
        context = outcome.get("extracted_context", {}) or {}
        context["__previous_result__"] = outcome["result"]
        context["__previous_topology__"] = (
            outcome.get("emitted_topology")
            or infer_topology(outcome["result"]).to_dict()
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "chain_ok request_id=%s client_ip=%s steps=%d wall_clock_ms=%d",
        request_id, client_ip, len(chain_trace), elapsed_ms,
    )
    return {
        "status": "success",
        "request_id": request_id,
        "chain": chain_trace,
        "error": None,
    }
