# TF.3a — Salience Surface (re-derived) — the example-fill detector's value-set

**This is TF.3a Step 0 (the gating precondition, DONE).** It **supersedes `D3-EXAMPLE-SALIENCE-INVENTORY.md`
as the detector's input**; D3 stays as archaeology. **Method-undercount correction, NOT drift** — `git log
5f2b2a6..HEAD` is empty for all six tool files; `grep -c 30sec_21 timeline.py` = 12 at pin == 12 at HEAD. D3's
sweep enumerated `Field(description=…)` + `e.g.`/`Example call:` but **missed the `Operator query:` / `Tool
call:` / `Response shape:` few-shot blocks from day one.** This re-derive adds them.
**Swept (live HEAD `61090c4`):** all five NL→tool demonstration kinds across `tools/{timeline,publish,reconform,
batch,utility,project}.py`.

---

## A. The newly-enumerated surface (few-shot blocks D3 missed) — HIGHEST lift risk

A worked `Operator query: → Tool call:` block is **directly pluggable** (it shows the exact param fill), so it
is *higher* risk than a `Field` example. **All in `timeline.py`:**

| Site | Block | Lifted value(s) | Notes |
|---|---|---|---|
| `:146-148` | show segments on `30sec_21` | `sequence_name="30sec_21"` (+ Response `"sequence":"30sec_21","count":30`) | read tool |
| **`:286-288`** | **rename shots on `30sec_21` with prefix `'noise'`** | **`sequence_name="30sec_21"` + `prefix="noise"`** | **COMPOUND — defect #1 (prefix→noise) AND defect #3 (seq→30sec_21) in ONE block. The strongest single lift-source for E2E-01's compound failure.** Response adds `renamed:30`. |
| `:687-689` | set start frames on `30sec_21` to `1001` | `sequence_name="30sec_21"` + `default_frame=1001` | **second compound** (seq + frame); ties the `1001` frame-value (`:697 "e.g. 1001"`) to a worked fill |
| `:1096` | Example call | `sequence_name="30sec_21"` | inspect-versions (read) |
| `:1100-1102` | inspect versions on `30sec_21` | `sequence_name="30sec_21"` (+ Response `"sequence":"30sec_21"`) | read tool |

**Consequence the room flagged:** operationalizing D3-as-written would make the detector blind to these →
**false negatives**, and the FP rate would be measured against an incomplete universe. They are now in-scope.

## B. The D3-confirmed surface (re-verified present at HEAD) — HIGH lift risk

| Site | Tool | Value | Class |
|---|---|---|---|
| `timeline:215` | `flame_preview_rename` (dry-run mutation) | `prefix "e.g. 'noise', 'tst'"` | prefix-lift |
| `timeline:243` | `flame_rename_shots` (MUTATION; C2 executor delegate) | `prefix "e.g. 'noise', 'tst'"` | **defect #1 confirmed source** |
| `timeline:1094` | `flame_inspect_sequence_versions` (READ) | `sequence_name="30sec_21"` | **defect #3 value source (cross-tool bleed)** |
| `publish:27` | `RenameShots` (stage/publish) | `prefix default="ABC", "e.g. 'noise','spk','gen'"` | prefix-lift (partly mitigated) |
| `publish:317` | `PublishSequence` (MUTATION) | `source_sequence_name "e.g. 'test long'"` | sequence-name-lift |
| `publish:320` | `PublishSequence` (MUTATION) | `published_sequence_name "e.g. 'test long_published'"` | sequence-name-lift |

## C. MEDIUM / LOW (vocab + format + path — re-confirmed) — KEEP, mark as vocab not example

Constrained-vocab examples the model *should* know (TF.1 / D3 ruling: mark as enum, do not strip):
`reconform:72` role `'graded','raw'` · `publish:51` footage→role · `batch:674` node types `'Comp','Write
File','Action'` · `batch:795` formats `'PIZ','OpenEXR','16-bit fp'` · `utility:264` `'Undo','Redo','Select
All'` · `project:279`/`timeline:1503` reel `'Sequences'`. **Path-lift (HIGH-ish, watch):** `batch:996/1030`
`/PROJEKTS/…` concrete paths. **Format-illustrative (LOW):** `batch:955` `[001001-001100]` · `timeline:922/973/
989/994` timecode/colorspace.

---

## D. The detector value-set (what the example-fill detector flags as "matches a known example")

The **liftable VALUE literals** (sections A + B + path-lift), as the machine-consumable set the detector reads:

```
30sec_21            # the dominant literal — A (×many) + B(timeline:1094)
noise, tst          # prefix examples — A(:287) + B(timeline:215/243)
noise, spk, gen     # prefix examples — B(publish:27)
ABC                 # prefix default — B(publish:27)
test long           # sequence name — B(publish:317)
test long_published # sequence name — B(publish:320)
1001                # default_frame — A(:688) + timeline:697
/PROJEKTS/012_12_12/_04_shots/ABC_010[...]   # path — C(batch:996/1030)
```

**Compound patterns** (a single block teaching a multi-param fill — the detector should be able to attribute a
lift to a *block*, not just a literal): `{30sec_21, noise}` (`:287`), `{30sec_21, 1001}` (`:688`).

**Vocab values are NOT in the detector set** (`graded/raw/Comp/PIZ/Sequences/Undo…`) — they are legitimate
constrained vocabulary; flagging them would be a definitional false positive.

## E. FP-surface note (feeds the Q4 FP study)

The detector's false positive = a value that matches the set above but was **genuinely grounded**. The literals
most prone to legitimate equality: **`30sec_21`** (a real sequence could be named this), **`noise`/`tst`** (a
real prefix could be these — they're plausible shot prefixes), **`ABC`** (a real prefix). Least prone:
`test long_published`, the concrete `/PROJEKTS/…` path (a real path equal to the example is near-impossible).
The FP study (TF.3a Step 5) hand-labels corpus values matching this set as `lifted` vs `legitimately-equal` and
reports the rate — and it now measures against the **complete** surface, not D3's partial one.
