"""Batch tools — node management, connections, attributes, rendering."""

import json
import textwrap
from typing import Optional

from pydantic import BaseModel, Field

from forge_bridge import bridge


# ── Tool: flame_list_batch_groups ───────────────────────────────────────


async def list_batch_groups() -> str:
    """List all batch groups on the current Flame Desktop.

    Returns each batch group name and whether it is the currently open
    batch context.

    Note: uses is_open (not opened) for boolean clarity.
    flame_list_libraries uses 'opened' as grandfathered field name.
    Both refactor together when canonical boolean prefix pattern
    matures (§11 follow-on).
    """
    data = await bridge.execute_json("""
        import flame, json

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        batch = flame.batch
        current_name = None
        try:
            if batch.opened:
                current_name = _name(batch)
        except Exception:
            current_name = None

        ws = flame.project.current_project.current_workspace
        desk = ws.desktop
        groups = []
        for group in desk.batch_groups:
            name = _name(group)
            groups.append({
                'name': name,
                'is_open': bool(current_name and name == current_name),
            })

        print(json.dumps(groups))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_node_types ──────────────────────────────────────────


async def get_node_types() -> str:
    """List valid live Flame Batch node type strings.

    Queries flame.batch.node_types from the current Flame session. Use this
    before flame_create_node when the operator needs valid node type values.
    """
    data = await bridge.execute_json("""
        import flame, json

        node_types = []
        for node_type in flame.batch.node_types:
            node_types.append(str(node_type))

        print(json.dumps({'node_types': node_types}))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_batch_iterations ────────────────────────────────────


async def get_batch_iterations() -> str:
    """List iterations for the currently open Flame Batch group.

    Read-only. Returns the current iteration index, total count, and
    available iteration indices. If no batch group is open, returns a
    structured no_batch_open error rather than raising.

    render_state per iteration is not exposed by PyBatchIteration
    directly. Determining render state requires disk inspection or
    node-graph traversal. Escape via flame_execute_python. Candidate
    for flame_get_iteration_render_state when use case crystallizes.
    """
    data = await bridge.execute_json("""
        import flame, json

        batch = flame.batch
        if not batch.opened:
            print(json.dumps({
                'error': 'no_batch_open',
                'message': 'Open a batch group first via flame_open_batch_group',
            }))
        else:
            iterations = []
            for iteration in getattr(batch, 'batch_iterations', []):
                iterations.append({
                    'index': int(iteration.iteration_number),
                })

            print(json.dumps({
                'current_iteration': int(getattr(batch, 'current_iteration_number', 0)),
                'total_iterations': len(iterations),
                'iterations': iterations,
            }))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_batch_reels ─────────────────────────────────────────


async def get_batch_reels() -> str:
    """List reels and shelf reels for the currently open Flame Batch group.

    This tool exposes only the minimum structured payload required
    for future filter predicates. For deeper metadata use
    flame_execute_python.

    Read-only. Returns reel/shelf-reel names and clip name/duration pairs.
    Colourspace, reel paths, tape metadata, publish state, handles, and bit
    depth are intentionally excluded.
    """
    data = await bridge.execute_json("""
        import flame, json

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

        def _reel_entry(reel, reel_type):
            clips = []
            for clip in getattr(reel, 'clips', []):
                clips.append({
                    'name': _name(clip),
                    'duration': _duration_frames(clip),
                })
            return {
                'name': _name(reel),
                'type': reel_type,
                'clips': clips,
            }

        batch = flame.batch
        if not batch.opened:
            print(json.dumps({
                'error': 'no_batch_open',
                'message': 'Open a batch group first via flame_open_batch_group',
            }))
        else:
            reels = []
            for reel in getattr(batch, 'reels', []):
                reels.append(_reel_entry(reel, 'reel'))
            for reel in getattr(batch, 'shelf_reels', []):
                reels.append(_reel_entry(reel, 'shelf_reel'))

            print(json.dumps({'reels': reels}))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_open_batch_group ────────────────────────────────────────


class OpenBatchGroupInput(BaseModel):
    """Input for opening a Flame Batch group."""

    batch_group_name: str = Field(
        ..., description="Exact batch group name to open in Flame's active UI session."
    )
    dry_run: bool = Field(
        default=False,
        description="If True, preview the context switch without opening the batch group.",
    )


async def open_batch_group(params: OpenBatchGroupInput) -> str:
    """Open a named Flame Batch group, binding subsequent batch operation context.

    Current shape: imperative context binding inside Flame's active
    UI session, not persistent graph-level selection state. This is the
    batch-domain instance of the select primitive (§11 item 12) — it
    binds execution context to a named batch group before downstream
    batch operations. Generic select primitive (cross-domain) remains
    future work.

    There is no close operation — opening a different batch group
    switches context. This matches Flame's native UX.

    dry_run=True returns a switch preview with current and proposed names.
    current is null when no batch group is currently open
    in the Flame session (e.g. fresh launch or no prior open call).
    """
    if params.dry_run:
        data = await bridge.execute_json(f"""
            import flame, json

            target_name = {params.batch_group_name!r}

            def _name(obj):
                try:
                    value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                    return str(value).strip("'")
                except Exception:
                    return str(obj).strip("'")

            def _current_name():
                try:
                    if flame.batch.opened:
                        return _name(flame.batch)
                except Exception:
                    pass
                return None

            ws = flame.project.current_project.current_workspace
            found = None
            for group in ws.desktop.batch_groups:
                if _name(group).casefold() == target_name.casefold():
                    found = _name(group)
                    break

            if found is None:
                print(json.dumps({{'error': 'batch_group_not_found',
                                   'batch_group_name': target_name}}))
            else:
                print(json.dumps({{
                    'dry_run': True,
                    'action': 'open_batch_group',
                    'proposed': found,
                    'current': _current_name(),
                }}))
        """)
        return json.dumps(data, indent=2)

    data = await bridge.execute_json(f"""
        import flame, json, threading

        target_name = {params.batch_group_name!r}

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _current_name():
            try:
                if flame.batch.opened:
                    return _name(flame.batch)
            except Exception:
                pass
            return None

        ws = flame.project.current_project.current_workspace
        target = None
        for group in ws.desktop.batch_groups:
            if _name(group).casefold() == target_name.casefold():
                target = group
                break

        if target is None:
            print(json.dumps({{'error': 'batch_group_not_found',
                               'batch_group_name': target_name}}))
        else:
            previous = _current_name()
            event = threading.Event()
            result = {{}}

            def _do():
                try:
                    if hasattr(target, 'open'):
                        target.open()
                    elif hasattr(flame.batch, 'open'):
                        flame.batch.open(target)
                    else:
                        raise RuntimeError('No Flame Batch open method available')
                    result['opened'] = _name(target)
                    result['previous'] = previous
                except Exception as e:
                    result['error'] = str(e)
                event.set()

            flame.schedule_idle_event(_do)
            event.wait(timeout=10)
            print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_delete_node ─────────────────────────────────────────────


class DeleteNodeInput(BaseModel):
    """Input for deleting a node from the currently open Batch group."""

    node_name: str = Field(..., description="Exact node name in the currently open batch.")
    dry_run: bool = Field(
        default=False,
        description="If True, preview node deletion without mutating the graph.",
    )


def _indent_flame_body(body: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in body.strip("\n").splitlines())


def _delete_node_code(node_name: str, *, dry_run: bool) -> str:
    schedule_prefix = "" if dry_run else "import threading"
    if dry_run:
        body = _indent_flame_body("""
print(json.dumps({
    'dry_run': True,
    'action': 'delete_node',
    'node_name': _name(node),
    'node_type': _node_type(node),
    'connected_inputs': _connected_count(node, 'input'),
    'connected_outputs': _connected_count(node, 'output'),
}))
""", 16)
    else:
        body = _indent_flame_body("""
event = threading.Event()
result = {}

def _do():
    try:
        if hasattr(batch, 'delete_node'):
            batch.delete_node(node)
        elif hasattr(node, 'delete'):
            node.delete()
        else:
            raise RuntimeError('No Flame Batch node delete method available')
        result['deleted'] = target_name
    except Exception as e:
        result['error'] = str(e)
    event.set()

flame.schedule_idle_event(_do)
event.wait(timeout=10)
print(json.dumps(result))
""", 16)
    return textwrap.dedent(f"""
        import flame, json
        {schedule_prefix}

        target_name = {node_name!r}

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _node_type(node):
            try:
                value = node.type.get_value() if hasattr(node.type, 'get_value') else node.type
                return str(value)
            except Exception:
                return type(node).__name__

        def _connected_count(node, direction):
            try:
                sockets = node.sockets
                if isinstance(sockets, dict):
                    values = sockets.values()
                else:
                    values = sockets
                return sum(1 for value in values if value)
            except Exception:
                pass
            attr = 'input_sockets' if direction == 'input' else 'output_sockets'
            try:
                return len(getattr(node, attr))
            except Exception:
                return 0

        batch = flame.batch
        if not batch.opened:
            print(json.dumps({{
                'error': 'no_batch_open',
                'message': 'Open a batch group first via flame_open_batch_group',
            }}))
        else:
            matches = [node for node in batch.nodes if _name(node).casefold() == target_name.casefold()]
            if len(matches) == 0:
                print(json.dumps({{'error': 'node_not_found', 'node_name': target_name}}))
            elif len(matches) > 1:
                print(json.dumps({{
                    'error': 'ambiguous_node_name',
                    'matches': len(matches),
                    'message': 'Multiple nodes share this name; rename or specify a unique node first.',
                }}))
            else:
                node = matches[0]
{body}
    """)


async def delete_node(params: DeleteNodeInput) -> str:
    """Delete a node from the currently open Flame Batch group.

    Operates on the currently open batch group. If no batch group is open,
    returns {"error": "no_batch_open", "message": "Open a batch group first via flame_open_batch_group"}.
    If multiple nodes share the requested name, returns ambiguous_node_name
    with the match count. dry_run=True previews Tier 1 node metadata and
    connection counts without scheduling a write.
    """
    data = await bridge.execute_json(_delete_node_code(params.node_name, dry_run=params.dry_run))
    return json.dumps(data, indent=2)


# ── Tool: flame_disconnect_nodes ────────────────────────────────────────


class DisconnectNodesInput(BaseModel):
    """Input for disconnecting two nodes in the currently open Batch group."""

    output_node: str = Field(..., description="Name of the source node.")
    input_node: str = Field(..., description="Name of the destination node.")
    output_socket: str = Field(default="Default", description="Output socket name.")
    input_socket: str = Field(default="Default", description="Input socket name.")
    dry_run: bool = Field(
        default=False,
        description="If True, preview disconnection without mutating the graph.",
    )


def _disconnect_nodes_code(params: DisconnectNodesInput) -> str:
    schedule_prefix = "" if params.dry_run else "import threading"
    if params.dry_run:
        body = _indent_flame_body("""
print(json.dumps({
    'dry_run': True,
    'action': 'disconnect_nodes',
    'input_node': _name(node),
    'input_socket': input_socket,
    'connection_exists': _connection_exists(node, input_socket),
}))
""", 20)
    else:
        body = _indent_flame_body("""
event = threading.Event()
result = {}

def _do():
    try:
        ok = batch.disconnect_node(node, input_socket)
        result['disconnected'] = bool(ok) if ok is not None else True
        result['input_node'] = _name(node)
        result['input_socket'] = input_socket
    except Exception as e:
        result['error'] = str(e)
    event.set()

flame.schedule_idle_event(_do)
event.wait(timeout=10)
print(json.dumps(result))
""", 20)
    return textwrap.dedent(f"""
        import flame, json
        {schedule_prefix}

        output_name = {params.output_node!r}
        input_name = {params.input_node!r}
        input_socket = {params.input_socket!r}

        def _name(obj):
            try:
                value = obj.name.get_value() if hasattr(obj.name, 'get_value') else obj.name
                return str(value).strip("'")
            except Exception:
                return str(obj).strip("'")

        def _connection_exists(node, input_socket):
            try:
                sockets = node.sockets
                haystack = str(sockets)
                return input_socket == 'Default' or input_socket in haystack
            except Exception:
                return False

        batch = flame.batch
        if not batch.opened:
            print(json.dumps({{
                'error': 'no_batch_open',
                'message': 'Open a batch group first via flame_open_batch_group',
            }}))
        else:
            try:
                node = batch.get_node(input_name)
            except Exception as e:
                print(json.dumps({{'error': 'node_not_found',
                                   'node_name': input_name,
                                   'message': str(e)}}))
            else:
{body}
    """)


async def disconnect_nodes(params: DisconnectNodesInput) -> str:
    """Disconnect two nodes in the currently open Flame Batch group.

    output_node is accepted in the schema for operator-query
    legibility (matching the 'disconnect from X to Y' mental
    model). The underlying Flame API only requires input_node
    + input_socket. output_node is informational and does not
    constrain behavior.

    Operates on the currently open batch group. If no batch group is open,
    returns {"error": "no_batch_open", "message": "Open a batch group first via flame_open_batch_group"}.
    dry_run=True previews the intended graph-state mutation and reports
    whether a matching connection appears to exist.
    """
    data = await bridge.execute_json(_disconnect_nodes_code(params))
    return json.dumps(data, indent=2)


# ── Tool: flame_list_batch_nodes ────────────────────────────────────────


async def list_batch_nodes() -> str:
    """List all nodes in the current batch with their types and connections.

    Returns every node in the schematic with name, type, position,
    input/output sockets, and what each socket is connected to.
    """
    data = await bridge.execute_json("""
        import flame, json
        b = flame.batch
        if not b.opened:
            print(json.dumps({'error': 'Batch is not open'}))
        else:
            nodes = []
            for node in b.nodes:
                name = node.name.get_value() if hasattr(node.name, 'get_value') else str(node.name)
                ntype = node.type.get_value() if hasattr(node.type, 'get_value') else str(getattr(node, 'type', '?'))
                info = {
                    'name': str(name),
                    'type': str(ntype),
                    'class': type(node).__name__,
                    'sockets': node.sockets,
                }
                try:
                    info['pos_x'] = node.pos_x.get_value()
                    info['pos_y'] = node.pos_y.get_value()
                except:
                    pass
                try:
                    info['bypass'] = node.bypass.get_value()
                except:
                    pass
                nodes.append(info)

            result = {
                'node_count': len(nodes),
                'nodes': nodes,
                'reels': [str(r.name) for r in b.reels],
                'shelf_reels': [str(r.name) for r in b.shelf_reels],
                'current_iteration': b.current_iteration_number,
            }
            print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_node_attributes ─────────────────────────────────────


class GetNodeAttrsInput(BaseModel):
    """Input for reading node attributes."""

    node_name: str = Field(
        ..., description="Exact node name in the batch schematic."
    )


async def get_node_attributes(params: GetNodeAttrsInput) -> str:
    """Get all attributes and their values for a batch node.

    Returns attribute names, current values, valid choices/ranges,
    and the node's socket connections.
    """
    data = await bridge.execute_json(f"""
        import flame, json
        b = flame.batch
        try:
            node = b.get_node({params.node_name!r})
        except Exception as e:
            print(json.dumps({{'error': f'Node not found: {{e}}'}}))
            raise SystemExit

        attrs = []
        for attr_name in node.attributes:
            try:
                val = getattr(node, attr_name)
                gv = val.get_value()
                try:
                    vs = val.values
                except:
                    vs = None
                # Stringify complex types
                gv_str = str(gv)
                if hasattr(gv, '__class__') and 'PyResolution' in type(gv).__name__:
                    gv_str = f'PyResolution({{gv.width}}x{{gv.height}})'
                attrs.append({{
                    'name': attr_name,
                    'value': gv_str,
                    'choices': str(vs) if vs else None,
                }})
            except Exception as e:
                attrs.append({{'name': attr_name, 'error': str(e)}})

        result = {{
            'node_name': {params.node_name!r},
            'node_type': str(node.type.get_value()) if hasattr(node.type, 'get_value') else '?',
            'class': type(node).__name__,
            'attribute_count': len(attrs),
            'attributes': attrs,
            'input_sockets': node.input_sockets,
            'output_sockets': node.output_sockets,
            'connections': node.sockets,
        }}
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_create_node ─────────────────────────────────────────────


class CreateNodeInput(BaseModel):
    """Input for creating a batch node."""

    node_type: str = Field(
        ...,
        description="Node type to create. Must match a value from "
        "batch.node_types (e.g. 'Comp', 'Write File', 'Action', "
        "'Colour Source', 'Resize & Crop', 'GMask Tracer').",
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional custom name. If omitted, Flame auto-names.",
    )


async def create_node(params: CreateNodeInput) -> str:
    """Create a new node in the current batch schematic.

    Runs on Flame's main thread. Returns the created node's name,
    type, and available sockets.
    """
    rename_code = ""
    if params.name:
        rename_code = f"""
                node.name.set_value({params.name!r})"""

    data = await bridge.execute_json(f"""
        import flame, json, threading
        b = flame.batch
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                node = b.create_node({params.node_type!r}){rename_code}
                result['name'] = node.name.get_value()
                result['type'] = node.type.get_value() if hasattr(node.type, 'get_value') else str(node.type)
                result['class'] = type(node).__name__
                result['input_sockets'] = node.input_sockets
                result['output_sockets'] = node.output_sockets
                result['ok'] = True
            except Exception as e:
                result['error'] = str(e)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=10)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_connect_nodes ───────────────────────────────────────────


class ConnectNodesInput(BaseModel):
    """Input for connecting two batch nodes."""

    output_node: str = Field(
        ..., description="Name of the source node (output side)."
    )
    input_node: str = Field(
        ..., description="Name of the destination node (input side)."
    )
    output_socket: str = Field(
        default="Default",
        description="Output socket name. 'Default' uses the first output "
        "(usually 'Result').",
    )
    input_socket: str = Field(
        default="Default",
        description="Input socket name. 'Default' uses the first input "
        "(usually 'Front'). For Action nodes, 'Default' connects "
        "to 'Background'.",
    )


async def connect_nodes(params: ConnectNodesInput) -> str:
    """Connect two nodes in the batch schematic.

    Wires output_node's output socket to input_node's input socket.
    Runs on Flame's main thread.
    """
    data = await bridge.execute_json(f"""
        import flame, json, threading
        b = flame.batch
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                out_node = b.get_node({params.output_node!r})
                in_node = b.get_node({params.input_node!r})
                ok = b.connect_nodes(out_node, {params.output_socket!r},
                                     in_node, {params.input_socket!r})
                result['connected'] = ok
                result['from'] = {params.output_node!r}
                result['to'] = {params.input_node!r}
                result['output_socket'] = {params.output_socket!r}
                result['input_socket'] = {params.input_socket!r}
            except Exception as e:
                result['error'] = str(e)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=10)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_set_node_attribute ──────────────────────────────────────


class SetNodeAttrInput(BaseModel):
    """Input for setting a node attribute."""

    node_name: str = Field(..., description="Target node name.")
    attribute: str = Field(
        ...,
        description="Attribute name. Use get_node_attributes to see "
        "available attributes and their valid values.",
    )
    value: str = Field(
        ...,
        description="New value as string. Booleans: 'true'/'false'. "
        "Numbers: '100' or '23.976'. Enums: exact choice string "
        "(e.g. 'PIZ', 'OpenEXR', '16-bit fp').",
    )


async def set_node_attribute(params: SetNodeAttrInput) -> str:
    """Set an attribute on a batch node.

    Runs on Flame's main thread. Use get_node_attributes first to see
    valid choices for enum attributes.
    """
    # Smart type coercion
    val = params.value
    if val.lower() == "true":
        value_expr = "True"
    elif val.lower() == "false":
        value_expr = "False"
    elif val.startswith("(") and val.endswith(")"):
        value_expr = val  # tuple
    else:
        # Try numeric, fall back to string
        try:
            float(val)
            value_expr = val
        except ValueError:
            value_expr = repr(val)

    data = await bridge.execute_json(f"""
        import flame, json, threading
        b = flame.batch
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                node = b.get_node({params.node_name!r})
                attr = getattr(node, {params.attribute!r})
                old_val = str(attr.get_value())
                attr.set_value({value_expr})
                new_val = str(attr.get_value())
                result['ok'] = True
                result['node'] = {params.node_name!r}
                result['attribute'] = {params.attribute!r}
                result['old_value'] = old_val
                result['new_value'] = new_val
            except Exception as e:
                result['error'] = str(e)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=10)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_render_batch ────────────────────────────────────────────


class RenderBatchInput(BaseModel):
    """Input for rendering the current batch."""

    mode: str = Field(
        default="Foreground",
        description="Render mode: 'Foreground' (blocking) or 'Background'.",
    )


async def render_batch(params: RenderBatchInput) -> str:
    """Render the current batch setup.

    Triggers a render on Flame's main thread.
    Foreground renders block until complete.
    """
    data = await bridge.execute_json(f"""
        import flame, json, threading
        b = flame.batch
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                ok = b.render(render_option={params.mode!r})
                result['rendered'] = ok
                result['mode'] = {params.mode!r}
            except Exception as e:
                result['error'] = str(e)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=300)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_batch_setup ─────────────────────────────────────────────


class BatchSetupInput(BaseModel):
    """Input for saving/loading batch setups."""

    action: str = Field(
        ..., description="'save' or 'load'."
    )
    path: str = Field(
        ..., description="Full file path for the batch setup file. "
        "⚠️ save_setup mangles the path: dots become underscores "
        "and '.batch' is appended. E.g. '/tmp/my_setup' saves to "
        "'/tmp/my_setup.batch' + '/tmp/my_setup/' directory. "
        "Use paths without extension for predictable results.",
    )


async def batch_setup(params: BatchSetupInput) -> str:
    """Save or load a batch setup file.

    Runs on Flame's main thread.
    """
    if params.action == "save":
        method = "save_setup"
    elif params.action == "load":
        method = "load_setup"
    else:
        return json.dumps({"error": f"Invalid action: {params.action}. Use 'save' or 'load'."})

    data = await bridge.execute_json(f"""
        import flame, json, threading
        b = flame.batch
        event = threading.Event()
        result = {{}}

        def _do():
            try:
                ok = b.{method}({params.path!r})
                result['ok'] = ok
                result['action'] = {params.action!r}
                result['path'] = {params.path!r}
            except Exception as e:
                result['error'] = str(e)
            event.set()

        flame.schedule_idle_event(_do)
        event.wait(timeout=30)
        print(json.dumps(result))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_get_write_file_path ─────────────────────────────────────


class GetWriteFilePathInput(BaseModel):
    """Input for resolving write file output paths."""

    node_name: str = Field(
        ..., description="Name of the Write File node."
    )
    frame: Optional[int] = Field(
        default=None,
        description="Specific frame number to resolve. If omitted, "
        "returns the range pattern (e.g. [001001-001100]).",
    )


async def get_write_file_path(params: GetWriteFilePathInput) -> str:
    """Resolve the output media path for a Write File node.

    Returns the actual file path with all Flame tokens resolved.
    """
    frame_arg = f", frame={params.frame}" if params.frame is not None else ""
    data = await bridge.execute_json(f"""
        import flame, json
        b = flame.batch
        try:
            node = b.get_node({params.node_name!r})
            result = {{
                'node': {params.node_name!r},
                'path': node.get_resolved_media_path(){frame_arg},
                'path_no_ext': node.get_resolved_media_path(show_extension=False),
                'media_path': node.media_path.get_value(),
                'media_path_pattern': node.media_path_pattern.get_value(),
                'file_type': node.file_type.get_value(),
                'bit_depth': str(node.bit_depth.get_value()),
                'range_start': node.range_start.get_value(),
                'range_end': node.range_end.get_value(),
            }}
            print(json.dumps(result))
        except Exception as e:
            print(json.dumps({{'error': str(e)}}))
    """)
    return json.dumps(data, indent=2)


# ── Tool: flame_inspect_batch_xml ─────────────────────────────────────


class InspectBatchXmlInput(BaseModel):
    """Input for inspecting a batch setup XML file on disk."""

    batch_path: str = Field(
        ..., description="Full path to a .batch file on disk. "
        "e.g. '/PROJEKTS/012_12_12/_04_shots/ABC_010/comp/flame/batch/ABC_010_v00.batch'"
    )


async def inspect_batch_xml(params: InspectBatchXmlInput) -> str:
    """Inspect a Flame batch setup XML file on disk (no Flame connection needed).

    Returns node list, connections/topology, and identifies dangling nodes.
    Useful for understanding batch structure before or after publish.

    NOTE: Requires forge_batch_xml script from flame_hooks/forge_tools/forge_publish_shots/scripts/.
    This dependency is not yet available in standalone forge-bridge.
    """
    raise RuntimeError(
        "inspect_batch_xml requires forge_batch_xml script from flame_hooks. "
        "This dependency is not yet available in standalone forge-bridge. "
        "To use this tool, port forge_batch_xml from the projekt-forge flame_hooks directory."
    )


# ── Tool: flame_prune_batch_xml ───────────────────────────────────────


class PruneBatchXmlInput(BaseModel):
    """Input for pruning junk nodes from batch XML."""

    batch_path: str = Field(
        default="",
        description="Full path to a specific .batch file. "
        "If empty, uses shot_dir to find all .batch files."
    )
    shot_dir: str = Field(
        default="",
        description="Shot directory to prune all batches in. "
        "e.g. '/PROJEKTS/012_12_12/_04_shots/ABC_010'. "
        "Ignored if batch_path is provided."
    )


async def prune_batch_xml(params: PruneBatchXmlInput) -> str:
    """Prune junk nodes (Resize, MUX) from published batch XML on disk.

    Removes passthrough nodes from PyExporter and wires clips directly
    to the Write File node. No Flame connection needed.

    NOTE: Requires forge_batch_prune script from flame_hooks/forge_tools/forge_publish_shots/scripts/.
    This dependency is not yet available in standalone forge-bridge.
    """
    raise RuntimeError(
        "prune_batch_xml requires forge_batch_prune script from flame_hooks. "
        "This dependency is not yet available in standalone forge-bridge. "
        "To use this tool, port forge_batch_prune from the projekt-forge flame_hooks directory."
    )
