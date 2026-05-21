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


def test_resolves_reel_contents_on_phrase():
    resolved = resolve_query_entities("list reel contents on Sequences")

    assert resolved["reel_name"] == {
        "value": "Sequences",
        "source": "Sequences",
    }


def test_resolves_reel_contents_without_preposition_phrase():
    resolved = resolve_query_entities("reel contents Sequences")

    assert resolved["reel_name"] == {
        "value": "Sequences",
        "source": "Sequences",
    }


def test_resolves_reel_contents_of_phrase():
    resolved = resolve_query_entities("reel contents of Sequences")

    assert resolved["reel_name"] == {
        "value": "Sequences",
        "source": "Sequences",
    }


def test_resolves_library_contents_on_phrase():
    resolved = resolve_query_entities("list library contents on Commercials")

    assert resolved["library_name"] == {
        "value": "Commercials",
        "source": "Commercials",
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


def test_resolves_preview_intent_as_dry_run_modifier():
    params = resolved_entity_params(
        resolve_query_entities(
            "Preview rename shots on 30sec 21 using prefix genesis",
        ),
    )

    assert params["sequence_name"] == "30sec_21"
    assert params["prefix"] == "genesis"
    assert params["dry_run"] is True
    assert isinstance(params["dry_run"], bool)


def test_resolves_ecological_preview_intent_phrases():
    assert resolved_entity_params(
        resolve_query_entities(
            "Show me what would change if we rename shots on 30sec 21 "
            "with prefix genesis",
        ),
    )["dry_run"] is True
    assert resolved_entity_params(
        resolve_query_entities(
            "What would happen if we rename shots on 30sec 21 "
            "with prefix genesis",
        ),
    )["dry_run"] is True


def test_resolves_dry_run_and_commit_as_explicit_intent_modifiers():
    dry_run_params = resolved_entity_params(
        resolve_query_entities("rename shots on 30sec 21 with prefix genesis dry_run"),
    )
    commit_params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix genesis commit"),
    )

    assert dry_run_params["dry_run"] is True
    assert commit_params["dry_run"] is False


def test_commit_in_prefix_value_position_does_not_fire_commit_directive():
    params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix commit"),
    )

    assert params["prefix"] == "commit"
    assert "dry_run" not in params


def test_commit_directive_fires_only_in_terminal_directive_position():
    params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix genesis commit"),
    )

    assert params["prefix"] == "genesis"
    assert params["dry_run"] is False


def test_dry_run_directive_fires_only_in_modifier_position():
    params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix genesis dry_run"),
    )

    assert params["prefix"] == "genesis"
    assert params["dry_run"] is True


def test_dry_run_in_prefix_value_position_does_not_fire_modifier():
    params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix dry_run"),
    )

    assert params["prefix"] == "dry_run"
    assert "dry_run" not in params


def test_spaced_dry_run_directive_fires_in_terminal_modifier_position():
    params = resolved_entity_params(
        resolve_query_entities("rename shots with prefix genesis dry run"),
    )

    assert params["prefix"] == "genesis"
    assert params["dry_run"] is True


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


def test_resolver_projects_filter_predicate_as_structured_ast():
    params = resolved_entity_params(resolve_query_entities("filter(duration > 1)"))

    assert params["filter_predicate"] == {
        "field": "duration",
        "operator": ">",
        "value": 1,
    }


def test_resolver_projects_if_gate_predicate_as_structured_ast():
    params = resolved_entity_params(resolve_query_entities("if(proposed_changes exists)"))

    assert params["if_predicate"] == {
        "field": "proposed_changes",
        "operator": "exists",
    }


def test_resolver_projects_unknown_if_gate_as_structured_error():
    params = resolved_entity_params(resolve_query_entities("if(only the changed shots)"))

    assert params["if_error"]["code"] == "unknown_predicate"
    assert "Could not parse filter predicate" in params["if_error"]["message"]


def test_resolver_projects_unknown_filter_as_structured_error():
    params = resolved_entity_params(
        resolve_query_entities("filter only the comp segments"),
    )

    assert params["filter_error"]["code"] == "unknown_predicate"
    assert "Could not parse filter predicate" in params["filter_error"]["message"]


def test_resolver_does_not_treat_keyed_value_only_as_filter():
    params = resolved_entity_params(resolve_query_entities("list versions project_name=Only"))

    assert "filter_predicate" not in params
    assert "filter_error" not in params


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
