#!/usr/bin/env python3
"""Greenscreen→roto authored-chain prototype — bridge-side, read/compute-safe.

Prototypes the bridge's half of the greenscreen→roto workflow against the LIVE
daemon, using the REAL bridge graph primitives (FilterNode / parse_filter_step)
to compose the live forge-vision operators. It proves the composable CORE today
and marks the two integration seams that the perception land + Flame must fill,
so the full authored chain is ready the moment those land.

Target authored chain (bridge-side, step 3 of the consumption e2e):

    flame_get_sequence_segments
      -> foreach(forge_is_greenscreen) -> collect
      -> filter(is_greenscreen == true)
      -> foreach(forge_roto_ref) -> collect
      -> foreach(forge_register_publish …) -> commit

What this harness verifies NOW (live, contract-proven):
  • foreach(forge_is_greenscreen): per-segment detection through the daemon,
    emitting the top-level `is_greenscreen` branch token (omit on abstain).
  • filter(is_greenscreen == true): the REAL bridge FilterNode routes on the
    top-level scalar (filter.py) — abstained/false shots drop out.
  • foreach(forge_roto_ref): per-routed-shot matte BY REFERENCE
    (DerivedHoldoutsArtifact: locator + sha256 payload_id + foreground_alpha).

SAFE BY CONSTRUCTION: live tool calls + in-process graph primitives only. No
Flame mutation, no register_publish, no ratify. Re-run freely.

    python scripts/drive_greenscreen_roto_chain.py
    FORGE_MCP=http://127.0.0.1:9997/mcp python scripts/drive_greenscreen_roto_chain.py

────────────────────────────────────────────────────────────────────────────
SEAMS (do NOT silently paper over — these are the perception land + Flame):

  SEAM-1  CHROMA PROVENANCE / OPERATOR SIGNATURE.
          The current operator is forge_is_greenscreen(frame_stats, shot_id) —
          it consumes PRE-COMPUTED 8-bit chroma. Flame segments do NOT carry
          chroma, and the chain engine binds a foreach body tool's args from
          public context + standard id-extraction (project_id/shot_id/
          version_id), NOT arbitrary arrays (_step.py:248-257, foreach body
          context _step.py:651-656). So `foreach(forge_is_greenscreen)` cannot
          supply per-segment `frame_stats` from segment data.
          → PERCEPTION-LAND CONTRACT NOTE: the real operator should take a
            PLATE-READING signature (shot_id + media locator) and read chroma
            itself, so the foreach body binds per-segment from the segment's
            own media reference. Until then this harness injects synthetic
            frame_stats as a STAND-IN for that read.

  SEAM-2  FLAME ENDS. flame_get_sequence_segments (front) and
          forge_register_publish / import_clips / commit (tail) need Flame
          connected. This harness substitutes a synthetic segment list for the
          front and stops before the publish/attach tail (bridge-authored, runs
          when real mattes land + Flame is up).
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from forge_bridge.graph.filter import FilterNode, parse_filter_step

MCP_URL = os.environ.get("FORGE_MCP", "http://127.0.0.1:9997/mcp")

# SEAM-1 stand-in: synthetic segments carrying shot_id + (stand-in) chroma. In
# the perception land these chroma arrays are replaced by the operator reading
# each segment's plate directly. 8-bit scale (GREEN_FLOOR=90, MARGIN=40).
_SEGMENTS = [
    {"id": "gs_010", "frame_stats": [{"mean_r": 40, "mean_g": 200, "mean_b": 50}] * 6},
    {"id": "gs_020", "frame_stats": [{"mean_r": 35, "mean_g": 190, "mean_b": 60}] * 6},
    {"id": "amb_030", "frame_stats": [{"mean_r": 70, "mean_g": 100, "mean_b": 70}] * 6},  # ambiguous → abstain
    {"id": "plate_040", "frame_stats": [{"mean_r": 120, "mean_g": 110, "mean_b": 115}] * 6},  # balanced → not gs
]


def _extract(res):
    sc = getattr(res, "structuredContent", None)
    if isinstance(sc, dict):
        return sc.get("result", sc)
    txt = "".join(getattr(b, "text", "") or "" for b in (getattr(res, "content", []) or []))
    try:
        return json.loads(txt)
    except Exception:
        return txt


async def main() -> int:
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession
    except Exception as exc:  # noqa: BLE001
        print(f"✗ mcp client import failed: {exc}")
        return 2

    print("== greenscreen→roto authored-chain prototype ==")
    print(f"   daemon MCP: {MCP_URL}")
    print("   target: ...foreach(is_greenscreen)->collect->filter(is_greenscreen==true)"
          "->foreach(roto_ref)->collect->foreach(register_publish)->commit\n")

    seam_notes: list[str] = []
    async with streamablehttp_client(MCP_URL) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()

            # ── foreach(forge_is_greenscreen) -> collect ─────────────────────
            # SEAM-1: frame_stats are stand-ins for the operator's plate read.
            print("STEP foreach(forge_is_greenscreen) -> collect "
                  "[SEAM-1: synthetic chroma stands in for the plate read]")
            detected: list[dict] = []
            for seg in _SEGMENTS:
                o = _extract(await s.call_tool("forge_is_greenscreen",
                    {"frame_stats": seg["frame_stats"], "shot_id": seg["id"]}))
                rec = {"id": seg["id"]}
                if "is_greenscreen" in o:  # omit-on-abstain: token absent ⇒ not stamped
                    rec["is_greenscreen"] = o["is_greenscreen"]
                detected.append(rec)
                print(f"     {seg['id']:>10}: token={rec.get('is_greenscreen', '∅ (abstain/omit)')}"
                      f"  ({o.get('recommendation')})")
            seam_notes.append("SEAM-1 frame_stats provenance — see operator-signature note")

            # ── filter(is_greenscreen == true) — the REAL bridge primitive ───
            node = FilterNode(predicate=parse_filter_step("filter(is_greenscreen == true)"))
            routed = node.selected_collection({"shots": detected})
            print("\nSTEP filter(is_greenscreen == true)  [real bridge FilterNode]")
            print(f"     in={len(detected)}  routed={[x['id'] for x in routed]}")

            # ── foreach(forge_roto_ref) -> collect ───────────────────────────
            print("\nSTEP foreach(forge_roto_ref) -> collect  [routed shots only]")
            mattes: list[dict] = []
            for shot in routed:
                o = _extract(await s.call_tool("forge_roto_ref",
                    {"shot_id": shot["id"], "luminance": [0.2, 0.4, 0.6, 0.5, 0.3, 0.7]}))
                ref = (o.get("artifact_refs") or [{}])[0]
                mattes.append({"shot_id": shot["id"], "ref": ref})
                print(f"     {shot['id']:>10}: {ref.get('artifact_type')} "
                      f"locator={ref.get('locator')}")

            # ── foreach(forge_register_publish …) -> commit ──────────────────
            print("\nSTEP foreach(forge_register_publish …) -> commit")
            print("     ⏸ SEAM-2: bridge-authored Flame tail — deferred (needs Flame + real mattes)")
            seam_notes.append("SEAM-2 Flame ends — flame_get_sequence_segments front + register_publish/commit tail")

    # ── verdict ──────────────────────────────────────────────────────────────
    routed_ids = [m["shot_id"] for m in mattes]
    ok_route = routed_ids == ["gs_010", "gs_020"]               # gs route; amb/balanced drop
    ok_byref = all(str(m["ref"].get("locator", "")).endswith(".exr") for m in mattes) and bool(mattes)
    print("\n── verdict ──")
    print(f"   routing correct (gs route, abstain/negative drop): {ok_route}  {routed_ids}")
    print(f"   roto_ref by-reference matte for each routed shot:  {ok_byref}")
    print(f"   open seams: {len(seam_notes)}")
    for n in seam_notes:
        print(f"     · {n}")
    core_ok = ok_route and ok_byref
    print(f"\n{'✅ CORE COMPOSES (live)' if core_ok else '❌ CORE BROKEN'} — "
          f"perception→filter→roto wired through the bridge; tail deferred to SEAM-2.")
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
