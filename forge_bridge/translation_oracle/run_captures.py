"""TF.3a Step 4 — build the reference corpus by pairing authored labels with
observed traces.

  seed cases  -> ObservedTrace transcoded from a matching comprehension trace (no model)
  live cases  -> ObservedTrace captured through the real compile path (Ollama qwen2.5-coder:14b)

Usage:
  python -m forge_bridge.translation_oracle.run_captures --seed-only   # no Ollama; writes the seed cases
  python -m forge_bridge.translation_oracle.run_captures               # full build; needs `ollama serve`
  python -m forge_bridge.translation_oracle.run_captures --postgate    # writes reference/postgate/

Rebuilds the committed reference corpus (`reference/cases.jsonl`) from scratch each
run, then prints the coverage report.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from forge_bridge.translation_oracle._authored import AUTHORED_CASES
from forge_bridge.translation_oracle._capture import capture_observed_trace
from forge_bridge.translation_oracle._corpus import (
    REFERENCE_DIR,
    append_case,
    coverage_report,
    read_cases,
)
from forge_bridge.translation_oracle._schema import SCHEMA_VERSION
from forge_bridge.translation_oracle._transcode import transcode_comprehension_record


def _load_seed_records() -> list[dict]:
    raw = os.environ.get("FORGE_COMPREHENSION_DIR")
    d = Path(raw).expanduser() if raw else Path.home() / ".forge-bridge" / "comprehension"
    records: list[dict] = []
    for f in sorted(d.glob("comprehension-*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if isinstance(r, dict) and not r.get("_header") and r.get("question"):
                records.append(r)
    return records


def _seed_observed_for(input_text: str, seed_records: list[dict]):
    cands = [r for r in seed_records if r.get("question") == input_text]
    if not cands:
        return None
    cands.sort(key=lambda r: -len(r.get("chain") or []))  # prefer the richest trace
    return transcode_comprehension_record(cands[0])


async def build(
    *,
    seed_only: bool = False,
    reuse_observed: bool = False,
    corpus_dir: Path = REFERENCE_DIR,
) -> tuple[list[str], list[tuple[str, str]]]:
    from forge_bridge.translation_oracle._detect import compute_well_formed

    path = corpus_dir / "cases.jsonl"

    # --reuse-observed: re-pair authored labels with already-captured observed
    # traces (no Ollama) — used to relabel/rebuild after a schema or label change.
    cached: dict[str, dict] = {}
    if reuse_observed and path.exists():
        for c in read_cases(corpus_dir=corpus_dir):
            inp = (c.get("label") or {}).get("input")
            if inp is not None:
                cached[inp] = c["observed"]

    if path.exists():
        path.unlink()  # rebuild from scratch

    seed_records = _load_seed_records()
    router = mcp = tools = None
    written: list[str] = []
    skipped: list[tuple[str, str]] = []

    for case in AUTHORED_CASES:
        cid, src, label = case["id"], case["source"], case["label"]
        if src == "seed":
            observed = _seed_observed_for(case["input"], seed_records)
            if observed is None:
                skipped.append((cid, "no matching seed trace"))
                continue
        elif reuse_observed and case["input"] in cached:
            observed = dict(cached[case["input"]])
            # recompute well_formed (older captures predate the field)
            wf, reason = compute_well_formed(
                observed.get("observed_graph") or [], outcome=observed.get("outcome"))
            observed["well_formed"], observed["well_formed_reason"] = wf, reason
        else:  # live
            if seed_only:
                skipped.append((cid, "live (skipped in --seed-only)"))
                continue
            if router is None:
                from forge_bridge.llm.router import LLMRouter
                from forge_bridge.mcp.server import mcp as _mcp
                router, mcp = LLMRouter(), _mcp
                tools = await mcp.list_tools()
            observed = await capture_observed_trace(
                router=router, tools=tools, mcp=mcp,
                user_prompt=case["input"], request_id=f"capture-{cid}",
                client_ip="capture", started=time.monotonic(),
            )
        append_case(
            {"schema_version": SCHEMA_VERSION, "observed": observed, "label": label},
            corpus_dir=corpus_dir,
        )
        written.append(cid)
    return written, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-only", action="store_true",
                    help="write only the seed-derived cases (no Ollama)")
    ap.add_argument("--reuse-observed", action="store_true",
                    help="re-pair authored labels with already-captured traces (no Ollama)")
    ap.add_argument("--postgate", action="store_true",
                    help="write to the post-gate reference corpus")
    ap.add_argument("--output", type=Path,
                    help="write to an explicit corpus directory")
    args = ap.parse_args()
    if args.postgate and args.output is not None:
        ap.error("--postgate and --output are mutually exclusive")
    corpus_dir = (
        args.output
        if args.output is not None
        else REFERENCE_DIR / "postgate"
        if args.postgate
        else REFERENCE_DIR
    )

    written, skipped = asyncio.run(
        build(
            seed_only=args.seed_only,
            reuse_observed=args.reuse_observed,
            corpus_dir=corpus_dir,
        )
    )
    print(f"written {len(written)}: {written}")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for cid, why in skipped:
            print(f"  {cid}: {why}")

    report = coverage_report(read_cases(corpus_dir=corpus_dir))
    print(f"\ncoverage complete: {report['complete']}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
