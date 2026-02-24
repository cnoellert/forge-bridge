# Writing Endpoint Adapters

An **endpoint** is any piece of software connected to forge-bridge. This guide explains how to write a new adapter so that your software can communicate through bridge.

---

## What an Adapter Does

An adapter has two jobs:

1. **Translate inbound** — convert your software's native data and events into bridge's canonical vocabulary
2. **Translate outbound** — convert bridge messages and events into actions or data in your software

The adapter is intentionally thin. It does not contain business logic. It maps between two languages.

---

## Anatomy of an Endpoint

An endpoint adapter consists of:

```
my_software_endpoint/
├── adapter.py          # Core translation logic
├── client.py           # Bridge connection management
├── vocabulary.py       # Mapping from native terms to bridge canonical
└── README.md           # What this endpoint connects and how
```

### adapter.py — Translation Layer

```python
from forge_bridge.client import BridgeClient
from forge_bridge.vocabulary import Entity, Shot, Version, Media

class MySoftwareAdapter:
    """Adapter connecting MySoftware to forge-bridge."""
    
    def __init__(self, bridge_url: str = "http://127.0.0.1:7777"):
        self.bridge = BridgeClient(bridge_url)
        
    async def on_export(self, native_export_event):
        """Called when MySoftware exports media.
        
        Translates the native event into bridge vocabulary and pushes it.
        """
        # Translate native concepts to bridge vocabulary
        shot = Shot(
            name=native_export_event.shot_code,
            sequence_id=self._resolve_sequence(native_export_event.sequence),
        )
        version = Version(
            version_number=native_export_event.version_number,
            parent_type="shot",
        )
        media = Media(
            format=native_export_event.file_format,
            resolution=native_export_event.resolution,
            colorspace=native_export_event.colorspace,
        )
        
        # Push to bridge
        await self.bridge.push(entity=shot)
        await self.bridge.push(entity=version, parent=shot)
        await self.bridge.push(entity=media, parent=version)
        
    async def on_bridge_event(self, event):
        """Called when bridge sends an event to this endpoint.
        
        Translates bridge events into actions in MySoftware.
        """
        if event.type == "version.updated":
            # Something upstream changed — act on it in MySoftware
            native_id = self.vocabulary.resolve_to_native(event.entity_id)
            my_software.refresh_asset(native_id)
```

### vocabulary.py — Term Mapping

The vocabulary file declares how your software's terms map to bridge's canonical vocabulary.

```python
# Mapping from MySoftware's native terms to bridge canonical terms

ENTITY_TYPE_MAP = {
    # MySoftware term  →  bridge canonical type
    "clip":            "shot",
    "reel":            "sequence",
    "project":         "project",
    "source":          "media",
}

STATUS_MAP = {
    # MySoftware status  →  bridge canonical status
    "work_in_progress": "in_progress",
    "pending_review":   "review",
    "approved":         "approved",
    "final":            "delivered",
}

ROLE_MAP = {
    # MySoftware's layer names  →  bridge role names
    "master":           "primary",
    "ref":              "reference",
    "alpha":            "matte",
}
```

---

## Existing Endpoint: Flame

The Flame endpoint is implemented in two parts:

**`flame_hooks/forge_bridge/scripts/forge_bridge.py`** — Runs inside Flame as an HTTP server. Accepts Python code via `POST /exec` and returns results. This is the lowest-level Flame adapter — it exposes raw Python execution rather than a structured vocabulary adapter.

**`forge_bridge/`** — The MCP client that connects to the Flame hook and wraps it as structured tools. This is the adapter layer that maps Flame concepts to bridge vocabulary via the MCP tool definitions.

The vocabulary mapping for Flame:
```
Flame term          →  bridge canonical
─────────────────────────────────────────
sequence/timeline   →  Sequence
segment             →  Shot (+ Layer)
reel                →  Sequence
library             →  Project (sub-container)
clip                →  Media
L01/L02/L03 stack   →  Stack (Layers with Role assignments)
```

---

## Existing Endpoint: MCP / LLM

The MCP endpoint treats an LLM (like Claude) as a connected endpoint. It speaks the Model Context Protocol on one side and bridge's HTTP API on the other.

This demonstrates that bridge is truly endpoint-agnostic — an AI is just another participant with no special status.

---

## Connecting a New Endpoint

### Step 1: Define your vocabulary mapping

Before writing any code, write down how your software's concepts map to bridge's canonical vocabulary. See [VOCABULARY.md](VOCABULARY.md).

Ask:
- What is a "shot" in your software? What is a "sequence"?
- How does versioning work? Is it explicit (version numbers) or implicit (dates, names)?
- How is media (files) referenced? By path? By ID? By URL?
- What events does your software emit? What events does it need to receive?

### Step 2: Implement the client connection

Your endpoint needs a connection to bridge. For now, this means an HTTP connection to bridge's REST API. Future versions will add socket and WebSocket options.

```python
import httpx

class BridgeClient:
    def __init__(self, url: str = "http://127.0.0.1:7777"):
        self.url = url
        
    async def push(self, entity, parent=None):
        async with httpx.AsyncClient() as client:
            await client.post(f"{self.url}/push", json=entity.to_bridge_dict())
            
    async def query(self, entity_type, **filters):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.url}/query", json={
                "type": entity_type,
                "filters": filters
            })
            return resp.json()
            
    async def subscribe(self, event_type, callback):
        # WebSocket/SSE subscription — planned
        pass
```

### Step 3: Implement translation in both directions

**Inbound (your software → bridge):**
Events and data that originate in your software need to be translated into bridge vocabulary before being pushed.

**Outbound (bridge → your software):**
Events from bridge (or from other endpoints via bridge) need to be translated into actions in your software.

### Step 4: Declare your endpoint's capabilities

When connecting, declare what your endpoint can do:

```python
ENDPOINT_DECLARATION = {
    "name": "my_software",
    "type": "dcc",                    # dcc, editorial, tracking, ai, custom
    "version": "1.0.0",
    "capabilities": {
        "can_read":  ["shot", "sequence", "media"],
        "can_write": ["shot", "version", "media"],
        "events_emitted":   ["media.exported", "shot.status_changed"],
        "events_subscribed": ["version.updated", "sequence.changed"],
    }
}
```

### Step 5: Document the adapter

Write a README for your endpoint adapter that covers:
- What software it connects
- What version(s) of that software it supports
- What vocabulary mappings it implements
- What events it emits and subscribes to
- How to install and configure it
- Known limitations

---

## Bridge Port Conventions

To avoid port conflicts as the number of endpoints grows:

| Endpoint | Default Port |
|----------|-------------|
| Flame bridge (HTTP) | 9999 |
| bridge core service | 7777 |
| MCP server (stdio) | — (stdio, no port) |
| MCP server (HTTP) | 8080 |

New endpoints should document their default port and allow it to be overridden via environment variable.

---

## Testing Your Adapter

A minimal test for any adapter:

```python
async def test_adapter_roundtrip():
    """Push an entity to bridge and query it back."""
    adapter = MySoftwareAdapter()
    
    # Push a shot
    await adapter.push_shot(name="EP60_010", sequence="EP60")
    
    # Query it back through bridge
    result = await adapter.bridge.query("shot", name="EP60_010")
    
    assert result["name"] == "EP60_010"
    assert result["sequence"]["name"] == "EP60"
```

---

## Future: Endpoint Registration

When the bridge core service is implemented, endpoints will register themselves on connect. Bridge will maintain a registry of connected endpoints and their capabilities, allowing:

- Automatic routing of events to appropriate endpoints
- Discovery of available endpoints by other connected software
- Health monitoring and reconnection handling
