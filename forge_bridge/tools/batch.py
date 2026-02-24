"""Batch tools — node management, connections, attributes, rendering."""

import json
from typing import Optional, List

from pydantic import BaseModel, Field

from forge_mcp import bridge


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
