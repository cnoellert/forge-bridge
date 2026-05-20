"""Project, workspace, and media library tools."""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_bridge import bridge


# ── Tool: flame_get_project ─────────────────────────────────────────────


async def get_project() -> str:
    """Flame: get the currently-open Flame project (name, paths, OCIO, version).

    Reads from the running Autodesk Flame session via its Python API.
    Returns workspace name, library count, media storage paths, Flame
    version, and the active OCIO config. Always safe to call (read-only).

    OCIO fields:
      ocio_config            — resolved absolute path of the active config
                                (symlinks dereferenced), or null if none
      ocio_config_symlink    — symlink target if config.ocio is a symlink
                                to one of Flame's bundled presets (lets
                                you identify which preset is active)
      ocio_custom_overlay    — path to project_custom_config.ocio if
                                present (per-project colorspace overrides
                                that merge over the base config)

    Use this tool ONLY when:
    - the user asks about the *currently-open Flame project* on the host
    - the user wants Flame-side metadata (paths, OCIO, version)

    Do NOT use this tool for:
    - listing forge-bridge pipeline projects (use forge_list_projects)
    - getting forge-bridge pipeline project details by ID (use forge_get_project)
    - shots, versions, media, libraries, or anything not at the Flame
      project level

    This tool is specific to the live Flame application — it requires
    a running Flame session on the host.
    """
    data = await bridge.execute_json("""
        import flame, json, os
        proj = flame.project.current_project
        ws = proj.current_workspace
        user = flame.users.current_user

        # OCIO config lives at {setups}/colour_mgmt/config.ocio. Flame writes
        # it as a symlink to a bundled preset or as a real file for a custom
        # config. project_custom_config.ocio (if present) holds per-project
        # colorspace overrides that merge over the base config.
        cm_dir = os.path.join(proj.setups_folder, 'colour_mgmt')
        cfg_path = os.path.join(cm_dir, 'config.ocio')
        custom_path = os.path.join(cm_dir, 'project_custom_config.ocio')

        ocio_config = os.path.realpath(cfg_path) if os.path.exists(cfg_path) else None
        ocio_symlink = os.readlink(cfg_path) if os.path.islink(cfg_path) else None
        ocio_custom = custom_path if os.path.exists(custom_path) else None

        info = {
            'project_name': proj.project_name,
            'nickname': str(proj.nickname.get_value()) if hasattr(proj.nickname, 'get_value') else str(proj.nickname),
            'description': str(proj.description.get_value()) if hasattr(proj.description, 'get_value') else '',
            'project_folder': proj.project_folder,
            'setups_folder': proj.setups_folder,
            'media_folder': proj.media_folder,
            'workspace': str(ws.name.get_value()) if hasattr(ws.name, 'get_value') else str(ws.name),
            'workspaces_count': proj.workspaces_count,
            'library_count': len(ws.libraries),
            'flame_version': flame.get_version(),
            'flame_home': flame.get_home_directory(),
            'current_tab': flame.get_current_tab(),
            'user': str(user.name),
            'user_nickname': str(user.nickname),
            'context_variables': proj.get_context_variables(),
            'ocio_config': ocio_config,
            'ocio_config_symlink': ocio_symlink,
            'ocio_custom_overlay': ocio_custom,
        }
        print(json.dumps(info))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_list_libraries ──────────────────────────────────────────


class ListLibrariesInput(BaseModel):
    """Input for listing libraries."""

    include_contents: bool = Field(
        default=False,
        description="If True, include folder/reel/clip counts for each library. "
        "Set False for a quick overview.",
    )


async def list_libraries(params: Optional[ListLibrariesInput] = None) -> str:
    """Flame: list libraries in the current Flame workspace.

    A "library" here is an Autodesk Flame *workspace library* — the
    top-level container shown in Flame's MediaHub. Returns each library's
    name and open/closed state, with optional folder/reel/clip counts.

    Use this tool ONLY when:
    - the user asks about *Flame libraries* (a Flame-specific concept)
    - the user wants the contents of the live Flame workspace

    Do NOT use this tool for:
    - listing forge-bridge pipeline projects → use forge_list_projects
    - listing pipeline shots → use forge_list_shots
    - listing pipeline versions → use forge_list_versions
    - listing media on disk → use forge_list_media or flame_find_media
    - role registry → use forge_list_roles
    - the Flame Desktop (a different container) → use flame_list_desktop

    This tool is specific to Flame workspace libraries only. If the user
    asks about "projects" or anything other than libraries, this tool is
    the WRONG choice.
    """
    # Pydantic v2 treats fields as required without a default. The CLI
    # `fbridge run flame_list_libraries` and the LLM tool-call path both
    # call this with no args — give ``params`` a default so the schema
    # doesn't reject the empty-arg call. ListLibrariesInput's own fields
    # already default; the missing piece was the parameter itself.
    if params is None:
        params = ListLibrariesInput()
    code = """
        import flame, json
        ws = flame.projects.current_project.current_workspace
        libs = []
        for lib in ws.libraries:
            name = lib.name.get_value() if hasattr(lib.name, 'get_value') else str(lib.name)
            entry = {'name': name, 'opened': lib.opened}
    """
    if params.include_contents:
        code += """
            entry['folders'] = len(lib.folders)
            entry['reels'] = len(lib.reels)
            entry['reel_groups'] = len(lib.reel_groups)
            entry['clips'] = len(lib.clips)
            entry['sequences'] = len(lib.sequences)
            # Recurse one level into folders
            folder_list = []
            for f in lib.folders:
                fname = f.name.get_value() if hasattr(f.name, 'get_value') else str(f.name)
                folder_list.append({
                    'name': fname,
                    'clips': len(f.clips),
                    'sequences': len(f.sequences),
                    'reels': len(f.reels),
                    'folders': len(f.folders),
                })
            entry['folder_details'] = folder_list
        """
    code += """
            libs.append(entry)
        print(json.dumps(libs))
    """
    data = await bridge.execute_json(code)
    return json.dumps(data, indent=2)


# ── Tool: flame_list_desktop ────────────────────────────────────────────


async def list_desktop() -> str:
    """Flame: list the current Flame Desktop's reel groups, reels, and batch groups.

    The "Desktop" is Flame's working surface — distinct from a library.
    Returns reel groups with nested reels and clip/sequence counts, plus
    batch group names.

    Use this tool ONLY when:
    - the user asks about the *Flame Desktop* specifically
    - the user wants what is currently on the artist's working surface

    Do NOT use this tool for:
    - Flame libraries (use flame_list_libraries — different container)
    - pipeline shots → use forge_list_shots
    - pipeline media → use forge_list_media

    This tool is specific to Flame's Desktop view; it does not see
    library, project, or pipeline-registry content.
    """
    data = await bridge.execute_json("""
        import flame, json
        ws = flame.project.current_project.current_workspace
        desk = ws.desktop
        reel_groups = []
        for rg in desk.reel_groups:
            rg_name = rg.name.get_value() if hasattr(rg.name, 'get_value') else str(rg.name)
            reels = []
            for r in rg.reels:
                r_name = r.name.get_value() if hasattr(r.name, 'get_value') else str(r.name)
                reels.append({
                    'name': r_name,
                    'clips': len(r.clips),
                    'sequences': len(r.sequences),
                })
            reel_groups.append({'name': rg_name, 'reels': reels})

        batch_groups = []
        for bg in desk.batch_groups:
            bg_name = bg.name.get_value() if hasattr(bg.name, 'get_value') else str(bg.name)
            batch_groups.append({'name': bg_name})

        result = {
            'reel_groups': reel_groups,
            'batch_groups': batch_groups,
        }
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_list_reel_groups ────────────────────────────────────────


async def list_reel_groups() -> str:
    """Flame: list all reel groups on the current desktop with their reels.

    Returns the top-level reel group structure of the Flame Desktop:
    each reel group name and its reels with clip/sequence counts.

    Use this tool ONLY when:
    - the user wants to know what reel groups exist on the desktop
    - the user needs reel names to pass to flame_list_reel_contents

    Do NOT use this tool for:
    - item names inside a reel → use flame_list_reel_contents
    - full desktop snapshot → use flame_context
    - libraries → use flame_list_libraries

    Note: output shape includes reels one level deep, consistent with
    flame_list_desktop. This is a conscious asymmetry with
    flame_list_libraries (names-only default) — reel groups are
    inherently shallow and the reel list is the primary operator-useful
    payload.
    """
    data = await bridge.execute_json("""
        import flame, json

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        ws = flame.project.current_project.current_workspace
        desk = ws.desktop
        reel_groups = []
        for rg in desk.reel_groups:
            reels = []
            for reel in rg.reels:
                reels.append({
                    'name': _name(reel),
                    'clips': len(reel.clips),
                    'sequences': len(reel.sequences),
                })
            reel_groups.append({'name': _name(rg), 'reels': reels})

        print(json.dumps(reel_groups))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_list_reel_contents ──────────────────────────────────────


class ListReelContentsInput(BaseModel):
    """Input for listing a reel's immediate contents."""

    reel_name: str = Field(
        ...,
        description='Name of the reel to enumerate, e.g. "Sequences" or "Reel 1 Footage graded".',
        min_length=1,
    )
    reel_group: str = Field(
        default="",
        description="Optional reel group name to narrow search; empty string searches all reel groups.",
    )


async def list_reel_contents(params: ListReelContentsInput) -> str:
    """Flame: list the flat top-level contents of a reel by name.

    Use this tool to enumerate what's in a reel by name.
    For full clip metadata use flame_get_clip.
    For sequence structure use flame_inspect_sequence_versions.

    Returns a flat list of clip/sequence names with type, duration, and
    sequence track count. This is deliberately shallow: no nested segment
    structures, embedded metadata objects, or recursive track trees.
    """
    data = await bridge.execute_json(f"""
        import flame, json

        target_reel = {params.reel_name!r}
        target_group = {params.reel_group!r}

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _duration_frames(obj):
            try:
                return int(obj.duration)
            except Exception:
                try:
                    return int(obj.duration.frame)
                except Exception:
                    try:
                        return int(float(str(obj.duration)))
                    except Exception:
                        return 0

        def _track_count(obj):
            try:
                if hasattr(obj, 'versions') and len(obj.versions) > 0:
                    return len(obj.versions[0].tracks)
            except Exception:
                pass
            return 0

        def _entry(item):
            return {{
                'name': _name(item),
                'type': type(item).__name__,
                'duration': _duration_frames(item),
                'track_count': _track_count(item),
            }}

        def _contents(reel):
            return [_entry(item) for item in list(reel.clips) + list(reel.sequences)]

        def _matches(value, target):
            return _name(value).casefold() == str(target).strip("'").casefold()

        ws = flame.project.current_project.current_workspace
        matches = []

        desk = ws.desktop
        for rg in desk.reel_groups:
            if target_group and not _matches(rg, target_group):
                continue
            for reel in rg.reels:
                if _matches(reel, target_reel):
                    matches.append(_contents(reel))

        for lib in ws.libraries:
            for rg in getattr(lib, 'reel_groups', []):
                if target_group and not _matches(rg, target_group):
                    continue
                for reel in rg.reels:
                    if _matches(reel, target_reel):
                        matches.append(_contents(reel))
            for reel in getattr(lib, 'reels', []):
                if target_group:
                    continue
                if _matches(reel, target_reel):
                    matches.append(_contents(reel))
            for folder in getattr(lib, 'folders', []):
                for reel in getattr(folder, 'reels', []):
                    if target_group:
                        continue
                    if _matches(reel, target_reel):
                        matches.append(_contents(reel))

        if matches:
            print(json.dumps(matches[0]))
        else:
            print(json.dumps({{'error': 'Reel not found', 'reel_name': target_reel,
                               'reel_group': target_group}}))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_clip ────────────────────────────────────────────────


class GetClipInput(BaseModel):
    """Input for retrieving Tier 1 clip metadata."""

    clip_name: str = Field(
        ...,
        description="Exact clip name, normalized against Flame's displayed clip names.",
        min_length=1,
    )
    reel_name: str = Field(
        default="",
        description="Optional reel name to narrow search.",
    )


async def get_clip(params: GetClipInput) -> str:
    """Flame: get Tier 1 operator-decision metadata for a named clip.

    Tier 1 clip metadata is operator-decision metadata,
    not archival provenance metadata. For deeper metadata
    use flame_execute_python.

    Returns immediate decision fields such as duration, dimensions, frame
    rate, colour space, bit depth, track count, and resolved media path when
    Flame exposes one. It intentionally excludes tape name, source timecode,
    creation dates, reel IDs, scanner metadata, and camera payloads.
    """
    data = await bridge.execute_json(f"""
        import flame, json

        target_clip = {params.clip_name!r}
        target_reel = {params.reel_name!r}

        def _value(value, default=''):
            try:
                if hasattr(value, 'get_value'):
                    value = value.get_value()
            except Exception:
                return default
            if value is None:
                return default
            return value

        def _name(obj):
            try:
                return str(_value(obj.name)).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _matches(obj, target):
            return _name(obj).casefold() == str(target).strip("'").casefold()

        def _duration_frames(obj):
            try:
                return int(obj.duration)
            except Exception:
                try:
                    return int(obj.duration.frame)
                except Exception:
                    try:
                        return int(float(str(obj.duration)))
                    except Exception:
                        return 0

        def _int_attr(obj, names):
            for attr in names:
                try:
                    value = _value(getattr(obj, attr))
                    if value not in ('', None):
                        return int(value)
                except Exception:
                    pass
            return 0

        def _str_attr(obj, names):
            for attr in names:
                try:
                    value = _value(getattr(obj, attr))
                    if value not in ('', None):
                        return str(value)
                except Exception:
                    pass
            return ''

        def _file_path(obj):
            for attr in ('file_path', 'path', 'media_path'):
                try:
                    value = _value(getattr(obj, attr))
                    if value:
                        return str(value)
                except Exception:
                    pass
            try:
                return str(obj.get_media_path())
            except Exception:
                return ''

        def _track_count(obj):
            for attr in ('tracks', 'versions'):
                try:
                    value = getattr(obj, attr)
                    if attr == 'versions' and len(value) > 0:
                        return len(value[0].tracks)
                    return len(value)
                except Exception:
                    pass
            return 0

        def _clip_entry(clip):
            frame_rate = _str_attr(clip, ('frame_rate', 'rate', 'fps'))
            if frame_rate and 'fps' not in frame_rate.lower():
                frame_rate = frame_rate + ' fps'
            return {{
                'name': _name(clip),
                'type': type(clip).__name__,
                'duration': _duration_frames(clip),
                'duration_tc': str(getattr(clip, 'duration', '')),
                'width': _int_attr(clip, ('width',)),
                'height': _int_attr(clip, ('height',)),
                'frame_rate': frame_rate,
                'colour_space': _str_attr(clip, ('colour_space', 'colorspace', 'colourspace')),
                'bit_depth': _str_attr(clip, ('bit_depth', 'bitdepth')),
                'track_count': _track_count(clip),
                'file_path': _file_path(clip),
            }}

        def _search_container(container):
            if target_reel and hasattr(container, 'name') and not _matches(container, target_reel):
                return None
            for clip in getattr(container, 'clips', []):
                if _matches(clip, target_clip):
                    return _clip_entry(clip)
            return None

        ws = flame.project.current_project.current_workspace

        result = None
        for rg in ws.desktop.reel_groups:
            for reel in rg.reels:
                if result:
                    break
                result = _search_container(reel)
            if result:
                break

        if not result:
            for lib in ws.libraries:
                if not target_reel:
                    result = _search_container(lib)
                    if result:
                        break
                for reel in getattr(lib, 'reels', []):
                    if result:
                        break
                    result = _search_container(reel)
                if result:
                    break
                for folder in getattr(lib, 'folders', []):
                    if result:
                        break
                    if not target_reel:
                        result = _search_container(folder)
                        if result:
                            break
                    for reel in getattr(folder, 'reels', []):
                        if result:
                            break
                        result = _search_container(reel)

        if result:
            print(json.dumps(result))
        else:
            print(json.dumps({{'error': 'Clip not found', 'clip_name': target_clip,
                               'reel_name': target_reel}}))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_list_library_contents ───────────────────────────────────


class ListLibraryContentsInput(BaseModel):
    """Input for listing a library's top-level contents."""

    library_name: str = Field(
        ...,
        description="Exact Flame workspace library name.",
        min_length=1,
    )


async def list_library_contents(params: ListLibraryContentsInput) -> str:
    """Flame: list one level of top-level contents in a workspace library.

    Complements flame_list_libraries, which returns library names. This
    tool expands exactly one named library by one level: reels, clips,
    sequences, and folders. Folders report child count only; they are not
    recursively expanded.
    """
    data = await bridge.execute_json(f"""
        import flame, json

        target_library = {params.library_name!r}

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _matches(obj, target):
            return _name(obj).casefold() == str(target).strip("'").casefold()

        def _count(container):
            count = 0
            for attr in ('reels', 'clips', 'sequences', 'folders'):
                try:
                    count += len(getattr(container, attr))
                except Exception:
                    pass
            return count

        ws = flame.project.current_project.current_workspace
        result = None
        for lib in ws.libraries:
            if not _matches(lib, target_library):
                continue
            items = []
            for reel in getattr(lib, 'reels', []):
                items.append({{'name': _name(reel), 'type': type(reel).__name__, 'count': _count(reel)}})
            for clip in getattr(lib, 'clips', []):
                items.append({{'name': _name(clip), 'type': type(clip).__name__, 'count': 0}})
            for seq in getattr(lib, 'sequences', []):
                items.append({{'name': _name(seq), 'type': type(seq).__name__, 'count': 0}})
            for folder in getattr(lib, 'folders', []):
                items.append({{'name': _name(folder), 'type': type(folder).__name__, 'count': _count(folder)}})
            result = items
            break

        if result is None:
            print(json.dumps({{'error': 'Library not found', 'library_name': target_library}}))
        else:
            print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_context ─────────────────────────────────────────────────


async def get_context() -> str:
    """Flame: full snapshot of the current Flame session (project, workspace, desktop, reels).

    Returns a complete snapshot of what Flame is currently showing:
    - Project name and path
    - Current workspace name
    - Current desktop name
    - Every reel group → reel → clip/sequence (by name, type, tracks)
    - Batch group names

    Use this tool ONLY when:
    - the user wants the *whole* Flame session state in one call
    - diagnosing "why isn't Flame finding my clip" / "what's loaded right now"

    Do NOT use this tool for:
    - just the project metadata → use flame_get_project
    - just the libraries → use flame_list_libraries
    - just the desktop → use flame_list_desktop
    - pipeline-registry projects/shots/versions → use forge_* equivalents

    This tool is broad-by-design: prefer a narrower flame_* tool when the
    user's question is scoped.
    """
    data = await bridge.execute_json("""
        import flame, json

        def _name(obj):
            try:
                return str(obj.name).strip("'")
            except Exception:
                return str(obj)

        proj = flame.project.current_project
        ws   = proj.current_workspace
        desk = ws.desktop

        reel_groups = []
        for rg in desk.reel_groups:
            reels = []
            for r in rg.reels:
                items = []
                for c in list(r.clips) + list(r.sequences):
                    entry = {'name': _name(c), 'type': type(c).__name__}
                    if hasattr(c, 'versions'):
                        try:
                            tracks = list(c.versions[0].tracks)
                            entry['tracks'] = len(tracks)
                            segs = []
                            for t in tracks:
                                for s in t.segments:
                                    sn = _name(s)
                                    if sn:
                                        segs.append(sn)
                            entry['segments'] = segs
                        except Exception:
                            pass
                    items.append(entry)
                reels.append({'name': _name(r), 'items': items})
            reel_groups.append({'name': _name(rg), 'reels': reels})

        batch_groups = [_name(bg) for bg in desk.batch_groups]

        result = {
            'project':      _name(proj),
            'project_folder': str(proj.project_folder),
            'workspace':    _name(ws),
            'desktop':      _name(desk),
            'reel_groups':  reel_groups,
            'batch_groups': batch_groups,
        }
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_find_media ──────────────────────────────────────────────


class FindMediaInput(BaseModel):
    """Input for finding media by name."""

    query: str = Field(
        ...,
        description="Search string — matches against clip/sequence names. "
        "Case-insensitive substring match.",
        min_length=1,
    )
    scope: str = Field(
        default="all",
        description="Where to search: 'desktop', 'libraries', or 'all'",
    )


async def find_media(params: FindMediaInput) -> str:
    """Flame: locate a *named* clip or sequence inside the live Flame
    session by substring match against the name.

    Searches Flame's desktop reels and/or workspace libraries for clips
    and sequences whose names contain the query (case-insensitive). The
    user must provide a query string. This tool searches *by name*; it
    is not a structural traversal of reel or sequence contents — without
    a specific name to match, it will not enumerate the items inside
    a reel, sequence, library, or folder.

    Use this tool ONLY when:
    - the user is searching for a *named clip or sequence inside Flame*
    - the user has a specific name (or substring of a name) to match
    - the search target is in the live Flame session (desktop or libraries)

    Do NOT use this tool for:
    - listing all libraries (use flame_list_libraries — no name filter)
    - listing media in the forge-bridge registry (use forge_list_media)
    - listing published plates from the pipeline (use forge_list_published_plates)
    - searching pipeline shots (use forge_list_shots)

    This tool requires a running Flame session and a query argument.
    """
    data = await bridge.execute_json(f"""
        import flame, json
        query = {params.query!r}.lower()
        scope = {params.scope!r}
        results = []

        def _check_container(container, location):
            for clip in container.clips:
                name = clip.name.get_value() if hasattr(clip.name, 'get_value') else str(clip.name)
                if query in str(name).lower():
                    results.append({{'type': 'clip', 'name': str(name), 'location': location,
                                     'duration': str(clip.duration), 'width': clip.width, 'height': clip.height}})
            for seq in container.sequences:
                name = seq.name.get_value() if hasattr(seq.name, 'get_value') else str(seq.name)
                if query in str(name).lower():
                    results.append({{'type': 'sequence', 'name': str(name), 'location': location,
                                     'duration': str(seq.duration), 'width': seq.width, 'height': seq.height}})

        ws = flame.projects.current_project.current_workspace

        if scope in ('desktop', 'all'):
            desk = ws.desktop
            for rg in desk.reel_groups:
                rg_name = str(rg.name)
                for r in rg.reels:
                    _check_container(r, f'Desktop/{{rg_name}}/{{r.name}}')

        if scope in ('libraries', 'all'):
            for lib in ws.libraries:
                lib_name = str(lib.name)
                _check_container(lib, f'Library/{{lib_name}}')
                for folder in lib.folders:
                    f_name = str(folder.name)
                    _check_container(folder, f'Library/{{lib_name}}/{{f_name}}')
                    for reel in folder.reels:
                        _check_container(reel, f'Library/{{lib_name}}/{{f_name}}/{{reel.name}}')

        print(json.dumps({{'query': {params.query!r}, 'count': len(results), 'results': results}}))
    """)
    return json.dumps(data, indent=2)
