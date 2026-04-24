# Phase 11: CLI Companion — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 11-cli-companion
**Areas discussed:** Filter flag grammar, Soft dogfood UAT
**Areas declined to user (captured as Claude's Discretion):** Doctor depth + remediation hint + exit codes, Server-unreachable UX for non-doctor commands, Rich output shape

---

## Gray Area Selection

| Area | Description | Selected |
|------|-------------|----------|
| 1. Doctor depth + remediation hints + exit codes | Beyond `/api/v1/health`: which extra checks (JSONL parseability, sidecar dirs, disk space)? Hint format? Exit code taxonomy? | (Claude's discretion) |
| 2. Server-unreachable UX for non-doctor commands | What do `tools` / `execs` / `manifest` / `health` print when `:9996` is down? Retry behavior? Stderr vs `--json` envelope? | (Claude's discretion) |
| 3. Rich output shape, density, column choices | Per-command tables; artist-friendly defaults vs engineer-friendly density; hash truncation; `--wide` flag? | (Claude's discretion) |
| 4. Filter flag naming + relative-time grammar on `tools` / `execs` | Mirror Web UI tokens vs Typer-idiomatic? `--since 24h` relative parsing? `--tool` W-01 handling? `--quarantined`? | ✓ (with reco request) |
| 5. Non-developer dogfood UAT gate for CLI | Hard D-36-class ship gate vs softer "record and note"? Fresh operator required? | ✓ |

**User's choice:** "4 I'd be looking for recos. 5 can be soft. If I can decipher the page then I think we're good."

**Notes:** User selected 4 with explicit ask for recommendations and selected 5 with the "soft" framing already announced. Areas 1, 2, 3 deferred to Claude's Discretion — Claude proposed defaults grounded in Phase 9/10/10.1 prior decisions. The "if I can decipher the page then I think we're good" line confirmed the soft-gate framing for area 5: developer-as-operator with a subjective legibility criterion.

---

## Area 4 — Filter flag grammar (recommendation request)

Claude presented seven recommendations (R-1 through R-7) with strong-reco framing per the user's prior feedback (`prefer strong recos for technical decisions`).

| Reco | Description | User decision |
|------|-------------|---------------|
| R-1 | Flag naming mirrors Web UI tokens one-to-one (`--origin`, `--namespace`, `--readonly`, `--tool`, `--since`, `--until`, `--promoted`, `--hash`, `-q/--search`) | Confirmed |
| R-2 | `--since` accepts both `Nm/Nh/Nd/Nw` relative AND ISO 8601; ~15 LOC parser | Confirmed |
| R-3 | `tools` filters run client-side; no API change | Confirmed |
| R-4 | `--tool` on `execs` runs client-side post-fetch; one-line stderr note about W-01 | Confirmed |
| R-5 | No `--quarantined` flag in Phase 11 (quarantined tools filtered upstream per Phase 10.1 D-40) | Confirmed |
| R-6 | One canonical `Examples:` block per command docstring; Typer surfaces in `--help` | Confirmed |
| R-7 | Per-command `--json`, `--no-color`, `--quiet/-q` flags; honor `NO_COLOR` / `FORCE_COLOR` env; no `--verbose` (use `FORGE_LOG_LEVEL` env) | Confirmed |

**User's choice:** "Confirmed" (all 1–7).

**Notes:** No counter-proposals or modifications. Recommendations were grounded in:
- Phase 9 D-01..D-05 envelope + filter-grammar lock
- Phase 9 W-01 (`/api/v1/execs?tool=...` deferred to v1.4)
- Phase 10 D-08 Web UI grammar tokens (one-to-one port)
- Phase 10.1 D-40 quarantine-surface deferral
- Pyproject.toml comment confirming T20 print-ban will extend to `forge_bridge/cli/`
- User feedback memory: "Prefer strong recos for technical decisions"

---

## Area 5 — Non-developer dogfood UAT gate

Question presented: "Do we treat this as a hard D-36-class ship gate (Phase ships back to planning on fail) or a softer 'record and note' since CLI users are assumed more technical? Do we pre-commit to a fresh operator (not `CN/dev`, not `ET/tester`) like Phase 10.1 D-44, and who runs it?"

| Option | Description | Selected |
|--------|-------------|----------|
| Hard gate | Mirror Phase 10.1 D-44 — fresh operator, 30s timer, ship-back-to-planning on fail | |
| Soft gate | Developer-as-operator acceptable; subjective "can I decipher" criterion; failure produces follow-up plan, not phase re-open | ✓ |

**User's choice:** "5 can be soft. If I can decipher the page then I think we're good."

**Notes:**
- Locked as D-08 in CONTEXT.md.
- Pass criterion: "can I decipher the output without re-reading the source?" — recorded as a single subjective `PASS / FAIL + note` line at `.planning/phases/11-cli-companion/11-UAT.md`.
- No 30-second timer.
- No "ships back to planning" clause — failure produces a follow-up plan inside Phase 11 or a Phase 11.1 micro-pass.
- Rationale: CLI users (SSH operators, CI scripts) are more technical than Web UI users; the developer running the CLI on their own SSH session IS a representative test subject. Phase 10.1's hard fresh-operator gate was the right tool for an artist-facing UI, not for a CLI.

---

## Claude's Discretion (Areas 1, 2, 3 — captured in CONTEXT.md with strong recommendations)

User declined to single out areas 1, 2, 3 — interpreted as "you have strong recos for those, just bake them in". Claude wrote each into CONTEXT.md `<decisions>` Claude's Discretion subsections with concrete defaults so the planner has clear direction without re-deriving.

### Area 1 — Doctor depth + hints + exit codes
- Doctor extends `/api/v1/health` with: JSONL parseability tail, sidecar dir presence + writability, probation dir presence, fresh `:9996` reachability probe, optional disk-space warn at < 100 MB / fail at < 10 MB.
- Hint format: structured `[check_name] ok|warn|fail / fact / try` row in Rich table (TTY) or one-line per check (`--quiet` / `--json`).
- Exit codes: `0` ok or warn-only; `1` any fail (CI gate per SC#2); `2` server unreachable (matches non-doctor commands).
- "Server not running" message: exact 2-line stderr block ending with `Start it with: python -m forge_bridge`.
- CI fail policy: critical services (mcp / watcher / instance_identity per Phase 9 D-15) → fail; degraded services (LLM offline, Flame down, storage absent) → warn.

### Area 2 — Server-unreachable UX
- All non-doctor commands: one connection attempt, no retry, no backoff. Connection error → stderr message identical to doctor's, exit code `2`.
- `--json` mode on connection error: emit `{"error": {"code": "server_unreachable", "message": "..."}}` to stdout AND exit code `2`. Stderr stays silent.
- Exit code taxonomy locked: `0` success, `1` server returned error response, `2` server unreachable, `3+` reserved.

### Area 3 — Rich output shape
- Tools list columns: `Name`, `Status` (chip), `Type`, `Created ▼` — mirror Phase 10.1 D-40/D-41 artist layout. Code_hash / namespace / observation_count demoted (visible only via `--json` or per-tool drilldown).
- Tool drilldown: full Panel with the 5 canonical `_meta` fields, tags, and 40-line raw-source preview (synthesized tools).
- Execs list: `Tool`, `Hash` (8-char), `Timestamp`, `Promoted`. Default sort timestamp DESC; default limit 50.
- Exec drilldown: full Panel with full hash + raw_code via Rich `Syntax` (Python lexer).
- Health: per-service Panel grouped by criticality.
- `Created ▼` glyph in column header signals default sort order — closes Phase 10.1 HUMAN-UAT item #2 on the CLI surface.
- No `--wide` / `--compact` density flags in Phase 11.
- Box style `rich.box.SQUARE`; header bold yellow.
- Hash truncation: 8 chars on lists, full on details (locked from Phase 10 D-16).

---

## Deferred Ideas (captured in CONTEXT.md `<deferred>`)

Mentioned during discussion or implied by the locked decisions; deferred to later phases:

- Server-side `/api/v1/tools` filter params (v1.4 if tool count > ~1k)
- W-01 `/api/v1/execs?tool=...` server-side support (v1.4 API extension)
- `--wide` / `--compact` density flags
- Humanized timestamps ("2h ago") — pairs with Phase 10.1 HUMAN-UAT follow-up
- `--quarantined` flag and quarantined-tool surfacing
- `--verbose` / `--debug` / `--log-level` CLI flags
- Watch / tail mode (pairs with v1.4 SSE/WebSocket push)
- Interactive REPL (`forge-bridge console shell`)
- Embedded server-start mode (explicitly rejected)
- Shell completion (planner may add as a freebie if low-cost)
- `console export` subcommand
- Configurable retry/backoff on connection error
- `--bind-host` / `--remote` flag (locked v1.3 non-goal — localhost-only)
