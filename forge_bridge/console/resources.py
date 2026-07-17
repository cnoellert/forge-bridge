"""MCP resource + tool shim registration for the v1.3 Artist Console.

Every resource body and every tool-shim body uses `_envelope_json` -- the
SAME serializer the HTTP handlers use -- so MCP resources and HTTP routes
produce byte-identical payloads (D-26). Cross-surface byte-identity is
tested in tests/test_console_mcp_resources.py.

Registration timing (P9-2): this function is called from `_lifespan` AFTER
ManifestService and ConsoleReadAPI are live. NOT at module import -- FastMCP
accepts @mcp.resource/@mcp.tool registration after server construction.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from forge_bridge.console.handlers import _envelope_json

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import ConsoleReadAPI

logger = logging.getLogger(__name__)


def register_console_resources(
    mcp: "FastMCP",
    manifest_service: "ManifestService",
    console_read_api: "ConsoleReadAPI",
    session_factory: Optional["async_sessionmaker"] = None,
) -> None:
    """Register the v1.3 Artist Console MCP surface.

    4 resources:
      forge://manifest/synthesis  -- full synthesis manifest (MFST-02)
      forge://tools               -- all registered tools with provenance (TOOLS-04)
      forge://tools/{name}        -- single tool by name (TOOLS-04 template)
      forge://health              -- full D-14 health body

    2 tool fallback shims for clients without resources support (P-03):
      forge_manifest_read           -- alias for forge://manifest/synthesis (MFST-03)
      forge_tools_read(name=None)   -- alias for forge://tools + tools/{name} (TOOLS-04 shim)
    """

    # Note: manifest_service is accepted for signature stability / future use
    # (e.g. cache invalidation callbacks); Phase 9 reads via console_read_api only.
    _ = manifest_service  # silence unused warning without touching ruff F841

    @mcp.resource("forge://manifest/synthesis", mime_type="application/json")
    async def synthesis_manifest() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.resource("forge://tools", mime_type="application/json")
    async def tools_list() -> str:
        tools = await console_read_api.get_tools()
        return _envelope_json([t.to_dict() for t in tools], total=len(tools))

    @mcp.resource("forge://tools/{name}", mime_type="application/json")
    async def tool_detail(name: str) -> str:
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({
                "error": {
                    "code": "tool_not_found",
                    "message": f"no tool named {name!r}",
                }
            })
        return _envelope_json(tool.to_dict())

    @mcp.resource("forge://health", mime_type="application/json")
    async def health() -> str:
        data = await console_read_api.get_health()
        return _envelope_json(data)

    # -- Tool fallback shims (D-24, P-03) -----------------------------------

    @mcp.tool(
        name="forge_manifest_read",
        description=(
            "Forge: read the synthesis manifest — promoted/probationary tools "
            "and synthesis stats from the learning pipeline.\n\n"
            "Use this tool ONLY when:\n"
            "- the user asks about synthesis state, promotion stats, or the manifest\n"
            "- the user wants to know which synth_* tools have been minted\n\n"
            "Do NOT use this tool for:\n"
            "- listing all tools available to the agent → use forge_tools_read\n"
            "- listing pipeline projects/shots/media → use the matching forge_list_*\n"
            "- Flame state → use flame_* tools\n\n"
            "Alias for `resources/read forge://manifest/synthesis` for MCP "
            "clients that don't support resources (Cursor, Gemini CLI)."
        ),
        annotations={"readOnlyHint": True},
    )
    async def forge_manifest_read() -> str:
        data = await console_read_api.get_manifest()
        return _envelope_json(data)

    @mcp.tool(
        name="forge_tools_read",
        description=(
            "Forge: list MCP tools registered with this forge-bridge instance "
            "(or one tool's detail by name).\n\n"
            "Use this tool ONLY when:\n"
            "- the user asks what tools/actions are available\n"
            "- the user wants the schema of one tool by name\n\n"
            "Do NOT use this tool for:\n"
            "- the synthesis manifest → use forge_manifest_read\n"
            "- pipeline projects/shots/media → use forge_list_*\n"
            "- Flame state → use flame_* tools\n\n"
            "Omit 'name' for the full registry (alias for `forge://tools`); "
            "pass 'name' for per-tool detail (alias for `forge://tools/{name}`)."
        ),
        annotations={"readOnlyHint": True},
    )
    async def forge_tools_read(name: str | None = None) -> str:
        if name is None:
            tools = await console_read_api.get_tools()
            return _envelope_json([t.to_dict() for t in tools], total=len(tools))
        tool = await console_read_api.get_tool(name)
        if tool is None:
            return json.dumps({
                "error": {
                    "code": "tool_not_found",
                    "message": f"no tool named {name!r}",
                }
            })
        return _envelope_json(tool.to_dict())

    # -- Phase 14 (FB-B) — staged-ops MCP tools (4 tools) --------------------
    # Per CONTEXT D-17 revised (Solution C): registered from register_console_resources
    # so closures capture console_read_api and session_factory natively.
    # NO registration in register_builtins() — D-17 revised removes them from there.
    #
    # Lazy import breaks the circular path:
    #   mcp.tools → console.handlers → console.__init__ → console.resources → mcp.tools
    # By importing inside the function (called from _lifespan, not at module load),
    # both modules are fully initialised before either import runs.
    from forge_bridge.mcp.tools import (  # noqa: PLC0415 — intentional deferred import
        ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput,
        RatifyGenerationGrantInput,
        ProposeConsentGrantInput, RatifyConsentGrantInput, BindConsentGrantInput,
        GetConsentGrantInput, WithdrawConsentGrantInput,
        _list_staged_impl, _get_staged_impl, _approve_staged_impl, _reject_staged_impl,
        _ratify_generation_grant_impl,
        _propose_consent_grant_impl, _ratify_consent_grant_impl, _bind_consent_grant_impl,
        _get_consent_grant_impl, _withdraw_consent_grant_impl,
    )

    # Inject input model names into module globals so FastMCP's get_type_hints()
    # can resolve `params: ListStagedInput` annotations on the nested @mcp.tool
    # functions below. Without this, `from __future__ import annotations` keeps
    # the annotations as strings and get_type_hints() looks them up in
    # fn.__globals__ — which is this module, not the local scope of the
    # deferred import. Documented FastMCP requirement for forward-ref tools.
    globals().update({
        "ListStagedInput": ListStagedInput,
        "GetStagedInput": GetStagedInput,
        "ApproveStagedInput": ApproveStagedInput,
        "RejectStagedInput": RejectStagedInput,
        "RatifyGenerationGrantInput": RatifyGenerationGrantInput,
        "ProposeConsentGrantInput": ProposeConsentGrantInput,
        "RatifyConsentGrantInput": RatifyConsentGrantInput,
        "BindConsentGrantInput": BindConsentGrantInput,
        "GetConsentGrantInput": GetConsentGrantInput,
        "WithdrawConsentGrantInput": WithdrawConsentGrantInput,
    })

    @mcp.tool(
        name="forge_list_staged",
        description=(
            "Forge: list staged pipeline operations awaiting approval/execution.\n\n"
            "Reads the staged_operation table — the queue of pending pipeline "
            "mutations (renames, set-startframes, publishes) the operator must "
            "approve before they run. Filters: status, project_id; supports "
            "pagination. status values: proposed|approved|rejected|executed|"
            "failed (default: all).\n\n"
            "Use this tool ONLY when:\n"
            "- the user asks about pending / proposed / staged operations\n"
            "- the user wants the approval queue for the pipeline\n\n"
            "Do NOT use this tool for:\n"
            "- listing pipeline projects/shots/media → use forge_list_projects, etc.\n"
            "- listing Flame libraries → use flame_list_libraries\n"
            "- a single staged operation by ID → use forge_get_staged\n"
            "- the proposed-only snapshot → use forge_staged_pending_read"
        ),
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_list_staged(params: Optional[ListStagedInput] = None) -> str:
        # PR22 Pattern B (see forge_bridge/mcp/tools.py module docstring + docs/TOOL_AUTHORING.md):
        # all fields in ListStagedInput are optional — invoking with `{}` is the
        # canonical "list everything with default pagination" call. _list_staged_impl
        # handles params is None.
        return await _list_staged_impl(params, console_read_api)

    @mcp.tool(
        name="forge_get_staged",
        description=(
            "Forge: get one staged pipeline operation by UUID.\n\n"
            "Use this tool ONLY when:\n"
            "- the user has a specific staged-operation UUID and wants its full record\n\n"
            "Do NOT use this tool for:\n"
            "- listing all staged operations → use forge_list_staged\n"
            "- the proposed-only queue → use forge_staged_pending_read\n"
            "- approving / rejecting → use forge_approve_staged / forge_reject_staged\n"
            "- pipeline shots / projects → use forge_list_shots / forge_list_projects"
        ),
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_get_staged(params: GetStagedInput) -> str:
        return await _get_staged_impl(params, console_read_api)

    @mcp.tool(
        name="forge_approve_staged",
        description=(
            "Forge: approve one staged pipeline operation so the proposer can execute it.\n\n"
            "Approval is bookkeeping — the proposer subscribes to the event and "
            "executes against its own domain. Requires a non-empty actor identity.\n\n"
            "Use this tool ONLY when:\n"
            "- the user explicitly approves a staged operation by ID\n\n"
            "Do NOT use this tool for:\n"
            "- listing or inspecting → use forge_list_staged / forge_get_staged\n"
            "- rejecting → use forge_reject_staged\n"
            "- direct pipeline mutations (creating shots, etc.) → use forge_create_*"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_approve_staged(params: ApproveStagedInput) -> str:
        return await _approve_staged_impl(params, session_factory)

    @mcp.tool(
        name="forge_reject_staged",
        description=(
            "Forge: reject one staged pipeline operation so the proposer drops it.\n\n"
            "Requires a non-empty actor identity. Like approval, rejection is "
            "bookkeeping — the proposer is the one that abandons the work.\n\n"
            "Use this tool ONLY when:\n"
            "- the user explicitly rejects a staged operation by ID\n\n"
            "Do NOT use this tool for:\n"
            "- listing or inspecting → use forge_list_staged / forge_get_staged\n"
            "- approving → use forge_approve_staged\n"
            "- direct pipeline mutations → use forge_create_* / forge_update_*"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_reject_staged(params: RejectStagedInput) -> str:
        return await _reject_staged_impl(params, session_factory)

    # -- GenerationGrant spend-gate (#146) — ratify tool (flip-critical) ------
    # Generators' paid forge_generate_* proof runs through MCP, so this is the
    # flip-critical surface: it ratifies a proposed grant (proposed -> ratified)
    # so a subsequent submit can consume it at the dispatch chokepoint. Pure
    # authority transition — nothing is applied/replayed here. The estimate/mint
    # side (forge_estimate_generation) is DEFERRED to the generators peer, which
    # owns the peer-declared cost; it mints the proposed grant via
    # GenerationGrantRepo.propose().
    @mcp.tool(
        name="forge_ratify_generation_grant",
        description=(
            "Forge: ratify a generation grant so a paid generation submit is "
            "authorized to spend.\n\n"
            "Ratification is authority — it advances a proposed grant (a free "
            "quote) to ratified. The submit then consumes it exactly once at the "
            "dispatch chokepoint. Requires a non-empty actor identity and the "
            "12-char grant_id from the estimate/quote.\n\n"
            "Use this tool ONLY when:\n"
            "- the operator explicitly approves a paid generation by grant_id\n\n"
            "Do NOT use this tool for:\n"
            "- staged pipeline operations → use forge_approve_staged\n"
            "- ratifying a compiled graph-intent (host mutation) → use the "
            "ratify endpoint / fbridge ratify\n"
            "- estimating/quoting a generation → that is the generators peer's "
            "forge_estimate_generation"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_ratify_generation_grant(
        params: RatifyGenerationGrantInput,
    ) -> str:
        return await _ratify_generation_grant_impl(params, session_factory)

    # -- ConsentGrant fitted-model consent latch (#161) — 5 lifecycle tools ----
    # Generators is a SEPARATE process, so the consent lifecycle is exposed over
    # MCP: propose (mint terms) / ratify (operator door) / bind (fit binds the
    # asset id) / get (verify-at-infer) / withdraw (operator door — triggers the
    # withdrawal→revocation propagation so a withdrawn consent refuses infer).
    # Bind to the ASSET, not the call (ADR-002 D-D); no CAS — consent is a
    # durable latch, not a single-use spend.
    @mcp.tool(
        name="forge_propose_consent_grant",
        description=(
            "Forge: propose (mint) a fitted-model consent grant authorizing a "
            "person's likeness to be fitted and replayed.\n\n"
            "A reversible proposal — no binding, no revoke. Requires "
            "owner_of_likeness; allowed_shot_scopes / forbidden_uses / valid_from "
            "/ valid_until are optional (the validity window generators verify at "
            "infer). Returns the 12-char grant_id.\n\n"
            "Use this tool ONLY when:\n"
            "- a person grants consent for likeness fitting/replay\n\n"
            "Do NOT use this tool for:\n"
            "- authorizing a paid generation spend → use the generation-grant tools\n"
            "- ratifying a compiled graph-intent → use the ratify endpoint"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_propose_consent_grant(params: ProposeConsentGrantInput) -> str:
        return await _propose_consent_grant_impl(params, session_factory)

    @mcp.tool(
        name="forge_ratify_consent_grant",
        description=(
            "Forge: ratify a fitted-model consent grant (proposed -> ratified).\n\n"
            "The operator/policy door — consent is granted for a person here; the "
            "fitted-model asset is bound later (forge_bind_consent_grant), once the "
            "model exists. Requires a non-empty actor and the 12-char grant_id.\n\n"
            "Use this tool ONLY when:\n"
            "- the operator/policy layer approves a proposed consent grant\n\n"
            "Do NOT use this tool for:\n"
            "- binding the trained asset → use forge_bind_consent_grant\n"
            "- withdrawing consent → use forge_withdraw_consent_grant"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_ratify_consent_grant(params: RatifyConsentGrantInput) -> str:
        return await _ratify_consent_grant_impl(params, session_factory)

    @mcp.tool(
        name="forge_bind_consent_grant",
        description=(
            "Forge: bind the fitted-model asset id to a ratified consent grant.\n\n"
            "The fit-time stamp — binds which trained asset this person's consent "
            "authorizes (the grant is ratified before the model exists). Only on a "
            "ratified grant; idempotent for the same asset; rejects rebinding a "
            "different asset. Requires grant_id, asset_id (UUID), and actor.\n\n"
            "Use this tool ONLY when:\n"
            "- a fit produces the trained asset for a ratified consent grant\n\n"
            "Do NOT use this tool for:\n"
            "- ratifying consent → use forge_ratify_consent_grant"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": False,
            "destructiveHint": False,
        },
    )
    async def forge_bind_consent_grant(params: BindConsentGrantInput) -> str:
        return await _bind_consent_grant_impl(params, session_factory)

    @mcp.tool(
        name="forge_get_consent_grant",
        description=(
            "Forge: read a fitted-model consent grant by grant_id (verify-at-infer)."
            "\n\nReturns the full consent shape — owner_of_likeness, bound_asset_id "
            "(the bound fitted-model asset UUID), allowed_shot_scopes, forbidden_uses, "
            "the valid_from/valid_until window, revoked (derived), and status. This "
            "is the read generators call to verify consent before an infer. The "
            "legacy identity_id field is a deprecated UUID alias and is NOT the "
            "generators trained-identity handle.\n\n"
            "Use this tool ONLY when:\n"
            "- verifying consent/validity/binding for a fitted model by grant_id"
        ),
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_get_consent_grant(params: GetConsentGrantInput) -> str:
        return await _get_consent_grant_impl(params, session_factory)

    @mcp.tool(
        name="forge_withdraw_consent_grant",
        description=(
            "Forge: withdraw a fitted-model consent grant — the hard consent gate."
            "\n\nThe operator door: flips the grant to withdrawn AND, atomically, "
            "revokes the bound fitted-model asset (if any) so inference immediately "
            "refuses (#160 gate). Idempotent — re-withdrawing is a no-op. Requires a "
            "non-empty actor and the 12-char grant_id; reason is optional.\n\n"
            "Use this tool ONLY when:\n"
            "- a person or policy withdraws consent for a fitted model\n\n"
            "Do NOT use this tool for:\n"
            "- rejecting a staged operation → use forge_reject_staged"
        ),
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
        },
    )
    async def forge_withdraw_consent_grant(params: WithdrawConsentGrantInput) -> str:
        return await _withdraw_consent_grant_impl(params, session_factory)

    # -- Phase 14 (FB-B) STAGED-07 — pending-queue snapshot resource + tool shim
    # Per D-12: ship only forge://staged/pending (proposed-only) + forge_staged_pending_read shim.
    # Per D-13: hardcoded limit=500 (the max) — guarantees the byte-identity property
    # with forge_list_staged(status='proposed', limit=500, offset=0).
    # P-03 prevention: tool shim alongside resource for clients without resources support
    # (Cursor, Gemini CLI). Same closure-capture as the manifest pair.

    @mcp.resource("forge://staged/pending", mime_type="application/json")
    async def staged_pending() -> str:
        records, total = await console_read_api.get_staged_ops(
            status="proposed", limit=500, offset=0, project_id=None,
        )
        return _envelope_json(
            [r.to_dict() for r in records],
            limit=500, offset=0, total=total,
        )

    @mcp.tool(
        name="forge_staged_pending_read",
        description=(
            "Forge: snapshot of pending (proposed-only) staged pipeline operations.\n\n"
            "Use this tool ONLY when:\n"
            "- the user wants the *pending approval* queue specifically\n"
            "- the user wants a quick snapshot without filtering options\n\n"
            "Do NOT use this tool for:\n"
            "- listing approved/rejected/executed staged ops → use forge_list_staged\n"
            "- one staged op by ID → use forge_get_staged\n"
            "- pipeline shots/projects/media → use forge_list_*\n\n"
            "Alias for `resources/read forge://staged/pending` for MCP clients "
            "that don't support resources (Cursor, Gemini CLI)."
        ),
        annotations={"readOnlyHint": True, "idempotentHint": True},
    )
    async def forge_staged_pending_read() -> str:
        records, total = await console_read_api.get_staged_ops(
            status="proposed", limit=500, offset=0, project_id=None,
        )
        return _envelope_json(
            [r.to_dict() for r in records],
            limit=500, offset=0, total=total,
        )
