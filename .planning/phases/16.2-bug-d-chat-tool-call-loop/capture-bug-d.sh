#!/usr/bin/env bash
# capture-bug-d.sh — Phase 16.2-01 Task 1
# Run on assist-01. Captures Ollama's response to the canonical CHAT-04 prompt
# with tools advertised, validates the Bug D shape, and emits a single
# paste-ready block for the orchestrator.

set -uo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MODEL="${MODEL:-qwen2.5-coder:32b}"
PROMPT='what synthesis tools were created this week?'
RAW_OUT="/tmp/ollama-bug-d-raw.json"
META_OUT="/tmp/ollama-bug-d-meta.txt"

echo "=== sanity ==="
OLLAMA_VERSION="$(ollama --version 2>/dev/null || echo 'ollama-not-found')"
echo "ollama --version: ${OLLAMA_VERSION}"
HAS_MODEL="$(ollama list 2>/dev/null | awk -v m="${MODEL%%:*}" 'NR>1 && $1 ~ m' | head -1)"
echo "ollama list (matched): ${HAS_MODEL:-<none>}"
TAGS_HEAD="$(curl -s --max-time 3 "${OLLAMA_URL}/api/tags" | head -c 200)"
echo "tags head: ${TAGS_HEAD:0:200}"
echo

if [ -z "${TAGS_HEAD}" ]; then
  echo "ABORT: Ollama daemon not reachable at ${OLLAMA_URL}" >&2
  exit 2
fi
if [ -z "${HAS_MODEL}" ]; then
  echo "ABORT: model ${MODEL} not present (\`ollama pull ${MODEL}\` first)" >&2
  exit 2
fi

echo "=== capture ==="
HTTP_CODE=$(curl -s -o "${RAW_OUT}" -w "%{http_code}" \
  "${OLLAMA_URL}/api/chat" \
  -H 'Content-Type: application/json' \
  -d @- <<JSON
{
  "model": "${MODEL}",
  "stream": false,
  "keep_alive": "10m",
  "options": {"temperature": 0.1},
  "messages": [
    {"role": "user", "content": "${PROMPT}"}
  ],
  "tools": [
    {"type": "function", "function": {
      "name": "forge_tools_read",
      "description": "Read synthesized tool metadata from the manifest",
      "parameters": {"type": "object", "properties": {"name": {"type": "string"}}}
    }}
  ]
}
JSON
)
echo "HTTP ${HTTP_CODE}"
if [ "${HTTP_CODE}" != "200" ]; then
  echo "ABORT: non-200 response — body follows" >&2
  cat "${RAW_OUT}" >&2
  exit 3
fi

echo "=== shape check ==="
python3 - "${RAW_OUT}" "${MODEL}" "${OLLAMA_VERSION}" "${PROMPT}" <<'PY'
import json, sys, datetime, socket, getpass

raw_path, model, ollama_version, prompt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(raw_path) as f:
    raw = json.load(f)

msg = raw.get("message", {}) or {}
content = msg.get("content", "") or ""
tool_calls = msg.get("tool_calls", None)

# Bug D positive markers
tool_calls_empty = (tool_calls is None) or (isinstance(tool_calls, list) and len(tool_calls) == 0)

content_parses = False
content_has_name_args = False
parsed = None
if isinstance(content, str) and content.strip():
    try:
        parsed = json.loads(content)
        content_parses = True
        if isinstance(parsed, dict) and "name" in parsed and "arguments" in parsed:
            content_has_name_args = True
    except Exception:
        pass

bug_d = bool(tool_calls_empty and content_parses and content_has_name_args)

artifact = {
    "capture_date_iso": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "captured_by": getpass.getuser(),
    "host": socket.gethostname(),
    "ollama_version": ollama_version.strip(),
    "model": model,
    "prompt": prompt,
    "tools_offered": ["forge_tools_read"],
    "bug_d_shape_confirmed": bug_d,
    "shape_evidence": {
        "tool_calls_empty_or_absent": tool_calls_empty,
        "content_parses_as_json": content_parses,
        "content_has_name_and_arguments": content_has_name_args,
        "raw_content_first_120": content[:120],
        "raw_tool_calls": tool_calls,
    },
    "notes": "Captured via capture-bug-d.sh — Phase 16.2-01 Task 1 (RED diagnosis lock).",
    "raw_response": raw,
}

print()
print("BUG_D_CONFIRMED=" + ("true" if bug_d else "false"))
print("------- BEGIN PASTE -------")
print(json.dumps(artifact, indent=2, sort_keys=False))
print("-------- END PASTE --------")
PY

echo
echo "Artifact saved at: ${RAW_OUT}"
echo "Paste the block between BEGIN PASTE / END PASTE back to the orchestrator."
