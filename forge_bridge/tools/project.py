"""Project, workspace, and media library tools."""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_bridge import bridge


# ── Tool: flame_get_project ─────────────────────────────────────────────


async def get_project() -> str:
    """Flame: get the currently-open Flame project (name, paths, OCIO, version).

    Reads from the running Autodesk Flame session via its Python API.
    Returns workspace name, library count, media storage paths, and the
    Flame version. Always safe to call (read-only).

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
        import flame, json
        proj = flame.project.current_project
        ws = proj.current_workspace
        user = flame.users.current_user
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
    """Flame: search the live Flame session for clips/sequences by name.

    Searches Flame's desktop reels and/or workspace libraries for clips
    and sequences whose names contain the query (case-insensitive). The
    user must provide a query string.

    Use this tool ONLY when:
    - the user is searching for a *named clip or sequence inside Flame*
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
