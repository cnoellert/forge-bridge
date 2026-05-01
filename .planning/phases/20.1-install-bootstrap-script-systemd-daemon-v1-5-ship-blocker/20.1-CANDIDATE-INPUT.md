---
status: candidate
phase: 20.1 (decimal phase per CONTEXT.md D-05 — pending Phase 20 close)
trigger: "Open after Phase 20 closes. Phase 20.1 picks up the install-script + persistent-config redesign that the Phase 20 UAT walk surfaced."
captured: 2026-05-01
captured_during: Phase 20 Track A author-walked UAT, Step 5 (env vars)
---

# Phase 20.1 candidate — install.sh + systemd daemon + persistent env config

> ## ⚠ HEADLINE — Phase 20.1 is a v1.5 milestone ship blocker
>
> The Phase 20 Track A UAT proved that **no normal Flame artist could complete `docs/INSTALL.md`**. The walker (project author with full system knowledge and SSH triage access) hit 13 gaps to reach all 5 surfaces. An artist would have abandoned in Step 3 within minutes — the doc demands knowledge (Postgres `pg_hba.conf` editing, `password_encryption` history, `--initdb` lifecycle, two-process launch order) that the doc itself does not provide.
>
> The architecture works (cross-host LLM via assist-01 Ollama validated end-to-end). The install procedure does not.
>
> **forge-bridge is not shippable to its target user until Phase 20.1 lands.** Treat 20.1 as the v1.5 ship gate, not as polish to defer.

## TL;DR (post-walk update, 2026-05-01 14:00)

Walked Phase 20 INSTALL.md end-to-end on flame-01. Surface 4 (chat endpoint cross-host to assist-01 Ollama) passed — the architecture works. But the walk surfaced **13 gaps** including a substantive doc lie (Step 6 claims `python -m forge_bridge` boots all four surfaces; reality is `python -m forge_bridge.server` must run first for `:9998`, then `python -m forge_bridge` for `:9996`/MCP). Combined with broken process lifecycle (Ctrl-C orphans), fragile env persistence (conda re-init), and pg_hba/`password_encryption` mismatches on stock Rocky, the conclusion is: **operator install belongs in systemd units, not in narrative prose**. Phase 20.1's spine is the daemon model. Bootstrap script + env file are supporting infrastructure. The "an artist can complete this" constraint is a first-class acceptance criterion — not just "the script runs cleanly," but "a Flame artist with no Linux/Postgres knowledge can run it and reach a working forge-bridge."

## Why this exists

During the Phase 20 Track A UAT walk on flame-01 (Rocky Linux 9.x, stock postgresql package), the walker hit **six** comprehension/operational gaps in INSTALL.md Step 3 alone before the doc walked end-to-end:

1. "As a Postgres superuser" gave no concrete identity (RHEL OS user `postgres` via sudo)
2. `sudo -u postgres` "permission denied" cwd warnings are benign — doc didn't pre-empt
3. `--initdb` needed even when the postgresql package was installed; doc's "if not installed" conditional was too soft
4. Stock Rocky `pg_hba.conf` ships with `ident` auth on 127.0.0.1, which rejects `forge:forge@localhost` out-of-the-box
5. `createuser -P` interactive password prompt is fragile (typo-prone, no idempotent re-run)
6. Cluster `password_encryption=md5` (Rocky default — pre-Postgres 14) requires md5 (not scram-sha-256) in pg_hba

Then at Step 5 (env vars), gap 7 surfaced:

7. Doc tells operator to `export FOO=bar` but never addresses persistence (~/.bashrc? .env? systemd?)

Gaps 3, 4, 6 are "doc-only-hard" — they require conditional logic against the actual fixture state (Postgres version, install method, password_encryption setting). That's exactly what scripts handle better than narrative prose. Gap 7 is a clean architectural decision that belongs in a config-file design, not exhortation in the doc.

The Phase 20 thesis was reality-audit. The audit caught a structural truth: **the install procedure is not a doc; it is a script with a verification checklist.** Phase 20 shipped the canonical doc as designed; Phase 20.1 is the honest follow-up that the walk evidence demands.

## Scope

### Deliverables

1. **Two systemd units** (the spine — confirmed by walk: forge-bridge is a two-process system, not one):
   - **`packaging/systemd/forge-bridge-server.service`** — runs `python -m forge_bridge.server` on `:9998` (the WebSocket bus). `Type=simple`, `EnvironmentFile=/etc/forge-bridge/forge-bridge.env`, `ExecStart=/path/to/conda/envs/forge/bin/python -m forge_bridge.server`, `Restart=on-failure`, `User=cnoellert` (or whatever operator user)
   - **`packaging/systemd/forge-bridge.service`** — runs `python -m forge_bridge` on `:9996` + MCP stdio. `Requires=forge-bridge-server.service`, `After=forge-bridge-server.service`, same EnvironmentFile, `StandardInput=null` (sidesteps the stdio handshake-exit problem entirely — no `tail -f /dev/null` keepalive needed in production), same Python path, `Restart=on-failure`
   - **Outcome:** `systemctl start forge-bridge` cascade-starts both processes in correct order, env loaded from one file, lifecycle managed cleanly, logs go to journalctl. Solves gaps 7, 8, 9, 10, 11, 12 in one architectural choice.

2. **`scripts/install-bootstrap.sh`** (the imperative setup the systemd units depend on existing):
   - Imperative bootstrap of Postgres on the operator host: package install detection → `postgresql-setup --initdb` if needed → `systemctl enable --now postgresql` → wait-for-port-5432 gate
   - `pg_hba.conf` auth-method alignment: probe `SHOW password_encryption`, set pg_hba accordingly (md5 OR scram-sha-256), reload (the Rocky/`md5` reality the walk surfaced)
   - Role + database creation via `psql -c "CREATE USER ... WITH PASSWORD 'forge'; CREATE DATABASE forge_bridge OWNER forge;"` (idempotent, password literal, single command — gap #5)
   - Alembic migrations (`alembic upgrade head`)
   - Copies `packaging/systemd/*.service` → `/etc/systemd/system/`, runs `systemctl daemon-reload`
   - Copies `packaging/forge-bridge.env.example` → `/etc/forge-bridge/forge-bridge.env` if absent, prompts the operator to edit
   - Idempotent re-runs (must succeed if already partially installed)
   - Distro detection (Rocky/RHEL primary; macOS support via launchd is a stretch goal — Phase 20.2 if needed)
   - Clear pass/fail output the operator can paste into a UAT log

3. **`packaging/forge-bridge.env.example`**:
   - `KEY=VALUE` format (no `export` — works for both shell sourcing and systemd `EnvironmentFile=`)
   - Every operator-tunable env var with a one-line comment explaining purpose
   - Sensible defaults (`FORGE_DB_URL`, `FORGE_LOCAL_LLM_URL=http://localhost:11434/v1`, `FORGE_LOCAL_MODEL=qwen2.5-coder:32b`, `FORGE_PORT=9998`, `FORGE_CONSOLE_PORT=9996`)
   - `FORGE_LOCAL_LLM_URL` line is heavily commented: "Most operators run Ollama on a separate LLM service host — set this to your LLM host's URL (e.g. http://192.168.86.15:11434/v1)"

4. **`docs/INSTALL.md` re-shape**:
   - Step 3 collapses to: "Run `sudo ./scripts/install-bootstrap.sh` — handles all Postgres setup, installs systemd units, copies env template. Verify with `nc -z localhost 5432` and `alembic current`."
   - Step 5 collapses to: "Edit `/etc/forge-bridge/forge-bridge.env` (created by Step 3). At minimum, set `FORGE_LOCAL_LLM_URL` to your LLM service host."
   - Step 6 collapses to: `sudo systemctl start forge-bridge && systemctl status forge-bridge`. The "all four surfaces in one shot" lie is removed; systemd handles the two-process orchestration invisibly.
   - Steps 1, 2, 4, 7, 8 stay roughly as-is (conda env, pip install, Flame hook install, surface verification, doctor). Scripts handle imperative bits; doc handles understanding + verification + topology.
   - Step 7's surface checks become honest because the underlying state is now reliable.
   - `Operator-workstation install` framing from Phase 20-07 is preserved.

5. **Stop / restart / logs documentation**:
   - `systemctl stop forge-bridge` / `systemctl restart forge-bridge`
   - `journalctl -u forge-bridge -f` (live logs)
   - `journalctl -u forge-bridge-server -f` (bus logs)
   - These replace the "how do I stop the server?" gap that Phase 20 surfaced (gap #12).

### Non-goals (don't drift)

- Do NOT bundle Flame install into `install.sh`. Flame install is its own story.
- Do NOT bundle Ollama install into `install.sh`. Ollama is on a SEPARATE host (or local with operator-installed). The script's job is forge-bridge + Postgres + env, not the LLM service host.
- Do NOT make `install.sh` interactive beyond `$EDITOR` for the env file. It must run cleanly under `bash install.sh -y` for unattended re-runs.
- Do NOT introduce auth (still v1.6+ scope per D-06).
- Do NOT replace the Track B / MCP-only carveout — `install.sh` should support `--track-b` to skip Flame-hook bits.

## Inputs from Phase 20

- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` — the gap log is the requirements doc. Every gap that says "scriptable" is a thing the script must handle.
- `.planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md` — D-04 in-flight gap-fix and D-05 decimal-phase rules. Phase 20.1 is the canonical D-05 invocation.
- `docs/INSTALL.md` at Phase 20 close — the "before" state of the doc; Phase 20.1 reshapes it.
- `scripts/install-flame-hook.sh` — the precedent for "scripts own imperative install, doc references the script."

## Acceptance criteria

### Primary criterion (the constraint that defines "done")

**A Flame artist with no Linux sysadmin background, no Postgres administration knowledge, and no familiarity with conda, systemd, or the forge-bridge architecture can complete the install end-to-end and reach all 5 surfaces.**

This is non-negotiable. If the artist hits a single comprehension gap that requires Stack Overflow, asking the author, or any out-of-doc knowledge, Phase 20.1 has not closed. "The script runs without error" is necessary but not sufficient. "An artist could install this and start using it" is the bar.

### Walk shape (Phase 20.1's own UAT)

1. Fresh Rocky 9 box, postgresql package present but cluster uninitialized, no forge user, no forge_bridge db
2. Operator clones the repo, runs `sudo ./scripts/install-bootstrap.sh`
3. Script detects state, initializes cluster, aligns pg_hba, creates role+db, runs alembic, installs systemd units, writes `/etc/forge-bridge/forge-bridge.env` from template, prompts operator to review
4. Operator edits env file (the template's prose makes "set `FORGE_LOCAL_LLM_URL` to your LLM host" obvious; defaults work for single-machine), saves
5. Operator runs `sudo systemctl start forge-bridge && systemctl status forge-bridge`
6. All 5 surfaces green; `forge doctor` reports healthy

### Validation requirements

- Phase 20.1's UAT MUST be walked by an actual non-author — not the project author, not Claude. If no human non-author is available, Phase 20.1 stays open until one is. (Compare to Phase 20's D-02.1 amendment, where author-walk was accepted as a deviation; for 20.1 it is NOT acceptable, because the whole point of 20.1 is to make the install accessible to non-authors.)
- The non-author MUST be a representative of the target user — a Flame artist or pipeline operator without sysadmin training. Not another developer.
- Zero gaps. Any gap surfaced is either a doc-only patch inline (D-04), a code-fix follow-up plan, or — if substantive — Phase 20.1.1 / 20.2 per fractal D-05.

## Cross-references

- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` (gap log — the requirements doc)
- `.planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md` (D-04 / D-05 dispositions)
- `docs/INSTALL.md` (the artifact being reshaped)
- `scripts/install-flame-hook.sh` (the script precedent)
- `forge_bridge/llm/router.py:181-210` (env vars `install.sh` must respect)
- `forge_bridge/store/session.py:44-54` (env vars `install.sh` must respect)
- `forge_bridge/cli/doctor.py` (the verification step `install.sh` should chain to)
