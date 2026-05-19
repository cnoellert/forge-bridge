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


def test_resolves_rename_numeric_directives_with_types():
    resolved = resolve_query_entities(
        "Rename the shots on 30sec 21 using prefix genesis "
        "4-digit padding increment 10 starting at 10",
    )
    params = resolved_entity_params(resolved)

    assert params == {
        "sequence_name": "30sec_21",
        "prefix": "genesis",
        "padding": 4,
        "increment": 10,
        "start": 10,
    }
    assert isinstance(params["prefix"], str)
    assert isinstance(params["padding"], int)
    assert isinstance(params["increment"], int)
    assert isinstance(params["start"], int)
    assert resolved["padding"]["source"] == "4-digit padding"
    assert resolved["increment"]["source"] == "increment 10"
    assert resolved["start"]["source"] == "starting at 10"


def test_resolves_rename_directive_phrase_variants():
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 with prefix genesis"),
    )["prefix"] == "genesis"
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 padding 4"),
    )["padding"] == 4
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 padding of 4"),
    )["padding"] == 4
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 increment of 10"),
    )["increment"] == 10
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 start at 10"),
    )["start"] == 10
    assert resolved_entity_params(
        resolve_query_entities("Rename shots on 30sec 21 starts at 10"),
    )["start"] == 10


def test_existing_rename_to_prefix_path_still_resolves():
    resolved = resolve_query_entities("Rename the shots to genesis")

    assert resolved["prefix"] == {"value": "genesis", "source": "genesis"}


def test_bare_rename_does_not_emit_optional_directives():
    params = resolved_entity_params(
        resolve_query_entities("Rename the shots on 30sec 21"),
    )

    assert params["sequence_name"] == "30sec_21"
    assert "prefix" not in params
    assert "padding" not in params
    assert "increment" not in params
    assert "start" not in params


def test_resolved_entity_params_preserves_string_and_int_types():
    params = resolved_entity_params(
        resolve_query_entities(
            "Rename the shots on 30sec 21 with prefix genesis padding 4",
        ),
    )

    assert isinstance(params["prefix"], str)
    assert isinstance(params["padding"], int)


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
