#!/usr/bin/env bash
#
# install-flame-hook.sh — deploy the forge-bridge Flame hook to a workstation.
#
# Usage:
#   # From a clone:
#   ./scripts/install-flame-hook.sh
#
#   # Standalone (no clone — downloads hook from GitHub at pinned tag):
#   curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.9.3/scripts/install-flame-hook.sh | bash
#
# Environment overrides:
#   FORGE_BRIDGE_VERSION   git tag to pull the hook from (default: v1.9.3)
#   FORGE_BRIDGE_HOOK_DIR  install target (default: /opt/Autodesk/shared/python/forge_bridge/scripts)
#
# What it does:
#   1. Resolves the hook source — prefers a local clone's file, falls back to a pinned GitHub raw URL.
#   2. Copies (or downloads) forge_bridge.py into Flame's Python hooks directory.
#   3. Parses the result with python3 as a lightweight sanity check.
#   4. Prints next-steps for Flame launch + bridge verification.
#
# What it does NOT do:
#   - No MCP server install (that's conda env + pip; see README § "Install the MCP server").
#   - No Flame restart — you must relaunch Flame for the hook to load.
#   - No sudo assumed — /opt/Autodesk/shared/python is world-writable on standard Flame installs.

set -euo pipefail

VERSION="${FORGE_BRIDGE_VERSION:-v1.9.3}"
TARGET_DIR="${FORGE_BRIDGE_HOOK_DIR:-/opt/Autodesk/shared/python/forge_bridge/scripts}"
SOURCE_URL="https://raw.githubusercontent.com/cnoellert/forge-bridge/${VERSION}/flame_hooks/forge_bridge/scripts/forge_bridge.py"

# Resolve the directory this script lives in (when invoked from a checkout).
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  LOCAL_HOOK="${SCRIPT_DIR}/../flame_hooks/forge_bridge/scripts/forge_bridge.py"
else
  # Invoked via stdin (curl | bash) — no script path to anchor to.
  LOCAL_HOOK=""
fi

echo "[forge-bridge] target: ${TARGET_DIR}"

if ! mkdir -p "${TARGET_DIR}" 2>/dev/null; then
  echo "[forge-bridge] ERROR: cannot create ${TARGET_DIR} — retry with sudo or set FORGE_BRIDGE_HOOK_DIR" >&2
  exit 1
fi

if [ -n "${LOCAL_HOOK}" ] && [ -f "${LOCAL_HOOK}" ]; then
  echo "[forge-bridge] source: ${LOCAL_HOOK} (local checkout)"
  cp "${LOCAL_HOOK}" "${TARGET_DIR}/forge_bridge.py"
else
  echo "[forge-bridge] source: ${SOURCE_URL} (remote)"
  if ! command -v curl >/dev/null 2>&1; then
    echo "[forge-bridge] ERROR: curl not found — install curl or run from a clone" >&2
    exit 1
  fi
  curl -fsSL "${SOURCE_URL}" -o "${TARGET_DIR}/forge_bridge.py"
fi

# Sanity: file parses as Python. Catches a truncated download or mangled paste.
if command -v python3 >/dev/null 2>&1; then
  if ! python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())" "${TARGET_DIR}/forge_bridge.py" 2>/dev/null; then
    echo "[forge-bridge] ERROR: installed hook fails Python parse — investigate ${TARGET_DIR}/forge_bridge.py" >&2
    exit 1
  fi
fi

# --- Stray-hook hygiene (bridge #173) -------------------------------------
# Flame imports every .py under its hooks paths on rescan. A stray
# forge_llm_test.py from an earlier deploy generation runs network integration
# tests at module import time, blocking Flame's main thread 60s+ when the LLM
# host is down. Remove that known hazard outright; warn about anything else.
if [ -f "${TARGET_DIR}/forge_llm_test.py" ]; then
  rm -f "${TARGET_DIR}/forge_llm_test.py"
  # find is nullglob-safe under `set -euo pipefail` (a bare glob would not be).
  find "${TARGET_DIR}/__pycache__" -maxdepth 1 -name 'forge_llm_test.*.pyc' -delete 2>/dev/null || true
  echo "[forge-bridge] removed stray ${TARGET_DIR}/forge_llm_test.py — known import-time-network hazard that blocks Flame's main thread on hook rescan (bridge #173)"
fi

# Warn about (but do NOT delete) any other .py files here: on older flat-layout
# deployments this directory doubles as projekt-forge's shared-module home (its
# hooks resolve ../../forge_bridge/scripts), so an unconditional sweep would
# break live consumers on those machines.
OTHER_PY="$(find "${TARGET_DIR}" -maxdepth 1 -name '*.py' ! -name 'forge_bridge.py' 2>/dev/null || true)"
if [ -n "${OTHER_PY}" ]; then
  echo "" >&2
  echo "[forge-bridge] WARNING: unexpected .py files found in ${TARGET_DIR}:" >&2
  printf '%s\n' "${OTHER_PY}" | while IFS= read -r f; do
    echo "  ${f}" >&2
  done
  echo "[forge-bridge] Flame imports every .py under its hooks paths on rescan (bridge #173)." >&2
  echo "[forge-bridge] Verify none of these execute anything (especially network calls) at import time." >&2
  echo "[forge-bridge] Left in place: shared modules may live here on older flat-layout deployments." >&2
  echo "" >&2
fi
# ---------------------------------------------------------------------------

ls -l "${TARGET_DIR}/forge_bridge.py"

cat <<'NEXT'

[forge-bridge] Hook deployed. Next steps:

  1. Launch (or relaunch) Flame. The bridge auto-starts on http://127.0.0.1:9999/
  2. Verify the bridge responds:

       curl -s http://localhost:9999/ -o /dev/null -w "%{http_code}\n"
       # expect: 200

  3. Optional round-trip against Flame's main thread (needs Flame focused):

       curl -s -X POST http://localhost:9999/exec -d 'flame.__name__' -m 30
       # expect: {"result": "flame", ...}

Environment overrides available on next Flame launch:
  FORGE_BRIDGE_HOST=0.0.0.0    # bind to LAN (default: 127.0.0.1)
  FORGE_BRIDGE_PORT=9999       # change port
  FORGE_BRIDGE_ENABLED=0       # disable without uninstalling

NEXT
