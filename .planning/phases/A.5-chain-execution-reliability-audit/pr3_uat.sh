#!/usr/bin/env bash
# PR 3 UAT — Persistence substrate operator-experience verification.
#
# Exercises four entry points the automated tests can't reach:
#   1. File reality-check          (does the persistence shape read as truthful infrastructure)
#   2. Corruption-locality live-fire (does the failure posture feel operationally sane)
#   3. Failure-invisibility sanity   (does "mechanically forgetful" hold as operator experience)
#   4. Cold architectural read-through (does the architecture explain itself)
#
# Interactive: pauses after each section so you can read, reflect,
# and form an operator-intuition judgment before continuing.
#
# Run from the repo root:
#   bash .planning/phases/A.5-chain-execution-reliability-audit/pr3_uat.sh
#
# Uses an isolated UAT corpus directory so the daemon's real corpus
# (when it exists) is never touched. Cleans up on exit unless
# UAT_KEEP_DIR=1 is set.

set -u  # not -e; we WANT to continue past intentional failures

# ── Setup ──────────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

# Resolve Python: prefer project venv, fall back to system python3.
if   [ -x "./.venv/bin/python3" ];     then PY="./.venv/bin/python3"
elif [ -x "./venv/bin/python3" ];      then PY="./venv/bin/python3"
elif [ -x "$HOME/.venv/bin/python3" ]; then PY="$HOME/.venv/bin/python3"
else                                        PY="python3"
fi

# Verify the corpus package imports under this Python; if not, bail
# with a clear hint so the operator can point us at the right venv.
if ! "$PY" -c "from forge_bridge.corpus import emit_divergence_capture, read_capture_file" 2>/dev/null; then
    echo "ERROR: 'from forge_bridge.corpus import ...' failed under: $PY"
    echo
    echo "Try one of:"
    echo "  PY=path/to/venv/bin/python3 bash $0"
    echo "  source path/to/venv/bin/activate && bash $0"
    exit 1
fi

UAT_DIR="$(mktemp -d -t forge-bridge-pr3-uat.XXXXXX)"
export FORGE_BRIDGE_CORPUS_DIR="$UAT_DIR"

cleanup() {
    if [ "${UAT_KEEP_DIR:-0}" = "1" ]; then
        echo
        echo "UAT corpus dir retained (UAT_KEEP_DIR=1): $UAT_DIR"
    else
        rm -rf "$UAT_DIR"
    fi
}
trap cleanup EXIT

# ── Pretty-printing ────────────────────────────────────────────────────────

bar() { printf '\n%s\n' "────────────────────────────────────────────────────────────────────"; }
section() { bar; printf 'PR 3 UAT — %s\n' "$1"; bar; }
pause() { echo; read -rp "Press ENTER to continue (or Ctrl-C to stop)…" _; }

echo
echo "PR 3 UAT — operator-experience verification"
echo
echo "Python:        $PY"
echo "Repo:          $REPO_ROOT"
echo "Corpus dir:    $FORGE_BRIDGE_CORPUS_DIR"
echo "Keep dir:      ${UAT_KEEP_DIR:-0}  (set UAT_KEEP_DIR=1 to retain on exit)"
echo
echo "Four entry points will run. Each pauses before continuing so you"
echo "can read the artifacts and form a judgment. There are no automated"
echo "pass/fail assertions — the question is whether the persistence"
echo "substrate behaves like the architecture claims it behaves."
pause

# ── Entry point 1: File reality-check ──────────────────────────────────────

section "1. File reality-check"

cat <<'NARRATIVE'
Generating ten varied captures: single-tool obvious, multi-intent,
conversational (no tool), unicode prompts, edge-case names. The
file produced is what an operator would see in production six
months from now, debugging a real issue.

Questions to hold while reading:
  - Does the file feel grep-friendly?
  - Are records readable cold, or do you need the spec?
  - Do topology / identity / arbitration separations read clearly?
  - Does Unicode survive cleanly?
  - Does the header feel truthful or decorative?
  - Does the file "look append-only" intuitively?
  - Could you debug a production issue from this artifact?
NARRATIVE

"$PY" - <<'PY_EOF'
from forge_bridge.corpus import emit_divergence_capture

# Lightweight stand-in for FastMCP Tool objects. The writer's
# _tool_names helper accepts strings, dicts, or anything with .name.
class T:
    def __init__(self, name): self.name = name

REGISTERED = [T(n) for n in [
    "forge_list_projects",
    "forge_list_staged",
    "forge_get_staged",
    "forge_get_events",
    "forge_blast_radius",
    "flame_prune_batch_xml",
    "list_media",
    "list_published_plates",
]]

def emit(prompt, narrower, post_reach=None, post_pr14=None,
         pr20=False, collapse=False, ambiguity="single_survivor"):
    emit_divergence_capture(
        prompt=prompt,
        registered_tools=REGISTERED,
        candidate_set_post_reachability=post_reach if post_reach is not None else REGISTERED,
        candidate_set_post_pr14=post_pr14 if post_pr14 is not None else narrower,
        narrower_decision=narrower,
        pr20_fired=pr20,
        collapse_occurred=collapse,
        ambiguity_state=ambiguity,
        narrower_latency_ms=1.5,
        source="fixture",
    )

# Single-tool obvious — narrower confident, deterministic short-circuit.
emit("list the projects",
     [T("forge_list_projects")], pr20=True)

emit("show me the staged operations",
     [T("forge_list_staged")], pr20=True)

# Multi-intent — narrower defers, multiple survivors.
emit("what projects exist and how many staged ops are pending",
     [T("forge_list_projects"), T("forge_list_staged")],
     ambiguity="multi_survivor")

# Conversational — narrower returns nothing, LLM should answer plainly.
emit("explain what forge-bridge is in one sentence",
     [], ambiguity="zero_survivor")

# Ambiguous operational.
emit("are there any plates that need re-roto",
     [T("list_published_plates")],
     ambiguity="single_survivor")

# Unicode — Japanese, emoji, accented Latin, RTL Arabic.
emit("プロジェクトを一覧表示してください",
     [T("forge_list_projects")], pr20=True)

emit("список проектов 🚀 café",
     [T("forge_list_projects")], pr20=True)

emit("ما هي المشاريع الحالية؟",
     [T("forge_list_projects")], pr20=True)

# Edge-case prompt content: quotes, newlines, control chars.
emit('list "all" projects\nwith\ttabs and quotes',
     [T("forge_list_projects")], pr20=True)

# Long prompt — verify line stays parseable at length.
emit("here is a much longer prompt that simulates a verbose operator "
     "asking about project status with embedded context like the date "
     "2026-05-07 and a UUID 550e8400-e29b-41d4-a716-446655440000 "
     "to verify nothing in the writer chokes on length or content",
     [T("forge_list_projects")], pr20=True)

print("Emitted 10 records.")
PY_EOF

# Find the produced file (date-bound; we just take whatever landed).
CAPTURE_FILE="$(find "$UAT_DIR" -type f -name 'capture-*.jsonl' | head -1)"

if [ -z "$CAPTURE_FILE" ]; then
    echo "ERROR: no capture file produced under $UAT_DIR"
    exit 1
fi

echo
echo "Capture file:  $CAPTURE_FILE"
echo "Line count:    $(wc -l < "$CAPTURE_FILE")"
echo "Byte size:     $(wc -c < "$CAPTURE_FILE")"
echo

echo "── Header (line 1, pretty-printed) ──"
head -1 "$CAPTURE_FILE" | "$PY" -m json.tool
echo
echo "── First record (line 2, pretty-printed) ──"
sed -n '2p' "$CAPTURE_FILE" | "$PY" -m json.tool
echo
echo "── Multi-intent record (line 4, pretty-printed) ──"
sed -n '4p' "$CAPTURE_FILE" | "$PY" -m json.tool
echo
echo "── Unicode record (line 7, raw — verify Japanese/emoji unescaped) ──"
sed -n '7p' "$CAPTURE_FILE"
echo
echo "── Grep test: find all prompts containing 'projects' ──"
grep -c '"prompt":"[^"]*projects' "$CAPTURE_FILE" 2>/dev/null || echo "(grep pattern matched 0)"
echo
echo "── Grep test: find Unicode literally (Japanese 'プロジェクト') ──"
grep -c 'プロジェクト' "$CAPTURE_FILE" 2>/dev/null || echo "(grep pattern matched 0)"
echo
echo "── Read each prompt cold (just prompts, no schema noise) ──"
"$PY" -c "
import json, sys
with open('$CAPTURE_FILE') as f:
    for i, line in enumerate(f, 1):
        rec = json.loads(line)
        if rec.get('_header'): continue
        p = rec['prompt']
        if len(p) > 70: p = p[:67] + '...'
        print(f'  L{i}: {p}')
"

pause

# ── Entry point 2: Corruption-locality live-fire ───────────────────────────

section "2. Corruption-locality live-fire"

cat <<'NARRATIVE'
Vandalizing a copy of the capture file in five operationally
realistic ways. The reader should isolate corruption to the
malformed line, log a WARNING that's readable, and continue
yielding subsequent records.

Question to hold: do the warnings feel operationally useful?
Specifically — could you find the corrupted record from the
warning alone?
NARRATIVE

VANDAL_FILE="$UAT_DIR/vandalized-$(date +%s).jsonl"

# Build a deliberately-corrupted file: header + valid + 5 bad cases + valid.
"$PY" - <<PY_EOF
import json
src = "$CAPTURE_FILE"
dst = "$VANDAL_FILE"

with open(src) as f:
    lines = f.readlines()

header = lines[0]
valid_a = lines[1]
valid_b = lines[2]

with open(dst, "wb") as out:
    out.write(header.encode())
    out.write(valid_a.encode())
    # Mode 1: truncated JSON (line cut off mid-string).
    out.write(b'{"schema_version":"1","capture_id":"abc","captured_at":"2026-05-07T12:00:00.000Z","sour\n')
    # Mode 2: invalid UTF-8 bytes on an otherwise plausible-looking line.
    out.write(b'{"prompt":"\xC3\x28invalid"}\n')
    # Mode 3: well-formed JSON missing required fields.
    out.write(b'{"only":"this_field"}\n')
    # Mode 4: stray header mid-file.
    out.write(b'{"_header":true,"schema_version":"1","created_at":"2026-05-07T00:00:00.000Z","format":"forge-bridge-divergence-corpus-v1"}\n')
    # Mode 5: empty line (should skip silently — no warning).
    out.write(b'\n')
    # Final valid record — the locality test: did we recover?
    out.write(valid_b.encode())

print(f"Built vandalized file: {dst}")
print(f"Total lines: {sum(1 for _ in open(dst, 'rb'))}")
PY_EOF

echo
echo "── Reader output (records yielded + warnings logged) ──"
"$PY" - <<PY_EOF 2>&1
import logging, sys
# Surface WARNINGs to stderr so they appear inline below.
logging.basicConfig(level=logging.WARNING, format="WARN: %(message)s")
from forge_bridge.corpus import read_capture_file
from pathlib import Path

records = list(read_capture_file(Path("$VANDAL_FILE")))
print(f"\nYielded {len(records)} records (expected 2: the two valid ones surrounding the malformed block).")
for i, r in enumerate(records, 1):
    p = r.get("prompt", "")
    if len(p) > 60: p = p[:57] + "..."
    print(f"  R{i}: prompt='{p}', source={r.get('source')}")
PY_EOF

pause

# ── Entry point 3: Failure-invisibility sanity pass ────────────────────────

section "3. Failure-invisibility sanity pass"

cat <<'NARRATIVE'
Three hostile persistence scenarios. After each, verify:
  - emit returned None (no exception escaped)
  - WARNING was logged (proportional, not spammy)
  - daemon-equivalent code path continues normally
  - residue test: subsequent successful emit lands cleanly
NARRATIVE

# Use a separate "hostile" subdir so we can chmod it without breaking
# the main UAT cleanup.
HOSTILE_DIR="$UAT_DIR/hostile"
mkdir -p "$HOSTILE_DIR"

"$PY" - <<PY_EOF 2>&1
import logging, os
logging.basicConfig(level=logging.WARNING, format="WARN: %(message)s")
from forge_bridge.corpus import emit_divergence_capture
from pathlib import Path

class T:
    def __init__(self, name): self.name = name
TOOLS = [T("forge_list_projects")]

def call(label):
    print(f"\n[{label}]")
    rv = emit_divergence_capture(
        prompt=f"hostile-test: {label}",
        registered_tools=TOOLS,
        candidate_set_post_reachability=TOOLS,
        candidate_set_post_pr14=TOOLS,
        narrower_decision=TOOLS,
        pr20_fired=True,
        collapse_occurred=False,
        ambiguity_state="single_survivor",
        narrower_latency_ms=1.0,
        source="fixture",
    )
    print(f"  return value: {rv!r} (expected: None)")

# Scenario A: corpus dir is unwritable.
import stat
hostile = Path(os.environ["FORGE_BRIDGE_CORPUS_DIR"]) / "hostile"
hostile.mkdir(parents=True, exist_ok=True)
os.environ["FORGE_BRIDGE_CORPUS_DIR"] = str(hostile)
hostile.chmod(0)  # no permissions
try:
    call("A. unwritable corpus directory")
finally:
    hostile.chmod(stat.S_IRWXU)  # restore so cleanup works

# Scenario B: corpus dir path points at a regular file (not a directory).
fake_path = hostile / "imafile"
fake_path.write_text("not a directory\n")
os.environ["FORGE_BRIDGE_CORPUS_DIR"] = str(fake_path)
call("B. corpus dir path is a file, not a directory")

# Scenario C: residue test. Restore healthy dir, emit, verify success.
recovery = hostile / "recovery"
recovery.mkdir(parents=True, exist_ok=True)
os.environ["FORGE_BRIDGE_CORPUS_DIR"] = str(recovery)
call("C. recovery emit after two failures (must produce a fresh file)")
files = list(recovery.glob("capture-*.jsonl"))
print(f"  recovery file count: {len(files)} (expected: 1)")
if files:
    print(f"  recovery file:       {files[0].name}")
    print(f"  recovery file size:  {files[0].stat().st_size} bytes")
PY_EOF

# Restore environment for any later sections.
export FORGE_BRIDGE_CORPUS_DIR="$UAT_DIR"

pause

# ── Entry point 4: Cold architectural read-through ─────────────────────────

section "4. Cold architectural read-through"

cat <<'NARRATIVE'
This entry point is structurally different — it's reading code,
not running it. Read in this order, without consulting the
conversation that produced this work:

  1. .planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR3-SPEC.md
  2. forge_bridge/corpus/_capture.py
  3. forge_bridge/corpus/reader.py
  4. The capture file from entry point 1

After each, ask yourself:
  - Do the carrier sentences feel load-bearing or decorative?
  - Is the writer/caller asymmetry legible?
  - Do rejection rows in §14 read as justified or paranoid?
  - Does the code read observational rather than participatory?
  - Could a new contributor understand "what this subsystem is for"
    from these four artifacts alone?

If at any point you find yourself thinking "wait, why does this
work this way?" — that's a signal worth noting.

The script does not pause here automatically, since this is a
read-and-reflect step rather than a run-and-observe step.
NARRATIVE

echo "Files for cold read:"
echo "  $REPO_ROOT/.planning/phases/A.5-chain-execution-reliability-audit/A.5.3.2-PR3-SPEC.md"
echo "  $REPO_ROOT/forge_bridge/corpus/_capture.py"
echo "  $REPO_ROOT/forge_bridge/corpus/reader.py"
echo "  $CAPTURE_FILE"
echo

bar
echo "UAT complete. Discuss findings before proceeding to PR 4."
bar
