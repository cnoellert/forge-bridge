# Flame Python API — Field Notes

Documented from live exploration of Flame 2026.2.1 via the HTTP bridge.

---

## Object Hierarchy

```
flame.projects.current_project          → PyProject
  .current_workspace                    → PyWorkspace
    .desktop                            → PyDesktop
      .reel_groups[]                    → PyReelGroup
        .reels[]                        → PyReel
          .sequences[]                  → PySequence
          .clips[]                      → PyClip
    .libraries[]                        → PyLibrary
```

### Traversing to segments

```python
desktop   = flame.projects.current_project.current_workspace.desktop
seq_reel  = next(r for rg in desktop.reel_groups
                   for r in rg.reels if r.name == 'Sequences')

for seq in seq_reel.sequences:
    for version in seq.versions:           # typically 1 version
        for track in version.tracks:       # multiple tracks (L01, L02...)
            for seg in track.segments:
                print(seg.name)            # e.g. "data_080_graded_L01"
```

### Key finding: no segment UIDs

`seg.uid` returns `None` in Flame 2026. Segment **name** is the stable key
for change detection. Names follow the FORGE convention `<shot>_<role>` e.g.
`data_080_graded_L01`.

---

## PySequence attributes

Notable attributes on a sequence:
`versions`, `groups`, `markers`, `frame_rate`, `start_frame`, `duration`,
`bit_depth`, `width`, `height`, `ratio`, `has_deliverables`, `creation_date`

Access tracks via `seq.versions[0].tracks`, not `seq.tracks` directly
(returns None).

---

## PySegment attributes

`name`, `type`, `start_frame`, `duration`, `tape_name`, `shot_name`,
`record_in`, `record_out`, `source_in`, `source_out`, `frame_rate`,
`version_uid`, `version_uids`, `effects`, `parent`

No `uid` in Flame 2026.

---

## PyReel attributes

`name`, `sequences`, `clips`, `attributes`, `parent`

Note: iterating `desktop.reel_groups[0].reels` with `[:3]` only returns
first 3 — always iterate the full list. A typical project has:
`Reel 1`, `Reel 2`, `Reel 3`, `Reel 4`, `Sequences`

---

## Python Hook Callbacks (Flame 2026)

Flame scans hook files for functions with these exact names.
**There is no `segment_created` callback** — timeline edits do not fire
Python hooks. The available hooks are:

### hook.py (generic)
- `app_initialized(project_name)` — fires on Flame startup
- `appStarted(info)` — fires at splash screen
- `userChanged(info)` — fires when user switches
- `renderEnded(moduleName, sequenceName, elapsedTimeInSeconds)`
- `playbackEnded(sequenceName, fps, debugInfo)`
- `getCustomUIActions()` → contextual menu items
- `getMainMenuCustomUIActions()` → main menu items
- `customUIAction(info, userData)` — menu item selected
- `timelineDefaultShotName(project)` → string
- `timelineDefaultMarkerName(project)` → string
- `timelineDefaultMarkerComment(project)` → string
- `project_changed_dict(info)` — fires on project open/switch

### Other hook files
- `archiveHook.py`: `archiveRestored`, `archiveComplete`, etc.
- `batchHook.py`: `batchSetupLoaded`, `batchSetupSaved`, `batchExportBegin`,
  `batchExportEnd`, `batchDefaultIterationName`, `batchDefaultRenderNodeName`

### Critical conflict rule
All hook files are loaded into the **same Python namespace**. If two files
define the same function name, the last one wins. Our two hooks:
- `forge_bridge.py` owns `app_initialized` (starts HTTP server)
- `forge_bridge_pipeline.py` uses `project_changed_dict` (launches sidecar)

---

## Timeline Snapshot Query

This is the canonical query to get all segments from a project's sequences:

```python
def get_timeline_snapshot():
    """Return {seq_name: {track_name: [seg_name, ...]}} for all sequences."""
    desktop = flame.projects.current_project.current_workspace.desktop
    snapshot = {}
    for rg in desktop.reel_groups:
        for reel in rg.reels:
            for seq in reel.sequences:
                tracks = {}
                try:
                    for version in seq.versions:
                        for track in version.tracks:
                            segs = [s.name for s in track.segments if s.name]
                            if segs:
                                tracks[track.name] = segs
                except Exception:
                    pass
                if tracks:
                    snapshot[seq.name] = tracks
    return snapshot
```

---

## Notes

- `flame` is a C extension (`flame.__file__` raises AttributeError)
- `flame.schedule_idle_event` is the only event-related API exposed
- Main-thread operations require `main_thread: true` in bridge `/exec`
- Port 9999 = HTTP bridge, Port 9997 = sidecar event listener, Port 9998 = forge-bridge server

---

## Publish Workflow — FORGE Shot Registration

### When does a shot exist in forge-bridge?

A shot is registered **at publish time**, not when it appears in the timeline.
The artist publishes using a Flame XML export template with tokens that resolve
shot names, roles, and plate types. forge-bridge is the system of record for
what has been published.

### Publish flow

```
Timeline (segments with L01/L02/L03 layers)
    ↓  artist triggers export using XML template
Pre-publish hook
    → check: does this shot already exist in forge-bridge?
    → check: do the shot names conform to naming conventions?
    → check: are versions being overwritten?
    → warn / block / proceed
        ↓  Flame renders each segment to disk
Per-segment publish hook  (fires for each component)
    → register Shot in forge-bridge (if new)
    → register Version with path, frame_range, role
    → register Media (file path, format, colorspace)
    → link: Version → Shot → Sequence → Project
```

### Relevant Flame hooks for publish

From `batchHook.py`:
- `batchExportBegin(info)` — fires before export starts (pre-publish check)
- `batchExportEnd(info)` — fires after export completes

From `mediaExportHook.py` (if it exists):
- Export hooks fire per-clip/per-segment

The XML template tokens resolve at export time, giving us the final
shot name, role, frame range, and output path for each published component.

### MCP tools needed

| Tool | Purpose |
|------|---------|
| `flame_check_shot(name)` | Does this shot exist? What versions? |
| `flame_check_shots(names[])` | Batch pre-publish check |
| `flame_register_publish(...)` | Register a published component |
| `flame_list_published(shot_name)` | What has been published for a shot? |
| `flame_list_sequences()` | All sequences and segment names |
| `flame_get_segment(name)` | Find a segment across all sequences |

---

## forge-bridge Integration Points

### Where forge-bridge hooks into the publish chain

The existing `forge_publish.py` hook chain in projekt-forge already fires
at exactly the right moments. forge-bridge registers into two of them:

#### `pre_custom_export` — Pre-publish check
Fires before the export starts. forge-bridge checks:
- Do any of the shot names already exist in the registry?
- If yes: what is the last published version number?
- Are any shot names malformed or missing?
- Report back warnings/blocks before anything is written to disk

The sidecar receives a `publish.preflight` event with all shot names,
queries forge-bridge, and returns a summary to display in the Flame dialog.

#### `post_export_asset` — Per-component registration
Fires once per exported component (one call per segment/layer).
`info` contains:
- `assetName` — segment name e.g. `tst_010_graded_L01`  
- `resolvedPath` — full output path on disk
- `startFrame` / `endFrame` — frame range
- `colourSpace` — colour space name
- `type` — media type

The sidecar receives a `publish.asset` event and registers:
- Shot (create if new, look up if existing)
- Version (increment from last)
- Media (path, frame range, colorspace, role derived from layer suffix)
- Links: Media → Version → Shot → Sequence → Project

#### `post_custom_export` — Batch completion
Fires after all assets in an export are done. forge-bridge finalises
the batch, marks all versions as `complete`, fires downstream events.

---

### Shot name → forge-bridge vocabulary

| Flame segment name | forge-bridge entities created |
|---|---|
| `tst_010_graded_L01` | Shot `tst_010`, Version v001, Media (role=`primary`) |
| `tst_010_graded_L02` | Shot `tst_010` (existing), Version v001, Media (role=`reference`) |
| `tst_010_graded_L03` | Shot `tst_010` (existing), Version v001, Media (role=`matte`) |

Layer suffix → role mapping: `L01=primary`, `L02=reference`, `L03=matte`
(configurable via registry roles)

---

### MCP tools for publish workflow

| Tool | Purpose |
|---|---|
| `forge_check_shots(names[])` | Pre-publish: do these shots exist? Last version? |
| `forge_register_publish(asset_info)` | Register one published component |
| `forge_list_published(shot_name)` | What has been published for this shot? |
| `forge_list_sequences()` | All sequences and segment names in current project |
| `forge_snapshot_timeline()` | Full timeline state: reel_groups→reels→seqs→segments |

---

## Start Frame Workflow — Key API

```
seg.head                    → int, head handle frames before cut point
seg.change_start_frame(n)   → sets clip start frame (call with n = target - head)
seg.start_frame             → current start frame (read-only inspection)
seg.source_name             → non-empty = real segment; empty = gap/filler
seg.file_path               → source media path (for role detection)
seg.record_in / record_out  → edit timecodes as strings (for shot propagation)
seg.shot_name               → PyAttribute with .get_value() / .set_value()
seg.name                    → PyAttribute with .get_value() / .set_value()
```

### Start frame math

```
target_frame = 1001          # desired first visible frame — pass this directly
head         = int(seg.head) # handle frames before cut — for validation only
clip_start   = target - head # must be >= 0 or Flame rejects it

seg.change_start_frame(target_frame)   # Flame handles head offset internally

# Validation only — block the operation if clip_start < 0
```

### Role detection from source path

```python
import re
m = re.search(r'footage/([^/]+)/', str(seg.file_path))
role = m.group(1) if m and m.group(1) in KNOWN_ROLES else 'source'
# KNOWN_ROLES = ['graded', 'raw', 'denoised', 'flat', 'external', 'scans', 'stock', 'source']
```

### All set operations require main thread

```python
# Must use main_thread=True or schedule_idle_event():
seg.name.set_value(new_name)
seg.shot_name.set_value(shot_name)
seg.change_start_frame(n)
```
