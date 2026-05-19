from forge_bridge.llm.resolver import (
    enrich_user_message_with_resolved_entities,
    resolve_query_entities,
    resolved_entity_params,
)


def test_resolves_spaced_sequence_name_to_canonical_form():
    resolved = resolve_query_entities(
        "Give me the versions on the sequence 30sec 21",
    )

    assert resolved["sequence_name"] == {
        "value": "30sec_21",
        "source": "30sec 21",
    }
    assert resolved_entity_params(resolved)["sequence_name"] == "30sec_21"


def test_resolves_compact_sequence_name_to_canonical_form():
    resolved = resolve_query_entities("Get the segments on 30sec21")

    assert resolved["sequence_name"] == {
        "value": "30sec_21",
        "source": "30sec21",
    }


def test_resolves_reel_name_with_same_normalization_pattern():
    resolved = resolve_query_entities("Use reel Main Reel")

    assert resolved["reel_name"] == {
        "value": "Main_Reel",
        "source": "Main Reel",
    }


def test_passes_operator_prefix_through_for_rename_query():
    resolved = resolve_query_entities(
        "Rename the shots on 30sec 21 to genesis, 4-digit padding, by 10s",
    )

    assert resolved["sequence_name"]["value"] == "30sec_21"
    assert resolved["prefix"] == {"value": "genesis", "source": "genesis"}


def test_enrichment_block_uses_resolved_context_shape():
    resolved = resolve_query_entities(
        "Preview the start frames for the sequence 30sec 21",
    )

    enriched = enrich_user_message_with_resolved_entities(
        "Preview the start frames for the sequence 30sec 21",
        resolved,
    )

    assert enriched.startswith("[Resolved entities from query]\n")
    assert 'sequence_name: "30sec_21"  (normalized from "30sec 21")' in enriched
    assert "User query: Preview the start frames" in enriched
