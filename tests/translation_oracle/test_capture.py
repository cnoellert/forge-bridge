"""TF.3a Step 2 — capture mapper tests.

Deterministic: exercises the ObservedTrace marker-extraction from real-shaped
CompileBranchOutcome fixtures (no live model/Flame). The load-bearing logic is
the mapping, not the model — a live capture run is a Step 4 concern.
"""
from __future__ import annotations

from forge_bridge.console._chat_compile import CompileBranchOutcome
from forge_bridge.translation_oracle import (
    SCHEMA_VERSION,
    observed_trace_from_compile_outcome,
    validate_translation_case,
)


def _outcome(
    regime,
    *,
    steps=None,
    chain_body=None,
    compile_error=None,
    salvage_applied=False,
    salvage_reason=None,
):
    return CompileBranchOutcome(
        regime=regime,
        steps=steps or [],
        preview=None,
        chain_body=chain_body,
        compile_error=compile_error,
        salvage_applied=salvage_applied,
        salvage_reason=salvage_reason,
    )


def _is_valid_label_free(observed):
    """The mapped ObservedTrace must be a valid label-free TranslationCase."""
    validate_translation_case({"schema_version": SCHEMA_VERSION, "observed": observed})


def test_non_mutating_read_maps_to_answered():
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome(
            "compiled_non_mutating",
            steps=["flame_inspect_sequence_versions sequence_name=30sec_21"],
            chain_body={"status": "success", "chain": [], "error": None},
        ),
        tools_filtered=1,
    )
    assert obs["outcome"] == "answered"
    assert obs["observed_graph"] == ["flame_inspect_sequence_versions sequence_name=30sec_21"]
    assert obs["tool_selected"] == "flame_inspect_sequence_versions"
    assert obs["tool_forced"] is False
    assert obs["tools_filtered"] == 1
    assert obs["abort_reason"] is None
    assert obs["capture_provenance"] == "instrumented-translation"
    _is_valid_label_free(obs)


def test_chain_aborted_surfaces_407_unresolved_as_abort_reason():
    """The :407 honest-decline (UNRESOLVED_REQUIRED_PARAM) must reach abort_reason
    — the decline-vs-misroute discriminator depends on it."""
    chain_body = {
        "status": "error",
        "chain": [],
        "error": {
            "code": "CHAIN_STEP_FAILED",
            "original_error": {"type": "UNRESOLVED_REQUIRED_PARAM"},
        },
    }
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome("chain_aborted", steps=["flame_rename_shots prefix=noise"],
                         chain_body=chain_body),
        tools_filtered=1,
    )
    assert obs["outcome"] == "chain_aborted"
    assert obs["abort_reason"] == "UNRESOLVED_REQUIRED_PARAM"
    _is_valid_label_free(obs)


def test_mutating_preview_maps_to_preview_emitted():
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome("compiled_mutating_preview",
                         steps=["flame_rename_shots sequence_name=30sec_21 prefix=noise", "commit"]),
        tools_filtered=2,
    )
    assert obs["outcome"] == "preview_emitted"
    assert obs["tool_selected"] == "flame_rename_shots"
    _is_valid_label_free(obs)


def test_compile_error_maps_reason_from_exception_type():
    class CompileUnresolvableIntent(RuntimeError):
        pass

    obs = observed_trace_from_compile_outcome(
        outcome=_outcome("compile_error", compile_error=CompileUnresolvableIntent("x")),
        tools_filtered=5,
    )
    assert obs["outcome"] == "compile_error"
    assert obs["abort_reason"] == "CompileUnresolvableIntent"
    assert obs["observed_graph"] == []
    assert obs["tool_selected"] is None
    _is_valid_label_free(obs)


def test_compile_error_with_preserved_detached_args_is_classifiable():
    class CompileInvalidChainShape(RuntimeError):
        pass

    obs = observed_trace_from_compile_outcome(
        outcome=_outcome(
            "compile_error",
            steps=[
                "flame_rename_shots prefix=tv",
                '{"params": {"sequence_name": "30sec_21"}}',
            ],
            compile_error=CompileInvalidChainShape("detached args"),
        ),
        tools_filtered=1,
    )

    assert obs["outcome"] == "compile_error"
    assert obs["observed_graph"] == [
        "flame_rename_shots prefix=tv",
        '{"params": {"sequence_name": "30sec_21"}}',
    ]
    assert obs["well_formed"] is False
    assert obs["well_formed_reason"] == "detached_args"
    assert obs["abort_reason"] == "CompileInvalidChainShape"
    _is_valid_label_free(obs)


def test_observed_resolved_params_reflect_the_partial_extractor():
    """The mapper exposes what the PRODUCTION (partial) extractor captured — not
    an idealized parse. Grounded against TF.1-CONTRACT §3: extract_explicit_params
    recognizes only UUID project_id today, NOT general key=value. So for a rename
    step the captured params are EMPTY — and that emptiness IS the defect-#2
    extraction signal (key 'sequence_name' in step-text, absent from params) that
    the extraction detector keys on. Capturing the idealized parse would hide the
    very defect the oracle exists to measure."""
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome("compiled_non_mutating",
                         steps=["flame_rename_shots sequence_name=30sec_21 prefix=noise"]),
        tools_filtered=1,
    )
    # partial extractor captures nothing here -> the extraction-gap signal
    assert obs["observed_resolved_params"]["0"] == {}

    # positive control: the recognized form (UUID project_id) IS captured
    obs2 = observed_trace_from_compile_outcome(
        outcome=_outcome("compiled_non_mutating",
                         steps=["forge_get_project project_id=7f1e2d3c-1111-2222-3333-444455556666"]),
        tools_filtered=1,
    )
    assert obs2["observed_resolved_params"]["0"] == {
        "project_id": "7f1e2d3c-1111-2222-3333-444455556666"
    }


def test_tool_forced_is_settable_for_the_forced_path():
    """Forced-path capture (additive follow-on) sets tool_forced=True."""
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome("compiled_non_mutating", steps=["forge_get_project"]),
        tools_filtered=1,
        tool_forced=True,
    )
    assert obs["tool_forced"] is True
    _is_valid_label_free(obs)


def test_salvage_observability_maps_from_compile_outcome():
    obs = observed_trace_from_compile_outcome(
        outcome=_outcome(
            "compiled_mutating_preview",
            steps=[
                'flame_rename_shots {"params": {"sequence_name": "30sec_21"}}',
                "commit",
            ],
            salvage_applied=True,
            salvage_reason="detached_args",
        ),
        tools_filtered=1,
    )

    assert obs["salvage_applied"] is True
    assert obs["original_reason"] == "detached_args"
    _is_valid_label_free(obs)
