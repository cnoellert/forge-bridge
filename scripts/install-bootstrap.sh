#!/usr/bin/env bash
#
# install-bootstrap.sh — bootstrap a forge-bridge install on a fresh machine.
#
# Usage:
#   sudo ./scripts/install-bootstrap.sh [flags]
#
# Flags:
#   --track-b            Skip Flame hook install (Track B / MCP-only deploy)
#   --no-postgres        Skip Postgres bootstrap (use existing remote DB)
#   --mcp-only           --track-b + --no-postgres + skip Console daemon
#   --with-flame-mac     macOS only — opt INTO Flame hook install (rare)
#   --non-interactive    Skip the FORGE_LOCAL_LLM_URL prompt
#   -h, --help           Show this help
#
# What it does:
#   1. Detects OS (Rocky/RHEL Linux or Darwin macOS) and validates pre-reqs
#   2. (Linux) dnf install + initdb + auth alignment + role+db creation + alembic upgrade
#   3. (macOS) Homebrew postgresql@16 detect/install (rare branch)
#   4. Installs /etc/forge-bridge/forge-bridge.env from the template (mode 0640)
#   5. Installs systemd units (Linux) or launchd plists + wrappers (macOS)
#   6. Substitutes __SUDO_USER__ placeholders in every copied artifact
#   7. Starts daemons (systemctl enable --now / launchctl bootstrap)
#   8. Auto-runs `forge-bridge console doctor` for verification
#
# What it does NOT do:
#   - No conda env install (operator does this in Step 1 of INSTALL.md)
#   - No pip install (operator does this in Step 2 of INSTALL.md)
#   - No Flame hook deploy (use scripts/install-flame-hook.sh for that)
#   - No Ollama install (Ollama runs on a separate LLM service host)
#   - No Homebrew auto-install on macOS (D-06 — operator-trust)

set -euo pipefail

# ── DEFAULTS ─────────────────────────────────────────────────────────────────
TRACK_B=0
NO_POSTGRES=0
MCP_ONLY=0
WITH_FLAME_MAC=0
NON_INTERACTIVE=0

usage() {
    cat <<'USAGE'
Usage: sudo ./scripts/install-bootstrap.sh [flags]

Flags:
  --track-b            Skip Flame hook install (Track B / MCP-only deploy)
  --no-postgres        Skip Postgres bootstrap (use existing remote DB)
  --mcp-only           --track-b + --no-postgres + skip Console daemon
  --with-flame-mac     macOS only — opt INTO Flame hook install (rare)
  --non-interactive    Skip the FORGE_LOCAL_LLM_URL prompt
  -h, --help           Show this help

Outcome on success: forge-bridge installed + daemonized + reachable on :9996.
Verify with: forge-bridge console doctor
USAGE
}

# ── FLAG PARSING ─────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --track-b)         TRACK_B=1 ;;
        --no-postgres)     NO_POSTGRES=1 ;;
        --mcp-only)        TRACK_B=1; NO_POSTGRES=1; MCP_ONLY=1 ;;
        --with-flame-mac)  WITH_FLAME_MAC=1 ;;
        --non-interactive) NON_INTERACTIVE=1 ;;
        -h|--help)         usage; exit 0 ;;
        *) echo "[forge-bridge] ERROR: unknown flag: $1" >&2; usage; exit 1 ;;
    esac
    shift
done

# ── PRIVILEGE ASSERTIONS ─────────────────────────────────────────────────────
[ "$EUID" -eq 0 ] || {
    echo "[forge-bridge] ERROR: must run with sudo — e.g. sudo ./scripts/install-bootstrap.sh" >&2
    exit 1
}
[ -n "${SUDO_USER:-}" ] || {
    echo "[forge-bridge] ERROR: \$SUDO_USER unset — running as actual root? Use sudo, not su." >&2
    exit 1
}

# ── OS DETECTION ─────────────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Linux)
        [ -f /etc/redhat-release ] || {
            echo "[forge-bridge] ERROR: Linux but not Rocky/RHEL — unsupported distro" >&2
            exit 1
        }
        echo "[forge-bridge] OS: Linux (Rocky/RHEL) detected"
        ;;
    Darwin)
        command -v brew >/dev/null 2>&1 || {
            echo "[forge-bridge] ERROR: macOS but Homebrew not installed — install from https://brew.sh" >&2
            exit 1
        }
        # Default: auto-apply --track-b on macOS (Flame is rare here).
        if [ "$WITH_FLAME_MAC" -eq 0 ]; then
            TRACK_B=1
            echo "[forge-bridge] macOS detected — auto-applying --track-b (skipping Flame hook); override with --with-flame-mac"
        fi
        echo "[forge-bridge] OS: Darwin (macOS) detected"
        ;;
    *)
        echo "[forge-bridge] ERROR: unsupported OS: $OS (only Linux/Rocky and Darwin/macOS are supported)" >&2
        exit 1
        ;;
esac

# ── $SUDO_USER VALIDATION (injection prevention — T-20.1-15) ─────────────────
# Validate $SUDO_USER for safe sed substitution (systemd unit injection prevention).
if ! [[ "$SUDO_USER" =~ ^[a-z][a-z0-9_-]*$ ]]; then
    echo "[forge-bridge] ERROR: \$SUDO_USER='$SUDO_USER' contains unsafe characters" >&2
    echo "[forge-bridge] ERROR: \$SUDO_USER must match ^[a-z][a-z0-9_-]*\$ — only lowercase alphanumeric, hyphen, underscore" >&2
    exit 1
fi

# ── PATH RESOLUTION ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONDA_BASE="$(sudo -u "$SUDO_USER" bash -lc 'conda info --base' 2>/dev/null || echo "/home/${SUDO_USER}/miniconda3")"
CONDA_PYTHON="${CONDA_BASE}/envs/forge/bin/python"

if [ ! -x "$CONDA_PYTHON" ]; then
    echo "[forge-bridge] ERROR: conda env 'forge' not found at $CONDA_PYTHON" >&2
    echo "[forge-bridge] HINT: complete Step 1 + Step 2 of docs/INSTALL.md before running this script" >&2
    exit 1
fi

echo "[forge-bridge] using Python: $CONDA_PYTHON"
echo "[forge-bridge] repo root:   $REPO_ROOT"
echo "[forge-bridge] operator:    $SUDO_USER"

# ── HELPER: substitute_placeholders (Pitfall 5 fix) ──────────────────────────
substitute_placeholders() {
    local file="$1"
    sudo sed -i.bak \
        -e "s|__SUDO_USER__|${SUDO_USER}|g" \
        -e "s|__CONDA_BASE__|${CONDA_BASE}|g" \
        -e "s|__REPO_ROOT__|${REPO_ROOT}|g" \
        "$file"
    sudo rm -f "${file}.bak"
}

# ── POSTGRES BOOTSTRAP — Linux (Pattern 3 verbatim) ──────────────────────────

probe_pg_auth() {
    # Print the cluster's password_encryption: 'md5' or 'scram-sha-256'.
    sudo -u postgres psql -tAc "SHOW password_encryption;" 2>/dev/null | tr -d ' '
}

resolve_pg_hba() {
    # Resolve pg_hba.conf path from the cluster itself — varies by version + install method.
    sudo -u postgres psql -tAc "SHOW hba_file;" 2>/dev/null | tr -d ' '
}

align_pg_hba() {
    local auth="$1"          # 'md5' or 'scram-sha-256'
    local pg_hba; pg_hba="$(resolve_pg_hba)"

    if [ -z "$pg_hba" ] || [ ! -f "$pg_hba" ]; then
        echo "[forge-bridge] ERROR: cannot resolve pg_hba.conf path" >&2
        return 1
    fi

    # Check if already aligned — idempotency wins.
    if grep -qE "^host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1/32[[:space:]]+${auth}" "$pg_hba"; then
        echo "[forge-bridge] pg_hba already aligned to ${auth}"
        return 0
    fi

    echo "[forge-bridge] aligning pg_hba auth method to ${auth}"
    # Backup (T-20.1-17), then edit lines matching the localhost rules.
    sudo cp "$pg_hba" "${pg_hba}.bak.$(date +%s)"
    sudo sed -i.tmp -E \
        "s|^(host[[:space:]]+all[[:space:]]+all[[:space:]]+(127\.0\.0\.1/32|::1/128)[[:space:]]+).*|\1${auth}|g" \
        "$pg_hba"
    sudo rm -f "${pg_hba}.tmp"

    sudo -u postgres psql -c "SELECT pg_reload_conf();" >/dev/null
}

bootstrap_pg() {
    echo "[forge-bridge] bootstrapping Postgres (Linux)"

    # 1. Detect: package present? cluster initialized? daemon running?
    if ! command -v psql >/dev/null 2>&1; then
        echo "[forge-bridge] psql not found — installing postgresql-server via dnf"
        sudo dnf install -y postgresql-server postgresql-contrib
    else
        echo "[forge-bridge] psql already on PATH — skipping dnf install"
    fi

    # Idempotency guard: only initdb if cluster directory absent (T-20.1-18).
    if [ ! -d /var/lib/pgsql/data/base ]; then
        echo "[forge-bridge] running postgresql-setup --initdb"
        sudo postgresql-setup --initdb
    else
        echo "[forge-bridge] cluster already initialized — skipping --initdb"
    fi

    sudo systemctl enable --now postgresql

    # 2. Wait for readiness (pg_isready is the canonical probe).
    echo "[forge-bridge] waiting for Postgres readiness on localhost:5432"
    for i in $(seq 1 30); do
        if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            echo "[forge-bridge] Postgres ready"
            break
        fi
        sleep 1
    done

    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "[forge-bridge] ERROR: Postgres did not become ready within 30s" >&2
        exit 1
    fi

    # 3. Align auth method (handles md5 on Rocky PG13 and scram-sha-256 on PG14+).
    local auth; auth="$(probe_pg_auth)"
    if [ -z "$auth" ]; then
        echo "[forge-bridge] ERROR: cannot probe password_encryption — Postgres unreachable" >&2
        exit 1
    fi
    echo "[forge-bridge] detected password_encryption: ${auth}"
    align_pg_hba "$auth"

    # 4. Idempotent role + db creation (CREATE USER forge WITH PASSWORD 'forge').
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='forge'" | grep -q 1; then
        echo "[forge-bridge] creating Postgres role 'forge'"
        sudo -u postgres psql -c "CREATE USER forge WITH PASSWORD 'forge';"
    else
        echo "[forge-bridge] Postgres role 'forge' already exists"
    fi

    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='forge_bridge'" | grep -q 1; then
        echo "[forge-bridge] creating database 'forge_bridge'"
        sudo -u postgres psql -c "CREATE DATABASE forge_bridge OWNER forge;"
    else
        echo "[forge-bridge] database 'forge_bridge' already exists"
    fi

    # 5. Run migrations against the default URL hardcoded in alembic.ini.
    echo "[forge-bridge] running alembic upgrade head"
    cd "$REPO_ROOT" && sudo -u "$SUDO_USER" "$CONDA_PYTHON" -m alembic upgrade head
}

# ── POSTGRES BOOTSTRAP — macOS (D-04 rare path) ──────────────────────────────
bootstrap_pg_macos() {
    echo "[forge-bridge] bootstrapping Postgres (macOS)"

    # Flame workstations ship with Autodesk-bundled Postgres at /opt/Autodesk/pgsql-*.
    # Detect it FIRST so we don't `brew install postgresql@16` on a host that already
    # has a working cluster. Found at portofino UAT walk during Phase 20.1; planted as
    # SEED-PHASE-20.1-POSTGRES-OWNERSHIP-V1.6+ for the deeper architectural fix
    # (forge-bridge owning the cluster vs. owning the schema).
    AUTODESK_PSQL_DIR=$(ls -d /opt/Autodesk/pgsql-*/bin 2>/dev/null | head -1)
    if [ -n "$AUTODESK_PSQL_DIR" ] && [ -x "$AUTODESK_PSQL_DIR/psql" ]; then
        echo "[forge-bridge] using Autodesk-bundled Postgres at $AUTODESK_PSQL_DIR"
        export PATH="$AUTODESK_PSQL_DIR:$PATH"
    fi

    if command -v psql >/dev/null 2>&1; then
        echo "[forge-bridge] psql already on PATH — skipping macOS Postgres install"
    elif brew list postgresql@16 >/dev/null 2>&1; then
        echo "[forge-bridge] postgresql@16 brew package present — starting via brew services"
        brew services start postgresql@16
    else
        echo "[forge-bridge] installing postgresql@16 via Homebrew (D-04 rare branch)"
        brew install postgresql@16
        brew services start postgresql@16
    fi

    # Readiness gate
    echo "[forge-bridge] waiting for Postgres readiness on localhost:5432"
    for i in $(seq 1 30); do
        if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            echo "[forge-bridge] Postgres ready"
            break
        fi
        sleep 1
    done

    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "[forge-bridge] ERROR: Postgres did not become ready within 30s" >&2
        exit 1
    fi

    # macOS Homebrew Postgres ships with `trust` for localhost — skip pg_hba alignment.
    # Idempotent role+db creation (psql defaults to current user as superuser on Homebrew).
    if ! psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='forge'" postgres 2>/dev/null | grep -q 1; then
        echo "[forge-bridge] creating Postgres role 'forge'"
        psql -c "CREATE USER forge WITH PASSWORD 'forge';" postgres
    else
        echo "[forge-bridge] Postgres role 'forge' already exists"
    fi

    if ! psql -tAc "SELECT 1 FROM pg_database WHERE datname='forge_bridge'" postgres 2>/dev/null | grep -q 1; then
        echo "[forge-bridge] creating database 'forge_bridge'"
        psql -c "CREATE DATABASE forge_bridge OWNER forge;" postgres
    else
        echo "[forge-bridge] database 'forge_bridge' already exists"
    fi

    echo "[forge-bridge] running alembic upgrade head"
    cd "$REPO_ROOT" && sudo -u "$SUDO_USER" "$CONDA_PYTHON" -m alembic upgrade head
}

# ── ENV FILE INSTALL (Pattern 4 verbatim) ────────────────────────────────────
prompt_for_llm_url() {
    if [ "$NON_INTERACTIVE" = "1" ]; then
        echo "[forge-bridge] non-interactive mode — keeping existing FORGE_LOCAL_LLM_URL"
        return 0
    fi
    local default="http://localhost:11434/v1"
    read -rp "Ollama base URL [${default}]: " url
    url="${url:-$default}"
    sudo sed -i.bak -E "s|^FORGE_LOCAL_LLM_URL=.*|FORGE_LOCAL_LLM_URL=${url}|" /etc/forge-bridge/forge-bridge.env
    sudo rm -f /etc/forge-bridge/forge-bridge.env.bak
}

install_env_file() {
    echo "[forge-bridge] installing env file at /etc/forge-bridge/forge-bridge.env"
    sudo mkdir -p /etc/forge-bridge
    if [ ! -f /etc/forge-bridge/forge-bridge.env ]; then
        sudo cp "${REPO_ROOT}/packaging/forge-bridge.env.example" /etc/forge-bridge/forge-bridge.env
        echo "[forge-bridge] installed /etc/forge-bridge/forge-bridge.env from template"
    else
        echo "[forge-bridge] /etc/forge-bridge/forge-bridge.env already exists — preserving operator edits"
    fi
    # Use $SUDO_USER's actual primary group, not the username. Linux's user-private-group
    # convention (each user has a same-named group) does NOT hold on macOS, where the
    # primary group is typically `staff` (gid 20). `id -gn` works on both platforms.
    SUDO_USER_GROUP=$(id -gn "$SUDO_USER" 2>/dev/null || echo "$SUDO_USER")
    sudo chown "root:${SUDO_USER_GROUP}" /etc/forge-bridge/forge-bridge.env
    sudo chmod 0640 /etc/forge-bridge/forge-bridge.env
    prompt_for_llm_url
}

# ── LINUX: SYSTEMD UNITS ──────────────────────────────────────────────────────
install_linux_units() {
    echo "[forge-bridge] installing systemd units"
    sudo cp "${REPO_ROOT}/packaging/systemd/forge-bridge-server.service" /etc/systemd/system/
    sudo cp "${REPO_ROOT}/packaging/systemd/forge-bridge.service" /etc/systemd/system/
    substitute_placeholders /etc/systemd/system/forge-bridge-server.service
    substitute_placeholders /etc/systemd/system/forge-bridge.service
    sudo systemctl daemon-reload
    echo "[forge-bridge] enabling + starting forge-bridge-server.service"
    sudo systemctl enable --now forge-bridge-server.service
    if [ "$MCP_ONLY" = "1" ]; then
        echo "[forge-bridge] --mcp-only — bus only; skipping forge-bridge.service start"
    else
        echo "[forge-bridge] enabling + starting forge-bridge.service"
        sudo systemctl enable --now forge-bridge.service
    fi
}

# ── macOS: LAUNCHD PLISTS + WRAPPERS ─────────────────────────────────────────
install_macos_units() {
    echo "[forge-bridge] installing launchd plists + wrappers"

    # Pitfall 2 fix: log dir MUST exist BEFORE launchctl bootstrap
    # (otherwise daemon silent-aborts with `last exit code = 78`).
    # Pitfall 2b (Phase 20.1 portofino UAT): the log dir MUST also be writable by the
    # daemon user — launchd opens StandardOutPath/StandardErrorPath BEFORE forking and
    # bails with EX_CONFIG=78 if it can't create the log file. With UserName=__SUDO_USER__
    # in the plist, root:wheel mode 755 is read-only for the daemon → silent fail.
    sudo mkdir -p /var/log/forge-bridge
    SUDO_USER_GROUP=$(id -gn "$SUDO_USER" 2>/dev/null || echo "$SUDO_USER")
    sudo chown "${SUDO_USER}:${SUDO_USER_GROUP}" /var/log/forge-bridge
    sudo chmod 755 /var/log/forge-bridge
    echo "[forge-bridge] created /var/log/forge-bridge (log directory, owned by ${SUDO_USER})"

    sudo cp "${REPO_ROOT}/packaging/launchd/com.cnoellert.forge-bridge-server.plist" /Library/LaunchDaemons/
    sudo cp "${REPO_ROOT}/packaging/launchd/com.cnoellert.forge-bridge.plist" /Library/LaunchDaemons/
    sudo cp "${REPO_ROOT}/packaging/launchd/forge-bridge-server-daemon" /usr/local/bin/
    sudo cp "${REPO_ROOT}/packaging/launchd/forge-bridge-daemon" /usr/local/bin/
    sudo chmod +x /usr/local/bin/forge-bridge-server-daemon /usr/local/bin/forge-bridge-daemon

    # Substitute placeholders in all copied artifacts (Pitfall 5 fix).
    substitute_placeholders /Library/LaunchDaemons/com.cnoellert.forge-bridge-server.plist
    substitute_placeholders /Library/LaunchDaemons/com.cnoellert.forge-bridge.plist
    substitute_placeholders /usr/local/bin/forge-bridge-server-daemon
    substitute_placeholders /usr/local/bin/forge-bridge-daemon

    # Idempotent: bootout-then-bootstrap is the modern reload path (RESEARCH.md TL;DR item 10).
    echo "[forge-bridge] bootstrapping forge-bridge-server.plist via launchctl"
    sudo launchctl bootout system /Library/LaunchDaemons/com.cnoellert.forge-bridge-server.plist 2>/dev/null || true
    sudo launchctl bootstrap system /Library/LaunchDaemons/com.cnoellert.forge-bridge-server.plist

    if [ "$MCP_ONLY" = "1" ]; then
        echo "[forge-bridge] --mcp-only — bus only; skipping forge-bridge.plist bootstrap"
    else
        echo "[forge-bridge] bootstrapping forge-bridge.plist via launchctl"
        sudo launchctl bootout system /Library/LaunchDaemons/com.cnoellert.forge-bridge.plist 2>/dev/null || true
        sudo launchctl bootstrap system /Library/LaunchDaemons/com.cnoellert.forge-bridge.plist
    fi
}

# ── DOCTOR VERIFICATION (D-12 auto-run) ──────────────────────────────────────
verify_doctor() {
    echo "[forge-bridge] running post-install verification (forge-bridge console doctor)"
    # Run as the operator user — doctor is operator-account state, not root.
    if sudo -u "$SUDO_USER" "$CONDA_PYTHON" -m forge_bridge console doctor; then
        echo "[forge-bridge] doctor PASS or PARTIAL — install OK"
        return 0
    else
        echo "[forge-bridge] doctor FAIL — see output above for the failing row"
        return 1
    fi
}

# ── MAIN ─────────────────────────────────────────────────────────────────────
echo "[forge-bridge] starting forge-bridge install bootstrap"
echo "[forge-bridge] flags: TRACK_B=${TRACK_B} NO_POSTGRES=${NO_POSTGRES} MCP_ONLY=${MCP_ONLY} WITH_FLAME_MAC=${WITH_FLAME_MAC} NON_INTERACTIVE=${NON_INTERACTIVE}"

case "$OS" in
    Linux)
        [ "$NO_POSTGRES" = "1" ] || bootstrap_pg
        install_env_file
        install_linux_units
        ;;
    Darwin)
        [ "$NO_POSTGRES" = "1" ] || bootstrap_pg_macos
        install_env_file
        install_macos_units
        ;;
esac

verify_doctor

cat <<'NEXT'

[forge-bridge] Install complete. Next steps:

  1. Visit the Artist Console at http://localhost:9996/ui/
  2. Inspect daemon logs (Linux):
       sudo journalctl -u forge-bridge -f
       sudo journalctl -u forge-bridge-server -f
  3. Inspect daemon logs (macOS):
       tail -f /var/log/forge-bridge/console.log
       tail -f /var/log/forge-bridge/server.log
  4. Re-run the doctor any time:
       forge-bridge console doctor

NEXT
