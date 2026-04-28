---
phase: 16-fb-d-chat-endpoint
plan: 03
subsystem: forge-bridge/console (Web UI presentation)
tags: [css, ui, chat-panel, logik-projekt-palette, tokens-only]
type: execute
wave: 1
autonomous: true
requirements:
  - CHAT-04
dependency_graph:
  requires:
    - .planning/phases/16-fb-d-chat-endpoint/16-CONTEXT.md (D-07/D-08/D-09/D-10 design decisions)
    - .planning/phases/16-fb-d-chat-endpoint/16-PATTERNS.md (lines 408-428 CSS pattern + token-mapping table)
    - forge_bridge/console/static/forge-console.css (existing LOGIK-PROJEKT palette at line 1)
  provides:
    - "LOGIK-PROJEKT amber spinner: .spinner-amber + @keyframes spin"
    - "Chat transcript layout: .chat-transcript flex container"
    - "Chat-message bubbles: .chat-message{,--user,--assistant,--tool}"
    - "Tool-trace transparency block: .chat-tool-trace + summary + pre"
    - "Chat textarea styling: #chat-input{,:focus}"
  affects:
    - .planning/phases/16-fb-d-chat-endpoint/16-05-PLAN.md (panel.html + forge-chat.js consume these classes)
tech_stack:
  added: []
  patterns:
    - "Append-only CSS extension via section-comment divider (existing convention at line 38+)"
    - "100% token reuse — every value references --color-*, --space-*, --text-*, --font-* defined in :root"
    - "Pure-CSS spinner animation (no SVG, no new asset)"
key_files:
  created: []
  modified:
    - forge_bridge/console/static/forge-console.css
decisions:
  - "Honored D-07 amber-bordered assistant message bubble (LOGIK-PROJEKT identity marker)"
  - "Honored D-08 amber-on-muted-amber spinner (track #664e00, leading edge #cc9c00)"
  - "Honored D-10 #chat-input ID (matches plan 16-05's panel.html selector)"
  - "Used --color-surface-deep (#1a1a1a) for .chat-tool-trace recessed-block look (matches existing .code-card pre treatment)"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-27T17:32:42Z"
  commits: 1
  files_modified: 1
  lines_added: 14
  lines_removed: 0
---

# Phase 16 Plan 03: Chat Panel CSS Foundation Summary

LOGIK-PROJEKT amber spinner CSS, chat-transcript flex layout, four chat-message bubble variants, collapsible tool-trace transparency block, and chat textarea styling — appended to `forge_bridge/console/static/forge-console.css` using zero new color values, only the existing `:root{--color-*}` token palette.

## Lines Appended

**14 lines added** to `forge_bridge/console/static/forge-console.css` (file grew from 69 → 83 lines):

1. Blank line (existing section-divider convention)
2. Section comment: `/* === Phase 16 (FB-D) -- chat panel === */`
3-13. Eleven CSS rules + one `@keyframes spin` at-rule:
   - `.chat-transcript` (flex column, max-height 60vh, scroll)
   - `.chat-message` (base bubble: surface bg, padding, rounded)
   - `.chat-message--user` (left border: muted text color)
   - `.chat-message--assistant` (left border: **amber `--color-accent`** — LOGIK-PROJEKT voice marker)
   - `.chat-message--tool` (mono, label-size, muted color)
   - `.chat-tool-trace` (deep surface, bordered, padded)
   - `.chat-tool-trace summary` (cursor pointer, amber, mono — clickable affordance)
   - `.chat-tool-trace pre` (whitespace-pre-wrap, word-break, mono, label-size)
   - `.spinner-amber` (12×12 inline-block, 2px amber border with leading edge, 0.7s linear spin)
   - `@keyframes spin` (single `to{transform:rotate(360deg)}` rule)
   - `#chat-input` (full-width textarea, mono, deep surface, vertical resize)
   - `#chat-input:focus` (amber border on focus — LOGIK-PROJEKT focus marker)

## No Existing Rules Modified

`git diff --stat`: **14 insertions(+), 0 deletions(-)**. The diff begins at the original line 70 and adds only new content; lines 1-69 are byte-identical to the pre-commit state. The LOGIK-PROJEKT palette declaration in `:root{}` (line 1) is untouched.

## Acceptance Criteria — All 9 PASS

| Criterion | Pre-edit | Post-edit | Pass |
|-----------|----------|-----------|------|
| `spinner-amber` count | 0 | 1 | ≥1 ✓ |
| `@keyframes spin` count | 0 | 1 | =1 ✓ |
| `chat-transcript` count | 0 | 1 | ≥1 ✓ |
| `chat-message--assistant` count | 0 | 1 | ≥1 ✓ |
| `chat-message--user` count | 0 | 1 | ≥1 ✓ |
| `chat-tool-trace` count | 0 | 3 | ≥1 ✓ |
| `#chat-input` count | 0 | 2 | ≥1 ✓ |
| `var(--color-accent)` delta | 10 | 14 | +4 ≥ +2 ✓ |
| Brace balance | 69 = 69 | 82 = 82 | balanced ✓ |
| Python sanity (`'spinner-amber' in css and ...`) | — | OK | ✓ |

## Token Reuse — Zero New Colors

Every CSS value references an existing token from the line-1 `:root{}` palette:

| Token | Used In |
|-------|---------|
| `--color-accent` (#cc9c00) | `.chat-message--assistant`, `.chat-tool-trace summary`, `.spinner-amber` (top-color), `#chat-input:focus` (border) |
| `--color-accent-muted` (#664e00) | `.spinner-amber` (track) |
| `--color-surface` (#2a2a2a) | `.chat-message` (bg) |
| `--color-surface-deep` (#1a1a1a) | `.chat-tool-trace` (bg), `#chat-input` (bg) |
| `--color-text` (#cccccc) | `.chat-tool-trace pre`, `#chat-input` |
| `--color-text-muted` (#999999) | `.chat-message--user` (border), `.chat-message--tool` |
| `--color-border` (#333333) | `.chat-tool-trace` (border) |
| `--color-border-md` (#555555) | `#chat-input` (border) |
| `--space-sm/md` (8px/16px) | gap, padding, margin throughout |
| `--text-label` (12px) | tool/trace/summary font sizes |
| `--font-mono` (Consolas/Monaco/...) | tool message, trace blocks, chat textarea |

Confirmed by `grep -c '^--color-' forge_bridge/console/static/forge-console.css` → 0 (no new custom properties added; the palette continues to live exclusively in the line-1 `:root{}` declaration).

## Plan 16-05 Consumption Contract

Plan 16-05 (panel.html + forge-chat.js) will consume these classes without re-declaring colors. The class names ship as the contract:

- `.spinner-amber` — applied to `<span>` shown via `x-show="loading"` Alpine binding during stream
- `.chat-transcript` — outer scroll container holding the message list
- `.chat-message` + variant — root class on each rendered message bubble; one of `--user` / `--assistant` / `--tool` always co-applied
- `.chat-tool-trace` — wraps the `<details><summary>tool: forge_list_pending</summary><pre>{stringified args/result}</pre></details>` collapsible block
- `#chat-input` — ID on the chat `<textarea>` (D-10 lock — selector identity matters because `forge-chat.js` will key off it via `document.getElementById`)

## Deviations from Plan

None — plan executed exactly as written. Pre-flight grep confirmed zero existing collisions; the appended block matches the plan's verbatim CSS literally, including formatting and the leading blank line + section-comment divider.

## Threat Flags

None. The plan's threat model anticipated only T-16-03-01 (information disclosure on a static asset — accepted) and T-16-03-02 (palette-token leak — mitigated by brace-balance assertion + new-token grep). Both mitigations verified post-edit:
- Brace balance: 82 = 82 ✓
- New `--color-*` properties: 0 ✓ (palette confined to line-1 `:root{}`)

## Self-Check: PASSED

**Created files (none — modifications only):**
- N/A

**Modified files:**
- `forge_bridge/console/static/forge-console.css` — FOUND, 83 lines, +14/-0 vs HEAD~1

**Commits:**
- `a3d9c41` — `feat(16-03): append chat-panel CSS rules to forge-console.css` — FOUND in `git log`

**Verification commands re-run post-commit:**

```text
$ python -c "import pathlib; css = pathlib.Path('forge_bridge/console/static/forge-console.css').read_text(); assert 'spinner-amber' in css and '@keyframes spin' in css and 'chat-transcript' in css and 'chat-message--assistant' in css and 'chat-tool-trace' in css and '#chat-input' in css; print('OK')"
OK: all 6 classes present

$ python -c "import pathlib; css = pathlib.Path('forge_bridge/console/static/forge-console.css').read_text(); assert css.count('{') == css.count('}')"
(exit 0)

$ git diff --stat HEAD~1 -- forge_bridge/console/static/forge-console.css
1 file changed, 14 insertions(+)
```

All acceptance criteria PASS. Plan 16-05 unblocked for the chat panel surface (Wave 3).
