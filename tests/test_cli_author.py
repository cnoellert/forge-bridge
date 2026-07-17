from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import typer
from typer.testing import CliRunner

from forge_bridge.cli.author import author_cmd, author_targets_cmd, qc_cmd


runner = CliRunner()


@dataclass(frozen=True)
class _Result:
    run_id: uuid.UUID
    artifact_id: uuid.UUID
    text: str = "draft"
    lifecycle_stage: str = "execution"
    lifecycle_status: str = "paused"

    def to_dict(self):
        return {
            "run_id": str(self.run_id),
            "artifact_id": str(self.artifact_id),
            "text": self.text,
            "lifecycle_stage": self.lifecycle_stage,
            "lifecycle_status": self.lifecycle_status,
        }


@dataclass(frozen=True)
class _Approval:
    run_id: uuid.UUID
    lifecycle_stage: str = "audit"
    lifecycle_status: str = "active"

    def to_dict(self):
        return {
            "run_id": str(self.run_id),
            "lifecycle_stage": self.lifecycle_stage,
            "lifecycle_status": self.lifecycle_status,
        }


def _app() -> typer.Typer:
    app = typer.Typer()
    app.command("author")(author_cmd)
    app.command("author-targets")(author_targets_cmd)
    app.command("qc")(qc_cmd)

    @app.command("__noop__", hidden=True)
    def _noop() -> None:
        pass

    return app


def test_author_json_is_pure(monkeypatch):
    run_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    async def _start(intent):
        assert intent == "write a beat"
        return _Result(run_id=run_id, artifact_id=artifact_id, text="hello")

    monkeypatch.setattr("forge_bridge.orchestration.manual_qc.start_author", _start)

    result = runner.invoke(_app(), ["author", "write a beat", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["run_id"] == str(run_id)
    assert payload["data"]["text"] == "hello"


def test_author_target_flags_flow_to_manual_qc(monkeypatch):
    run_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    async def _start(intent, **kwargs):
        assert intent == "write motion"
        assert kwargs == {
            "target_operator": "generate_video_from_image",
            "target_backend": "comfyui.seedance_2_0",
        }
        return _Result(run_id=run_id, artifact_id=artifact_id)

    monkeypatch.setattr("forge_bridge.orchestration.manual_qc.start_author", _start)

    result = runner.invoke(
        _app(),
        [
            "author",
            "write motion",
            "--target-operator",
            "generate_video_from_image",
            "--target-backend",
            "comfyui.seedance_2_0",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["ok"] is True


def test_author_backend_requires_operator(monkeypatch):
    result = runner.invoke(
        _app(),
        ["author", "write motion", "--target-backend", "comfyui.seedance_2_0", "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["error"]["code"] == "invalid_args"


def test_author_targets_json_lists_discovered_coordinates(monkeypatch):
    class _Option:
        def to_dict(self):
            return {
                "target": {
                    "operator_id": "generate_still",
                    "backend_identity_triple": {
                        "surface": "higgsfield-cli",
                        "path": "nano_banana_2",
                        "auth_mechanism": "no-auth",
                        "revision": "consumer-cli-v1",
                    },
                },
                "backend_id": "higgsfield-cli.nano_banana_2",
                "tool_id": "forge_generators.generate_still.higgsfield-cli.nano_banana_2",
                "label": None,
                "summary": "generate_still via nano_banana_2",
            }

    async def _discover(*, operator_id):
        assert operator_id == "generate_still"
        return (_Option(),)

    monkeypatch.setattr(
        "forge_bridge.cli.author.discover_authoring_target_options",
        _discover,
    )

    result = runner.invoke(
        _app(),
        ["author-targets", "--operator", "generate_still", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"]["count"] == 1
    assert payload["data"]["targets"][0]["backend_id"] == (
        "higgsfield-cli.nano_banana_2"
    )


def test_qc_note_json_calls_revise(monkeypatch):
    run_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    async def _revise(got_run_id, note):
        assert got_run_id == str(run_id)
        assert note == "tighten it"
        return _Result(run_id=uuid.uuid4(), artifact_id=artifact_id, text="revised")

    monkeypatch.setattr("forge_bridge.orchestration.manual_qc.revise", _revise)

    result = runner.invoke(_app(), ["qc", str(run_id), "tighten it", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["text"] == "revised"


def test_qc_approve_json_calls_approve(monkeypatch):
    run_id = uuid.uuid4()

    async def _approve(got_run_id, *, actor):
        assert got_run_id == str(run_id)
        assert actor == "reviewer"
        return _Approval(run_id=run_id)

    monkeypatch.setattr("forge_bridge.orchestration.manual_qc.approve", _approve)

    result = runner.invoke(
        _app(),
        ["qc", str(run_id), "--approve", "--actor", "reviewer", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["lifecycle_stage"] == "audit"


def test_qc_requires_note_unless_approving():
    result = runner.invoke(_app(), ["qc", str(uuid.uuid4()), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["error"]["code"] == "invalid_args"
