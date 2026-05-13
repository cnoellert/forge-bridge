# forge-bridge Recipes

Step-by-step workflows for the daily tasks that compose forge-bridge's five surfaces. Each recipe states when you'd reach for it, the prerequisites, the steps, and how to verify success.

Recipes assume forge-bridge is already installed — if it isn't, start with [Recipe 1: First-time setup](#recipe-1-first-time-setup).

---

## Recipe shape

Every recipe in this document follows the same skeleton:

- **Outcome** — the success target you'll reach.
- **When to use this** — the workflow situation that prompts the recipe.
- **Prerequisites** — what must be in place before starting.
- **Steps** — numbered actions with expected outcomes and dive-deeper references.
- **Verification** — concrete signals that you got what you came for.

Two optional sections appear where they earn their keep:

- **What this recipe doesn't cover** — deferred scope, surfaced when a reader is likely to expect adjacent coverage that lives elsewhere.
- **Common pitfalls** — known traps inside this specific workflow.

Each recipe closes with a **Next** pointer to its natural successor. A `**Requirement:**` line immediately under the heading maps the recipe back to its v1.5 roadmap requirement.

Recipes are not replacement reference material — they lean on [`INSTALL.md`](INSTALL.md), [`GETTING-STARTED.md`](GETTING-STARTED.md), and the in-tree `fbridge --help` / `fbridge doctor` output for substance, and provide the **workflow framing around the references**.

---

## Requirement → recipe map

| Requirement | Recipe |
|---|---|
| RECIPES-01 | [Recipe 1: First-time setup](#recipe-1-first-time-setup) |
| RECIPES-02 | [Recipe 2: Wire Claude Desktop to your bridge](#recipe-2-wire-claude-desktop-to-your-bridge) |
| RECIPES-03 | [Recipe 3: Watch a tool get synthesized](#recipe-3-watch-a-tool-get-synthesized) |
| RECIPES-04 | [Recipe 4: Drive Flame from chat](#recipe-4-drive-flame-from-chat) |
| RECIPES-05 | [Recipe 5: Approve a staged operation](#recipe-5-approve-a-staged-operation) |
| RECIPES-06 | [Recipe 6: Inspect the synthesis manifest](#recipe-6-inspect-the-synthesis-manifest) |

---

## Recipe 1: First-time setup

**Requirement:** RECIPES-01
**Outcome:** a running forge-bridge install with doctor passing and all primary surfaces reachable.
**Tracks covered:** Track A (full install, including Flame hook) and Track B (MCP-only, no Flame).

### When to use this

You sat down at a fresh workstation (or container, or VM) and you want to bring forge-bridge up end-to-end for the first time. By the end of the recipe you'll have a running MCP server, a reachable Artist Console at `http://localhost:9996/ui/`, a chat endpoint that answers a "hello" call against a local LLM, and — for Track A — a Flame hook that responds on `:9999`.

This is the workflow framing around [`INSTALL.md`](INSTALL.md). INSTALL.md is the substance — every step here references back into it. The recipe exists to make the *shape* of a fresh install legible at a glance and to flag the workflow-level pitfalls the reference doc doesn't emphasize.

### What this recipe doesn't cover

- **Recovery from a broken install.** That's `docs/TROUBLESHOOTING.md` — forthcoming under Phase 23 of the v1.5 Legibility milestone. If you ran the bootstrap once and want to re-run it cleanly, the script is idempotent (Step 3c of INSTALL.md) — but diagnosing a partial failure is a different workflow.
- **Multi-machine or multi-user deployment.** v1.5 ships the single-operator workstation install path. Multi-user and caller-identity work is intentionally deferred to v1.6+ — see `.planning/seeds/SEED-AUTH-V1.5.md`.
- **The substance of each install step.** This recipe enumerates the eight steps and the key decisions at each one; INSTALL.md is the reference for what each step does and why.

### Prerequisites

- A workstation you have `sudo` access on (Rocky/RHEL Linux or macOS Darwin — the bootstrap script auto-detects).
- A reachable Postgres-capable target. Default: local Postgres bootstrapped by the script. Remote Postgres is supported by pointing `FORGE_DB_URL` at it during Step 5.
- A reachable Ollama daemon. Default: local on `:11434`. Most operators run Ollama on a separate LLM service host because Flame saturates a workstation's GPU and RAM — set `FORGE_LOCAL_LLM_URL` to your LLM host's URL during Step 5 in that case. See INSTALL.md "Topology / network reachability" for the long version.
- **For Track A:** Flame 2026.x installed on the workstation. (Skip the Flame hook step on Track B; surfaces 1-4 work without Flame.)
- About 30 minutes for the first walk-through. Repeat installs are ~10 minutes thanks to bootstrap idempotency.
- **Stick to `qwen2.5-coder:32b` as the LLM.** `qwen3:32b` exceeds the 60-second wall-clock budget on cold start due to thinking-mode token verbosity. Context: `SEED-DEFAULT-MODEL-BUMP-V1.4.x`.

### Steps

1. **Prepare the conda env** — `conda create -n forge python=3.11 -y && conda activate forge`. Reference: INSTALL.md Step 1.
2. **Install the package with LLM extras** — `pip install -e ".[dev,llm]"`. The `[llm]` extra is **mandatory** for the chat endpoint and the learning-pipeline synthesizer; bare `pip install -e .` silently disables both. Reference: INSTALL.md Step 2.
3. **Verify Ollama reachability** — `curl -s http://YOUR-LLM-HOST:11434/api/version` (substitute `localhost` if Ollama is local). Should return JSON with a `version` field. Fix this before continuing — the chat endpoint will fail at runtime if Ollama is unreachable.
4. **Run the bootstrap script** — `sudo ./scripts/install-bootstrap.sh`. This is the heavy lifting: Postgres setup, env file install at `/etc/forge-bridge/forge-bridge.env`, systemd/launchd unit registration, alembic migrations, and a doctor verification. The script is idempotent. For Track B / MCP-only operators with an existing remote Postgres, add `--track-b --no-postgres`. Reference: INSTALL.md Step 3.
5. **Install the Flame hook (Track A only)** — `./scripts/install-flame-hook.sh`, then **relaunch Flame**. The hook auto-starts an HTTP server on `:9999` inside Flame. Reference: INSTALL.md Step 4.
6. **Confirm both daemons are running** — on Linux, `sudo systemctl status forge-bridge forge-bridge-server`; on macOS, `sudo launchctl print system/com.cnoellert.forge-bridge`. Both should be `active`/`running`. Reference: INSTALL.md Step 6.
7. **Run the post-install doctor** — `fbridge doctor`. Exit 0 means all surfaces are healthy. Exit 1 means at least one check failed; the output names which one. Reference: INSTALL.md Step 8.
8. **Smoke-test the surfaces** — open `http://localhost:9996/ui/` in a browser, confirm the five views render (tools, execs, manifest, health, chat), and use the chat tab to send `hello`. On a cold Ollama the first response can take 30-60s as the model loads; subsequent calls are sub-10s. Reference: INSTALL.md Step 7.

### Verification

You're done with this recipe when **all four** of these signals are green:

- `fbridge doctor` exits 0. (Track B: `flame_bridge: degraded` is expected — that's the Phase 07.1 graceful-degradation contract working as designed, not a failure.)
- The browser at `http://localhost:9996/ui/` renders the Artist Console and shows non-empty tools and health views.
- `curl -s http://localhost:9999/status` returns `{"status":"running","flame_available":true,...}`. (Track A only — Track B should expect connection refused on `:9999`.)
- A chat call from the Artist Console's chat tab returns a natural-language response in under 60 seconds.

### Common pitfalls

- **`qwen3:32b` as the default model.** Thinking-mode token verbosity (400-525 tok/turn) exceeds the 60s wall-clock budget. Stay on `qwen2.5-coder:32b`. If `fbridge doctor` reports the chat endpoint hitting `LLMLoopBudgetExceeded`, this is almost always the cause.
- **`pip install -e .` without `[llm]` extras.** Chat and synthesis fail silently — there's no daemon-start error, the endpoint just 500s on first call. Re-run as `pip install -e ".[dev,llm]"`.
- **Conda env vs. daemon env confusion.** The daemons run as system services with absolute python paths from the `forge` conda env. `conda activate forge` is for *your shell* (so `fbridge` resolves) — it doesn't affect the running daemons. After editing `/etc/forge-bridge/forge-bridge.env`, restart the daemon: `sudo systemctl restart forge-bridge` (Linux) or `sudo launchctl kickstart -k system/com.cnoellert.forge-bridge` (macOS).
- **Ollama unreachable from the operator host.** If `FORGE_LOCAL_LLM_URL` points at a remote LLM host, that host must be network-reachable from the workstation *at install time*. Test with `curl` (Step 3) before running the bootstrap.
- **Bootstrap script run without `sudo`.** It needs to write to `/etc/`, `/etc/systemd/system/` (Linux) or `/Library/LaunchDaemons/` (macOS), and start services. Run it with `sudo`.

### Next

[Recipe 2: Wire Claude Desktop to your bridge](#recipe-2-wire-claude-desktop-to-your-bridge) — once the install is green, the next natural step is connecting an external MCP client to it.

---

## Recipe 2: Wire Claude Desktop to your bridge

**Requirement:** RECIPES-02
**Outcome:** Claude Desktop (or another MCP-compliant client) discovers forge-bridge's tool catalogue and can invoke `forge_*` and `flame_*` tools from inside a conversation.

### When to use this

You have a healthy local forge-bridge install and want Claude Desktop (or another MCP-compliant client — Cursor, Gemini CLI) to discover bridge's tool catalogue and let an external agent operate against it.

This is the most common second step after a fresh install. Once Claude Desktop sees your bridge, you can describe pipeline tasks in natural language and let Claude pick the right tools — query staged operations, read the manifest, drive synthesized tools — without leaving the conversation.

### What this recipe doesn't cover

- **Using Claude Desktop itself.** This recipe assumes you have it installed, signed in, and know the basics of starting a conversation. Anthropic's [Claude Desktop docs](https://claude.ai/download) are the reference.
- **MCP protocol theory.** The wiring here is the *minimum* you need to make a connection; the [MCP spec](https://modelcontextprotocol.io) is the reference for the protocol itself.
- **Multi-client setups.** Cursor, Gemini CLI, and other MCP clients follow the same pattern — config file location and JSON key names differ. This recipe walks the Claude Desktop path; treat it as a template.
- **Streamable-HTTP transport.** The MCP HTTP endpoint at `http://localhost:9997/mcp` is reachable, but Claude Desktop's HTTP-transport config story is still moving — stdio is the universal path and the one this recipe walks. Check Claude Desktop's current release notes for HTTP-transport syntax if you want to use that endpoint instead.

### Prerequisites

- A completed [Recipe 1](#recipe-1-first-time-setup): bridge is installed, `fbridge doctor` exits 0, and the `forge` conda env contains the CLI.
- Claude Desktop installed and signed in.
- The **absolute path** to your `fbridge` binary inside the conda env. Find it with `which fbridge` (look for something like `/Users/you/miniconda3/envs/forge/bin/fbridge` on macOS or `/home/you/miniconda3/envs/forge/bin/fbridge` on Linux). Claude Desktop does **not** inherit your shell's `$PATH`, so an absolute path is essential.
- About 5 minutes, including a Claude Desktop restart.

### Steps

1. **Find your Claude Desktop MCP config file.** It lives at:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

   If the file doesn't exist, create it with `{}` as the body. Claude Desktop reads it once at startup.

2. **Add the forge-bridge MCP entry.** Merge this into the file, preserving any other `mcpServers` entries already there:

   ```json
   {
     "mcpServers": {
       "forge-bridge": {
         "command": "/absolute/path/to/conda/envs/forge/bin/fbridge",
         "args": ["mcp", "stdio"]
       }
     }
   }
   ```

   Substitute the path from your `which fbridge` output. The `mcp stdio` subcommand starts the FastMCP stdio transport — the surface every MCP client expects.

3. **Validate the JSON.** A trailing comma or a missing brace silently breaks the entire config and Claude Desktop will load with **no** MCP servers visible. Run `python -m json.tool < "$HOME/Library/Application Support/Claude/claude_desktop_config.json" > /dev/null` (substitute the right path on Linux / Windows); a clean exit means the file parses.

4. **Fully quit Claude Desktop.** Cmd-Q on macOS, or "Quit Claude" from the menu — closing the window is not enough. The config is only read at startup.

5. **Relaunch Claude Desktop and confirm the bridge is connected.** Open a new conversation. The MCP indicator in the chat input bar (a hammer / tools icon in recent versions) should expand to show `forge-bridge` among the connected servers, with `forge_*` and `flame_*` tools listed underneath.

### Verification

You're done when **all three** signals are green:

- The MCP indicator in Claude Desktop shows `forge-bridge` as connected (not "error", "disconnected", or "not running").
- The tool list under that server includes at least `forge_list_projects`, `forge_list_shots`, `forge_manifest_read`, and `flame_ping`.
- You can ask Claude something like "list the projects in forge-bridge" and the response shows Claude invoking `forge_list_projects` and reporting back its result (an empty list is still a valid result — what matters is that the tool ran).

### Common pitfalls

- **`command` resolved via `$PATH` instead of absolute path.** Claude Desktop launches the MCP command without your shell environment — `fbridge` alone usually fails to start with a silent error. Always use the absolute path from `which fbridge`.
- **JSON syntax errors silently disable all MCP servers.** A trailing comma, a missing brace, or an extra quote breaks the entire config — not just the offending server entry. Validate with `python -m json.tool` after every edit.
- **"Closing the window" instead of fully quitting.** macOS Claude Desktop keeps running in the background when you close the window. Cmd-Q (or "Quit Claude" from the menu) is required to reload the config.
- **Conda env not active when running `which fbridge`.** If you forget to `conda activate forge` before running `which fbridge`, you'll get the wrong path (or no path at all). Activate the env first.
- **Bare `python -m forge_bridge` as the command.** This worked in pre-v1.4.x configs but now prints help and exits — the canonical invocation is `fbridge mcp stdio` (or `python -m forge_bridge mcp stdio` if you prefer the package-relative form).

### Next

[Recipe 3: Watch a tool get synthesized](#recipe-3-watch-a-tool-get-synthesized) — with Claude Desktop wired in, the natural next step is driving workflows that trigger the learning pipeline and observing a tool promotion end-to-end.

---

## Recipe 3: Watch a tool get synthesized

**Requirement:** RECIPES-03
**Outcome:** you observe a synthesized tool's full lifecycle — from execution-log threshold crossing through LLM synthesis to a registered, callable tool — and understand the provenance recorded on it.

*(Scaffold — full text forthcoming in Phase 22.)*

### When to use this

You're using bridge in daily VFX work, the learning pipeline has observed enough repeated patterns to promote them to synthesized tools, and you want to watch a promotion happen end-to-end — from execution-log threshold crossing through LLM synthesis to a registered tool callable via MCP.

### Prerequisites

*(To be authored — anticipated: completed Recipe 1; Ollama reachable for synthesis; a workload that generates repeated executions in `~/.forge-bridge/executions.jsonl`; awareness of the probation system.)*

### Steps

*(To be authored — anticipated: tail the execution log; tail the synthesizer log; observe a promotion event in the Artist Console's manifest view; inspect the resulting synthesized tool entry; confirm the tool is callable via `fbridge run <tool_name>` or MCP.)*

### Verification

*(To be authored — anticipated: a new entry in `forge://manifest/synthesis`; `fbridge actions` lists the new tool; an invocation returns a sane result.)*

---

## Recipe 4: Drive Flame from chat

**Requirement:** RECIPES-04
**Outcome:** a multi-step Flame pipeline task completed conversationally through the chat endpoint, with the result reflected in Flame's UI and the tool-call sequence visible in the chat transcript.
**Prerequisite:** a working Flame workstation (assist-01 or equivalent — see Recipe 1 Track A).

*(Scaffold — full text forthcoming in Phase 22.)*

### When to use this

You're at a Flame workstation, you have a multi-step pipeline task that would normally require a sequence of MCP tool calls, and you want to drive it conversationally through the chat endpoint — letting the agentic tool-call loop choose tools, observe results, and synthesize an answer for you.

### Prerequisites

*(To be authored — anticipated: completed Recipe 1 Track A; Flame running with the hook on `:9999`; chat endpoint healthy in `fbridge doctor`; an example pipeline task to drive — e.g., "rename shots 010 through 015 to use the new convention".)*

### Steps

*(To be authored — anticipated: open the Artist Console chat tab or `POST /api/v1/chat` directly; phrase the intent; observe the tool-call loop in the chat panel transcript; verify the result inside Flame's UI.)*

### Verification

*(To be authored — anticipated: chat response references the tools actually called; the operation is visible in Flame; execution-log entries match the chat transcript.)*

---

## Recipe 5: Approve a staged operation

**Requirement:** RECIPES-05
**Outcome:** a proposed operation reviewed, decided, and executed (or rejected) end-to-end through the `proposed → approved → executed/rejected/failed` state machine, with the audit trail intact.
**Prerequisite:** a working Flame workstation (assist-01 or equivalent — see Recipe 1 Track A).

*(Scaffold — full text forthcoming in Phase 22.)*

### When to use this

An LLM agent or downstream consumer has proposed a destructive operation (rename, replace media, set start frames, publish) that's been parked in the staged-operation table for human review. You want to inspect the proposal, decide whether to approve or reject it, and let the proposer execute against its domain.

### Prerequisites

*(To be authored — anticipated: completed Recipe 1; at least one staged operation in `proposed` state; familiarity with the FB-A `proposed → approved → executed/rejected/failed` state machine.)*

### Steps

*(To be authored — anticipated: list staged ops via `fbridge run forge_list_staged` or the manifest view; inspect a single proposal via `forge_get_staged`; approve via `forge_approve_staged` or reject via `forge_reject_staged`; observe the state transition; confirm the proposer's downstream execution.)*

### Verification

*(To be authored — anticipated: the staged op moves to `approved`; the proposer subscribes, executes, and the op terminates in `executed` or `failed`; the audit trail is intact in `forge_get_events`.)*

---

## Recipe 6: Inspect the synthesis manifest

**Requirement:** RECIPES-06
**Outcome:** a clear picture of which tools are currently registered, where they came from, and how their provenance reconciles with the execution log.

*(Scaffold — full text forthcoming in Phase 22.)*

### When to use this

You want to audit what tools currently exist in bridge's synthesis manifest, where they came from (observation-count, code-hash, when they were synthesized), and whether any have been quarantined or promoted recently. The manifest is bridge's tool catalogue — inspecting it is the entry point for debugging "why is this tool here?" and "why isn't this tool here?".

### Prerequisites

*(To be authored — anticipated: completed Recipe 1; awareness of the `_meta.forge-bridge/*` provenance fields; access to the Artist Console manifest view or `fbridge` CLI.)*

### Steps

*(To be authored — anticipated: open the manifest view in the Artist Console; or `fbridge run forge_manifest_read`; or read the resource directly via `forge://manifest/synthesis`; cross-reference observation counts with the execution log; inspect provenance metadata on individual tools.)*

### Verification

*(To be authored — anticipated: manifest contents reconcile with `fbridge actions`; provenance fields match expected origins; quarantined tools are visibly distinguished from promoted ones.)*

---

## Cross-links

- [`INSTALL.md`](INSTALL.md) — operator-workstation install reference
- [`GETTING-STARTED.md`](GETTING-STARTED.md) — mental model + five-surface map (read this first if recipes feel ungrounded)
- [`VOCABULARY.md`](VOCABULARY.md) — canonical entity model
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — design rationale + decision log
- [`API.md`](API.md) — Flame bridge HTTP API
- `../README.md` — project overview + Quick Start
