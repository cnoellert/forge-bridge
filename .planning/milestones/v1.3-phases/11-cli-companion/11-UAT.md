# Phase 11 — CLI Companion — Soft UAT (D-08)

**Operator:** CN/dev (developer-as-operator per D-08)
**Date:** 2026-04-24
**Server:** `python -m forge_bridge` on :9996
**Criterion:** "Can I decipher the output without re-reading the source?"

---

[2026-04-24] PASS — all five subcommands decipherable on a real TTY; only friction was that `manifest` and `tools` rendered visually indistinguishable, so the operational reason for both existing isn't legible from the output alone.

## Notes

- `tools`, `execs --since 24h`, `health`, and `doctor` each communicated their purpose without re-reading source. Doctor's `[check] ok|warn|fail / fact / try` table reads exactly as designed; the `try:` column made the next action obvious.
- Server-unreachable UX confirmed end-to-end (locked stderr message + exit 2; `--json` envelope on stdout + exit 2).
- Rich rendering on TTY confirmed: amber bold-yellow headers, `rich.box.SQUARE` borders, `Created ▼` glyph legible, status chips colored, 8-char hash on lists.

## Observation worth carrying forward (NOT a fail per D-08)

`forge-bridge console manifest` and `forge-bridge console tools` show the same column set. This is per CONTEXT.md Area 3 ("Manifest — same column set as `tools` list since the manifest IS the tool list with sidecar metadata"), so the rendering is faithful to the design. But during dogfood the redundancy was visible — there's no on-screen signal of *why* both commands exist or what the operator should reach for in each case.

Candidate follow-ups (no Phase 11.1 needed; this is v1.4 polish material):

1. **Differentiate column set on `manifest`** — surface sidecar-only fields the tool registry doesn't carry (e.g., `synthesized_at` source path, `intent_summary`, sidecar file size or sha) so the manifest view earns its own real estate.
2. **Caption-line in `manifest`** — a one-line subtitle above the table ("Synthesized tool sidecars on disk — N entries") that names what this view is *for* relative to `tools`.
3. **Cross-link in `--help` text** — explicit "see also: `console tools`" in `manifest --help` and vice versa, plus a one-liner on which to use when.

Recommend bundling option 2 + option 3 into a v1.4 polish pass alongside the Phase 10.1 HUMAN-UAT humanized-timestamps follow-up — both are "obvious in hindsight" UX finishes that don't warrant their own phase.

Per D-08 no-ship-back-to-planning clause: this is a PASS, not a FAIL. The follow-up is queued as a deferred note, not a blocking gap.
