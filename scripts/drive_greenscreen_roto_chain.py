#!/usr/bin/env python3
"""Greenscreen→roto authored-chain prototype — bridge-side, read/compute-safe.

Prototypes the bridge's half of the greenscreen→roto workflow against the LIVE
daemon, using the REAL bridge graph primitives (FilterNode / parse_filter_step)
to compose the live forge-vision operators. It proves the wire/contract
composition today and marks the remaining Flame tail seam, so the full authored
chain is ready the moment that lands.

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
  • foreach(forge_roto_ref): per-routed-shot matte BY REFERENCE. The target is
    chain-authored explicit NL/markup (`target_spec`), not inferred from
    `is_greenscreen`: target_spec → GroundingDINO/SAM2 multi-object
    video-propagated masks → union → ViTMatte; output wire stays the same
    artifact_refs envelope. Bridge passes the wire through unchanged.

SAFE BY CONSTRUCTION: live tool calls + in-process graph primitives only. No
Flame mutation, no register_publish, no ratify. Re-run freely.

    python scripts/drive_greenscreen_roto_chain.py
    FORGE_MCP=http://127.0.0.1:9997/mcp python scripts/drive_greenscreen_roto_chain.py

────────────────────────────────────────────────────────────────────────────
SEAMS (do NOT silently paper over — these are the bridge/Flame boundaries):

  SEAM-1  CLOSED — CHROMA PROVENANCE / OPERATOR SIGNATURE.
          forge_is_greenscreen now takes the plate-reading signature SEAM-1
          anticipated: shot_id + clip_ref. The bridge foreach body can bind the
          per-segment media reference directly; no synthetic frame_stats stand-in
          remains in this harness.

  SEAM-1b ROTO TARGET + CLIP SEAM.
          Roto's target is now chain-authored explicit NL/markup, severed from
          is_greenscreen. The harness uses mock:// clip_ref values to exercise
          forge_roto_ref's safe synthetic path; the real-plate heavy round-trip
          swaps in a real clip_ref without changing the bridge wire.

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

# Synthetic segments carry the same public args the chain body tools consume:
# shot_id plus clip_ref, and target_spec for the routed roto step.
_SEGMENTS = [
    {
        "id": "gs_010",
        "clip_ref": "mock://gs_010.mov",
        "detection_clip_ref": "mock://perception/is_greenscreen/gs_010_true",
        "target_spec": {
            "objects": [{"prompt": "person"}],
            "annotated_frame": "middle",
        },
    },
    {
        "id": "gs_020",
        "clip_ref": "mock://gs_020.mov",
        "detection_clip_ref": "mock://perception/is_greenscreen/gs_020_true",
        "target_spec": {
            "objects": [{"prompt": "person"}, {"prompt": "person"}],
            "annotated_frame": "middle",
        },
    },
    {
        "id": "amb_030",
        "detection_clip_ref": "mock://perception/is_greenscreen/amb_030_abstain",
    },  # ambiguous → abstain
    {
        "id": "plate_040",
        "detection_clip_ref": "mock://perception/is_greenscreen/plate_040_false",
    },  # balanced → not gs
]


def _extract(res):
    def _loads_nested(value):
        for _ in range(3):
            if not isinstance(value, str):
                return value
            try:
                loaded = json.loads(value)
            except Exception:
                return value
            if loaded == value:
                return value
            value = loaded
        return value

    sc = getattr(res, "structuredContent", None)
    if isinstance(sc, dict):
        return _loads_nested(sc.get("result", sc))
    txt = "".join(getattr(b, "text", "") or "" for b in (getattr(res, "content", []) or []))
    return _loads_nested(txt)


def _roto_ref_ok(result: dict) -> bool:
    refs = result.get("artifact_refs") or []
    if refs:
        ref = refs[0]
        return (
            ref.get("artifact_type") == "DerivedHoldoutsArtifact"
            and bool(ref.get("payload_id"))
            and str(ref.get("locator", "")).endswith(".exr")
        )
    reason = result.get("reason") or result.get("abstention_reason")
    return bool(reason) and not result.get("locator")


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
            print("STEP foreach(forge_is_greenscreen) -> collect "
                  "[SEAM-1 closed: shot_id + clip_ref]")
            detected: list[dict] = []
            for seg in _SEGMENTS:
                o = _extract(await s.call_tool("forge_is_greenscreen",
                    {"shot_id": seg["id"],
                     "clip_ref": seg.get("detection_clip_ref")}))
                rec = {
                    "id": seg["id"],
                    "clip_ref": seg.get("clip_ref"),
                    "target_spec": seg.get("target_spec"),
                }
                if "is_greenscreen" in o:  # omit-on-abstain: token absent ⇒ not stamped
                    rec["is_greenscreen"] = o["is_greenscreen"]
                detected.append(rec)
                print(f"     {seg['id']:>10}: token={rec.get('is_greenscreen', '∅ (abstain/omit)')}"
                      f"  ({o.get('recommendation')})")
            seam_notes.append("SEAM-1 closed — is_greenscreen consumes shot_id + clip_ref")

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
                    {"shot_id": shot["id"],
                     "clip_ref": shot["clip_ref"],
                     "target_spec": shot["target_spec"]}))
                ref = (o.get("artifact_refs") or [{}])[0]
                mattes.append({"shot_id": shot["id"], "result": o, "ref": ref})
                if ref:
                    print(f"     {shot['id']:>10}: {ref.get('artifact_type')} "
                          f"locator={ref.get('locator')}")
                else:
                    print(f"     {shot['id']:>10}: abstain "
                          f"reason={o.get('reason') or o.get('abstention_reason')}")

            # ── foreach(forge_register_publish …) -> commit ──────────────────
            print("\nSTEP foreach(forge_register_publish …) -> commit")
            print("     ⏸ SEAM-2: bridge-authored Flame tail — deferred (needs Flame + real mattes)")
            seam_notes.append("SEAM-2 Flame ends — flame_get_sequence_segments front + register_publish/commit tail")

    # ── verdict ──────────────────────────────────────────────────────────────
    routed_ids = [m["shot_id"] for m in mattes]
    ok_route = routed_ids == ["gs_010", "gs_020"]               # gs route; amb/balanced drop
    ok_byref = all(_roto_ref_ok(m["result"]) for m in mattes) and bool(mattes)
    print("\n── verdict ──")
    print(f"   routing correct (gs route, abstain/negative drop): {ok_route}  {routed_ids}")
    print(f"   roto_ref by-reference matte for each routed shot:  {ok_byref}")
    print(f"   seam notes: {len(seam_notes)}")
    for n in seam_notes:
        print(f"     · {n}")
    core_ok = ok_route and ok_byref
    print(
        f"\n{'✅ WIRE/CONTRACT COMPOSES (mock target_spec → by-ref matte)' if core_ok else '❌ WIRE BROKEN'} — "
        "real-plate SAM2/ViTMatte remains the separate operator-coordinated "
        "round-trip; tail deferred to SEAM-2."
    )
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
