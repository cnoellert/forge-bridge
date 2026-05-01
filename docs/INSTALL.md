# forge-bridge Install Guide

Single-machine operator install for forge-bridge v1.4.1. Walks a fresh conda env on a workstation that already has Flame, Postgres, and Ollama running, all the way to a five-surface check (Web UI, CLI, chat endpoint, MCP server, Flame hook).

This is the **opinionated** path — one route through. Multi-machine deployment, multi-user / authenticated setups, and the projekt-forge consumer walkthrough are out of scope (deferred to v1.6+ and Phase 21 respectively). For design rationale, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Before you start

### External dependencies

Set these up BEFORE following the steps below. Install will fail mid-flight if any are missing.

| Dependency | Required for | Minimum | Reference (tested at v1.4.1) |
|------------|-------------|---------|------------------------------|
| conda | env isolation | latest stable | conda ~24.x |
| Python | runtime | 3.10 | 3.11 |
| PostgreSQL | staged ops + execution-log SQL mirror | 14 | 16.x |
| Ollama | chat endpoint + LLM tool synthesis | latest stable | 0.21.0 |
| `qwen2.5-coder:32b` model | chat + synthesis (locked default) | n/a | pulled via `ollama pull qwen2.5-coder:32b` |
| Flame | Flame hook surface (skip for Track B) | 2026.x | 2026.2.1 |
| Anthropic API key | OPTIONAL — only for `sensitive=False` cloud routing | n/a | n/a (chat hardcodes `sensitive=True`) |

**Do not use `qwen3:32b`** as the default model. Cold-start LLM thinking-mode token verbosity (400-525 tok/turn) exceeds the 60s wall-clock budget. Stay on `qwen2.5-coder:32b` (locked default). Context: `.planning/seeds/SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`.

### If you don't have Flame (Track B / MCP-only operators)

Skip Step 4 (Flame hook install) entirely. Surfaces 1-4 (Web UI, CLI, chat, MCP server) work without Flame. Surface 5 (Flame hook on `:9999`) will not be reachable, and the `flame_*` MCP tools will return errors when invoked. The `forge-bridge console doctor` output will mark `flame_bridge` as `degraded` rather than failing — this is expected behavior (see Phase 07.1 graceful-degradation contract).

Without Postgres, the staged-ops endpoints (`/api/v1/staged`, `forge_*_staged` MCP tools) will fail with DB connection errors. Either run Step 3 (Postgres setup) or expect those features to be unavailable.

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

## Step 3: Set up Postgres

forge-bridge defaults to `forge:forge@localhost:5432/forge_bridge`. Either match those defaults or set `FORGE_DB_URL` to your own.

Default-credential setup:

```bash
# As a Postgres superuser:
createuser -P forge          # set password 'forge' when prompted
createdb -O forge forge_bridge
```

Run the three Alembic migrations:

```bash
# From the repo root:
alembic upgrade head
```

**Note on Alembic + custom credentials:** `alembic.ini` hardcodes the sync URL `postgresql+psycopg2://forge:forge@localhost:5432/forge_bridge` and does NOT auto-read `FORGE_DB_URL`. If you set `FORGE_DB_URL` to non-default credentials in Step 5, you must also either:
- edit `sqlalchemy.url` in `alembic.ini`, OR
- pass the URL explicitly: `alembic -x url=postgresql+psycopg2://USER:PASS@HOST:PORT/DB upgrade head`

Verify migrations applied:

```bash
alembic current   # shows 0003_staged_operation as the head revision
```

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

## Step 5: Configure environment variables

All forge-bridge configuration is via environment variables — there is no config file. Set these in your shell or `.env` profile (do **not** commit secrets to a version-controlled file).

Required for the daily operator workflow:

```bash
# Postgres connection (override the default if your credentials differ)
export FORGE_DB_URL="postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge"
```

Optional (defaults are usually fine):

```bash
# Ollama backend (default http://localhost:11434/v1)
export FORGE_LOCAL_LLM_URL="http://localhost:11434/v1"

# Local model (default qwen2.5-coder:32b — DO NOT use qwen3:32b, see warning above)
export FORGE_LOCAL_MODEL="qwen2.5-coder:32b"

# Flame target host (default 127.0.0.1)
export FORGE_BRIDGE_HOST="127.0.0.1"

# Web UI / chat endpoint port (default 9996)
export FORGE_CONSOLE_PORT="9996"
```

Optional — cloud LLM routing (NOT required for the daily operator workflow; chat hardcodes `sensitive=True` which routes through local Ollama):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export FORGE_CLOUD_MODEL="claude-sonnet-4-6"
```

**Anthropic key handling:** put it in your shell profile (`~/.zshrc` / `~/.bashrc`) or a sourced `.env` file outside version control. Never paste it on the command line directly (shell history will capture it). Never commit it to git.

---

## Step 6: Start the server

The single `python -m forge_bridge` process boots **all four hosted surfaces in one shot** — MCP server (stdio), Artist Console Web UI (`:9996`), chat endpoint (`:9996/api/v1/chat`), and the WebSocket event server (`:9998`).

Daily local launch:

```bash
python -m forge_bridge
```

On a headless host where stdin closes immediately (deploy hosts, ssh-detached sessions), keep stdin alive so FastMCP doesn't exit:

```bash
tail -f /dev/null | python -m forge_bridge
```

The first run auto-creates the operator-facing artifact directory `~/.forge-bridge/`:

```
~/.forge-bridge/executions.jsonl    # source-of-truth execution log
~/.forge-bridge/synthesized/        # auto-promoted MCP tool Python files
~/.forge-bridge/probation/          # in-probation tool state
~/.forge-bridge/quarantined/        # quarantined tool state
```

Leave the server running in another terminal / tmux pane and proceed to Step 7.

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
| `FORGE_DB_URL` | `postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge` | Postgres async URL |
| `FORGE_LOCAL_LLM_URL` | `http://localhost:11434/v1` | Ollama base URL |
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

## Reference: Cross-links

- [API.md](API.md) — Flame bridge HTTP API (`POST /exec` semantics, namespace persistence)
- [ARCHITECTURE.md](ARCHITECTURE.md) — design rationale + decision log
- [VOCABULARY.md](VOCABULARY.md) — canonical entity model (Project → Sequence → Shot → Version → Media + Stack/Layer/Asset + traits)
- [ENDPOINTS.md](ENDPOINTS.md) — guide to writing new endpoint adapters
- `../README.md` — project overview + Quick Start
- `../CLAUDE.md` — context-recovery doc for AI assistants
