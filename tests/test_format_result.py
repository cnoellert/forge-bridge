import json

import pytest

from forge_bridge.formatters import format_result as format_module
from forge_bridge.formatters.format_result import (
    FormatResultInput,
    build_format_prompt,
    condense_payload,
    format_result,
)


def test_condense_strips_hashes_frames_and_non_email_paths():
    condensed = condense_payload(
        {
            "sequence": "30sec_21",
            "code_hash": "abc123",
            "file_path": "/Volumes/show/plate.exr",
            "record_in": 1001,
            "segments": [
                {
                    "shot_name": "genesis_0010",
                    "source_path": "/Volumes/show/source.exr",
                    "start_frame": 1001,
                    "_debug": "noise",
                },
            ],
        },
        "table",
    )

    assert condensed.stripped["hashes"] == 1
    assert condensed.stripped["paths"] == 2
    assert condensed.stripped["frame_numbers"] == 2
    assert condensed.stripped["internal"] == 1
    text = json.dumps(condensed.data)
    assert "abc123" not in text
    assert "/Volumes/show" not in text
    assert "1001" not in text
    assert "genesis_0010" in text


def test_condense_keeps_paths_for_email_but_never_hashes():
    condensed = condense_payload(
        {
            "file_path": "/Volumes/show/plate.exr",
            "sha256": "secret-hash",
        },
        "email",
    )

    assert condensed.data == {"file_path": "/Volumes/show/plate.exr"}
    assert condensed.stripped["hashes"] == 1


def test_condense_hard_caps_cloud_payload(caplog):
    data = {"segments": [{"shot_name": f"shot_{i:04d}"} for i in range(3000)]}

    with caplog.at_level("WARNING", logger="forge_bridge.formatters.format_result"):
        condensed = condense_payload(data, "bullets")

    assert condensed.truncated is True
    assert condensed.data["truncated"] is True
    assert len(json.dumps(condensed.data)) <= format_module._MAX_CLOUD_CHARS
    assert "condensation truncated payload" in caplog.text


def test_build_prompt_names_vfx_context_and_audit():
    prompt = build_format_prompt(
        format_class="email",
        condensed_payload={"segments": [{"shot_name": "genesis_0010"}]},
        stripped={"hashes": 1},
        truncated=False,
    )

    assert "VFX production data from Flame" in prompt
    assert "Format class: email" in prompt
    assert "stripped={'hashes': 1}" in prompt
    assert "genesis_0010" in prompt


@pytest.mark.asyncio
async def test_format_result_calls_cloud_router_and_warns_once(monkeypatch):
    class FakeRouter:
        def __init__(self):
            self.calls = []

        async def acomplete(self, prompt, *, sensitive, temperature):
            self.calls.append({
                "prompt": prompt,
                "sensitive": sensitive,
                "temperature": temperature,
            })
            return "Producer-ready summary"

    router = FakeRouter()
    format_module._reset_for_tests()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("forge_bridge.llm.router.get_router", lambda: router)

    first = await format_result(
        FormatResultInput(data={"sequence": "30sec_21"}, format="email"),
    )
    second = await format_result(
        FormatResultInput(data={"sequence": "30sec_21"}, format="email"),
    )

    assert first.startswith("format_result sends condensed data")
    assert first.endswith("Producer-ready summary")
    assert second == "Producer-ready summary"
    assert router.calls[0]["sensitive"] is False
    assert router.calls[0]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_format_result_requires_anthropic_api_key(monkeypatch):
    format_module._reset_for_tests()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="requires ANTHROPIC_API_KEY"):
        await format_result(
            FormatResultInput(data={"sequence": "30sec_21"}, format="email"),
        )
