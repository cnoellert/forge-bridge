"""Bridge-owned request reference inventory and feasibility policy."""

from __future__ import annotations

from pathlib import Path

from forge_contracts.generation import ReferenceRequirementSpec

from forge_bridge.orchestration.request_reference_inventory import (
    RequestReferenceInventory,
    evaluate_reference_requirements,
)


def test_inventory_normalizes_contract_roles_assignments_and_unique_references() -> None:
    inventory = RequestReferenceInventory.from_inputs_catalog(
        {
            "inputs": [
                {
                    "artifact_id": "image-1",
                    "artifact_type": "image/png",
                    "payload_id": "payload-1",
                    "locator": {
                        "reference_id": "locator-1",
                        "kind": "url",
                        "role": "identity",
                        "target": "https://example.test/frame.png",
                    },
                },
                {
                    # Repeating the canonical artifact does not inflate count.
                    "artifact_id": "image-1",
                    "artifact_type": "image",
                    "metadata": {"role": "style"},
                },
                {
                    "artifact_id": "audio-1",
                    "artifact_type": "audio/wav",
                    "metadata": {"roles": ["audio"]},
                },
            ],
            "role_assignments": {
                "structural": "payload-1",
                "source_truth_anchor": [{"reference_id": "locator-1"}],
                "motion": "missing-artifact",
            },
        }
    )

    assert inventory.reference_ids == frozenset({"image-1", "audio-1"})
    assert inventory.reference_count == 2
    assert inventory.present_roles == frozenset(
        {"audio", "identity", "source_truth_anchor", "structural", "style"}
    )
    assert inventory.first_frame_reference_ids == frozenset({"image-1"})
    assert inventory.has_first_frame is True


def test_inventory_does_not_repurpose_unassigned_image_as_first_frame() -> None:
    inventory = RequestReferenceInventory.from_inputs_catalog(
        {
            "inputs": [
                {
                    "artifact_id": "identity-1",
                    "artifact_type": "image",
                    "metadata": {"role": "identity"},
                }
            ],
            "role_assignments": {},
        }
    )

    assert inventory.present_roles == frozenset({"identity"})
    assert inventory.has_first_frame is False


def test_inventory_accepts_explicit_first_frame_attestation() -> None:
    inventory = RequestReferenceInventory.from_inputs_catalog(
        {
            "inputs": [
                {
                    "artifact_id": "frame-1",
                    "artifact_type": "media",
                    "metadata": {"is_first_frame": True},
                }
            ]
        }
    )

    assert inventory.first_frame_reference_ids == frozenset({"frame-1"})


def test_inventory_recognizes_direct_tool_image_path_shape() -> None:
    inventory = RequestReferenceInventory.from_inputs_catalog(
        {
            "inputs": [
                {
                    "artifact_id": "frame-1",
                    "artifact_type": "media",
                    "metadata": {
                        "role": "structural",
                        "url": "https://example.test/frame.exr?download=1",
                    },
                }
            ]
        }
    )

    assert inventory.has_first_frame is True


def test_reference_policy_reports_every_hard_block_reason() -> None:
    inventory = RequestReferenceInventory(
        reference_ids=frozenset({"identity-1", "identity-2"}),
        present_roles=frozenset({"identity"}),
    )

    result = evaluate_reference_requirements(
        ReferenceRequirementSpec(
            required_roles=["audio", "structural"],
            max_references=1,
            requires_first_frame=True,
        ),
        inventory,
    )

    assert result.feasible is False
    assert result.missing_roles == ("audio", "structural")
    assert result.exceeds_reference_limit is True
    assert result.missing_first_frame is True
    assert result.reason_codes == (
        "missing_required_roles",
        "reference_limit_exceeded",
        "input_first_frame_missing",
    )


def test_reference_policy_accepts_exact_declared_limit() -> None:
    inventory = RequestReferenceInventory(
        reference_ids=frozenset({"frame-1"}),
        present_roles=frozenset({"structural"}),
        first_frame_reference_ids=frozenset({"frame-1"}),
    )

    result = evaluate_reference_requirements(
        ReferenceRequirementSpec(
            required_roles=["structural"],
            max_references=1,
            requires_first_frame=True,
        ),
        inventory,
    )

    assert result.feasible is True
    assert result.reason_codes == ()


def test_inventory_module_does_not_import_generator_oracle() -> None:
    source = Path("forge_bridge/orchestration/request_reference_inventory.py").read_text(
        encoding="utf-8"
    )

    assert "forge_generators" not in source
