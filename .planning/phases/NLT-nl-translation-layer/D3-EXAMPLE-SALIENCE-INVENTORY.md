# D3 — Example-Salience Inventory (NLT discovery, bridge-side)

**Purpose:** defect #1 (`prefix→noise`) was one instance; D3 maps the whole liftable-example class across the
tool surface the compiler sees, so Phase 4's grounding slice knows its true scope.
**Method:** swept `forge_bridge/tools/*.py` for literal example *values* in `Field(description=…)` + docstrings
(`e.g.`, quoted literals, `Example call:`), then classified by **liftability risk** = can the LLM copy the
literal into a real param and produce a plausible-but-wrong value?

---

## Three headline findings (the part that matters)

1. **The prefix-lift is a 3-site class, not one bug.** The exact `"e.g. 'noise', 'tst'"` /
   `"e.g. 'noise', 'spk', 'gen'"` pattern appears on **three** rename-family mutation tools — defect #1 is
   the class, not an isolated defect. (`[[feedback-sibling-check-before-fix-scope-declared]]`.)
2. **Cross-tool bleed — read-tool examples leak into mutation fills.** Defect #3's wrong *value* `30sec_21`
   is almost certainly lifted from `InspectVersionsInput`'s docstring (`sequence_name="30sec_21"`, appears
   **twice**, `timeline.py:1094`) — a **read** tool. So the fix CANNOT be scoped to mutation tools: the
   compiler sees the whole tool surface, and a read tool's example supplied a mutation's bad fill.
3. **Example-salience is the fill-of-last-resort.** When a param lacks a grounded source — contextual gap
   (defect #3), extraction gap (defect #2) — the model reaches for the nearest example. So stripping
   liftable *value* examples shrinks the blast radius of the OTHER translation gaps too, not just defect #1.
   This is why D3 is worth doing as its own slice even though each named defect has its own root cause.

---

## Inventory (classified by liftability risk)

### HIGH — concrete identifier/name/prefix values; lift → plausible-but-wrong real param

| Site | Tool | Field / source | Lifted value class |
|---|---|---|---|
| `timeline.py:243` | `flame_rename_shots` (RenameInput) — **MUTATION**; also the C2 executor's discover delegate (`ApplyRenameInput ≡ RenameInput`) | `prefix` `"e.g. 'noise', 'tst'"` | **defect #1 confirmed source** |
| `timeline.py:215` | `flame_preview_rename` (PreviewRenameInput) — dry-run mutation | `prefix` `"e.g. 'noise', 'tst'"` | prefix-lift |
| `publish.py:27` | `RenameShots` (stage/publish) | `prefix` `default="ABC"`, `"e.g. 'noise', 'spk', 'gen'"` | prefix-lift (partly mitigated — desc says "operator should set this", but e.g. values still liftable) |
| `publish.py:317` | `PublishSequence` — **MUTATION** | `source_sequence_name` `"e.g. 'test long'"` | sequence-name-lift |
| `publish.py:320` | `PublishSequence` — **MUTATION** | `published_sequence_name` `"e.g. 'test long_published'"` | sequence-name-lift |
| `timeline.py:1094` | `flame_inspect_sequence_versions` (**READ**) | docstring `sequence_name="30sec_21"` ×2 | **defect #3 value source (cross-tool bleed)** |

### MEDIUM — constrained-vocab / structural examples; lift → valid-vocab-but-maybe-wrong

| Site | Field | Note |
|---|---|---|
| `timeline.py` RenameInput | `role_overrides` `{'0': 'graded', '2': 'raw'}` | concrete index→role dict, literally pluggable |
| `reconform.py:72` | `role` `"e.g. 'graded', 'raw'"` | role is a real constrained vocab |
| `publish.py:51` | role auto-detect `footage/graded → 'graded'` | fallback path; lower |
| `batch.py:996/1030` | concrete `/PROJEKTS/…` paths | path-lift risk |
| `batch.py:674/795`, `utility.py:264` | `'Comp'` / `'PIZ'` / `'Undo','Redo'` | command/format vocab |

### LOW — read tools / format-illustrative (lift unlikely or harmless)

`project.py:279` + `timeline.py:1503` reel `'Sequences'` (read enumerate) · `batch.py:955` range pattern
`[001001-001100]` (format) · `timeline.py:922/973/989/994` timecode/colorspace format examples.

---

## Fix-shape implications (for Phase 4 — NOT prescribed here)

The fix differs by sub-class — do not flatten:

- **Value examples** (`'noise'`, `'30sec_21'`, `'test long'`, paths): the dangerous class. Options — strip
  the literal; replace with a non-pluggable placeholder that reads as "fill from intent, do not copy"; or
  move the example out of the salient opener position (`[[feedback-rhetorical-position-as-architectural-control-surface]]`).
- **Vocab examples** (roles `graded`/`raw`, node types): KEEP — these are a real constrained vocabulary the
  model *should* know. The fix is to mark them as an enum/vocabulary, not an example to copy. Stripping
  these would lose grounding.
- **Read-tool docstring examples** (the `30sec_21` bleed): in scope — the compiler sees read + mutation
  tools together. Don't scope the strip to mutation tools.

**Scope note:** this inventory is the bridge tool surface as of `5f2b2a6`. The C2 rename executor inherits
`RenameInput`'s `prefix` example via the discover delegate, so fixing `timeline.py:243` covers the executor
path too (no separate executor-side example to strip).

---

## Feeds

- Phase 2 taxonomy: the **grounding/example-salience** cell + its interaction with the contextual /
  extraction cells (fill-of-last-resort).
- Phase 4 quality: the "strip liftable value examples" slice — now scoped as a 3-site prefix class + the
  sequence-name sites + the cross-tool read-docstring bleed, value-vs-vocab distinction preserved.
