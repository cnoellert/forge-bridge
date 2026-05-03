"""PR28 / PR29 — Deterministic user-supplied parameter injection.

The PR27 disambiguation contract (`MULTIPLE_PROJECTS`) tells the caller
"the system holds N candidates; pick one." This module is the picker:
it parses an explicit, machine-verifiable selection out of the user
message and hands a parameter dict to ``resolve_required_params``
BEFORE memory hydration or resolver dispatch run.

Hard constraints (mirror ``_tool_chain``):
  1. **No LLM involvement.** Pure regex / string ops — runs in the
     request thread.
  2. **No fuzzy matching.** No partial, no substring, no transformed
     matches. Only strict UUIDs and EXACT names (case-insensitive,
     trimmed); name resolution itself lives in ``_name_resolve``.
  3. **No guessing.** Two-or-more bare UUIDs → return nothing.
     Ambiguity stays ambiguous and PR27 ``MULTIPLE_PROJECTS`` fires.
  4. **No memory writes.** Caller-supplied values are passed through
     ``resolve_required_params`` as caller params; PR26's "explicit
     never writes memory" contract handles the rest of the precedence
     chain (explicit > memory > resolver).
  5. **Fail closed.** Any malformed input → empty dict. Never
     substitute a default, never raise — the downstream graceful
     contract surfaces the right error.

Supported input forms (STRICT, in priority order):

  1. ``project_id=<uuid>`` (PR28) — most specific. Returns
     ``{"project_id": "<uuid>"}`` and short-circuits all other forms.
     The KEY match is case-insensitive (``PROJECT_ID=``,
     ``Project_Id=``); the UUID VALUE is preserved verbatim. The
     candidate boundary is ``[^\\w-]`` so trailing punctuation
     (``,`` ``.`` ``;`` ``)``) terminates cleanly; only valid 8-4-4-4-12
     hex passes ``fullmatch``, malformed candidates fall through.

  2. ``project_name=<string>`` (PR29) — explicit name selector. Returns
     ``{"project_name": "<value>"}`` and short-circuits the bare-UUID
     fallback. The KEY match is case-insensitive; the VALUE is
     whitespace-terminated (names with embedded spaces must use the
     UUID form). Resolution is NOT attempted here — this module only
     extracts the literal token; ``_name_resolve.resolve_name_from_
     candidates`` does the matching against the PR27 candidate list.

  3. Bare UUID (single match only) — fallback for users who paste just
     a project id. If the message contains two-or-more bare UUIDs, we
     return ``{}`` — better to let PR27 disambiguation fire than to
     pick one arbitrarily.

Precedence is encoded by control flow: each higher-priority form
returns early when matched. A message that contains both
``project_id=<uuidA>`` and ``project_name=Beta`` resolves to
``{"project_id": "<uuidA>"}`` — the UUID is the canonical handle.
A message with ``project_name=Beta`` and a stray bare UUID resolves
to ``{"project_name": "Beta"}`` — explicit keyed name wins over
incidental UUID context.

Whitespace handling: leading and trailing whitespace on the message is
stripped before parsing so trivial formatting variance (a chat client
appending ``"\n"``, copy-paste padding) does not change behavior.
Inner whitespace is preserved as the candidate-terminator for both
keyed forms.
"""
from __future__ import annotations

import re
from typing import Dict


# Strict canonical 8-4-4-4-12 hex UUID. Word boundaries keep the
# pattern from chewing through adjacent identifiers (e.g. an upstream
# ``shot_id=<32-hex>`` field would not falsely match here). ASCII-only
# hex on purpose — the canonical UUID format does not carry locale.
#
# Public — exported as the SINGLE source of truth for UUID parsing
# across the console package. Other modules MUST import this constant
# rather than redefining the pattern. A second copy anywhere in the
# tree silently invites drift (e.g. ``shot_id`` parsing later relaxing
# the boundaries) — keep this canonical.
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)


def extract_explicit_params(message: str) -> Dict[str, str]:
    """Parse explicit, deterministic parameters out of a user message.

    Returns a dict suitable for forwarding as caller params to
    ``resolve_required_params`` (when the dict carries ``project_id``)
    or to the chat handler's PR29 name-resolution branch (when the dict
    carries ``project_name``). Today only those two keys are produced;
    the surface will grow as additional explicit selectors come online.

    Rules:
      - Leading / trailing whitespace on the message is stripped before
        parsing; trivial formatting variance must not change behavior.
      - All keyed forms are case-insensitive (``Project_Id=``,
        ``PROJECT_NAME=``, etc.); VALUES are preserved verbatim.
      - Precedence (higher → lower):
          1. ``project_id=<uuid>`` (PR28) — short-circuits everything
             else; returns ``{"project_id": "<uuid>"}``.
          2. ``project_name=<string>`` (PR29) — short-circuits the
             bare-UUID fallback; returns ``{"project_name": "<value>"}``.
          3. Bare UUID single-match — returns
             ``{"project_id": "<uuid>"}``.
      - Two-or-more bare UUIDs → ``{}`` (let PR27 disambiguate).
      - No transformation: the value the caller wrote is the value
        downstream code sees (matching is done by callers, not here).
    """
    params: Dict[str, str] = {}

    if not isinstance(message, str) or not message:
        return params

    # Strip leading / trailing whitespace so a chat client's default
    # ``"\n"`` framing doesn't shift candidate offsets. Inner whitespace
    # is preserved — the keyed form's whitespace-terminated split below
    # still relies on it to know where the candidate ends.
    text = message.strip()
    if not text:
        return params

    # Lowercased view used ONLY for key detection. The original ``text``
    # remains the source of truth for slicing the UUID candidate so its
    # case is preserved verbatim into the returned dict (the regex itself
    # is already case-insensitive on hex digits, so case-folding the
    # candidate for matching would be a redundant transformation).
    lower = text.lower()

    # Explicit keyed form — first occurrence wins. ``find`` on the
    # lowercased view locates the key without forcing the candidate
    # through case-folding; we then slice the ORIGINAL ``text`` from the
    # same offset so an uppercase UUID like ``project_id=ABCD-...``
    # round-trips unchanged. The ``fullmatch`` on the whitespace-
    # terminated token rejects trailing garbage (e.g. ``project_id=
    # <uuid>.`` becomes a candidate of ``<uuid>.`` and fails strict
    # validation, falling through to the bare-UUID branch below).
    key = "project_id="
    if key in lower:
        idx = lower.find(key) + len(key)
        after = text[idx:]
        # Split at the first character that is NEITHER a word char nor
        # a dash — i.e. anything outside the UUID-allowed alphabet
        # ``[A-Za-z0-9_-]``. This is strictly tighter than splitting on
        # whitespace alone: trailing punctuation (``,``, ``.``, ``;``,
        # ``)``, etc.) now correctly terminates the candidate so the
        # keyed branch resolves directly instead of falling through to
        # the bare-UUID fallback. The boundary is intentionally narrow
        # — ``\w`` includes ``_``, which is not a UUID character but
        # also won't validate via ``fullmatch``, so a stray underscore
        # still surfaces as a malformed candidate (no broadening).
        candidate = re.split(r"[^\w-]", after, maxsplit=1)[0] if after else ""
        if candidate and UUID_RE.fullmatch(candidate):
            params["project_id"] = candidate
            return params

    # PR29 — explicit name selector. Only fires when no valid keyed
    # UUID was extracted above; a UUID is more specific (canonical
    # handle) and wins by code order. The candidate boundary here is
    # plain whitespace, NOT the UUID-narrow ``[^\w-]`` boundary —
    # names can legitimately contain punctuation (``Project-Alpha``,
    # ``proj.beta``), so we only stop at the first whitespace token.
    # Names with embedded spaces are out of scope: the user must use
    # the UUID form for those (a v1 limitation locked by the brief's
    # "value is everything after = until end-of-token" rule).
    name_key = "project_name="
    if name_key in lower:
        idx = lower.find(name_key) + len(name_key)
        after = text[idx:]
        # ``str.split(maxsplit=1)`` returns ``[]`` for an empty / all-
        # whitespace string; the ``or [""]`` fallback keeps the index
        # access safe without a separate branch.
        candidate = (after.split(maxsplit=1) or [""])[0]
        if candidate:
            params["project_name"] = candidate
            # Return early so an incidental bare UUID elsewhere in the
            # message can't silently override the explicit keyed name —
            # the user committed to the name form, honor it.
            return params

    # Bare-UUID fallback — only fires when the message contains exactly
    # one UUID. Two-or-more matches are treated as ambiguous; we hand
    # back ``{}`` so the existing PR27 disambiguation contract owns the
    # response shape (no premature picker logic in this module).
    matches = UUID_RE.findall(text)
    # Explicitly reject ambiguous input — never pick the first, never
    # the last, never compose from multiple. This early return makes
    # the "no guessing" rule visible at the call site rather than
    # encoded as the absence of an else-branch. Pin via
    # ``test_extract_multiple_uuids_returns_empty``.
    if len(matches) > 1:
        return {}
    if len(matches) == 1:
        params["project_id"] = matches[0]

    return params
