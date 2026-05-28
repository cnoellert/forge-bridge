"""End-to-end smoke tests for Phase 4B orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.event_consumer import GraphEngineEventConsumer
from forge_bridge.orchestration.manifest import ProvenanceManifestAssembler
from forge_bridge.orchestration.replay import (
    RUN_LINEAGE_REL_KEYS,
    ReconstructionRequest,
    ReplayEngine,
)
from forge_bridge.orchestration.worker import GenerationPoller
from forge_bridge.store.orchestration_promotion_ledger_repo import (
    OrchestrationPromotionLedgerRepo,
)
from forge_bridge.store.repo import RelationshipRepo

from tests.smoke_helpers import (
    build_smoke_setup,
    default_failed_driver_script,
    default_happy_driver_script,
    drive_consumer_to_audit,
    drive_execution_to_terminal,
    emit_audit_and_promote,
    insert_submitted_artifacts,
    lifecycle_for,
    make_planner,
    run_events,
    seed_smoke_entities,
    stage_to_execution_via_planner,
    stage_to_routing,
    transition_publish_and_assemble_manifest,
)


async def _drive_from_execution_to_publish(
    session_factory,
    session,
    *,
    fixtures,
    ctx,
    artifact_count: int = 2,
) -> tuple[uuid.UUID, object]:
    artifact_ids = await insert_submitted_artifacts(
        session,
        run_id=ctx.run_id,
        count=artifact_count,
        rule_snapshot_id=ctx.rule_snapshot_id,
    )
    await session.commit()

    poller = GenerationPoller(session_factory, fixtures.driver_registry)
    terminal_events = await drive_execution_to_terminal(
        session_factory, poller=poller, artifact_ids=artifact_ids
    )

    async with session_factory() as post_session:
        engine = GraphEngine(post_session)
        consumer = GraphEngineEventConsumer(post_session, graph_engine=engine)
        await drive_consumer_to_audit(
            post_session, terminal_events=terminal_events, consumer=consumer
        )
        canonical_id = artifact_ids[0]
        promotion_id = await emit_audit_and_promote(
            post_session,
            ctx=ctx,
            candidate_artifact_id=canonical_id,
            engine=engine,
        )
        assembler = ProvenanceManifestAssembler(post_session)
        manifest = await transition_publish_and_assemble_manifest(
            post_session,
            ctx=ctx,
            promotion_id=promotion_id,
            engine=engine,
            assembler=assembler,
        )
        await post_session.commit()
    return canonical_id, manifest


async def _drive_run_to_publish(
    session_factory,
    session,
    *,
    fixtures,
    ctx,
    artifact_count: int = 2,
) -> tuple[uuid.UUID, object]:
    engine = GraphEngine(session)
    planner = make_planner(session, fixtures)
    await stage_to_routing(session, ctx=ctx, engine=engine)
    await stage_to_execution_via_planner(
        session, ctx=ctx, engine=engine, planner=planner
    )
    artifact_ids = await insert_submitted_artifacts(
        session,
        run_id=ctx.run_id,
        count=artifact_count,
        rule_snapshot_id=ctx.rule_snapshot_id,
    )
    await session.commit()

    poller = GenerationPoller(session_factory, fixtures.driver_registry)
    terminal_events = await drive_execution_to_terminal(
        session_factory, poller=poller, artifact_ids=artifact_ids
    )

    async with session_factory() as post_session:
        engine = GraphEngine(post_session)
        consumer = GraphEngineEventConsumer(post_session, graph_engine=engine)
        await drive_consumer_to_audit(
            post_session, terminal_events=terminal_events, consumer=consumer
        )
        canonical_id = artifact_ids[0]
        promotion_id = await emit_audit_and_promote(
            post_session,
            ctx=ctx,
            candidate_artifact_id=canonical_id,
            engine=engine,
        )
        assembler = ProvenanceManifestAssembler(post_session)
        manifest = await transition_publish_and_assemble_manifest(
            post_session,
            ctx=ctx,
            promotion_id=promotion_id,
            engine=engine,
            assembler=assembler,
        )
        await post_session.commit()
    return canonical_id, manifest


async def test_smoke_happy_path(session_factory) -> None:
    fixtures = build_smoke_setup()
    async with session_factory() as session:
        ctx = await seed_smoke_entities(session)
        fixtures.driver.set_script(
            default_happy_driver_script(rule_snapshot_id=ctx.rule_snapshot_id)
        )
        canonical_id, manifest = await _drive_run_to_publish(
            session_factory, session, fixtures=fixtures, ctx=ctx
        )
        lifecycle = await lifecycle_for(session, ctx.run_id)
        history = await OrchestrationPromotionLedgerRepo(session).get_history(
            ctx.shot_id
        )
        run_id = ctx.run_id
        intent_id = ctx.intent_id
        shot_id = ctx.shot_id

    assert lifecycle.current_stage == "publish"
    assert lifecycle.status == "completed"
    assert len(history) == 1
    assert manifest.attributes["canonical_artifact_id"] == str(canonical_id)
    assert manifest.attributes["run_id"] == str(run_id)
    assert manifest.attributes["intent_id"] == str(intent_id)
    bundled = manifest.attributes["snapshots_bundled_by_content"]["rule_snapshot"]
    assert bundled is not None
    assert bundled["body"]["source_ref"] == "methodology/smoke"
    superseded = manifest.attributes["full_lineage"]["superseded_within_run"]
    assert len(superseded) == 1
    assert manifest.attributes["cost_summary"]["total_by_currency"]["USD"] == 10

    async with session_factory() as session:
        events = await run_events(session, run_id)
    assert "run_created" in events
    assert events.count("stage_advanced") >= 4
    assert "lock_intent" in events
    assert "promote_candidate" in events


async def test_smoke_replay(session_factory) -> None:
    fixtures = build_smoke_setup()
    async with session_factory() as session:
        ctx = await seed_smoke_entities(session)
        fixtures.driver.set_script(
            default_happy_driver_script(rule_snapshot_id=ctx.rule_snapshot_id)
        )
        _, manifest_1 = await _drive_run_to_publish(
            session_factory, session, fixtures=fixtures, ctx=ctx
        )
        await session.commit()
        manifest_1_id = manifest_1.id
        manifest_1_hash = manifest_1.content_hash
        source_run_id = ctx.run_id
        shot_id = ctx.shot_id
        rule_snapshot_id = ctx.rule_snapshot_id
        partial_snapshot_id = ctx.partial_fidelity_snapshot_id

    async with session_factory() as session:
        refresh = await seed_smoke_entities(session)
        fixtures2 = build_smoke_setup()
        fixtures2.driver.set_script(
            default_happy_driver_script(
                rule_snapshot_id=refresh.rule_snapshot_id,
                cost=12.0,
            )
        )
        replay_engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=make_planner(session, fixtures2),
        )
        request = ReconstructionRequest(
            request_id=uuid.uuid4(),
            kind="replay",
            source_run_id=source_run_id,
            pinning_mode="refresh_current",
            authored_at=datetime.now(timezone.utc),
        )
        replay_lifecycle = await replay_engine.reconstruct(
            request,
            current_rule_snapshot_id=refresh.rule_snapshot_id,
            current_partial_fidelity_snapshot_id=refresh.partial_fidelity_snapshot_id,
            current_capability_snapshot_id=None,
        )
        new_run_id = replay_lifecycle.run_id
        edges = await RelationshipRepo(session).get_outgoing(
            new_run_id, RUN_LINEAGE_REL_KEYS["replays_run"]
        )
        assert len(edges) == 1
        assert replay_lifecycle.plan_id is not None
        assert replay_lifecycle.current_stage in {"routing", "execution"}

        refresh.run_id = new_run_id
        refresh.shot_id = shot_id
        refresh.intent_id = replay_lifecycle.intent_id
        refresh.rule_snapshot_id = rule_snapshot_id
        refresh.partial_fidelity_snapshot_id = partial_snapshot_id
        refresh.plan_id = replay_lifecycle.plan_id
        if replay_lifecycle.current_stage == "routing":
            await GraphEngine(session).transition(
                new_run_id,
                to_stage="execution",
                plan_id=replay_lifecycle.plan_id,
                intent_id=replay_lifecycle.intent_id,
            )

        canonical_id, manifest_2 = await _drive_from_execution_to_publish(
            session_factory,
            session,
            fixtures=fixtures2,
            ctx=refresh,
            artifact_count=1,
        )
        history = await OrchestrationPromotionLedgerRepo(session).get_history(shot_id)
        await session.commit()

    assert manifest_2.content_hash != manifest_1_hash
    assert manifest_2.id != manifest_1_id
    assert len(history) == 2
    assert canonical_id is not None


async def test_smoke_remediation(session_factory) -> None:
    fixtures = build_smoke_setup(driver_script=default_failed_driver_script())
    async with session_factory() as session:
        ctx = await seed_smoke_entities(session)
        engine = GraphEngine(session)
        planner = make_planner(session, fixtures)
        await stage_to_routing(session, ctx=ctx, engine=engine)
        await stage_to_execution_via_planner(
            session, ctx=ctx, engine=engine, planner=planner
        )
        artifact_ids = await insert_submitted_artifacts(
            session,
            run_id=ctx.run_id,
            count=2,
            rule_snapshot_id=ctx.rule_snapshot_id,
        )
        await session.commit()
        poller = GenerationPoller(session_factory, fixtures.driver_registry)
        terminal_events = await drive_execution_to_terminal(
            session_factory, poller=poller, artifact_ids=artifact_ids
        )
        async with session_factory() as post_session:
            engine = GraphEngine(post_session)
            consumer = GraphEngineEventConsumer(post_session, graph_engine=engine)
            result = await drive_consumer_to_audit(
                post_session, terminal_events=terminal_events, consumer=consumer
            )
            paused = await lifecycle_for(post_session, ctx.run_id)
            await engine.apply_decision_event(
                ctx.run_id,
                "approve_remediation",
                {"remediation_entry": "replan_same_intent"},
            )
            await post_session.commit()

        failed_run_id = ctx.run_id
        shot_id = ctx.shot_id

    assert result.action == "paused_zero_candidates"
    assert paused.status == "paused"
    assert paused.block["kind"] == "awaiting_decision"
    assert paused.block["decision_type"] == "approve_remediation"

    fixtures_ok = build_smoke_setup()
    async with session_factory() as session:
        refresh = await seed_smoke_entities(session)
        refresh.shot_id = shot_id
        fixtures_ok.driver.set_script(
            default_happy_driver_script(rule_snapshot_id=refresh.rule_snapshot_id)
        )
        replay_engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=make_planner(session, fixtures_ok),
        )
        request = ReconstructionRequest(
            request_id=uuid.uuid4(),
            kind="remediation",
            source_run_id=failed_run_id,
            remediation_entry="replan_same_intent",
            pinning_mode="refresh_current",
            authored_at=datetime.now(timezone.utc),
        )
        replay_lifecycle = await replay_engine.reconstruct(
            request,
            current_rule_snapshot_id=refresh.rule_snapshot_id,
            current_partial_fidelity_snapshot_id=refresh.partial_fidelity_snapshot_id,
            current_capability_snapshot_id=None,
        )
        edges = await RelationshipRepo(session).get_outgoing(
            replay_lifecycle.run_id, RUN_LINEAGE_REL_KEYS["remediates_run"]
        )
        assert len(edges) == 1
        refresh.run_id = replay_lifecycle.run_id
        refresh.intent_id = replay_lifecycle.intent_id
        if replay_lifecycle.current_stage == "routing":
            await GraphEngine(session).transition(
                replay_lifecycle.run_id,
                to_stage="execution",
                plan_id=replay_lifecycle.plan_id,
                intent_id=replay_lifecycle.intent_id,
            )
        canonical_id, manifest = await _drive_from_execution_to_publish(
            session_factory,
            session,
            fixtures=fixtures_ok,
            ctx=refresh,
            artifact_count=1,
        )
        failed_lifecycle = await lifecycle_for(session, failed_run_id)
        await session.commit()

    assert failed_lifecycle.status == "paused"
    record_ids = {
        r.get("record_id")
        for r in manifest.attributes.get("refusal_and_partial_records", [])
    }
    assert "sibling-partial" not in record_ids
    assert manifest.attributes["canonical_artifact_id"] == str(canonical_id)


async def test_consumer_idempotency(session_factory) -> None:
    fixtures = build_smoke_setup(
        driver_script=default_happy_driver_script(rule_snapshot_id=uuid.uuid4())
    )
    async with session_factory() as session:
        ctx = await seed_smoke_entities(session)
        fixtures.driver.set_script(
            default_happy_driver_script(rule_snapshot_id=ctx.rule_snapshot_id)
        )
        engine = GraphEngine(session)
        planner = make_planner(session, fixtures)
        await stage_to_routing(session, ctx=ctx, engine=engine)
        await stage_to_execution_via_planner(
            session, ctx=ctx, engine=engine, planner=planner
        )
        artifact_ids = await insert_submitted_artifacts(session, run_id=ctx.run_id, count=1)
        await session.commit()
        poller = GenerationPoller(session_factory, fixtures.driver_registry)
        terminal_events = await drive_execution_to_terminal(
            session_factory, poller=poller, artifact_ids=artifact_ids
        )
        async with session_factory() as post_session:
            engine = GraphEngine(post_session)
            consumer = GraphEngineEventConsumer(post_session, graph_engine=engine)
            first = await consumer.process_terminal_event(terminal_events[0])
            second = await consumer.process_terminal_event(terminal_events[0])
            await post_session.commit()

    assert first.action == "advanced_to_audit"
    assert second.action == "no_op_already_advanced"
