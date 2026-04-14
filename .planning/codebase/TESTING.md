# Testing Patterns

**Analysis Date:** 2026-04-14

## Test Framework

**Runner:**
- pytest 7.x+ (specified in `pyproject.toml` dev dependencies)
- Async support via pytest-asyncio
- Config: `pyproject.toml` `[tool.pytest.ini_options]` section sets `asyncio_mode = "auto"`

**Assertion Library:**
- pytest built-in assertions (`assert`, `with pytest.raises()`)
- No external assertion library

**Run Commands:**
```bash
pytest tests/                              # Run all tests
pytest tests/test_core.py -v               # Verbose output
pytest tests/test_integration.py -v        # Integration tests only
pytest --tb=short                          # Short traceback format
```

## Test File Organization

**Location:**
- Separate directory: `tests/` at repository root, parallel to `forge_bridge/` package directory
- Not co-located with source code

**Naming:**
- Test files: `test_*.py` prefix
- Test classes: `Test*` PascalCase
- Test methods: `test_*` snake_case
- Fixtures: descriptive names in pytest `@pytest.fixture` or `@pytest_asyncio.fixture`

**Structure:**
```
tests/
├── test_core.py          # Core vocabulary, entities, registry
├── test_integration.py   # Server + clients, WebSocket, protocol
└── test_e2e.py          # End-to-end: server + MCP + Flame clients
```

## Test Structure

**Suite Organization:**
```python
# test_core.py pattern
class TestTimecode:
    def test_from_string(self):
        tc = Timecode.from_string("01:00:00:00")
        assert tc.hours == 1 and tc.frames == 0

    def test_to_frames_24fps(self):
        tc = Timecode(1, 0, 0, 0, fps=Fraction(24))
        assert tc.to_frames() == 86400

class TestFrameRange:
    def test_duration(self):
        assert FrameRange(1001, 1100).duration == 100
    
    def test_invalid(self):
        with pytest.raises(ValueError):
            FrameRange(1100, 1001)
```

**Patterns:**
- One test class per domain (entity type, registry component, client behavior)
- `setup_method(self)` runs before each test in class
- `@pytest.fixture(scope="module")` for expensive setup (test servers)
- `@pytest.fixture` for per-test setup
- Async tests marked with `@pytest.mark.asyncio`

**Async test pattern:**
```python
@pytest.mark.asyncio
async def test_async_operation(self, server_url):
    async with AsyncClient.connect("test", server_url) as client:
        result = await client.request(ping())
        # assertions
```

## Mocking

**Framework:** unittest.mock (`AsyncMock`, `MagicMock`, `patch`)

**Patterns:**
Database mocking (no Postgres needed for tests):
```python
# test_integration.py pattern
class InMemoryStore:
    def __init__(self):
        self.projects: dict[str, dict] = {}
        self.entities: dict[str, dict] = {}
        self.locations: dict[str, list] = {}
        self.rels: list[dict] = []
        self.events: list[dict] = []
        self.sessions: dict[str, dict] = {}

def _make_mock_session(store: InMemoryStore):
    """Build a mock AsyncSession that uses the InMemoryStore."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    
    async def mock_get(model_cls, pk):
        # Return mock objects from in-memory store
        return None
    
    session.get = mock_get
    session.add = MagicMock()
    return session
```

Server DB patching in test startup:
```python
def _patch_db(self) -> None:
    """Replace get_session with a no-op in-memory version."""
    @asynccontextmanager
    async def fake_get_session(*args, **kwargs):
        session = AsyncMock()
        session.commit   = AsyncMock()
        session.rollback = AsyncMock()
        session.flush    = AsyncMock()
        session.add      = MagicMock()
        
        async def _get(cls, pk):
            return None
        session.get = _get
        
        async def _execute(stmt):
            r = MagicMock()
            r.scalars.return_value.all.return_value = []
            r.scalar_one_or_none.return_value = None
            r.all.return_value = []
            return r
        session.execute = _execute
        
        yield session
    
    import forge_bridge.server.router as router_mod
    import forge_bridge.store.session as session_mod
    session_mod.get_session = fake_get_session
    router_mod.get_session = fake_get_session
```

**What to Mock:**
- Database/storage layer (Postgres → in-memory dict or mock)
- External services (if any)
- File I/O in unit tests
- System time (via monkeypatch for deterministic tests)

**What NOT to Mock:**
- WebSocket connections — real `websockets` library used in integration tests
- Core business logic (Registry, entities, traits)
- Protocol message serialization/deserialization
- Client-server message routing

## Fixtures and Factories

**Test Data Pattern:**
The codebase does not use explicit factory patterns. Data is constructed directly in test methods:
```python
def test_stack_assembles(self):
    self.reg = Registry.default()
    shot = Shot(name="EP60_010")
    stack = Stack(shot_id=shot.id)
    for role in ("primary", "reference", "matte"):
        stack.add_layer(Layer(role, registry=self.reg))
    assert stack.depth == 3
```

**Fixture Pattern (per-test setup):**
```python
@pytest.fixture
def server_url(test_server):
    return test_server.url

@pytest.fixture
def test_server():
    """Module-scoped test server on port 19998."""
    server = TestServer(port=19998)
    server.start()
    yield server
    server.stop()
```

**Location:**
- Test fixtures defined in same test file where used
- Module-scoped fixtures use `@pytest.fixture(scope="module")`
- Per-test fixtures use `@pytest.fixture` (default scope="function")

## Coverage

**Requirements:** No enforced minimum in `pyproject.toml`

**View Coverage:**
```bash
pytest --cov=forge_bridge tests/
pytest --cov=forge_bridge --cov-report=html tests/
```

## Test Types

**Unit Tests:**
- Scope: Single class or function
- Location: `test_core.py` — tests for Registry, entities, traits, vocabulary
- Approach: Construct object, call method, assert result
- No network, no async (unless testing async function directly)
- Example: `TestTimecode.test_from_string()` — tests Timecode parsing
- Example: `TestRoleRegistry.test_standard_roles_present()` — tests Registry initialization

**Integration Tests:**
- Scope: Server + client, protocol, message routing
- Location: `test_integration.py`
- Approach: Start real test server (in background thread), connect async and sync clients, exercise request/response cycle
- No Postgres required (mocked with InMemoryStore)
- Real WebSocket connections between client and server
- Example: `TestAsyncClient.test_connect_and_welcome()` — client connects, receives session_id
- Example: `TestAsyncClient.test_event_received_by_subscriber()` — Client A publishes event, Client B receives it

**E2E Tests:**
- Scope: Server + multiple client types (MCP, Flame, observer) operating together
- Location: `test_e2e.py`
- Approach: Real server, real clients, simulate Flame segment creation, version publishing
- No Postgres required (same mocking as integration tests)
- Tests end-to-end workflows: Flame creates project → MCP reads it, MCP registers role → Flame receives broadcast
- Example: `test_three_clients_connect()` — all three client types connect simultaneously and see each other
- Example: `test_flame_endpoint_segment_created()` — FlameEndpoint publishes shot entity visible to MCP client

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_ping_pong(self, server_url):
    """Ping gets a pong back."""
    async with AsyncClient.connect("test_ping", server_url) as client:
        result = await client.request(ping())
        # pong has no result body — just no error is fine
```

**Context Manager Pattern:**
```python
# AsyncClient supports async context manager
async with AsyncClient.connect("test", server_url) as client:
    # client automatically starts and stops in scope
    pass

# SyncClient supports sync context manager
with SyncClient("sync_test", server_url) as client:
    # client connects in __enter__, disconnects in __exit__
    pass
```

**Event Subscription Testing:**
```python
async def test_event_received_by_subscriber(self, server_url):
    """Client A registers a role → Client B receives the event."""
    received = asyncio.Event()
    received_event = {}

    async with AsyncClient.connect("sender", server_url) as sender:
        async with AsyncClient.connect("listener", server_url) as listener:
            @listener.on("role.registered")
            async def on_role(event):
                received_event.update(event)
                received.set()

            await sender.request(role_register("broadcast_test_role"))

            # Give the event a moment to propagate
            await asyncio.wait_for(received.wait(), timeout=3.0)
            assert received_event.get("event_type") == "role.registered"
```

**Error Testing:**
```python
async def test_role_duplicate_raises(self, server_url):
    """Registering an existing role name raises ServerError."""
    async with AsyncClient.connect("test_dup", server_url) as client:
        await client.request(role_register("dup_role"))
        with pytest.raises(ServerError) as exc:
            await client.request(role_register("dup_role"))
        assert "ALREADY_EXISTS" in exc.value.code
```

**Sync Client Testing:**
```python
def test_role_register_sync(self, server_url):
    with SyncClient("sync_role", server_url) as client:
        result = client.role_register("sync_custom_role", label="Sync Test")
        assert result["name"] == "sync_custom_role"
        assert "key" in result
```

**Protocol Testing (no network):**
```python
class TestProtocol:
    """Unit tests for the wire protocol — no network required."""

    def test_message_round_trip(self):
        msg = hello("test_client", "flame")
        parsed = Message.parse(msg.serialize())
        assert parsed.type == MsgType.HELLO
        assert parsed["client_name"] == "test_client"
        assert parsed.msg_id is not None
```

**Monkeypatch Pattern:**
```python
@pytest.mark.asyncio
async def test_mcp_tools_ping(server_url, monkeypatch):
    """forge_ping MCP tool returns connected status."""
    mcp = await _mcp_client(server_url)

    # Patch the module-level _client so tools.ping() can find it
    import forge_bridge.mcp.server as mcp_server
    monkeypatch.setattr(mcp_server, "_client", mcp)

    from forge_bridge.mcp.tools import ping
    result_json = await ping()

    import json
    result = json.loads(result_json)
    assert result.get("status") == "connected"
    assert "session_id" in result

    await mcp.stop()
```

## Test Servers

**TestServer (test_integration.py):**
- Lightweight server on port 19998 (module-scoped fixture)
- Runs WebSocket listener in background thread with event loop
- Mocked database (no Postgres)
- Real Registry, ConnectionManager, Router
- Used by async and sync client tests

**E2EServer (test_e2e.py):**
- Similar to TestServer but on port 19999
- Same no-DB mocking pattern
- Supports multiple concurrent clients (MCP, Flame, observer)
- Used for end-to-end scenario testing

**Setup pattern:**
```python
class TestServer:
    def __init__(self, port: int):
        self.port = port
        self.url = f"ws://localhost:{port}"
        self.registry = Registry.default()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        """Start the server in a background thread."""
        self._thread = threading.Thread(
            target=self._run, name="forge-test-server", daemon=True
        )
        self._thread.start()
        assert self._ready.wait(timeout=10), "Test server did not start in time"

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._patch_db()
        # ... create server, start WebSocket, set ready
        self._loop.run_forever()

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._server.stop(), self._loop
            ).result(timeout=5)
            self._loop.call_soon_threadsafe(self._loop.stop)
```

---

*Testing analysis: 2026-04-14*
