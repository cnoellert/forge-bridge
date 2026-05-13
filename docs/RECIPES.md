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
| RECIPES-03 | [Recipe 3: Observe the synthesis pipeline operate](#recipe-3-observe-the-synthesis-pipeline-operate) |
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

3. **Validate the JSON.** A trailing comma or a missing brace silently breaks the entire config and Claude Desktop will load with **no** MCP servers visible. Run `python -m json.tool "<path-to-config>"` against the file you just edited (use the path from Step 1; keep the quotes to survive the space in the macOS path). If it prints the formatted JSON, the file parses; if it prints `Expecting ...` with a line/column, fix the indicated syntax error and retry.

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

[Recipe 3: Observe the synthesis pipeline operate](#recipe-3-observe-the-synthesis-pipeline-operate) — with Claude Desktop wired in, the natural next step is making the synthesis pipeline's behavior visible end-to-end.

---

## Recipe 3: Observe the synthesis pipeline operate

**Requirement:** RECIPES-03
**Outcome:** you can observe every stage of the synthesis pipeline on a stock install — execution log, threshold crossing, LLM generation, watcher registration, manifest publication — and you know which surfaces reveal what.

### When to use this

forge-bridge ships the synthesis pipeline and the persistence substrate; a *consumer application* is responsible for recording execution patterns into that substrate. In production, [projekt-forge](https://github.com/cnoellert/projekt-forge) plays this role — its tools call `ExecutionLog.record(code, intent)` during real Flame work, and the pipeline reacts. This recipe uses a small demo driver so you can observe the pipeline directly on a stock install, without depending on a consumer.

You'd reach for this recipe when you want to understand operationally what the synthesis pipeline does — which files it writes, which thresholds it watches, which logs surface which events — so that when synthesis fires during real work, you know how to read it.

### What this recipe doesn't cover

- **Tuning the synthesis prompt or the LLM model.** The synthesizer ships with its own system prompt and uses `qwen2.5-coder:32b` for sensitive routing. Modifying either is internal-development territory, not a daily operator workflow.
- **Pre-synthesis hooks.** The `pre_synthesis_hook` extension point exists for consumers to inject domain context into the synthesis prompt; that's consumer-side configuration, out of scope here.
- **Debugging failed synthesis.** When synthesis errors out (LLM unreachable, syntax error in output, safety check fails), the daemon logs a `WARNING: Synthesis failed: <reason>`. Recovery and tuning belong in `docs/TROUBLESHOOTING.md` — forthcoming under Phase 23.

### Prerequisites

- A completed [Recipe 1](#recipe-1-first-time-setup): bridge is installed, both daemons are running, `fbridge doctor` exits 0.
- Ollama reachable and `qwen2.5-coder:32b` pulled. Synthesis is an LLM call; if `fbridge doctor` reports `llm_router: degraded`, fix that first.
- The `forge` conda env active in the shell you'll run the driver from (`conda activate forge`) — the driver imports `forge_bridge` directly.
- About 5 minutes. The first synthesis call may take 30-60s as Ollama loads the model.

### Steps

1. **Set up two observability terminals.** You'll watch the execution log and the daemon log in parallel.

   ```bash
   # Terminal A — execution log (operator-facing JSONL):
   tail -f ~/.forge-bridge/executions.jsonl
   ```

   ```bash
   # Terminal B — daemon log (synthesizer events surface here):
   sudo journalctl -u forge-bridge -f         # Linux
   tail -f /var/log/forge-bridge/console.log    # macOS
   ```

2. **Save and run the demo driver.** Save this to a temp file (e.g. `/tmp/synth_demo.py`) and run it from the `forge` env. The promotion threshold defaults to **3** observations of the same normalized pattern; override via `FORGE_PROMOTION_THRESHOLD` in `/etc/forge-bridge/forge-bridge.env`.

   ```python
   import asyncio
   from forge_bridge.learning.execution_log import ExecutionLog, normalize_and_hash
   from forge_bridge.learning.synthesizer import SkillSynthesizer

   log, synth = ExecutionLog(), SkillSynthesizer()
   intent = "set the project's frame rate"

   # Three calls with different integer literals. AST normalization strips
   # the literals, so all three count as observations of the SAME pattern.
   for code in [
       "flame.projects.current_project.frame_rate = 24",
       "flame.projects.current_project.frame_rate = 25",
       "flame.projects.current_project.frame_rate = 30",
   ]:
       promoted = log.record(code, intent=intent)
       _, h = normalize_and_hash(code)
       count = log.get_count(h)
       print(f"  recorded: count={count}  promoted={promoted}")
       if promoted:
           path = asyncio.run(synth.synthesize(raw_code=code, intent=intent, count=count))
           print(f"  synthesized: {path}")
           log.mark_promoted(h)
   ```

   ```bash
   conda activate forge
   python /tmp/synth_demo.py
   ```

3. **Watch the lifecycle unfold.** Across the two observability terminals you should see, in order:
   - **Terminal A (execution log):** three new JSONL rows appear, one per `record()` call. The three rows share the same `code_hash` — AST normalization at work.
   - **Driver stdout:** `promoted=False` on the first two calls, `promoted=True` on the third. After the True, `synthesized: <path>` prints with a path under `~/.forge-bridge/synthesized/`.
   - **Terminal B (daemon log):** the watcher picks up the new file and registers it. Expect a few seconds of lag — the watcher polls the synthesized directory at intervals.

4. **Inspect the synthesized tool on disk.**

   ```bash
   ls -la ~/.forge-bridge/synthesized/
   head -40 ~/.forge-bridge/synthesized/<name>.py
   ```

   The file is a Python module with a single decorated function — that's what the watcher registers as an MCP tool.

5. **Confirm the tool is registered and inspect its provenance.**

   ```bash
   fbridge actions | grep <name>
   fbridge run forge_manifest_read --json | jq '.result.data.tools[] | select(.name == "<name>")'
   ```

   You'll see `origin: "synthesized"`, a `code_hash`, `synthesized_at` timestamp, `version`, and `observation_count: 3` matching the threshold that triggered synthesis. (Recipe 6 walks the full manifest-inspection surface — this step's invocation is the minimum to confirm the new tool landed.)

### Verification

You're done when **all five** signals are green:

- `~/.forge-bridge/executions.jsonl` grew by exactly 3 rows (one per driver call).
- The driver printed `promoted=True` on the 3rd call and `synthesized: <path>` after it.
- A new `<name>.py` file exists under `~/.forge-bridge/synthesized/`.
- The daemon log shows `INFO: Synthesized tool written: <path>`.
- `fbridge actions` lists the new tool, and its manifest provenance fields are populated as above.

### Common pitfalls

- **Ollama unreachable when the driver runs.** Synthesis silently skips with `WARNING: LLM unavailable — skipping synthesis` in the daemon log. The three JSONL rows still get written and the threshold-cross still fires, but no tool file gets created. Fix Ollama reachability first (`curl http://YOUR-LLM-HOST:11434/api/version`).
- **Re-running the driver without changing the pattern.** Once a hash is marked promoted, the same hash won't re-promote — the third call returns `False` and no new synthesis fires. To re-run the demo against a fresh pattern, change the demo code beyond literal substitution (e.g., assign `start_frame` instead of `frame_rate`) so it normalizes to a different hash. Wiping `~/.forge-bridge/executions.jsonl` works too but destroys all history.
- **Driver fails with `ImportError: forge_bridge`.** The `forge` conda env isn't active in your shell. Run `conda activate forge` and retry.
- **Tool doesn't appear in `fbridge actions` immediately.** The registry watcher polls the synthesized directory rather than using filesystem-notification events on every platform. Wait a few seconds and retry.
- **Reading the wrong synthesizer log on macOS.** macOS daemon logs go to `/var/log/forge-bridge/console.log`, not `journalctl`. If Terminal B shows no synthesizer events, you may be reading the wrong stream.

### Next

[Recipe 6: Inspect the synthesis manifest](#recipe-6-inspect-the-synthesis-manifest) — once you've watched the synthesis pipeline fire, the natural next step is auditing the artifact it produced. Inspectability is where operator trust starts; recipe numbering follows the requirement IDs, but the readable traversal jumps to 6 here.

---

## Recipe 4: Drive Flame from chat

**Requirement:** RECIPES-04
**Outcome:** you can drive Flame state queries through the chat endpoint conversationally — phrase a question in natural language, watch the agent pick the right Flame tool, see the structured result, and read a synthesized answer.
**Prerequisite:** Flame running with the hook installed; canonical topology **portofino** (see Topology note below).

### When to use this

You want to ask the bridge questions about Flame state in natural language — "what's on my desktop?", "what project am I in?", "list the libraries in this project" — and let the agentic tool-call loop pick the right tool, execute it, and synthesize a natural-language answer. This is the entry point for chat-driven workflows: a human-readable query in, a human-readable answer out, with every intermediate tool call visible in the transcript.

This recipe is read-heavy and deliberately stays clear of destructive operations. Recipe 5 covers the *authority* shape — what happens when chat proposes a destructive operation and a human has to approve before it executes.

### What this recipe doesn't cover

- **Destructive operations through chat.** Anything that mutates Flame state (rename, replace media, set start frames, publish) routes through the staged-operation state machine in v1.4+ — covered in [Recipe 5](#recipe-5-approve-a-staged-operation). Chat proposes; humans decide.
- **Multi-host distributed deployment.** This recipe uses the converged single-host topology (see Topology note below). Splitting LLM, bridge, and Flame across hosts changes operator commands (URLs, log paths) but not the chat-loop behavior — that's a future advanced recipe or Phase 23 troubleshooting concern, not this recipe's job.
- **Tool prompt or system-prompt tuning.** The chat endpoint ships with `LLMRouter` defaults; modifying them is internal-development territory.

### Prerequisites

- A completed [Recipe 1](#recipe-1-first-time-setup): bridge is installed, both daemons are running, `fbridge doctor` exits 0.
- A completed [Recipe 3](#recipe-3-observe-the-synthesis-pipeline-operate) is **strongly recommended** — knowing how to read the synthesis pipeline makes the chat-loop tool selection legible.
- **Flame running with the hook installed on the bridge host.** `flame_ping` should return `flame_available: true`.
- About 5 minutes. First chat call may take 30-60s for Ollama cold start.

**Topology note:** This recipe uses the **portofino** topology — LLM + bridge + Flame on a single host. In larger studio deployments these surfaces live on separate machines (e.g. `assist-01` for the LLM runtime, `flame-01` for Flame, with bridge services routing between them). The chat-loop behavior is identical across topologies; commands referencing `localhost` would need network-aware substitutions in distributed setups. Authoring against the converged topology keeps operator focus on workflow, authority, and orchestration rather than distributed-infra debugging.

### Steps

1. **Confirm Flame is reachable.** From the bridge host:

   ```bash
   fbridge run flame_ping --json | jq '.result'
   # → expected: {"flame_available": true, ...}
   ```

   If `flame_available` is `false`, relaunch Flame (the hook auto-starts on launch) before proceeding.

2. **Open the Artist Console chat panel.** Point a browser at `http://localhost:9996/ui/` and click the chat tab. (You can also POST directly to `http://localhost:9996/api/v1/chat`; the chat tab is the easiest visual surface for this recipe.)

3. **Ask a Flame state question.** Type a natural-language query:

   ```
   What's on my Flame desktop right now?
   ```

   The agent should pick the `flame_list_desktop` tool, call it, observe the result, and synthesize a natural-language answer.

4. **Read the tool-call trace.** The chat panel shows the agent's intermediate steps — each tool call (e.g. `flame_list_desktop({})`), each tool result (the structured response from Flame), and the final assistant message. **Every tool call is visible.** This is the observable-authority story: nothing happens behind the scenes.

5. **Verify against Flame's UI.** Switch to Flame and look at the actual desktop. The reels, clips, and groups the agent reported should match what you see directly.

6. **(Optional) Try a multi-step question.** Ask something that requires more than one tool call:

   ```
   What project am I in, and what libraries does it contain?
   ```

   Watch the agent call `flame_get_project`, observe the result, then call `flame_list_libraries`, observe that result, then synthesize. The trace shows the full sequence.

### Verification

You're done when **all four** signals are green:

- The chat response is a natural-language answer (not raw JSON, not an error).
- The trace shows at least one `flame_*` tool call with a structured result.
- The result matches what you see in Flame's UI directly.
- The chat call returned in under 60s (cold Ollama may push the first call to 60s; subsequent calls are sub-10s).

### Common pitfalls

- **Flame hook unreachable.** If `flame_ping` returns `flame_available: false`, Flame either isn't running or the hook didn't load. Relaunch Flame and confirm the hook starts its HTTP server on `:9999` (check Flame's stdout).
- **`LLMLoopBudgetExceeded` on cold start.** Almost always a model-choice problem — the chat endpoint hardcodes `sensitive=True` and routes through local Ollama. If you swapped the model to `qwen3:32b`, thinking-mode token verbosity blows the 60s wall-clock budget. Revert to `qwen2.5-coder:32b`.
- **Agent responds with raw JSON instead of executing.** This was Phase 16.2's Bug D — the LLM emitting tool-call shapes in the `content` field instead of the structured `tool_calls` field. The `OllamaToolAdapter` salvages it now; if you see raw JSON tool-call shapes in the response, file a bug.
- **Asking a destructive question through chat.** Chat won't directly execute destructive operations — those route through staged ops. If you ask "rename shot ABC to XYZ", expect the agent to create a staged proposal and ask you to approve it via [Recipe 5](#recipe-5-approve-a-staged-operation).

### Next

[Recipe 5: Approve a staged operation](#recipe-5-approve-a-staged-operation) — chat drives state queries directly; destructive operations go through the staged-ops state machine for human approval. Authority before execution.

---

## Recipe 5: Approve a staged operation

**Requirement:** RECIPES-05
**Outcome:** a destructive operation proposed → reviewed → decided through the `proposed → approved/rejected` state machine, with the audit trail intact and authority gated at the human review step.
**Prerequisite:** bridge install per Recipe 1; canonical topology **portofino** (see Topology note below).

### When to use this

You want to understand how the bridge enforces human authority over destructive operations. Read-only state queries (Recipe 4) flow through chat directly; destructive operations (rename, replace media, set start frames, publish) park in the **staged-operation state machine** until a human inspects and decides. The bridge does not bypass this — by design, the only path from "agent wants to do something destructive" to "Flame actually does it" runs through human approval.

This is the **observable authority boundary**. Recipe 6 taught you how to audit the *artifacts* the bridge produces; this recipe teaches you how to audit (and decide on) the *actions* it proposes.

### What this recipe doesn't cover

- **The propose-side tools.** Like the synthesis pipeline (Recipe 3), bridge ships the staged-ops **substrate** — the state machine table, the approval/rejection tools, the audit log — but a *consumer application* provides the propose-side tools that put proposals INTO the table. In production, projekt-forge exposes `forge_stage_rename`, `forge_stage_publish_shots`, `forge_stage_set_startframes` and similar via its own MCP server. forge-bridge alone ships only `forge_list_staged` / `forge_get_staged` / `forge_approve_staged` / `forge_reject_staged` — the approval surface. This recipe uses a tiny demo driver to mint a proposal directly, mirroring Recipe 3's pattern.
- **Downstream execution after approval.** Approval is bookkeeping; the proposer subscribes to `staged.approved` events and executes against its own domain. Without a consumer wired, an approved op sits at `approved` indefinitely — the state machine itself works correctly, but no Flame mutation happens. The recipe's demonstrable scope stops at the approval event; production behavior includes the downstream execution.
- **Multi-host distributed deployment.** Single-host portofino topology assumed (see Topology note below).

### Prerequisites

- A completed [Recipe 1](#recipe-1-first-time-setup): bridge is installed, both daemons are running, `fbridge doctor` exits 0.
- [Recipe 4](#recipe-4-drive-flame-from-chat) and [Recipe 6](#recipe-6-inspect-the-synthesis-manifest) recommended for vocabulary continuity (chat-loop framing + JSON inspection patterns).
- The `forge` conda env active in the shell you'll run the driver from (`conda activate forge`).
- About 5 minutes.

**Topology note:** Same as Recipe 4 — converged **portofino** topology is canonical (LLM + bridge + Flame on one host); distributed `assist-01` + `flame-01` deployments work the same with network-aware command substitutions.

### Steps

1. **Save and run the demo driver to mint a staged proposal.** Save this to `/tmp/staged_demo.py` and run it from the `forge` env. The driver inserts a row into the `staged_operation` table with `status='proposed'` and emits a `staged.proposed` audit event:

   ```python
   import asyncio
   from forge_bridge.store.session import get_session
   from forge_bridge.store.staged_operations import StagedOpRepo

   async def main():
       async with get_session() as session:
           repo = StagedOpRepo(session)
           op = await repo.propose(
               operation="flame.rename_shot",
               proposer="RECIPE-05-DEMO",
               parameters={
                   "shot_name": "DEMO_010",
                   "new_name": "DEMO_010_v2",
               },
           )
           print(f"proposed: id={op.id} operation={op.operation} status={op.status}")

   asyncio.run(main())
   ```

   ```bash
   conda activate forge
   python /tmp/staged_demo.py
   ```

   Note the printed `id` — you'll use it in subsequent steps. (`StagedOpRepo.propose()` is the only sanctioned construction path; in production the propose-side MCP tools wrap this same call.)

2. **List all staged proposals.** Confirm your proposal landed and see the queue shape:

   ```bash
   fbridge run forge_list_staged --json | jq '.result.data'
   ```

   You'll see an array of operations, each with `id`, `operation` (e.g. `"flame.rename_shot"`), `status` (`"proposed"`), `proposer`, `parameters`, `proposed_at`, and other audit-trail fields.

3. **Inspect the proposal in detail.** Use the `id` from Step 1:

   ```bash
   fbridge run forge_get_staged --json --kwarg op_id=<ID> | jq '.result.data'
   ```

   The full record shows the exact parameters the proposer wants the consumer to execute. **This is the audit point** — you see exactly what would happen on approval, before anything happens.

4. **Decide: approve or reject.**

   ```bash
   # Approve:
   fbridge run forge_approve_staged --json --kwarg op_id=<ID> --kwarg approver=cnoellert

   # Or reject:
   fbridge run forge_reject_staged --json --kwarg op_id=<ID> --kwarg actor=cnoellert
   ```

   The `approver` / `actor` kwarg is the human identity making the decision — required non-empty per FB-A. (Caller-identity migration is `SEED-AUTH-V1.5`, deferred to v1.6+; for now it's an honor-system string.)

5. **Confirm the state transition.** Re-list the staged ops:

   ```bash
   fbridge run forge_list_staged --json | jq '.result.data[] | {id, operation, status}'
   ```

   For an approved op, the status is now `"approved"` — the state machine moved cleanly. In production with a consumer wired, the proposer would receive a `staged.approved` event and execute against its own domain, transitioning the state again to `executed` or `failed`. On a stock install without a consumer, status stays at `approved` — that's the substrate-without-producer signal (see [Recipe 3](#recipe-3-observe-the-synthesis-pipeline-operate)'s framework/consumer framing for the same pattern).

6. **Audit the full event trail.** Every state transition is logged with actor identity and timestamp:

   ```bash
   fbridge run forge_get_events --json | jq '.result.data'
   ```

   For your proposal you'll see `staged.proposed` followed by `staged.approved` (or `staged.rejected`), each with timestamps and the actor identity from Steps 1 and 4. This is the complete audit log for the operation — exactly what an after-the-fact compliance or debugging pass would consume.

### Verification

You're done when **all five** signals are green:

- A proposal landed in `proposed` state (visible via `forge_list_staged`).
- You inspected the full payload and understood exactly what would happen on approval.
- Your decision (approve or reject) flipped the state correctly to `approved` / `rejected`.
- The event log shows the transition with your actor identity.
- You understand that downstream execution (the `approved → executed` transition) requires a consumer subscribed to `staged.approved` events — bridge ships the approval surface; the consumer ships the executor.

The fifth signal is the trust-and-authority story made operational: every destructive operation produced an inspectable proposal, every decision was logged with an identifier, and *nothing executed without a human in the loop*.

### Common pitfalls

- **Demo driver fails with `ImportError`.** The `forge` conda env isn't active in your shell. `conda activate forge` and retry.
- **Approval fails with "actor required".** The `approver` / `actor` kwarg must be non-empty per FB-A. Don't omit it.
- **Proposal stays at `approved` indefinitely.** This is **expected behavior** without a consumer wired (substrate/consumer split — see Recipe 3 framing). In production with projekt-forge subscribed, you'd see `approved → executed` happen seconds after approval. On a stock install, the recipe's demonstrable scope stops at the approval event itself.
- **Re-running the demo driver creates duplicate proposals.** Each `propose()` call inserts a new row. To clean up between runs, either reject the demo proposals (so they don't clutter the queue) or query/delete from the database directly (advanced — beyond recipe scope).

### Next

The recipes form a loop: first-time setup → wiring → synthesis pipeline observability → manifest inspection → chat-driven workflows → authority over destructive operations. With Recipe 5 complete you've walked the full operator surface of the bridge.

For diagnostic / recovery workflows when things break — Flame crashes, Postgres restarts, Ollama hangs, the chat budget exceeds — see `docs/TROUBLESHOOTING.md` (forthcoming under Phase 23 of v1.5).

---

## Recipe 6: Inspect the synthesis manifest

**Requirement:** RECIPES-06
**Outcome:** you can audit any tool in the bridge's registry — its origin (builtin vs synthesized), provenance fields, and how its `observation_count` reconciles against the execution log.

### When to use this

You want to know what tools the bridge currently exposes, where each one came from, and — for synthesized tools — what evidence trail produced them. The manifest is the bridge's tool catalogue; inspecting it is the entry point for "what's available?", "where did this come from?", and "can I trust this synthesized tool?"

Manifest visibility is also where the bridge's "AI but inspectable" story lives. Every synthesized tool carries a `code_hash`, an `observation_count`, a timestamp, and a copy of the original observed code on disk — operators reading the manifest can reconstruct exactly why each synthesized tool exists, without trusting the LLM as a black box. Recipe 3 generated such a tool; this recipe walks the inspection surface for it.

### What this recipe doesn't cover

- **Modifying or removing tools from the manifest.** Tool lifecycle (add / quarantine / remove) is consumer-side concern; the manifest is read-mostly from the operator surface.
- **Quarantine and probation recovery.** When a synthesized tool fails repeatedly, the probation system quarantines it; recovery and tuning belong in `docs/TROUBLESHOOTING.md` — forthcoming under Phase 23.
- **Multi-machine manifest replication.** v1.4.x is single-operator-workstation scope; cross-machine manifest sync is v1.6+.

### Prerequisites

- A completed [Recipe 1](#recipe-1-first-time-setup): bridge is installed, both daemons are running, `fbridge doctor` exits 0.
- **Strongly recommended:** complete [Recipe 3](#recipe-3-observe-the-synthesis-pipeline-operate) first so there's a synthesized tool to inspect. Without a consumer feeding the substrate (or the Recipe 3 demo driver), the manifest will contain only builtin tools — still inspectable, but the trust-building `observation_count` / `code_hash` story has no synthesized example to anchor on.
- `jq` installed (or equivalent JSON tool) for slicing the manifest output.
- About 5 minutes.

### Steps

1. **Get the canonical tool list.** This is the registry view — every tool the bridge will hand to an MCP client.

   ```bash
   fbridge actions
   ```

   Tools you'll see: `forge_*` (project / shot / version / manifest / staged), `flame_*` (Flame API operations), and any synthesized tools registered by the watcher (typically `synth_<intent_slug>`).

2. **Pull the full manifest as JSON.** This is the source-of-truth structured view — every tool with its provenance fields.

   ```bash
   fbridge run forge_manifest_read --json | jq '.result.data'
   ```

   You'll see the envelope: `{"tools": [...], "count": N, "schema_version": "1"}`. Each tool entry has flat fields — `name`, `origin`, `namespace`, `synthesized_at`, `code_hash`, `version`, `observation_count`, `tags`, `meta`, `available`.

3. **Group tools by origin.** This separates first-party (`origin: "builtin"`) from synthesized (`origin: "synthesized"`) — the first audit axis.

   ```bash
   fbridge run forge_manifest_read --json | \
     jq '.result.data.tools | group_by(.origin) | map({origin: .[0].origin, count: length, names: map(.name)})'
   ```

   Builtin tools ship with the package and update with `pip install`. Synthesized tools were produced by the learning pipeline against an observed pattern (see Recipe 3 for the lifecycle).

4. **Inspect a single synthesized tool's provenance.** Pick a synthesized tool (e.g. one from Recipe 3) and read its full ToolRecord:

   ```bash
   fbridge run forge_manifest_read --json | \
     jq '.result.data.tools[] | select(.origin == "synthesized") | {name, code_hash, synthesized_at, version, observation_count}'
   ```

   The four fields together form the audit signal: *when* it was created, *what* pattern hash produced it, *how many* observations crossed the threshold, and *which* synthesizer version was active.

5. **Reconcile `observation_count` against the execution log.** The trust check: the tool says it was synthesized from N observations; the log should confirm exactly N matching rows.

   ```bash
   # Substitute the code_hash from Step 4:
   grep '"code_hash": "<hash>"' ~/.forge-bridge/executions.jsonl | wc -l
   ```

   The count should equal `observation_count` from Step 4, plus exactly one `"promoted": true` marker row from `mark_promoted()` (see Recipe 3 Step 2). If the numbers don't match, something is off — re-run `fbridge doctor` and check the daemon log for storage-callback errors.

6. **Read the synthesized tool's source on disk.** The manifest points at provenance; the source file IS the artifact you're trusting.

   ```bash
   head -40 ~/.forge-bridge/synthesized/<name>.py
   ```

   This is the file the watcher registered, and what `bridge.execute()` will run when an MCP client calls the tool. Reading the source closes the audit loop: you can see exactly what the LLM produced, against exactly which pattern, from exactly which observations.

7. **Open the Artist Console manifest view.** Same data, visual surface.

   ```bash
   open http://localhost:9996/ui/   # macOS — or point any browser at the URL
   ```

   The manifest view shows the same tools grouped by origin, with sortable provenance columns. Useful when you want to scan many tools at once rather than slice a single one.

### Verification

You're done when you can answer **all four** of these questions for any synthesized tool in your manifest:

- **What is its origin and namespace?** (`origin: "synthesized"`, `namespace: "synth"` for synthesized tools.)
- **When was it created, and by which synthesizer version?** (`synthesized_at` + `version`.)
- **What observation pattern produced it?** (`code_hash` — and you can find the matching rows in `executions.jsonl` via the same hash.)
- **How many observations crossed the threshold?** (`observation_count`, reconciling with the log count from Step 5.)

If all four are crisp, the synthesized tool is fully inspectable — you've closed the loop from observation through synthesis to registered artifact, and you're not trusting the LLM blindly.

### Common pitfalls

- **Empty or builtin-only manifest.** If you skipped Recipe 3, the synthesis pipeline hasn't fired and the manifest has no synthesized entries to audit. That's expected behavior on a stock install — see the substrate/consumer note in `CLAUDE.md` for the architectural reason. Either run Recipe 3 to seed a synthesized tool, or wire a consumer (projekt-forge in production) that records executions organically.
- **jq path errors.** The output envelope is `{ok, action, result: {data: {...}}}`; manifest data lives at `.result.data`. Mixing up `.data` (envelope's inner data) with `.result` (CLI's top-level result wrapper) is the most common slice error.
- **Watcher polling lag.** A freshly-synthesized tool may not appear in `fbridge actions` or the manifest immediately — the watcher polls the synthesized directory at intervals. Wait a few seconds and retry.
- **Manifest count vs `fbridge actions` count drift.** `fbridge actions` includes runtime-only tools (some shim aliases); the synthesis manifest only carries tools the watcher registered from disk. Small drift is normal; large drift means something's missing on one surface — inspect both to locate the gap.

### Next

[Recipe 4: Drive Flame from chat](#recipe-4-drive-flame-from-chat) — with the manifest inspection surface understood, the next step is exercising the bridge through chat-driven operational workflows. Inspectability now established makes staged-ops legitimacy (Recipe 5) feasible afterward.

---

## Cross-links

- [`INSTALL.md`](INSTALL.md) — operator-workstation install reference
- [`GETTING-STARTED.md`](GETTING-STARTED.md) — mental model + five-surface map (read this first if recipes feel ungrounded)
- [`VOCABULARY.md`](VOCABULARY.md) — canonical entity model
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — design rationale + decision log
- [`API.md`](API.md) — Flame bridge HTTP API
- `../README.md` — project overview + Quick Start
