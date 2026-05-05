---
arc: PR40-PR42 — Single Runtime Consolidation
generated: 2026-05-04
project: forge-bridge
counts:
  decisions: 7
  lessons: 7
  patterns: 6
  surprises: 5
note: |
  Manual extraction. PR40/41/42 were not formally a GSD phase (no
  .planning/phases/40-... directory), so gsd-extract_learnings could not
  operate as-designed. This file mirrors that workflow's shape (decisions,
  lessons, patterns, surprises with source attribution).
---

# Single Runtime Consolidation: PR40 → PR42

The arc that took the system from "every client embeds the engine" to "every client posts to one daemon." Three PRs, ~11 hours of conversation, one accidental discovery that the production launchd daemon had been crash-looping for an unknown period.

## Decisions

### Daemon-first sequencing over Flame-first iteration
Park the in-process Flame work (PR37–PR39) as a proof-of-contract, build the HTTP daemon endpoint, then convert the clients in turn (CLI → Flame). Don't polish the in-process path further — it gets deleted when the daemon lands.

**Rationale:** Every line of in-process code (asyncio.run inside Flame's UI thread, the integration.py wrapper, the import-bomb on first call) is throwaway against the daemon. Polishing the wrong shape compounds the cost. The daemon also unblocks the chat reliability blocker for v1.5 — same fix, two surfaces.
**Source:** Conversation, PR37–PR39 review.

### `/api/v1/exec` on the existing :9996 console process — not a separate daemon
Add a route to the already-running FastAPI/Starlette console app rather than stand up a parallel daemon process.

**Rationale:** Console already imports `execute_command`'s full transitive tree (chat goes through the same engine). A separate daemon means two runtimes to keep alive, two unit files, two ports — exactly the divergence we're trying to eliminate. "Single runtime for all clients" is *more* true with one process, not less.
**Source:** PR40 spec review (multiple iterations).

### No client-side fallback to in-process execution
If the daemon is unreachable, fail loudly. CLI emits exit 2; Flame returns a synthesized PR31 envelope.

**Rationale:** A silent fallback re-creates the divergence the consolidation was paid for. Two execution paths is what got us here.
**Source:** PR40 spec, PR41/PR42 specs.

### Stdlib `urllib.request` in Flame, not httpx
Flame's hook talks to the daemon via `urllib.request.urlopen`, not the httpx client used elsewhere.

**Rationale:** httpx pulls h11, anyio, certifi, etc. into Flame's bundled Python interpreter — same heavy-import problem the daemon was supposed to eliminate. Stdlib HTTP is sync, ~30 lines, zero new dependencies, and Flame's hook already runs synchronously on the Qt thread.
**Source:** PR41 spec discussion (PR42 prep), PR42 spec.

### Empty-input belongs to the engine, not the clients
Neither CLI nor Flame short-circuits empty/whitespace input. Both forward to the daemon and let `execute_command` return its `EMPTY_COMMAND` envelope.

**Rationale:** Otherwise CLI says one thing ("Nothing to execute after parsing.") and Flame says another ("Command is empty.") for the identical condition — exactly the divergence the single-runtime PR is supposed to eliminate. Cost is one HTTP round-trip on a no-op input. Worth it.
**Source:** PR42 spec review (drove the local short-circuit removal).

### Preserve dual-mode CLI rendering — don't regress to "always JSON"
PR41 keeps the existing default per-step formatted output and `--json` opt-in unchanged; only swaps the data source from `asyncio.run(execute_command(...))` to `_exec_http(text)`.

**Rationale:** "Always JSON" was a UX regression hidden in the spec. The existing dual-mode CLI is good — artists running `fbridge exec "list projects"` get readable output by default, scripts pass `--json`. Single-runtime invariant doesn't require touching the rendering.
**Source:** PR41 spec review.

### Expand exit codes from {0, 1} to {0, 1, 2, 3, 4}
Distinguish CLI usage error (1), transport failure (2), protocol error (3), execution error (4) — matches what scripts piping `fbridge exec` actually need.

**Rationale:** Diverges from `console doctor`'s {0, 1, 2}, but exec consumers benefit from being able to distinguish "daemon unreachable" from "command failed" from "malformed response." Documented in DIRECT_EXECUTION.md.
**Source:** PR41 spec.

---

## Lessons

### caplog passing does not prove production logging works
PR40's `caplog` test asserted that `forge.exec` INFO records were emitted, and the test passed. Production logs were silent. caplog installs its own root handler that survives `dictConfig` calls; uvicorn's `log_config=STDERR_ONLY_LOGGING_CONFIG` (no `root` entry) wiped the root config installed by `mcp/server.py:352`'s `basicConfig` at server start, leaving `forge.*` loggers propagating to a handler-less root.

**Context:** Discovered when manually verifying logging via curl + `tail console.log` — the lines never appeared. Fix was four lines: a `forge` namespace logger entry in `STDERR_ONLY_LOGGING_CONFIG` routed to the existing stderr handler.
**Source:** Conversation, `forge_bridge/console/logging_config.py`.

### `ps PPID=1` does not mean "launchd-supervised"
`subprocess.Popen(..., start_new_session=True)` produces a process with PPID=1 because the parent shell exits and init/launchd reaps. We assumed the running :9996 daemon was plist-managed for an entire diagnostic round before realizing `fbridge up` had started it.

**Context:** Burned ~30 minutes troubleshooting why `launchctl kickstart` wasn't restarting the working daemon. It wasn't — kickstart restarted the *broken* plist wrapper, which crash-looped silently. The actual working daemon was unrelated.
**Source:** Conversation, `forge_bridge/runtime/manager.py:148`.

### Test contracts can outlive the code they describe
Plan 20.1-08 wrote both the launchd wrapper templates AND test assertions enforcing `--transport streamable-http --mcp-port 9997`. Later, the CLI was refactored to use a `mcp http --port` subcommand. Templates, tests, and docs all stayed frozen at the old contract. The wrapper crash-looped in production, the tests passed because they validated the wrapper-as-written (not against the live CLI).

**Context:** The integration test `test_daemon_persistence` would have failed (it actually spawns the process) — but it was probably never run in CI, or marked integration-only. Fixed in `fix(packaging): realign Plan 20.1-08 contract with mcp http CLI` (5eb41a2).
**Source:** `tests/test_packaging.py`, `5eb41a2`.

### `httpx.ConnectTimeout` is NOT a subclass of `httpx.ConnectError`
It's `httpx.TimeoutException` → `httpx.HTTPError`. Catching only `httpx.ConnectError` misclassifies connect timeouts as protocol errors. Same shape in `urllib.error`: `HTTPError` *is* a subclass of `URLError`, so the order of `except` branches matters.

**Context:** Caught during PR41 spec review; pinned with regression-guard tests in both `tests/cli/test_pr41_exec_cli.py::test_exec_http_connect_timeout_classified_as_transport` and `tests/flame/test_pr42_http_integration.py::test_socket_timeout`.
**Source:** PR41/PR42 spec reviews.

### Click 8.2+ removed `mix_stderr` from `CliRunner`
The kwarg is gone; stderr is always captured separately via `result.stderr`. Code copying the old pattern fails with `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'`.

**Context:** First test run of `tests/cli/test_pr41_exec_cli.py` failed at fixture setup. `tests/test_cli_run.py` still uses the old form — likely also broken, separate cleanup.
**Source:** PR41 implementation.

### `print()` is not a fix for `extra={}` logging
When a logger doesn't print fields you set via `extra={}`, the answer isn't to switch to `print()` — it's to use positional args (`log.info("rid=%s ...", rid, ...)`). `print()` bypasses log levels, won't be captured cleanly by systemd/launchd's journal, and is inconsistent with the rest of the codebase.

**Context:** PR40 first-pass implementation considered this; spec review caught it. Final implementation uses `logging.getLogger("forge.exec").info(...)` with positional args.
**Source:** PR40 spec round 4.

### Reading env vars at module-level breaks tests that monkeypatch them
`BASE_URL = os.getenv("FORGE_CONSOLE_URL", "...")` at module top runs once at import. Tests that set `FORGE_CONSOLE_URL` after the module is imported will silently miss. Read inside the function for late-binding.

**Context:** PR41 spec review caught it; pinned with `test_exec_http_uses_env_override` and `test_env_override_changes_target_url`.
**Source:** PR41/PR42 spec reviews.

---

## Patterns

### Two-angle test split for HTTP-fronted commands
Helper-only tests pin transport correctness via `httpx.MockTransport` / `_MockResponse` urlopen mocks; CLI tests stub the helper with `monkeypatch.setattr` and exercise the Typer command end-to-end via `CliRunner`.

**When to use:** Any time a CLI command thinly wraps a transport. Helper tests fail clearly when transport classification breaks; CLI tests fail clearly when exit codes / rendering break. Each layer's failures point at one cause, not a tangle.
**Source:** `tests/cli/test_pr41_exec_cli.py`, `tests/flame/test_pr42_http_integration.py`.

### Synthesized PR31 envelope on transport failure
Flame's `run_command_from_flame` returns the same envelope shape for transport failures (CONNECT_ERROR, HTTP_STATUS, INVALID_JSON, UNKNOWN_ERROR) that the engine returns for execution failures. UI consumers don't branch on origin.

**When to use:** Any client adapter where the caller is a UI thread or other place that should never see exceptions. Pair with a documented note distinguishing synthesized vs engine-originated envelopes (e.g. via `request_id` semantics) so debugging is unambiguous.
**Source:** `forge_bridge/flame/integration.py`, PR42 spec.

### Lazy import of heavy modules inside CLI helpers
Inside `_exec_http`: `import httpx` happens on call, not at module top. Preserves the `cli/__init__.py` contract that `--help` is fast (no httpx in the import tree until a command actually needs it).

**When to use:** Any CLI tool with subcommands where most invocations don't touch the heavy import. Pair with a single-line comment so the next reader doesn't "fix" the import location.
**Source:** `forge_bridge/cli/exec.py`, `forge_bridge/cli/__init__.py`.

### Optional-injection for testability without a DI framework
`_exec_http(text, *, client: httpx.Client | None = None)` — production code passes nothing (own client created and closed); tests pass `httpx.Client(transport=MockTransport(handler))`. No global state, no DI container, no decorator magic.

**When to use:** Whenever a function constructs a single dependency that tests need to mock. Document the test-only nature of the kwarg in the docstring.
**Source:** `forge_bridge/cli/exec.py:42`.

### Stdlib HTTP for hosted-interpreter environments
For Flame's bundled Python (or any environment where you can't install dependencies), `urllib.request` covers single-shot POST cleanly: `Request(url, data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST")` + `urlopen(req, timeout=...)`. Roughly 30 lines including error classification.

**When to use:** Embedded Python interpreters, sandboxed environments, anywhere "no new dependency" is a hard constraint. Document the trade-off (no async, no connection pooling) explicitly.
**Source:** `forge_bridge/flame/integration.py`.

### `forge` namespace logger as escape hatch for `dictConfig` configs
When uvicorn's `LOGGING_CONFIG` doesn't set a root handler, application logs propagate to nothing. Adding a single `"forge": {"handlers": ["default"], "level": "INFO", "propagate": False}` entry routes the entire `forge.*` namespace to whatever handler the uvicorn config already has, without touching root.

**When to use:** Any application running under uvicorn (or any framework that rebuilds logging via `dictConfig`) where you have a stable application logger namespace.
**Source:** `forge_bridge/console/logging_config.py:31`.

---

## Surprises

### The launchd plist had been crash-looping silently for an unknown period
`/var/log/forge-bridge/console.log` had ~85,000 lines of Click error blocks (`No such option: --transport`). The wrapper's invocation hadn't matched the CLI's interface for who knows how long. Nobody noticed because the *working* daemon was started by `fbridge up` at some prior point, was running independently, and `fbridge status` reports it as "managed."

**Impact:** No functional impact (working daemon was unaffected) but represents a class of silent infrastructure rot — a supervisor running a broken script under KeepAlive that forever fails fast and respawns. Worth a periodic `tail console.log | head` check, or a heartbeat assertion in `fbridge doctor` that the plist's most recent stdout doesn't look like Click error output.
**Source:** Conversation, PR40 logging diagnosis.

### Logging visibility was the unblocker for everything
The actual fix was 4 lines (one entry in `STDERR_ONLY_LOGGING_CONFIG`). Discovering that the fix was *needed* (vs. a false positive in caplog testing) took more session time than every other PR40 task combined.

**Impact:** Reinforced: never trust caplog as proof of production logging. Always run a real curl against a real daemon and `tail` the real log destination once before declaring logging "done."
**Source:** PR40 verification round.

### The "right" log destination wasn't the documented one
The plist's StandardOutPath was `/var/log/forge-bridge/console.log`, but the actually-running daemon (started by `fbridge up`) wrote to `~/.forge-bridge/logs/mcp_http.log`. We spent ~10 minutes verifying that the logs were broken when actually they were just in a different file.

**Impact:** Two log destinations for the "same" daemon depending on launch path is a discoverability footgun. After PR42 + the plist fix, both routes write to `console.log` (one process supervised by launchd). The runtime/manager.py log path is dead unless `fbridge up` is used outside the plist-supervised flow.
**Source:** PR40 verification round.

### The packaging test suite was wrong, not protective
`test_packaging.py` had three Plan 20.1-08 contract assertions enforcing the *old* `--transport ... --mcp-port ...` invocation against templates that were correct-when-written but wrong-as-shipped. The tests passed because they tested templates against templates, not against the live CLI. The integration test that *would* have caught the divergence (`test_daemon_persistence`, marked `@pytest.mark.integration`) was excluded from default runs.

**Impact:** Test contracts are most valuable when they catch drift between layers. Same-layer tests (template ↔ template) are tautologies. Realigned in `5eb41a2`.
**Source:** `tests/test_packaging.py`, commit `5eb41a2`.

### Empty-input behavior diverged across surfaces before PR42 fix
Pre-PR42, the engine returned `"Nothing to execute after parsing."` for empty input, but Flame's adapter short-circuited locally with `"Command is empty."`. Same code (`EMPTY_COMMAND`), different message, same condition. Nobody had hit it because the right-click hook prompts and early-returns on cancel — but the divergence existed in code for an unknown duration.

**Impact:** Local short-circuits in adapters are tempting (they save a round-trip!) but actively dangerous when the goal is single-runtime uniformity. Single source of truth means *every* caller goes through the same path, including for trivial cases. Fixed in PR42 by removing the local check entirely.
**Source:** PR42 spec review.

---

## Final architecture

```
CLI   → HTTP → /api/v1/exec
Flame → HTTP → /api/v1/exec
Chat  → HTTP → /api/v1/exec
                  ↓
             execute_command
```

Three commits over ~11 hours: `d16c1e0` (PR40), `5eb41a2` (packaging contract realignment), `63a8dea` (PR41), `3dad491` (PR42). Net diff: +1,019 / -213 across 14 files, plus deletion of `tests/flame/test_pr38_integration.py`.
