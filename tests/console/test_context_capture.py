"""S3.2 — /api/v1/context-capture storage-only endpoint."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.context_pressure import read_records


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


@pytest.fixture
def client():
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ManifestService(),
        llm_router=MagicMock(),
    )
    return TestClient(build_console_app(api))


def _payload(**over):
    p = {
        "captured_at": "2026-06-04T12:00:00Z",
        "prompt": "rename this sequence with prefix tv",
        "compiled_graph": ["flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true"],
        "outcome": "preview_emitted",
        # raw carries the live PyAttribute-quoted form — the server-side canonical
        # assembler must unwrap it (single source of truth).
        "world_state_raw": {"timeline": {"active_sequence": "'30sec_edit 21'"}},
        "provenance": {"context_source": "flame", "capture_version": "1",
                       "capture_surface": "python_console", "capture_adapter": "sgtk_console_v1"},
    }
    p.update(over)
    return p


def test_capture_appends_record_with_canonical_assembly(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CONTEXT_PRESSURE_DIR", str(tmp_path))
    r = client.post("/api/v1/context-capture", json=_payload())
    assert r.status_code == 200, r.text
    assert r.json()["data"]["appended"] is True

    records = read_records(corpus_dir=tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec["analysis"] is None  # capture never authors
    assert rec["outcome"] == "preview_emitted"
    # the CANONICAL assembler ran server-side: raw preserved quoted, extracted clean
    assert rec["world_state"]["raw"] == {"timeline": {"active_sequence": "'30sec_edit 21'"}}
    assert rec["world_state"]["extracted"]["flame.active_sequence"] == "30sec_edit 21"


@pytest.mark.parametrize("bad", [
    {"captured_at": ""},
    {"prompt": 123},
    {"compiled_graph": "not-a-list"},
    {"world_state_raw": "not-a-dict"},
    {"provenance": {"capture_version": "1"}},   # missing context_source
    {"outcome": "answered"},                     # not in OUTCOME_VALUES
])
def test_capture_rejects_malformed_payload(client, tmp_path, monkeypatch, bad):
    monkeypatch.setenv("CONTEXT_PRESSURE_DIR", str(tmp_path))
    r = client.post("/api/v1/context-capture", json=_payload(**bad))
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "validation_error"


def test_capture_rejects_non_json(client):
    r = client.post("/api/v1/context-capture", data="not json",
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 400
