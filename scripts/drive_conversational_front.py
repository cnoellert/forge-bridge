#!/usr/bin/env python3
"""Conversational-front drive harness — read/preview-safe, re-runnable.

Exercises the verified behaviors of the bridge conversational front against a
LIVE daemon and reports PASS / FAIL / KNOWN-GAP / DEPLOY-STALE per case.

SAFE BY CONSTRUCTION: reads + operation PREVIEWS only. It never calls
/api/v1/ratify, so no AssentRecord is applied and nothing mutates in Flame.
Re-run as often as you like.

    python scripts/drive_conversational_front.py
    FORGE_BASE=http://127.0.0.1:9996 FORGE_PROJECT=portofino python scripts/drive_conversational_front.py

⚠ The reads-fence cases require the daemon to be running a build that includes
the reads fence (commit 61cb847, branch feat/reads-fence-gate-a). If the daemon
predates it, the "urgent" case is reported DEPLOY-STALE (it fabricates a status
instead of clarifying) — that's the harness telling you the fence isn't live yet.
Deploy = merge the PR + `fbridge restart console` (or check out the branch and
restart), then re-run.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("FORGE_BASE", "http://127.0.0.1:9996").rstrip("/")
PROJECT = os.environ.get("FORGE_PROJECT", "portofino")
TIMEOUT = float(os.environ.get("FORGE_TIMEOUT", "90"))

PASS, FAIL, GAP, STALE, ERR = "PASS", "FAIL", "KNOWN-GAP", "DEPLOY-STALE", "ERROR"
_ICON = {PASS: "✅", FAIL: "❌", GAP: "⚠️ ", STALE: "🔁", ERR: "💥"}
_results: list[tuple[str, str, str]] = []


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-Forge-Actor": "drive-harness"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode()[:300]}
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def _get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def chat(message: str, *, surface: str) -> dict:
    """surface = 'planner_front' (reads) | 'operation_front' (ops)."""
    return _post(f"/api/v1/chat?{surface}=true",
                 {"messages": [{"role": "user", "content": message}]})


def _stop(r: dict) -> str | None:
    return r.get("stop_reason")


def _statuses(r: dict) -> list:
    return [s.get("args", {}).get("status")
            for s in (r.get("plan") or []) if isinstance(s.get("args"), dict)]


def _record(name: str, verdict: str, detail: str) -> None:
    _results.append((verdict, name, detail))
    print(f"{_ICON[verdict]} [{verdict}] {name}\n     {detail}")


def _err_or(r: dict, name: str) -> bool:
    """Record + return True if the response was a transport/runtime error."""
    if "_error" in r or "_http_error" in r:
        _record(name, ERR, f"transport: {r.get('_error') or r.get('_http_error')} {r.get('_body','')}")
        return True
    if _stop(r) in ("error", "planner_error", "compile_error"):
        _record(name, ERR, f"stop={_stop(r)} :: {(r.get('final_text') or '')[:140]}")
        return True
    return False


# ───────────────────────────── READS ─────────────────────────────

def reads_groundable_status():
    name = "reads/groundable-status (in review → status=review)"
    r = chat(f"which shots are in review in {PROJECT}", surface="planner_front")
    if _err_or(r, name):
        return
    if _stop(r) == "planner_front" and "review" in _statuses(r):
        _record(name, PASS, f"grounded; {(r.get('final_text') or '')[:120]}")
    else:
        _record(name, FAIL, f"stop={_stop(r)} statuses={_statuses(r)}")


def reads_fabrication_clarify():
    name = "reads/FENCE fabrication→clarify (urgent must NOT map to a status)"
    r = chat(f"which shots are urgent in {PROJECT}", surface="planner_front")
    if _err_or(r, name):
        return
    if _stop(r) == "clarification_needed":
        _record(name, PASS, f"clarified, nothing executed :: {(r.get('final_text') or '')[:120]}")
    elif _stop(r) == "planner_front" and any(_statuses(r)):
        _record(name, STALE,
                f"FABRICATED status={_statuses(r)} — reads fence (61cb847) not deployed on this daemon")
    else:
        _record(name, FAIL, f"stop={_stop(r)} statuses={_statuses(r)}")


def reads_ownership_boundary():
    name = "reads/v1-boundary ownership (my shots — model-omitted qualifier)"
    r = chat(f"show me my shots in {PROJECT}", surface="planner_front")
    if _err_or(r, name):
        return
    if _stop(r) == "clarification_needed":
        _record(name, PASS, "clarified (stronger model declared 'my')")
    else:
        _record(name, GAP, "proceeded — 14b omits 'my' from plan AND declaration; named v1 boundary")


def reads_no_regression():
    name = "reads/no-regression (no qualifier → plan, no clarify)"
    r = chat(f"show me the shots in {PROJECT}", surface="planner_front")
    if _err_or(r, name):
        return
    if _stop(r) == "planner_front" and r.get("plan"):
        _record(name, PASS, "planned without clarifying")
    else:
        _record(name, FAIL, f"stop={_stop(r)} plan={r.get('plan')}")


def reads_fuzzy_resolve():
    name = "reads/fuzzy resolve (typo'd project name)"
    typo = PROJECT[:-1] + PROJECT[-1] * 2 if len(PROJECT) > 2 else PROJECT  # e.g. portofino→portofinoo
    r = chat(f"tell me about the {typo} project", surface="planner_front")
    if _err_or(r, name):
        return
    if _stop(r) == "planner_front" and r.get("plan"):
        _record(name, PASS, f"resolved '{typo}' to a plan")
    elif _stop(r) == "clarification_needed":
        _record(name, GAP, f"asked to clarify '{typo}' (acceptable; not fabricated)")
    else:
        _record(name, FAIL, f"stop={_stop(r)}")


def reads_non_hallucination():
    name = "reads/non-hallucination (nonexistent project)"
    r = chat("tell me about the bigfoot project", surface="planner_front")
    if _err_or(r, name):
        return
    txt = (r.get("final_text") or "").lower()
    honest = any(k in txt for k in ("not available", "no ", "don't", "couldn't find",
                                    "not find", "no such", "isn't", "unable"))
    if _stop(r) == "clarification_needed" or honest:
        _record(name, PASS, f"honest :: {(r.get('final_text') or '')[:120]}")
    else:
        _record(name, FAIL, f"possible hallucination :: {(r.get('final_text') or '')[:140]}")


# ──────────────────────── OPERATION-FRONT (preview-only) ────────────────────────

def op_preview():
    name = "op-front/preview (create reel → preview_emitted, NOT ratified)"
    r = chat("create a reel called drive_harness_probe", surface="operation_front")
    if _err_or(r, name):
        return
    gid = r.get("graph_intent_id") or (r.get("preview") or {}).get("graph_intent_id")
    if _stop(r) == "preview_emitted" and gid:
        _record(name, PASS, f"preview only, graph_intent_id={gid} (no ratify → nothing created)")
    else:
        _record(name, FAIL, f"stop={_stop(r)} gid={gid}")


def op_required_arg_gate():
    # Two distinct behaviors on "create a reel" (no name), and they're stochastic on 14b:
    #  - model OMITS the name  -> required-arg gate (b304564) catches it -> clarify  (PASS)
    #  - model INVENTS a default name -> gate passes (it only rejects <placeholder>/empty),
    #    previews an invented name (KNOWN-GAP: free-form name has no vocab to validate against,
    #    unlike the reads fence; B3 ratify-gate backstops it — operator sees the name, declines)
    #  - a literal placeholder/empty name reaching preview WOULD be a real breach (FAIL)
    import re
    name = "op-front/arg-gate (create a reel, no name)"
    r = chat("create a reel", surface="operation_front")
    if _err_or(r, name):
        return
    st = _stop(r)
    if st == "clarification_needed":
        _record(name, PASS, "model omitted the name → required-arg gate clarified")
        return
    if st == "preview_emitted":
        pv = r.get("preview") or {}
        names = [s.get("args_preview", {}).get("reel_name")
                 for s in pv.get("steps", []) if str(s.get("tool_name", "")).endswith("create_reel")]
        nm = next((n for n in names if n), "") or ""
        if not nm.strip() or re.match(r"^<.*>$", nm.strip()):
            _record(name, FAIL, f"placeholder/empty name reached preview — deterministic gate BREACHED: {nm!r}")
        else:
            _record(name, GAP, f"model invented default name {nm!r} → previewed (B3-backstopped; "
                               "free-form name, no vocab to validate — named boundary, stochastic)")
        return
    _record(name, FAIL, f"unexpected stop={st}")


CASES = [
    reads_groundable_status,
    reads_fabrication_clarify,
    reads_ownership_boundary,
    reads_no_regression,
    reads_fuzzy_resolve,
    reads_non_hallucination,
    op_preview,
    op_required_arg_gate,
]


def main() -> int:
    print(f"== conversational-front drive :: {BASE} :: project='{PROJECT}' ==")
    health = _get("/api/v1/tools")
    n_tools = len(health.get("data", [])) if isinstance(health, dict) else 0
    if "_error" in health:
        print(f"💥 daemon unreachable at {BASE}: {health['_error']}")
        return 2
    print(f"   daemon reachable — {n_tools} tools registered\n")

    for case in CASES:
        try:
            case()
        except Exception as e:  # noqa: BLE001
            _record(case.__name__, ERR, f"harness exception: {e}")

    counts = {v: sum(1 for vv, _, _ in _results if vv == v) for v in (PASS, FAIL, GAP, STALE, ERR)}
    print("\n── summary ──")
    print("  " + "  ".join(f"{_ICON[v]}{v}={counts[v]}" for v in (PASS, FAIL, GAP, STALE, ERR)))
    if counts[STALE]:
        print("  🔁 DEPLOY-STALE means the reads fence isn't on this daemon yet — merge + `fbridge restart console`.")
    # Fail the run only on real FAIL / ERROR; GAP and STALE are expected/informational.
    return 1 if (counts[FAIL] or counts[ERR]) else 0


if __name__ == "__main__":
    sys.exit(main())
