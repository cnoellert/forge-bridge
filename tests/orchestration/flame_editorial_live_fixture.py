"""Trusted empty-decoration Flame sequence fixture for live editorial UATs."""

from __future__ import annotations

import copy

from forge_core.traffik.tests.test_editing_federation import (
    _flame_sequence_data,
)


def trusted_live_flame_sequence_data() -> dict:
    """Return the federation fixture with every live read channel observed."""

    data = copy.deepcopy(_flame_sequence_data())
    data["markers"] = []
    data["marker_extraction_errors"] = []
    for version in data["versions"]:
        for track in version["tracks"]:
            track.update(
                transition_scope="video_track",
                transitions=[],
                transition_extraction_errors=[],
            )
            for segment in track["segments"]:
                segment.update(
                    markers=[],
                    marker_extraction_errors=[],
                    timewarp=None,
                    timewarp_observation={
                        "status": "absent",
                        "effect_collection_observed": True,
                        "effect_count": 0,
                        "timewarp_effect_count": 0,
                        "sample_count": 0,
                        "invalid_sample_count": 0,
                        "sample_index_domain": "segment_record_frame_1_based",
                        "sample_frame_domain": "flame_media_disk_frame",
                        "coordinate_authority": (
                            "provisional_live_proof_pending"
                        ),
                        "mapping_method": "forge_align_disk_frame_v1",
                    },
                    timewarp_extraction_errors=[],
                )
    return data
