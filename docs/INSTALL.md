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
# Ollama base URL — change to your LLM service host if Ollama is not local
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
