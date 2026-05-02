# forge-bridge Install Guide

Operator-workstation install for forge-bridge v1.4.1. Walks a fresh conda env on a workstation that runs Flame and Postgres locally and reaches an Ollama daemon over the network (typically on a separate LLM service host — Flame already saturates a workstation's GPU and RAM), all the way to a five-surface check (Web UI, CLI, chat endpoint, MCP server, Flame hook).

This is the **opinionated** path — one route through. Multi-machine deployment, multi-user / authenticated setups, and the projekt-forge consumer walkthrough are out of scope (deferred to v1.6+ and Phase 21 respectively). For design rationale, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Before you start

### What runs where

Two roles. Most Flame operators put them on separate hosts: the workstation runs Flame + bridge + Postgres; Ollama runs on a dedicated LLM service host. Single-machine is *possible* but only with substantial GPU + RAM headroom beyond what Flame already consumes — it is the exception, not the default.

**Operator host** — the Flame workstation that runs Flame + bridge + Postgres locally:

| Dependency | Required for | Minimum | Reference (tested at v1.4.1) |
|------------|-------------|---------|------------------------------|
| conda | env isolation | latest stable | conda ~24.x |
| Python | runtime | 3.10 | 3.11 |
| PostgreSQL | staged ops + execution-log SQL mirror | 14 | 16.x |
| Flame | Flame hook surface (skip for Track B) | 2026.x | 2026.2.1 |

**Reachable network services** — must respond on the operator host's network at install time:

| Service | Required for | Minimum | Reference (tested at v1.4.1) |
|---------|-------------|---------|------------------------------|
| Ollama daemon | chat endpoint + LLM tool synthesis | latest stable | 0.21.0 |
| `qwen2.5-coder:32b` model (pulled on the Ollama host) | chat + synthesis (locked default) | n/a | `ollama pull qwen2.5-coder:32b` on the LLM host |
| Anthropic API | OPTIONAL — only for `sensitive=False` cloud routing | n/a | n/a (chat hardcodes `sensitive=True`) |

**Do not use `qwen3:32b`** as the default model. Cold-start LLM thinking-mode token verbosity (400-525 tok/turn) exceeds the 60s wall-clock budget. Stay on `qwen2.5-coder:32b` (locked default). Context: `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`.

### Topology / network reachability

Ollama runs as a network service. The realistic deployment for a Flame operator is a separate LLM service host on the same network — Flame's GPU and RAM use leaves little headroom on the workstation for a 32B-parameter model. Single-machine (Ollama on the operator host) is supported, but expect contention with Flame for GPU/RAM unless you have substantial dedicated headroom. The operator host needs to *reach* Ollama — it does not need to *run* it.

The knob is `FORGE_LOCAL_LLM_URL` (Step 5). Default: `http://localhost:11434/v1`. Set it to your LLM service host's URL — e.g. `http://llm-host.local:11434/v1` or `http://10.0.0.42:11434/v1`. Leave it at the default only if you have dedicated GPU/RAM headroom for the model on the operator host.

Verify reachability from the operator host BEFORE Step 1:

```bash
# If Ollama is local:
curl -s http://localhost:11434/api/version

# If Ollama is on another host (replace with your LLM host):
curl -s http://llm-host.local:11434/api/version
```

Both should return JSON with `version`. If the remote host doesn't respond, fix that before installing — the chat endpoint will fail at runtime if it can't reach Ollama, and `forge doctor` will report `llm_router: degraded`.

Postgres has the same shape: it can be local (Step 3 default) or remote — point `FORGE_DB_URL` (Step 5) at whichever Postgres you intend to use. Most operators run Postgres locally.

### If you don't have Flame (Track B / MCP-only operators)

Skip Step 4 (Flame hook install) entirely. Surfaces 1-4 (Web UI, CLI, chat, MCP server) work without Flame. Surface 5 (Flame hook on `:9999`) will not be reachable, and the `flame_*` MCP tools will return errors when invoked. The `forge-bridge console doctor` output will mark `flame_bridge` as `degraded` rather than failing — this is expected behavior (see Phase 07.1 graceful-degradation contract).

Without Postgres, the staged-ops endpoints (`/api/v1/staged`, `forge_*_staged` MCP tools) will fail with DB connection errors. Either run Step 3 (Postgres setup) or expect those features to be unavailable. Track B operators commonly point `FORGE_LOCAL_LLM_URL` at a separate LLM service host (see Topology subsection above) — Track B does not require Ollama to be local.

---

## Step 1: Prepare the conda environment

forge-bridge expects a conda env named `forge` running Python 3.11 — this matches the reference deployment.

```bash
conda create -n forge python=3.11 -y
conda activate forge
```

Verify Python:

```bash
python --version    # Python 3.11.x
```

---

## Step 2: Install forge-bridge

Clone the repo (or `cd` into your existing checkout) and install with the LLM extras:

```bash
git clone https://github.com/cnoellert/forge-bridge.git
cd forge-bridge
pip install -e ".[dev,llm]"
```

The `[dev]` extra adds pytest + ruff for development. The `[llm]` extra adds `openai`, `anthropic`, and `ollama` — **mandatory** for the chat endpoint and the learning-pipeline tool synthesizer. Bare `pip install -e .` will silently break both.

Verify the package version self-reports correctly:

```bash
python -c "import forge_bridge; print(forge_bridge.__version__)"   # 1.4.1
```

Verify the CLI entry point installed:

```bash
forge-bridge --help
```

---

## Step 3: Run the bootstrap script

The bootstrap script handles Postgres setup, env-file install, systemd unit registration (Linux) or launchd plist registration (macOS), and the post-install `forge doctor` verification — all in one shot. Closes the Phase 20 install gaps that demanded sysadmin-level Postgres + pg_hba + service-management knowledge from operators who shouldn't need it.

**Skip this step if you are running Track B / MCP-only AND have an existing remote Postgres** — instead use the `--no-postgres` flag below.

### 3a. Run the script

```bash
sudo ./scripts/install-bootstrap.sh
```

The script auto-detects your OS (Rocky/RHEL Linux or macOS Darwin) and runs the right install path. It is **idempotent** — running it twice in a row is a no-op on the second run (operator env-file edits are preserved).

### 3b. Optional flags

Pass any combination of these flags for partial-install scenarios:

| Flag | Effect |
|---|---|
| `--track-b` | Skip Flame hook install (Track B / MCP-only deploy) |
| `--no-postgres` | Skip Postgres bootstrap entirely (use existing remote DB) |
| `--mcp-only` | `--track-b` + `--no-postgres` + skip Console daemon (BUS+MCP only) |
| `--with-flame-mac` | macOS only — opt INTO Flame hook install (default skips on macOS) |
| `--non-interactive` | Skip the FORGE_LOCAL_LLM_URL prompt; use defaults |

Run `sudo ./scripts/install-bootstrap.sh --help` for the live flag matrix.

### 3c. What the script does

On a fresh Rocky/RHEL machine:
- Installs `postgresql-server` + `postgresql-contrib` if missing
- Initializes the cluster via `postgresql-setup --initdb` if needed
- Probes the cluster's `password_encryption` (md5 vs scram-sha-256) and aligns `/var/lib/pgsql/data/pg_hba.conf` to match
- Creates the `forge` Postgres role + `forge_bridge` database (idempotent; default password `'forge'` — local-only, see Step 5 for hardening)
- Runs `alembic upgrade head` against the new database
- Installs `/etc/forge-bridge/forge-bridge.env` from the in-tree template (mode `0640 root:$YOUR_USER`)
- Copies `packaging/systemd/*.service` → `/etc/systemd/system/`, runs `systemctl daemon-reload`, enables and starts both units
- Auto-runs `forge-bridge console doctor` as the install-success gate

On macOS:
- Detects existing Postgres (`psql` on PATH, or Homebrew `postgresql@16`); installs Homebrew variant if neither present
- Skips `pg_hba` alignment (Homebrew Postgres ships `trust` for localhost)
- Same `forge` role + `forge_bridge` database creation + alembic
- Auto-applies `--track-b` (skips Flame hook); pass `--with-flame-mac` to override
- Creates `/var/log/forge-bridge/` (mode `755 root:wheel`) for daemon log files
- Copies `packaging/launchd/*.plist` → `/Library/LaunchDaemons/`, copies wrappers → `/usr/local/bin/`
- Runs `launchctl bootstrap system /Library/LaunchDaemons/com.cnoellert.forge-bridge*.plist` (modern syntax; replaces deprecated `launchctl load`)
- Same auto-doctor verification

### 3d. Custom Postgres credentials

If your Postgres role/DB is NOT the default `forge:forge@localhost:5432/forge_bridge` — for example on a shared development cluster — pass `--no-postgres` to skip the Postgres bootstrap and edit `/etc/forge-bridge/forge-bridge.env` to point `FORGE_DB_URL` at your cluster. Then run alembic manually:

```bash
alembic -x url=postgresql+psycopg2://USER:PASS@HOST:PORT/DB upgrade head
```

(The `+psycopg2` driver is required because Alembic's sync engine doesn't support `+asyncpg`. forge-bridge runtime uses `+asyncpg` per `FORGE_DB_URL` in the env file.)

---

## Step 4: Install the Flame hook

**Skip this step if you are running Track B / MCP-only.**

From the repo root:

```bash
./scripts/install-flame-hook.sh
```

Or standalone on any Flame workstation (no clone required):

```bash
curl -fsSL https://raw.githubusercontent.com/cnoellert/forge-bridge/v1.4.1/scripts/install-flame-hook.sh | bash
```

The installer copies `forge_bridge.py` into `/opt/Autodesk/shared/python/forge_bridge/scripts/`, sanity-checks it parses as Python, and prints next-step instructions. Override defaults via:

| Env var | Default | Purpose |
|---------|---------|---------|
| `FORGE_BRIDGE_VERSION` | `v1.4.1` | git tag to pull the hook from |
| `FORGE_BRIDGE_HOOK_DIR` | `/opt/Autodesk/shared/python/forge_bridge/scripts` | install target |

Launch (or relaunch) Flame. The hook auto-starts a Python HTTP server on `http://127.0.0.1:9999/`.

---

## Step 5: Configure environment

The bootstrap script (Step 3) installed `/etc/forge-bridge/forge-bridge.env` (mode `0640 root:$YOUR_USER`) — both daemons read it on start (systemd via `EnvironmentFile=`; macOS via the wrapper-script `set -a; . FILE; set +a` pattern). It is the single source of truth for forge-bridge configuration.

Closes Phase 20 gaps #7 (env persistence — the env file IS the persistence path) and #8 (conda re-init — daemons run with absolute python paths, no shell sourcing).

### 5a. Edit the env file (optional)

All defaults work for single-machine local-Ollama setups. Edit only if you need to change them — most operators set `FORGE_LOCAL_LLM_URL` once during the bootstrap script's interactive prompt and never touch the file again.

```bash
sudo $EDITOR /etc/forge-bridge/forge-bridge.env
```

Common changes:
- `FORGE_LOCAL_LLM_URL` — point at your separate Ollama host (e.g. `http://192.168.86.15:11434/v1`)
- `ANTHROPIC_API_KEY` — paste your Anthropic key if you need cloud-LLM routing (OPTIONAL — chat hardcodes `sensitive=True` and routes through local Ollama; cloud is NOT the daily operator workflow)

### 5b. Reload after editing

After edits, restart the daemons so they pick up the new values:

**Linux:**
```bash
sudo systemctl restart forge-bridge
```

**macOS:**
```bash
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge
```

Both commands are idempotent — restart is safe even if no edits were made.

### 5c. About the `forge:forge` Postgres password

The default `FORGE_DB_URL=postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge` ships with the literal password `'forge'` because the cluster is local-only on a single-operator workstation and forge-bridge has no auth surface at v1.4.x (caller-identity migration is `SEED-AUTH-V1.5`, deferred to v1.6+). If you later expose the cluster beyond localhost, rotate the role password via `psql -c "ALTER USER forge WITH PASSWORD '...';"` and update `FORGE_DB_URL` accordingly.

---

## Step 6: Verify the daemons are running

The bootstrap script (Step 3) registered TWO services on your machine and started them in the right order. forge-bridge is a two-process system:

- **`forge-bridge-server`** — the WebSocket bus on `:9998` (the canonical event-driven backplane; runs `python -m forge_bridge.server`)
- **`forge-bridge`** — the MCP server + Artist Console + chat endpoint on `:9996` (runs `python -m forge_bridge`); depends on the bus

Closes Phase 20 gap #11 — earlier versions of this doc claimed `python -m forge_bridge` boots all surfaces in one shot. That was incorrect; the bus is a separate process and must start first. systemd `Requires=` (Linux) and a wrapper-script `:9998` readiness gate (macOS) handle the ordering invisibly now.

### 6a. Linux — `systemctl`

```bash
sudo systemctl status forge-bridge-server   # WS bus on :9998
sudo systemctl status forge-bridge          # MCP + Console on :9996
```

Live logs:

```bash
sudo journalctl -u forge-bridge -f          # MCP + Console
sudo journalctl -u forge-bridge-server -f   # bus
```

Stop / restart / disable:

```bash
sudo systemctl restart forge-bridge                 # restarts MCP+Console (bus stays up)
sudo systemctl restart forge-bridge-server          # restarts bus (Console will follow due to Requires=)
sudo systemctl stop forge-bridge forge-bridge-server   # full stop
sudo systemctl disable forge-bridge forge-bridge-server   # do not start at next boot
```

### 6b. macOS — `launchctl`

```bash
sudo launchctl print system/com.cnoellert.forge-bridge-server
sudo launchctl print system/com.cnoellert.forge-bridge
```

Live logs (macOS plists write to file, not stdout — `tail -f` directly):

```bash
tail -f /var/log/forge-bridge/console.log
tail -f /var/log/forge-bridge/server.log
```

Stop / restart:

```bash
sudo launchctl kickstart -k system/com.cnoellert.forge-bridge   # restart MCP+Console
sudo launchctl bootout system /Library/LaunchDaemons/com.cnoellert.forge-bridge.plist           # stop one daemon
sudo launchctl bootout system /Library/LaunchDaemons/com.cnoellert.forge-bridge-server.plist    # stop bus too
```

### 6c. About the lifespan model

Both daemons are managed by the OS init system — systemd on Linux, launchd on macOS. Process supervision (start at boot, restart on crash, journal logging) comes for free. The stdin-keepalive workaround from earlier versions is no longer needed — daemons run as supervised services with `StandardInput=null` (Linux) or detached stdin (macOS), so the FastMCP stdio handshake-exit issue is solved at the unit level.

---

## Step 7: Verify all five surfaces

Run each smoke test. All five should pass on a Track A workstation; Surface 5 (Flame hook) will skip for Track B.

```bash
# 1. Flame hook (Track A only — needs Flame running with the hook installed)
curl -s http://localhost:9999/status
# → {"status":"running","flame_available":true,"namespace_keys":[...]}

# 2. MCP server (CLI entry point)
forge-bridge --help
# → Typer help text (subcommands: console)

# 3. Artist Console Web UI
curl -fsS http://localhost:9996/ui/ -o /dev/null -w "%{http_code}\n"
# → 200

# 4. Chat endpoint (needs Ollama + qwen2.5-coder:32b loaded)
curl -s -X POST http://localhost:9996/api/v1/chat \
  -H "content-type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
# → JSON with messages, stop_reason, request_id

# 5. Browser check — open http://localhost:9996/ui/ and confirm the five views
#    (tools, execs, manifest, health, chat) all render
```

First chat call may take 30-60s on a cold Ollama (model load). Subsequent calls are sub-10s.

---

## Step 8: Post-install diagnostic

Run the `forge doctor` check. It probes JSONL log parseability, sidecar/probation dir writability, port reachability, disk space, and the Ollama backend:

```bash
forge-bridge console doctor
```

Expected exit codes: `0` = ok, `1` = check failure, `2` = server unreachable.

`forge doctor` does **not** currently cover Postgres reachability or Ollama model presence (just daemon up). If you need those, hit them directly:

```bash
psql -h localhost -U forge -d forge_bridge -c '\dt'   # lists tables — confirms migrations + connection
ollama list | grep qwen2.5-coder                       # confirms model is pulled
```

---

## Reference: Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `FORGE_DB_URL` | `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge` | Postgres async URL — local default; set to remote Postgres URL if applicable |
| `FORGE_LOCAL_LLM_URL` | `http://localhost:11434/v1` | Ollama base URL — set to remote LLM host if Ollama runs separately |
| `FORGE_LOCAL_MODEL` | `qwen2.5-coder:32b` | Local model (do NOT use qwen3:32b) |
| `FORGE_CLOUD_MODEL` | `claude-sonnet-4-6` | Anthropic model (only used when `sensitive=False`) |
| `ANTHROPIC_API_KEY` | unset | Optional — cloud routing only |
| `FORGE_CONSOLE_PORT` | `9996` | Web UI / chat endpoint port |
| `FORGE_BRIDGE_HOST` | `127.0.0.1` | Flame bridge target host |
| `FORGE_BRIDGE_PORT` | `9999` | Flame bridge port |
| `FORGE_BRIDGE_ENABLED` | `1` | Set `0` to disable the Flame hook without uninstalling |
| `FORGE_BRIDGE_VERSION` | `v1.4.1` | (`install-flame-hook.sh` only) git tag to pull the hook from |
| `FORGE_BRIDGE_HOOK_DIR` | `/opt/Autodesk/shared/python/forge_bridge/scripts` | (`install-flame-hook.sh` only) install target |

---

## Reference: Ports

| Port | Surface | Process |
|------|---------|---------|
| `9996` | Web UI + `/api/v1/chat` + `/api/v1/staged` + Read API | `python -m forge_bridge` |
| `9998` | WebSocket event server | `python -m forge_bridge` (graceful degradation if unreachable per Phase 07.1) |
| `9999` | Flame hook HTTP server | Flame process (loads hook on launch) |

---

## Reference: LLM service host (separate-host Ollama)

If Ollama runs on a host SEPARATE from the operator workstation, that host needs:

1. The Ollama daemon installed and running on `:11434`, reachable from the operator host's network. Ollama install: <https://ollama.com/download>.
2. The locked default model pulled on that host: `ollama pull qwen2.5-coder:32b`.

That is the entire install for the LLM service host. Do NOT install bridge, Postgres, conda, or Flame on a host whose only job is to run Ollama.

On the operator host (Step 5), set:

```bash
export FORGE_LOCAL_LLM_URL="http://YOUR-LLM-HOST:11434/v1"
```

Where `YOUR-LLM-HOST` is the LLM host's hostname or IP reachable from the operator workstation.

To verify the LLM service host is healthy, from the operator host:

```bash
curl -s http://YOUR-LLM-HOST:11434/api/version              # daemon up
curl -s http://YOUR-LLM-HOST:11434/api/tags | grep qwen2.5  # model pulled
```

Both must return non-empty before Step 6 (server start) on the operator host.

---

## Reference: Cross-links

- [API.md](API.md) — Flame bridge HTTP API (`POST /exec` semantics, namespace persistence)
- [ARCHITECTURE.md](ARCHITECTURE.md) — design rationale + decision log
- [VOCABULARY.md](VOCABULARY.md) — canonical entity model (Project → Sequence → Shot → Version → Media + Stack/Layer/Asset + traits)
- [ENDPOINTS.md](ENDPOINTS.md) — guide to writing new endpoint adapters
- `../README.md` — project overview + Quick Start
- `../CLAUDE.md` — context-recovery doc for AI assistants
