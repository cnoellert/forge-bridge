"""PR28 — Deterministic user-supplied parameter injection.

The PR27 disambiguation contract (`MULTIPLE_PROJECTS`) tells the caller
"the system holds N candidates; pick one." This module is the picker:
it parses an explicit, machine-verifiable selection out of the user
message and hands a parameter dict to ``resolve_required_params``
BEFORE memory hydration or resolver dispatch run.

Hard constraints (mirror ``_tool_chain``):
  1. **No LLM involvement.** Pure regex — runs in the request thread.
  2. **No fuzzy matching.** No name-based, no partial, no transformed
     matches. Only a strict UUID by default.
  3. **No guessing.** If the message holds two-or-more bare UUIDs we
     return nothing — ambiguity stays ambiguous and the existing PR27
     ``MULTIPLE_PROJECTS`` envelope still fires.
  4. **No memory writes.** Caller-supplied values are passed through
     ``resolve_required_params`` as caller params; PR26's "explicit
     never writes memory" contract handles the rest of the precedence
     chain (explicit > memory > resolver).
  5. **Fail closed.** Any malformed input → empty dict. Never
     substitute a default, never raise — the downstream graceful
     contract surfaces the right error.

Supported input forms (STRICT, in priority order):

  1. ``project_id=<uuid>`` — primary explicit form. Whitespace-
     terminated. The KEY match is case-insensitive (``PROJECT_ID=``
     and ``Project_Id=`` qualify); the UUID VALUE is preserved
     verbatim from the original message. ``fullmatch`` on the
     candidate so trailing punctuation/garbage falls through to the
     bare-UUID fallback.

  2. Bare UUID (single match only) — fallback for users who paste
     just a project id. If the message contains two-or-more bare
     UUIDs, we return ``{}`` — better to let PR27 disambiguation
     fire than to pick one arbitrarily.

The keyed form takes precedence over the bare form. A message that
contains both ``project_id=<uuidA>`` and a stray ``<uuidB>`` resolves
to ``<uuidA>`` — the caller was explicit about the keyed value, the
bare UUID is ignored as incidental context.

Whitespace handling: leading and trailing whitespace on the message is
stripped before parsing so trivial formatting variance (a chat client
appending ``"\n"``, copy-paste padding) does not change behavior.
Inner whitespace is preserved as the candidate-terminator for the
keyed form.
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
    ``resolve_required_params``. Today the only key produced is
    ``project_id``; the registry will grow as additional chain
    resolvers come online.

    Rules:
      - Leading / trailing whitespace on the message is stripped before
        parsing; trivial formatting variance must not change behavior.
      - The ``project_id=`` key match is case-insensitive (``Project_Id=``
        and ``PROJECT_ID=`` both qualify); the UUID *value* is preserved
        verbatim from the original message so the downstream tool sees
        what the caller wrote.
      - ``project_id=<uuid>`` takes precedence over a bare UUID.
      - The keyed candidate is ``fullmatch``-validated against the UUID
        regex — partial / suffixed candidates fall through.
      - Bare UUID fallback fires ONLY when the message contains exactly
        one match. Multiple bare UUIDs → ``{}`` (let PR27 disambiguate).
      - No transformation: the value the caller wrote is the value the
        downstream tool sees.
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
