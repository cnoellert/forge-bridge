---
name: SEED-AUTH-V1.5
description: FB-D rate-limiting → caller-identity follow-up once v1.5 auth ships
type: forward-looking-idea
planted_during: v1.4 milestone open (2026-04-25)
trigger_when: v1.5 auth milestone is opened (any phase that introduces caller identity / authentication)
---

# SEED-AUTH-V1.5: Migrate FB-D rate limiting from IP-based to caller-identity-based

## Idea

When v1.5 introduces auth (caller identity), revisit FB-D's `/api/v1/chat` rate limiting and replace IP-based bucketing with identity-based bucketing. The CHAT-01 acceptance criterion ("eleven rapid requests from the same IP within one minute returns HTTP 429") is the v1.4 stopgap; once we know who the caller is, the right bucket key is the caller's identity, not their network address.

## Why This Matters

- **IP-based rate limiting is the wrong primitive once auth lands** — single-NAT teams (multiple artists behind one office IP) all share the same bucket and starve each other; multi-IP single-callers (laptop on VPN + desktop on LAN) get double the budget by accident.
- **Per-caller cost accounting is the v1.5 ask** — projekt-forge v1.5 will likely want to attribute LLM cost to a user, not an IP. Rate limit and cost meter share the same identity dimension.
- **Behavioral budgets become possible** — different caller classes (artist UI, batch CLI, projekt-forge service-account) can carry different budgets; today they're flattened.

## When to Surface

This seed should resurface when:

- A v1.5 milestone is opened that mentions auth, identity, sessions, or callers
- Any phase plan introduces a `caller_identity`, `user_id`, `session_id`, or `service_account` parameter to a public API
- A phase touches `/api/v1/chat` rate-limiting code paths (deferred polish phases in v1.4.x do NOT count — rate limiter stays IP-only until auth lands)

## How to Apply

When triggered:

1. Re-read the FB-D rate-limiter implementation (whatever ships in `forge_bridge/server/` for `/api/v1/chat`)
2. Add a caller-identity bucket key alongside the IP bucket; gate the swap behind a config flag during the migration phase
3. Capture the migration as an explicit requirement (e.g., `CHAT-05` or in the v1.5 auth phase's requirements) — do NOT silently swap; the IP fallback should remain reachable for unauthenticated debug/CI paths
4. Update CHAT-01 acceptance criterion to reflect identity-based bucketing once the swap completes; add a backwards-compat fallback test for the IP path

## Cross-References

- v1.4 ROADMAP Phase FB-D, success criterion #1 (eleven-requests-from-same-IP-returns-429)
- v1.4 REQUIREMENTS.md CHAT-01 (carry-over from Phase 12 supersession)
- Phase 12 (superseded) original CHAT-01..04 scope — v1.3 milestone archive
- v1.3 PROJECT.md "Out of Scope" entry: "Authentication — deferred, local-only for now"
