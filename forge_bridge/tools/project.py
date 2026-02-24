"""Project, workspace, and media library tools."""

import json
from typing import Optional

from pydantic import BaseModel, Field

from forge_mcp import bridge


# ── Tool: flame_get_project ─────────────────────────────────────────────


async def get_project() -> str:
    """Get current Flame project info: name, paths, resolution, OCIO config.

    Returns project metadata including workspace name, library count,
    media storage paths, and Flame version. Always safe to call.
    """
    data = await bridge.execute_json("""
        import flame, json
        proj = flame.projects.current_project
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


async def list_libraries(params: ListLibrariesInput) -> str:
    """List all libraries in the current workspace with optional content counts.

    Returns library names and, if requested, counts of folders, reels,
    clips, and sequences within each.
    """
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
    """List the desktop's reel groups, reels, batch groups, and their contents.

    Returns the full desktop structure including reel groups with their
    reels and clip/sequence counts, plus batch group names.
    """
    data = await bridge.execute_json("""
        import flame, json
        desk = flame.projects.current_project.current_workspace.desktop
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
    """Search for clips and sequences by name across the project.

    Searches desktop reels and/or libraries for clips and sequences
    whose names contain the query string (case-insensitive).
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
