# Phase 11: CLI Companion — Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A Typer-based CLI that gives a headless / SSH / CI operator the same read-only surface the v1.3 Web UI provides — `forge-bridge console {tools,execs,manifest,health,doctor}` — by calling the existing `/api/v1/*` JSON API on `:9996`. Output is Rich-formatted (tables / panels) when stdout is a TTY and plain JSON when piped or `--json` is set. Pure client: the CLI never starts the server, never mutates state, never holds long connections, never embeds an LLM.

In scope (REQ-IDs): CLI-01, CLI-02, CLI-03, CLI-04, TOOLS-03, EXECS-03, MFST-05, HEALTH-02, HEALTH-03.

Out of scope for Phase 11:
- Refactoring `forge_bridge/__main__.py` Typer root or the `console_app` group plumbing — Phase 9 D-10/D-11 already shipped the scaffold; Phase 11 only fills the empty group.
- Extending `/api/v1/*` (no new server-side filter params, no new endpoints, no W-01 fix). The CLI consumes the API as it is.
- LLM chat (Phase FB-D), mutation actions, auth, real-time push, multi-project, watch/tail mode, interactive REPL, embedded "start the server" auto-launch.
- A second presentation surface beyond Rich + JSON (no CSV / Parquet / Markdown writers).

</domain>

<decisions>
## Implementation Decisions

### Filter flag grammar (R-1, locked)

- **D-01:** Subcommand filter flags are kebab-case Typer options that mirror the Phase 10 D-08 Web UI grammar tokens one-for-one — same word, same semantics — so an artist who learns one dialect uses both. Concrete flag rosters:

  | Command | Filter flags |
  |---------|--------------|
  | `tools` | `--origin {builtin,synthesized}`, `--namespace TEXT`, `--readonly / --no-readonly`, `-q, --search TEXT` |
  | `execs` | `--tool TEXT`, `--since TEXT`, `--until TEXT`, `--promoted / --no-promoted`, `--hash TEXT` (aliased to API `code_hash`), `--limit INT` (default 50, max 500), `--offset INT` |
  | `manifest` | `-q, --search TEXT`, `--status TEXT` (reserved; today returns all) |
  | `health` / `doctor` | no filters |

- **D-02 (`--since` grammar, R-2):** `--since` and `--until` accept BOTH a small relative grammar (`Nm` / `Nh` / `Nd` / `Nw` — minutes/hours/days/weeks) AND ISO 8601 timestamps (passthrough to API). Parsing happens client-side and emits ISO 8601 to `/api/v1/execs?since=...`. Rejected: "yesterday", "last tuesday", ISO 8601 durations, locale-specific date strings — keep the parser ~15 LOC.

### API filter strategy (R-3, R-4, R-5, locked)

- **D-03 (R-3):** `tools` filters run **client-side**. Fetch the full tool list from `/api/v1/tools` once per invocation, filter in Python before rendering. Rationale: the registry is naturally small (tens to low hundreds), the API already serializes the full list for every Web UI request, and adding query params to `/api/v1/tools` is scope creep — Phase 11 consumes the Phase 9/10 API, never extends it. Re-evaluate if tool count ever crosses ~1k (v1.4 candidate).
- **D-04 (R-4 — W-01 workaround):** `execs --tool TEXT` runs **client-side** on top of the server-side filters (`--since`, `--promoted`, `--hash`, `--limit`). Implementation: build the API request from the server-supported filters, then filter the returned records by `tool` in Python before rendering. Emit one stderr line on every `--tool` invocation: `note: --tool is filtered client-side until v1.4 API support; narrow with --since to scan less history.` Cap the server fetch at the user-supplied `--limit` (default 50, max 500 per Phase 9 D-05). Rejected alternatives: hard-error ("not implemented") — worse UX; add API support now — scope creep; auto-paginate the whole log — unbounded I/O.
- **D-05 (R-5 — quarantined surfacing):** No `--quarantined` flag in Phase 11. Quarantined tools are filtered out at the `ConsoleReadAPI` / watcher layer (Phase 10.1 D-40) and never appear in `/api/v1/tools`, so the flag would always return empty. Document the upstream filtering in `console tools --help` (one line). Surfacing quarantined tools is deferred alongside admin/auth (v1.4+).

### CLI ergonomics (R-6, R-7, locked)

- **D-06 (R-6 — `--help` examples):** Each subcommand's docstring ends with a single `Examples:` block containing **one** canonical invocation. Typer surfaces this in `--help` automatically. Not exhaustive — one example per command, focused on the artist path. Sample for `execs`:
  ```
  Examples:
    forge-bridge console execs --since 24h --promoted
    forge-bridge console execs --tool synth_foo --limit 20 --json
  ```
- **D-07 (R-7 — global flags):** Per-command flags (NOT group-scoped, to keep each `--help` clean):
  - `--json` — REQUIRED on every subcommand per CLI-03; emits the raw `/api/v1/*` JSON response body to stdout (envelope and all). When set, all human-formatting code paths short-circuit.
  - `--no-color` — disables Rich color output for the current invocation. Honors `NO_COLOR` and `FORCE_COLOR` env vars natively (Rich already handles these).
  - `--quiet, -q` — suppresses Rich decorations (panels, headers, color) and emits a minimal plain-text rendering. Distinct from `--json`: `--quiet` is for shell/awk, `--json` is for programmatic consumers.
  - **No** `--verbose` / `--debug` / `--log-level` — log level is controlled via `FORGE_LOG_LEVEL` env (already the project pattern). If logging-via-env proves awkward in the soft UAT, add a CLI flag in Phase 12 / v1.4.
  - **No** group-level (`forge-bridge console <flag>`) flags. Phase 9's `--console-port` stays on the bare `forge-bridge` invocation per D-27.

### Soft dogfood UAT gate (locked)

- **D-08:** Phase 11 SC#4 ("operator answers two questions from the terminal") is a **soft, self-administered** gate. Acceptable operators: developer (`CN/dev`) acting as their own test subject — no fresh-operator requirement (Phase 10.1 D-44 does NOT apply to Phase 11). Pass criterion: "can I decipher the output without re-reading the source?" — recorded as a single subjective `PASS / FAIL + note` line at `.planning/phases/11-cli-companion/11-UAT.md`. No 30-second timer. **No "ships back to planning" clause** — failure produces a follow-up plan inside Phase 11 or a Phase 11.1 micro-pass, not a re-open. Rationale: CLI users are assumed more technical than Web UI users (SSH operators, CI scripts, scripted pipelines), and Phase 10.1's hard fresh-operator gate produced expensive UAT cycles that mostly deferred follow-ups to a HUMAN-UAT side file anyway. The soft gate respects the actual user population without losing the dogfood-or-die discipline.

### Claude's Discretion

The user did not single these out, but the planner needs concrete defaults — captured here so the planner doesn't re-derive them and so they can be reviewed before plan execution.

#### Doctor depth, remediation hint shape, and exit-code policy (Area 1)

- **Doctor checks** = HEALTH-01 baseline (`/api/v1/health` consumed via the same client) **plus** these client-side probes the API doesn't run:
  - JSONL parseability — open `~/.forge-bridge/executions.jsonl` (or `FORGE_EXECUTION_LOG_PATH` if set), tail the last 100 lines, attempt JSON parse per line; surface the line numbers and exception class names of any failures (NEVER `str(exc)` — Phase 8 LRN-05 credential-leak rule).
  - Synthesized-tool sidecar dir presence + writability — `~/.forge-bridge/synthesized/` (or the equivalent), `os.access(..., os.W_OK)` probe.
  - Probation dir presence — same shape.
  - Console port reachability from localhost — already covered by `/api/v1/health.services.console_port`, BUT doctor re-confirms by attempting a fresh `httpx.get('http://127.0.0.1:9996/api/v1/health', timeout=2)` so the user gets a coherent connection-failure message even if the server returns an HTTP-200 health body that lies about itself.
  - Optional: disk space at JSONL log dir — WARN at < 100 MB free, FAIL at < 10 MB.
- **Hint format** = one structured row per check, rendered in a Rich table (TTY) or one line per check (`--quiet` / `--json`):
  ```
  [check_name]  ok|warn|fail
  fact:        <one-line factual observation>
  try:         <one-line remediation hint, omitted on ok>
  ```
- **Exit codes:**
  - `0` — all checks `ok` OR only `warn` checks (warn = degraded but not blocking).
  - `1` — any `fail` (CI-gating signal — SC#2).
  - `2` — server unreachable on `:9996` (distinct from "server reported a fail" — see D-04 Area 2 below for parity with non-doctor commands).
- **"Server not running" message** — exact string when the doctor's `:9996` probe fails:
  ```
  forge-bridge console: server is not running on :9996.
  Start it with: python -m forge_bridge
  ```
  Printed to stderr; exit 2; no other doctor checks attempted (probing JSONL etc. is meaningful only when the live server is the canonical reader).
- **What counts as a CI fail (SC#2 disambiguation):** critical services (mcp / watcher / instance_identity per Phase 9 D-15) failing → `fail`; degraded services (LLM backend offline, storage_callback absent, Flame bridge unreachable) → `warn`. So a CI job running on a host with no Flame instance still passes `doctor`; a host where the MCP lifespan never started fails it.

#### Server-unreachable UX for non-doctor commands (Area 2)

- **All non-doctor commands** (`tools`, `execs`, `manifest`, `health`) attempt one connection per invocation. On `httpx.ConnectError` / `httpx.TimeoutException` / `httpx.ConnectTimeout`:
  - Print to stderr the SAME message as doctor (D-08 above); exit code `2`.
  - **No silent retry. No exponential backoff.** Pure client behavior — if `:9996` isn't up, it isn't up; the user knows what to do.
- **`--json` mode** on connection error: emit `{"error": {"code": "server_unreachable", "message": "<msg>"}}` to **stdout** (matches the API's error envelope shape per Phase 9 D-01) AND exit code `2`. Stderr stays silent in `--json` mode so pipes and JSON-consuming scripts don't get fed a mixed stream.
- **Exit-code taxonomy across the CLI:**
  - `0` — success.
  - `1` — server returned an error response body (HTTP 4xx / 5xx with `{error: ...}` envelope).
  - `2` — server unreachable / connection error / timeout.
  - `3+` — reserved for future use (e.g., schema mismatch, version skew).

#### Rich output shape, density, and column choices (Area 3)

- **Render contract:** `--json` prints the raw API response to stdout, byte-faithful (no re-encoding, no field renaming). All other modes use Rich primitives.
- **Tools list (`forge-bridge console tools`)** — default columns mirror the Phase 10.1 D-40/D-41 artist layout:
  - `Name` (mono)
  - `Status` (chip — `active` green, `loaded` dim cyan; quarantined never appears, see D-05)
  - `Type` (mapped from `origin`: `Synthesized` / `Built-in`)
  - `Created ▼` (ISO 8601 UTC timestamp; the `▼` glyph in the header signals the default sort order — see "Default-sort affordance" specifics below)
  - Demoted/hidden by default: `code_hash`, `namespace`, `observation_count`. Visible only via `--json` or via the per-tool drilldown.
- **Tool drilldown (`forge-bridge console tools <name>`)** — full Rich Panel mirroring Phase 10 D-14:
  - 2-column key/value table for the 5 canonical `_meta` fields (`origin`, `code_hash` (FULL), `synthesized_at`, `version`, `observation_count`).
  - Tags row.
  - For synthesized tools: raw source preview as a Rich `Syntax` block (Python lexer, plain background — Rich's default theme matches the LOGIK-PROJEKT amber-on-dark feel well enough). Truncated at 40 lines with a `… (use --json for full source)` footer.
- **Execs list (`forge-bridge console execs`)** — default columns:
  - `Tool`, `Hash` (8-char short — Phase 10 D-16), `Timestamp` (ISO 8601 UTC), `Promoted` (✓ / blank).
  - Default sort: timestamp DESC; default limit: 50 records (matches EXECS-03).
- **Exec drilldown (`forge-bridge console execs <hash>`)** — Rich Panel with the full `ExecutionRecord`: full `code_hash`, `timestamp`, `promoted` flag, `intent`, and `raw_code` rendered in a Rich `Syntax` block (Python lexer) with no truncation.
- **Manifest (`forge-bridge console manifest`)** — same column set as `tools` list (since the manifest IS the tool list with sidecar metadata). `--json` returns the byte-identical `/api/v1/manifest` body for parity with `forge://manifest/synthesis`.
- **Health (`forge-bridge console health`)** — Rich Panel per service group with the aggregate status pill at top (matches Phase 10 D-18 strip semantics):
  - `mcp · watcher · console_port` block (critical)
  - `flame_bridge · ws_server` block (degraded-tolerant)
  - `llm_backends` block (one line per backend)
  - `storage_callback · instance_identity` block (provenance)
  - Status colors: `ok` green, `degraded` / `warn` amber, `fail` / `absent-when-required` red, `absent` dim.
- **`Created ▼` default-sort affordance** — the `▼` glyph in the column header explicitly signals "sorted descending by this column" so the default sort order is legible without the user asking. This directly addresses Phase 10.1 HUMAN-UAT item #2 ("operator couldn't tell tables were sorted by Created"); applying the lesson here in Phase 11 closes the same gap on the CLI surface even though the Web UI fix remains a deferred follow-up.
- **No `--wide` / `--compact` density flags** in Phase 11. Default is artist-friendly; `--json` is the engineer escape hatch. Add `--wide` later if the soft UAT surfaces "I want code_hash on the list view".
- **Box style** = `rich.box.SQUARE` (clean, monospace-friendly). Header style = bold yellow (renders as amber-ish in most terminals; matches LOGIK-PROJEKT lineage without requiring 24-bit color detection).
- **Hash truncation**: 8 chars on lists; full hash on details — locked from Phase 10 D-16. Short hashes always paired with `… (use --json for full)` hint at table footer.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before producing artifacts.**

### Phase 11 inputs (locked scope + requirements)

- `./CLAUDE.md` — project guidelines (forge-bridge = protocol-agnostic middleware; Flame is one endpoint; local-first; UX philosophy)
- `.planning/PROJECT.md` — v1.3 "Artist Console" milestone scope; locked non-goals (no auth, no admin/mutation, no streaming push, no `LLMRouter` hot-reload, no shared-path JSONL writers); all v1.0–v1.2 key design decisions that still bind Phase 11
- `.planning/REQUIREMENTS.md` — REQ-IDs CLI-01..04, TOOLS-03, EXECS-03, MFST-05, HEALTH-02, HEALTH-03; full traceability table
- `.planning/ROADMAP.md` §"Phase 11: CLI Companion" — 4 success criteria
- `.planning/STATE.md` §"Session Handoff" — v1.3 implementation constraints, especially: Typer 0.24.1 sync constraint (verified via live test), ConsoleReadAPI as sole read path, MFST-02/03 same-plan rule (informational — Phase 11 doesn't ship MCP resources), `jinja2`-only-new-dep rule (Phase 11 should add `rich` and nothing else, if `rich` isn't already pinned via `mcp[cli]`)

### Phase 9/10/10.1 hand-off (the API + UI contract Phase 11 consumes)

- `.planning/phases/09-read-api-foundation/09-CONTEXT.md` — locked decisions Phase 11 inherits without modification:
  - D-01..D-05 — API envelope (`{data, meta}`), pagination (`limit`/`offset`, max 500), filter grammar (plain query params), `snake_case` end-to-end
  - D-10..D-12 — Typer-root scaffolding already in `forge_bridge/__main__.py`; Phase 11 fills the empty `console_app`
  - D-13..D-18 — full health response shape (`/api/v1/health`); doctor consumes this exact body
  - D-22 — ruff T20 `print(` ban; extend per-file-ignores carve-out from `forge_bridge/console/` to `forge_bridge/cli/` if any module needs `print()` (none should)
  - D-25..D-26 — single read path; CLI is the third surface (Web UI, MCP resources, CLI) reading the byte-identical envelope
  - D-27..D-29 — port resolution (`--console-port` flag → `FORGE_CONSOLE_PORT` env → 9996); 127.0.0.1 only; graceful degradation when port unavailable (server-side concern; CLI's parity is the D-04 Area 2 connection-error UX)
- `.planning/phases/09-read-api-foundation/09-01-PLAN.md`, `09-02-PLAN.md`, `09-03-PLAN.md` — as-shipped Typer + ConsoleReadAPI surface Phase 11 calls into
- `.planning/phases/10-web-ui/10-CONTEXT.md` — Web UI grammar tokens (D-08), preset chip roster (D-09), code-hash truncation rule (D-16). The CLI flag set in D-01 is a one-to-one port of D-08
- `.planning/phases/10.1-artist-ux-gap-closure/10.1-CONTEXT.md` — Status chip taxonomy (D-40), column header relabel rule (`Created` instead of `Synthesized`, D-41), telemetry demotion pattern (`code_hash` / `obs_count` / `namespace` not as primary columns). Phase 11 ports the same artist-facing layout into the Rich tables
- `.planning/phases/10.1-artist-ux-gap-closure/10.1-HUMAN-UAT.md` — pending follow-up item #2 ("Default-sort affordance legibility") informs the `Created ▼` glyph choice in D-?? Area 3 above; the Phase 11 CLI applies the lesson even though the Web UI fix is still pending

### Research (inherited from v1.3 milestone — still HIGH confidence)

- `.planning/research/SUMMARY.md` §"Phase 11: CLI Companion" — recommended stack (Typer + Rich + sync `httpx`), DF-3 doctor feature scope, anti-picks (async commands, click subcommand groups, embedded server-start)
- `.planning/research/STACK.md` — Typer 0.24.1 sync constraint (verified via live test; `async def` is silently dropped); `httpx` already in base deps; `rich` available transitively via `mcp[cli]` and Typer
- `.planning/research/FEATURES.md` — DF-3 doctor feature scope, artist-vs-engineer user taxonomy (Phase 11 leans engineer-friendly per D-08 soft-gate framing while still applying artist-UX lessons from Phase 10.1)
- `.planning/research/PITFALLS.md` — P-09 (CLI vs Web UI drift — mitigated by the single-read-path discipline and the byte-identical envelope contract); P-01 (stdout corruption — Phase 11's `--json` mode MUST never mix Rich and JSON on stdout; `--quiet` and `--json` short-circuit Rich entirely)

### Code surface Phase 11 touches

- `forge_bridge/__main__.py` — Typer root + `console_app` group already wired (Phase 9 D-10/D-11). Phase 11 adds five `console_app.command(...)` registrations; does NOT refactor the file structure.
- `forge_bridge/cli/` (NEW directory) — subcommand modules: `tools.py`, `execs.py`, `manifest.py`, `health.py`, `doctor.py`. T20 ruff print-ban applies (extend `[tool.ruff.lint.per-file-ignores]` if any module needs `print()` — none expected to).
- `forge_bridge/cli/client.py` (NEW) — sync `httpx` client wrapping the `/api/v1/*` surface; canonical envelope unwrap; connection-error → exit-code-2 logic per D-?? Area 2.
- `forge_bridge/cli/render.py` (NEW) — Rich rendering helpers: status-chip → Rich `Text` with style, code-hash truncation, ISO timestamp formatter, Panel/Table builders shared across subcommands. Single home for the artist-UX lessons from Phase 10.1.
- `forge_bridge/cli/since.py` (NEW; planner may merge into client.py) — `Nm/Nh/Nd/Nw` + ISO 8601 parser per D-02. ~15 LOC.
- `pyproject.toml` — extend `[tool.ruff.lint.per-file-ignores]` for `forge_bridge/cli/` if any module needs `print()`. Pin `rich` as a direct dep IF it isn't already transitively available via `mcp[cli]` — planner verifies. No other dep changes.
- `tests/test_cli_*.py` (NEW) — `typer.testing.CliRunner` unit tests per command + a sync `httpx` integration test against the running console fixture server (reuse the Phase 10.1 fixture-server pattern from `tests/test_ui_js_disabled_graceful_degradation.py`). Test the connection-error UX explicitly (server-down, server-up-but-error).
- `forge_bridge/console/handlers.py` — read-only reference; no changes (Phase 11 does NOT extend the API; W-01 stays open per D-04).
- `forge_bridge/console/read_api.py` — read-only reference; no changes.
- `.planning/phases/11-cli-companion/11-UAT.md` (NEW, written at phase closure) — soft self-UAT record per D-08.

### Palette / UX philosophy provenance

- Memory: `forge-bridge UX philosophy — artist-first, LOGIK-PROJEKT aesthetic` — applies in spirit (artist-facing column choices in D-?? Area 3) even though CLI has no CSS palette to inherit. The bold-yellow Rich header style + amber-status mapping carry the visual lineage as far as ANSI permits.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 9/10/10.1 shipped)

- **`forge_bridge/__main__.py` `console_app`** — empty Typer subcommand group, mounted via `app.add_typer(console_app, name="console")`. Phase 11's only `__main__.py` edit is five `console_app.command("...")(...)` registrations.
- **`/api/v1/tools` `/api/v1/execs` `/api/v1/manifest` `/api/v1/health`** — canonical read surface; CLI is a pure client.
- **`{data, meta}` envelope contract** (Phase 9 D-01) — CLI's `client.py` unwraps once, then hands the inner `data` to renderers.
- **`forge_bridge/console/manifest_service.py` `ToolRecord` and `forge_bridge/learning/execution_log.py` `ExecutionRecord`** — same dataclasses the API serializes; CLI renderers can rebuild them via `**kwargs` from the JSON dict if a typed surface is preferred, OR render from the plain dict (planner picks; both are clean).
- **`httpx`** — already in base deps (`pyproject.toml` line 11). Sync `httpx.Client(base_url=...).get(...)` is the standard pattern.
- **`rich`** — available transitively via `mcp[cli]` and Typer's own help rendering. Planner confirms whether to pin as a direct dep (recommended) or rely on transitive availability.
- **`tests/test_ui_js_disabled_graceful_degradation.py` fixture-server pattern** — boot a fresh console server on a free port, hit it, tear down. The CLI integration tests reuse this helper directly (or factor it into a shared `conftest.py` fixture if Phase 11 adds enough call sites to justify the extraction).
- **Phase 10 `forge_bridge/console/handlers.py` envelope helpers (`_envelope`, `_error`, `_envelope_json`)** — read-only reference for the canonical envelope shape Phase 11's client unwraps and Phase 11's `--json` mode emits.

### Established Patterns

- **ConsoleReadAPI as sole read path** — Web UI, MCP resources, and now CLI all consume the byte-identical `/api/v1/*` envelope (Phase 9 D-25/D-26). Phase 11 adds zero new read code; it only adds presentation.
- **Sync everything in Typer commands** — Phase 9 STATE.md constraint: Typer 0.24.1 silently drops `async def`. Use sync `httpx.Client.get(...)`; never `asyncio.run()` inside a command body.
- **Logger-per-module via `logging.getLogger(__name__)`** — universal across the codebase; CLI follows. `FORGE_LOG_LEVEL` env controls verbosity (no CLI flag).
- **T20 ruff print-ban** — currently scopes `forge_bridge/console/`; extend to `forge_bridge/cli/` if any module legitimately needs `print()` (none expected — Rich `Console.print()` and `typer.echo()` cover everything).
- **Frozen dataclasses for records** — `ToolRecord`, `ExecutionRecord` are `@dataclass(frozen=True)`. CLI renderers can pass them to Rich tables directly (`{{ record.field }}`-style) without DTO translation.
- **Env-var-then-default config** — Phase 9 D-27 (`FORGE_CONSOLE_PORT`); Phase 11 inherits this for the CLI's base URL.

### Integration Points

- **`forge_bridge/__main__.py`** — registers five new commands via `console_app.command("tools")(tools.tools_cmd)` etc. The CLI flag for `--console-port` already exists on the bare `forge-bridge` invocation; the CLI commands inherit the resolved port via `FORGE_CONSOLE_PORT`.
- **`forge_bridge/cli/client.py`** — single sync `httpx.Client` factory that reads `FORGE_CONSOLE_PORT` (default `9996`) and binds `127.0.0.1`. Wraps `client.get("/api/v1/...")`, unwraps the envelope, raises a typed `ServerUnreachableError` on connection error and `ServerError` on HTTP 4xx/5xx — both caught at the command boundary and translated to exit codes per D-04 Area 2.
- **`forge_bridge/cli/render.py`** — single home for status-chip styling, hash truncation, timestamp formatting, Panel/Table builders. Imported by every subcommand. No subcommand re-implements rendering primitives.
- **`forge_bridge/__init__.py`** — no new public symbols expected (CLI is private to the `forge-bridge` entry point). Minor version bump deferred unless a new public symbol genuinely needs to be re-exported.
- **`pyproject.toml`** — pin `rich` as a direct dep IF transitive availability via `mcp[cli]` is fragile (planner verifies); extend per-file-ignores carve-out for `forge_bridge/cli/` only if needed (none expected). No new optional extras.

</code_context>

<specifics>
## Specific Ideas

- **"Conventional API, friendly UI" applied a third time.** Phase 9 locked the JSON API; Phase 10 layered an artist-friendly Web UI on top; Phase 11 layers a Rich-formatted CLI on top. One read layer, three presentation surfaces, all byte-identical at the envelope level. The CLI is the third proof that the single-read-path discipline (Phase 9 D-25) was the right call.
- **Same data, two surfaces, same lessons.** The Phase 10.1 D-40/D-41 column-demotion lessons (artist columns first, telemetry demoted) port directly into the Rich table column choices. The CLI doesn't get to re-litigate "should we show code_hash by default" — Phase 10.1 already answered no.
- **Exit codes are the engineer escape hatch, JSON is the consumer-script escape hatch, Rich is the human escape hatch.** Three audiences, three formats, one read layer. CI cares about exit codes; pipeline scripts care about `--json`; humans care about Rich panels. The taxonomy in D-04 Area 2 (`0` ok, `1` server-error, `2` unreachable) gives all three what they need without overlap.
- **Default-sort affordance closes a Phase 10.1 follow-up.** The `Created ▼` column header glyph is a one-character fix that makes the sort order legible — directly addressing Phase 10.1 HUMAN-UAT item #2 ("operator couldn't tell tables were sorted by Created"). The Web UI's equivalent fix is still a deferred follow-up; the CLI applies the lesson now, in the surface that ships next, so the same operator gets a better experience on at least one surface immediately.
- **Soft dogfood gate respects the actual user population.** Phase 10/10.1's hard fresh-operator gate was the right tool for an artist-facing UI surface where the developer is NOT a representative user. For a CLI consumed by SSH operators, scripted pipelines, and CI jobs, the developer running it themselves IS the representative test — making the gate softer (developer-as-operator, "can I decipher" criterion, no 30s timer, follow-up plan instead of phase re-open) without losing the dogfood-or-die discipline that Phase 10 taught us we needed.
- **W-01 stays open by design.** The `/api/v1/execs?tool=...` 400 `not_implemented` is locked deferral per Phase 9 RESEARCH; Phase 11's `execs --tool` does the right thing client-side with an honest stderr note. The phase does NOT close W-01 — that's a v1.4 API extension.
- **No new MCP surface in Phase 11.** Phase 11 is purely a CLI client; it adds no new MCP resources, no new tool shims, no new server endpoints. The Phase 9 single-read-path discipline holds.
- **`--json` and `--quiet` short-circuit Rich entirely** — never mix Rich-styled output and JSON on the same stream. The P-01 stdout-corruption pitfall applies just as forcefully to CLI output as it did to MCP stdio.

</specifics>

<deferred>
## Deferred Ideas

- **Server-side filter params on `/api/v1/tools`** — added when tool count exceeds ~1k, alongside the W-01 `/api/v1/execs?tool=...` support in v1.4.
- **`/api/v1/execs?tool=...` server-side filter (W-01)** — already locked-deferral per Phase 9; the CLI works around with client-side filtering + stderr note (D-04). v1.4 API extension.
- **`--wide` / `--compact` density flags** — not in Phase 11. Default tables show the artist-facing column set; `--json` is the engineer escape hatch. Add `--wide` later if the soft UAT surfaces "I want code_hash on the list view".
- **Humanized timestamps ("2h ago")** — Phase 10.1 HUMAN-UAT follow-up item #2 (legibility); if Phase 11 dogfood echoes the same pain on the CLI surface, fold the fix into a v1.4 polish pass that touches both Web UI and CLI together.
- **`--quarantined` flag and quarantined-tool surfacing** — deferred to v1.4 / admin/auth milestone (matches Phase 10.1 D-40 deferral). Quarantined tools are filtered out at the read layer today.
- **`--verbose` / `--debug` / `--log-level` CLI flags** — use `FORGE_LOG_LEVEL` env instead. Add a CLI flag in Phase 12 / v1.4 if logging-via-env proves awkward in the soft UAT.
- **Watch / tail mode (`forge-bridge console execs --watch`)** — pairs with v1.4 SSE/WebSocket streaming push. Out of scope for v1.3 (poll-only locked).
- **Interactive REPL (`forge-bridge console shell`)** — out of scope; defer to a dedicated UX-polish phase if SSH operators ever ask. Most SSH workflows don't need a REPL — `--help` + scriptable subcommands cover them.
- **Embedded "start the server if it's not running" mode** — explicitly rejected. CLI is pure client per the locked architecture; auto-launching `python -m forge_bridge` from a CLI subcommand would couple the CLI to server lifecycle in a way that breaks the read-only contract and surprises users running CI scripts.
- **Shell completion (bash/zsh/fish)** — Typer supports it natively (`--install-completion`). Planner can add as a freebie or defer if it complicates packaging. Recommend including in plan if low-cost; defer if it requires shell-specific file installation logic.
- **`console export` subcommand** for piping the manifest/execs into other tools (CSV / Parquet / SQL dump) — `--json` already covers programmatic consumption. Revisit when a structured export request actually surfaces.
- **Configurable retry / backoff on connection error** — D-04 locks "no retry, no backoff" for v1.3. Reconsider if the soft UAT surfaces "the server is flaky during boot" — but the server is local; flakiness probably means a real bug, not a need to retry.
- **`--bind-host` / `--remote` flag to point the CLI at a non-localhost server** — out of scope. Localhost-only is a locked v1.3 non-goal (pairs with the auth milestone).

</deferred>

---

*Phase: 11-cli-companion*
*Context gathered: 2026-04-24*
