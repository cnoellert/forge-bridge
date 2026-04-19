# Feature Research

**Domain:** Cross-repo pip dependency consumption and learning pipeline integration for a downstream Python application
**Researched:** 2026-04-15
**Confidence:** HIGH — based on direct code inspection of both repos, pyproject.toml analysis, and verified Python packaging best practices

---

## Context: What This Milestone Actually Is

forge-bridge v1.1 is NOT a new product feature. It is an integration milestone with three concrete sub-goals:

1. **Harden forge-bridge's public API surface** so projekt-forge can import from it safely
2. **Rewire projekt-forge** to import from `forge-bridge` (pip dep) instead of duplicating code
3. **Wire the learning pipeline into projekt-forge** — LLM override, prompt enrichment, DB persistence

The "features" here are engineering contracts, not user-visible capabilities. The audience for FEATURES.md in this context is: what must forge-bridge expose, and what must projekt-forge consume, for both repos to remain independently deployable and testable.

---

## Table Stakes (Expected Behaviors for Cross-Repo Pip Consumption)

Features a downstream pip consumer expects. Missing these = integration is fragile or impossible.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Stable public API surface via `__init__.py` exports | Consumers import from package root; anything not in `__all__` or top-level `__init__` is internal and may change | LOW | forge-bridge's top-level `forge_bridge/__init__.py` currently has one line: a docstring. No exports declared. Must add explicit `__all__` and re-export key symbols. |
| `configure()` callable before first use | projekt-forge connects to a different host/port than the default 127.0.0.1:9999 (render node vs. desktop) | LOW | `bridge.configure()` already exists. Needs to be re-exported from package root and documented as stable API. |
| `register_tools()` and `get_mcp()` as stable entry points | projekt-forge adds forge-specific tools (catalog, orchestrate, scan, seed) to the shared MCP server without forking server.py | LOW | Already implemented in `forge_bridge/mcp/__init__.py`. Needs to appear in top-level exports and have integration-level test coverage. |
| `set_execution_callback()` as stable hook | projekt-forge wires its own execution observer (learning pipeline integration point) without modifying bridge.py | LOW | Already exists in bridge.py. Is not currently exported from package root. Must be promoted to stable API. |
| pyproject.toml extras maintained for optional deps | Consumers who don't need LLM features (e.g. a plain Flame tool user) should not be forced to install openai/anthropic | LOW | Already implemented as `[project.optional-dependencies] llm = [...]`. Must remain — do not collapse into main dependencies. |
| LLM router importable as standalone component | projekt-forge needs to override the LLM backend (use its own Ollama config, its own DB connection) without inheriting forge-bridge defaults | MEDIUM | `from forge_bridge.llm.router import LLMRouter` must work and LLMRouter must accept constructor injection (base_url, model, system_prompt) rather than relying solely on env vars. |
| Learning pipeline components importable independently | projekt-forge wires ExecutionLog, SkillSynthesizer, and ProbationTracker against its own DB without activating forge-bridge's full server | MEDIUM | Currently each component is importable from `forge_bridge.learning.*`. Must remain importable without triggering MCP server startup side-effects. |
| No side effects at import time | `import forge_bridge` must not start servers, connect to databases, or read files | LOW | Critical for downstream consumers who control their own startup lifecycle. Current server.py and mcp/server.py both have module-level `mcp = FastMCP(...)` instantiation — harmless if not called, but must be verified. |
| Documented migration path for duplicated code | projekt-forge's `forge_bridge/bridge.py`, `forge_bridge/tools/*` are duplicates of forge-bridge equivalents. The removal path must be unambiguous. | MEDIUM | At minimum: which modules to delete, which imports to change, which tests to re-point. This is implementation guidance, not a code feature, but it must exist before anyone touches the code. |

---

## Differentiators (Integration Value-Add)

Features that make the integration more than a simple re-import.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LLM router constructor injection (not env-var-only) | projekt-forge has its own Ollama on assist-01 and its own model preferences. If forge-bridge's router only reads env vars, projekt-forge must set global env vars (fragile in multi-process deployments). Constructor injection lets each consumer own its router config. | MEDIUM | `LLMRouter(base_url=..., model=..., system_prompt=...)` — fall back to env vars when constructor args are None. Clean override semantics. |
| Execution log path overridable at construction | projekt-forge persists execution data in its own Postgres DB and its own filesystem layout. The log path `~/.forge-bridge/executions.jsonl` is a forge-bridge default that projekt-forge should not be forced to use. | LOW | `ExecutionLog(log_path=Path(...))` already accepts a path argument. The default is fine for standalone use. Document that downstream consumers should pass their own path. |
| Learning pipeline wiring via callback, not subclassing | projekt-forge integrates by providing a callback to `set_execution_callback()` — no subclassing, no monkey-patching | LOW | The callback pattern is already in place. What's missing is documentation and a reference integration. The feature is: write the integration example that projekt-forge implements. |
| Synthesized tool output dir overridable | projekt-forge may want synthesized tools in a project-specific location, not `~/.forge-bridge/synthesized/` | LOW | `watch_synthesized_tools(synthesized_dir=Path(...))` already accepts override. Document this as an integration point. |
| Parallel LLM prompt enrichment from forge DB | projekt-forge has richer project/shot context in Postgres than forge-bridge's generic system prompt provides. Enriched prompts produce better synthesized tools. | HIGH | This is the most complex integration feature. projekt-forge intercepts synthesis calls and prepends shot/project context from its DB before invoking forge-bridge's LLMRouter. Requires a synthesis prompt hook (inject before LLM call). Not currently supported — needs a `pre_synthesis_hook` callback on SkillSynthesizer. |
| Tool provenance visible in MCP tool metadata | Agents calling MCP tools benefit from knowing whether a tool is builtin, synthesized, or forge-specific. The `_source` tag on registered tools already supports this. | LOW | Already implemented in registry.py. The differentiator is exposing this through the MCP tool description/annotation so agents see it without calling a separate introspection tool. |

---

## Anti-Features

Features that seem natural but create architectural problems.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Merge forge-bridge and projekt-forge into a monorepo | Tempting once they depend on each other, but forge-bridge must remain independently deployable (no forge DB, no forge CLI) | Keep separate repos. Use pip editable install during development (`pip install -e /path/to/forge-bridge`). CI in projekt-forge installs forge-bridge from git or TestPyPI. |
| projekt-forge importing private internals (`forge_bridge._*`) | Private symbols may change without notice. Integration on private internals breaks silently. | Harden the public API first. Any symbol projekt-forge needs that isn't exported is a signal to promote it, not to hack around it. |
| Vendoring forge-bridge inside projekt-forge | Copies diverge immediately. Bug fixes in forge-bridge don't propagate. Defeats the whole purpose of extraction. | Always consume via pip. `pip install -e .` for local dev, pinned version for production. |
| Shared database between forge-bridge and projekt-forge | forge-bridge has its own PostgreSQL schema (entities, relationships, events, registry). projekt-forge has its own schema (projects, shots, media, users). Merging schemas creates migration coupling. | Keep separate schemas, possibly same Postgres instance. forge-bridge's schema is an independent service boundary. |
| Learning pipeline activation on every import | If `import forge_bridge.learning` starts watchers, opens file handles, or connects to DB, it breaks consumers who only want specific components | Lazy activation only. Components must be instantiated explicitly by the consumer. No module-level singleton initialization. |
| Blocking LLM calls in projekt-forge's async handlers | projekt-forge uses asyncio throughout. Calling sync LLM completions inside async handlers blocks the event loop. | Use `LLMRouter.acomplete()`. If the router only has sync `complete()`, the consumer must wrap with `asyncio.to_thread()` — document this explicitly. |
| Auto-wiring learning pipeline in forge-bridge server startup | If forge-bridge's `__main__.py` activates the learning pipeline unconditionally, projekt-forge (which starts its own server) gets double-wiring | `set_execution_callback()` must default to None (already does). Server startup must not set a callback unless explicitly configured. Consumer owns the wiring. |
| Namespace collision between forge-bridge and projekt-forge tools | Both repos have tools named things like `flame_publish_sequence`. If both register against the same MCP instance, the second registration overwrites the first. | Namespace enforcement via registry.py's `_VALID_PREFIXES` already blocks this. projekt-forge registers under `forge_*` prefixes. forge-bridge's builtins use `flame_*` and `forge_*` prefixes for its own tools. The split must be documented and tested. |

---

## Feature Dependencies

```
Stable public API (`__init__.py` exports)
  └──required by──> projekt-forge import rewiring
  └──required by──> Cross-repo integration tests

configure() re-exported from package root
  └──required by──> projekt-forge startup (non-default host/port)

set_execution_callback() re-exported from package root
  └──required by──> Learning pipeline wiring in projekt-forge
      └──required by──> LLM override in projekt-forge
      └──required by──> Prompt enrichment from forge DB

LLMRouter constructor injection
  └──required by──> LLM override in projekt-forge
      └──required by──> Prompt enrichment hook

pre_synthesis_hook on SkillSynthesizer
  └──required by──> Prompt enrichment from forge DB (highest complexity)
  └──depends on──> SkillSynthesizer existing (v1.0 complete)

register_tools() / get_mcp() stable exports
  └──required by──> projekt-forge registering its own tools
  └──required by──> Integration tests that verify tool registration

Cross-repo integration tests
  └──required by──> Confidence that both repos work together
  └──depends on──> Stable API surface (all items above)
```

### Dependency Notes

- **Stable API surface** is the unblocking item. Everything else in this milestone depends on knowing which symbols are stable contracts vs. internal implementation details. Start here.
- **LLM override** (constructor injection) is independent of the import rewiring. Can be done in parallel.
- **Prompt enrichment** is the highest complexity item and the only one that requires a new feature in forge-bridge (pre_synthesis_hook). Block it on everything else.
- **Import rewiring** in projekt-forge (deleting duplicated files, fixing imports) is purely mechanical once the API surface is stable. Low risk, medium effort.

---

## MVP Definition

### Launch With (v1.1)

Minimum viable integration — projekt-forge consumes forge-bridge and learning pipeline is wired.

- [ ] **Stable `__init__.py` exports** — `configure`, `set_execution_callback`, `register_tools`, `get_mcp`, `BridgeResponse`, `BridgeError`, `BridgeConnectionError` re-exported from package root. `__all__` declared.
- [ ] **LLMRouter constructor injection** — `LLMRouter(base_url, model, system_prompt)` with env-var fallback. Documents the override contract.
- [ ] **projekt-forge import rewiring** — delete duplicated `forge_bridge/bridge.py`, `forge_bridge/tools/*.py` (non-forge-specific), replace with `from forge_bridge import ...`. Done in projekt-forge repo.
- [ ] **Learning pipeline wired in projekt-forge** — projekt-forge startup calls `set_execution_callback(callback)` where callback records to projekt-forge's storage.
- [ ] **Cross-repo integration smoke test** — pytest fixture that installs forge-bridge as editable dep and verifies: configure(), tool registration, and execution callback fire correctly from projekt-forge's call sites.

### Add After Validation (v1.1.x)

- [ ] **Prompt enrichment hook** (`pre_synthesis_hook` on SkillSynthesizer) — add only once basic wiring is confirmed working. High complexity, high payoff.
- [ ] **Synthesized tool output dir override** documented and tested in projekt-forge context.
- [ ] **Tool provenance in MCP annotations** — surface `_source` tag in tool description strings.

### Future Consideration (v2+)

- [ ] **Shared synthesis manifest** — projekt-forge and forge-bridge sharing a synthesized tool registry (complex schema and lifecycle questions, defer).
- [ ] **Re-synthesis on failure with forge DB context** — failure re-synthesis enriched with project/shot data from forge Postgres.
- [ ] **Authentication** — explicitly deferred by design decision, not needed in local-first deployment.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Stable `__init__.py` exports | HIGH — unblocks all other items | LOW — declare exports, no logic change | P1 |
| configure() re-export | HIGH — projekt-forge breaks without it | LOW — one-liner re-export | P1 |
| set_execution_callback() re-export | HIGH — integration hook | LOW — one-liner re-export | P1 |
| register_tools() / get_mcp() re-export | HIGH — enables forge tool registration | LOW — already in mcp/__init__.py | P1 |
| LLMRouter constructor injection | HIGH — LLM override without env var hacks | MEDIUM — refactor constructor, maintain fallback | P1 |
| Import rewiring in projekt-forge | HIGH — eliminates drift risk | MEDIUM — mechanical but broad file changes | P1 |
| Learning pipeline wiring (callback) | HIGH — core milestone goal | MEDIUM — write integration code in projekt-forge | P1 |
| Cross-repo integration smoke tests | HIGH — confidence in correctness | MEDIUM — pytest fixture + editable install setup | P1 |
| pre_synthesis_hook on SkillSynthesizer | MEDIUM — better synthesis quality | HIGH — new API surface in forge-bridge | P2 |
| Synthesized dir override (documented) | LOW — only needed for custom deployments | LOW — already implemented, needs docs/tests | P2 |
| Tool provenance in MCP annotations | LOW — agent convenience | LOW — string formatting in registration | P3 |

---

## Cross-Repo Testing Strategy

This section is specific to this integration milestone and has no equivalent in the prior v1.0 research.

**Standard pattern for Python cross-repo integration:**

```bash
# In projekt-forge dev environment:
pip install -e /path/to/forge-bridge          # editable install for dev
pip install -e /path/to/forge-bridge[llm]     # with LLM extras

# In CI (GitHub Actions / local CI):
pip install forge-bridge @ git+https://github.com/cnoellert/forge-bridge.git@main
```

**What to test at integration boundary:**

| Test Type | What It Verifies | Where It Lives |
|-----------|-----------------|----------------|
| Import smoke test | `from forge_bridge import configure, set_execution_callback, register_tools` succeeds | projekt-forge tests/ |
| configure() override test | Setting non-default host/port propagates to HTTP calls | projekt-forge tests/ |
| callback wiring test | Execution callback fires with correct code + response args | projekt-forge tests/ |
| tool registration test | `register_tools(get_mcp(), [my_fn], prefix="forge_")` registers and is discoverable | projekt-forge tests/ |
| LLM override test | `LLMRouter(base_url="http://assist-01:11434/v1")` uses the injected URL | projekt-forge tests/ |
| No-side-effects test | `import forge_bridge` does not start servers or open DB connections | forge-bridge tests/ |

**Avoid:** Running projekt-forge's full integration test suite as part of forge-bridge CI. That creates a circular dependency. forge-bridge CI tests only forge-bridge. projekt-forge CI tests the integration.

---

## Sources

- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/__init__.py` — current state: one-line docstring, no exports (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/bridge.py` — configure(), set_execution_callback(), BridgeResponse, BridgeError (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/mcp/__init__.py` — register_tools(), get_mcp() already implemented (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/forge_bridge/llm/router.py` — LLMRouter env-var-only config, no constructor injection (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/forge-bridge/pyproject.toml` — optional deps correctly configured (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/bridge.py` — exists as duplicate, imports `from forge_bridge import bridge` internally (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/server/mcp.py` — imports all tools directly, no use of forge-bridge's register_tools() (HIGH confidence)
- Direct code inspection: `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` — no forge-bridge dependency listed (HIGH confidence, confirms work not yet done)
- Python Packaging User Guide — public API surface, __all__, SemVer: https://packaging.python.org/en/latest/discussions/versioning/
- Real Python — public API surface best practices: https://realpython.com/ref/best-practices/public-api-surface/
- setuptools entry_points documentation — plugin/callback registration patterns: https://setuptools.pypa.io/en/latest/userguide/entry_point.html
- pytest good integration practices — editable install cross-repo testing: https://docs.pytest.org/en/stable/explanation/goodpractices.html

---
*Feature research for: forge-bridge v1.1 projekt-forge integration*
*Researched: 2026-04-15*
