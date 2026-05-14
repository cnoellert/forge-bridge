---
name: forge-align-color-setup
description: Diagnose forge-align colour management — verify that the active Flame project's OCIO config is reachable, that forge-io's source colorspace names are resolvable in it, and that the CV Align hook's subprocess env injection is wired up. Use when CV Align reports OCIOConfigError, when a plate decodes but feature matching gives nonsense, or when the user wants confirmation that align is using the right OCIO before running a job.
---

# forge-align colour management — diagnosis

The forge-align CV Align hook **auto-resolves OCIO at run time** by reading
the active Flame project's `colour_mgmt/config.ocio` symlink and exporting
it as `OCIO=` into the cli_solve subprocess. There is no install-time
config sync to perform. This skill is for **verifying** that the auto-
resolution is producing the right config and that the project's OCIO
namespace can resolve forge-io's reader-emitted source colorspace strings.

## When to invoke

- `/tmp/forge_cv_align.log` contains `OCIOConfigError: No OCIO config`
- Plate decodes correctly but match confidence is low / nonsense — possibly an
  OCIO transform that's wrong because the source CS name isn't recognized
- User asks "what OCIO config is align using right now?"
- User just switched Flame projects and wants confirmation align picked it up
- Suspect mismatch between forge-io's emitted CS name (`ACES2065-1` for ARRI,
  `Linear REDWideGamutRGB` for RED) and the names the project's OCIO config knows

## Workflow

### 1. Snapshot what Flame currently has

Call `mcp__projekt-forge__flame_get_project`. Relevant fields:

| Field | Meaning |
|---|---|
| `setups_folder` | Where `colour_mgmt/config.ocio` lives on disk |
| `ocio_config` | Absolute path of the resolved config (symlinks dereferenced) |
| `ocio_config_symlink` | The bundled-preset target if it's a symlink (e.g. `.../aces2.0_config/config.ocio`) — tells you which preset is active |
| `ocio_custom_overlay` | Path to `project_custom_config.ocio` if facility overrides are in play |

If `ocio_config` is null, the project has no colour management config selected
in Flame. Fix in Flame: Project Settings → Colour Management → pick one. The
auto-resolver in the hook only finds what Flame writes.

### 2. Confirm forge-io's CS names exist in that config

forge-io v0.3.2+ emits OCIO-canonical names:

- ARRI (`.ari`, `.arx`) → `source_colorspace = "ACES2065-1"`
- RED (`.r3d`) → `source_colorspace = "Linear REDWideGamutRGB"`

Grep the chosen config for these:

```bash
grep -E "name: (ACES2065-1|Linear REDWideGamutRGB)" /path/to/config.ocio
```

Flame's `aces2.0_config` (and `flame_core_config`) **have ACES2065-1** but
**not Linear REDWideGamutRGB** as of 2026.0. For RED workflows the facility
needs to either:
- Add `Linear REDWideGamutRGB` as a real colorspace in `project_custom_config.ocio`, or
- Alias it to `ACEScg` in the overlay for a CV-acceptable approximation
  (small gamut shift, transfer is correct — SIFT doesn't care).

### 3. Confirm the hook will inject OCIO into cli_solve

Verify the deployed hook has the env injection:

```bash
grep -n "_resolve_flame_ocio_config\|OCIO resolved from Flame" /opt/Autodesk/shared/python/forge_cv_align/forge_cv_align.py
```

If those strings aren't present, the hook deployment is older than the
forge-align v0.3.2 integration. Rerun `bash install.sh --deploy-only` from
`forge-align/`, then evict the Flame cached module:

```python
import sys; [sys.modules.pop(k) for k in list(sys.modules) if 'forge_cv_align' in k]
```

(or just restart Flame).

### 4. Check the log after a small test run

Have the user CV-Align a small selection. `/tmp/forge_cv_align.log` should
show one of:

- `OCIO resolved from Flame project: /…/config.ocio` — auto-resolution worked
- `OCIO unresolved …` — Flame project has no colour_mgmt/config.ocio, go to step 1

If `OCIO resolved …` shows but cli_solve still errors with
`OCIOTransformError` or `UnknownColorspaceTransformError`, the config is
reachable but doesn't know how to transform forge-io's emitted source CS
to the requested working space — go to step 2.

## Things this skill does NOT do

- Does not modify Flame's colour management settings — Flame is source of truth.
- Does not write to `~/.forge/config.yaml` for OCIO. The hook auto-discovers;
  storing the path there would just be a stale snapshot.
- Does not edit the project's OCIO config. RED-coverage gaps need the facility's
  colour department to address in `project_custom_config.ocio`.

## Related

- `mcp__projekt-forge__flame_get_project` — surfaces the OCIO fields this skill consumes
- `forge-align/scripts/forge_cv_align.py` — `_resolve_flame_ocio_config()` and `_subprocess_env()` do the auto-resolution
- forge-io v0.3.2 — the release that aligned reader-emitted CS names with OCIO-canonical strings
