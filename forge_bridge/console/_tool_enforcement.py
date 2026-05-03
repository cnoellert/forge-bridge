"""forge_bridge.console._tool_enforcement — PR15 deterministic tool-calling.

Pure helpers, no I/O. The chat handler composes a stronger system prompt
before invoking the LLM router, then validates the terminal assistant text
before returning it to the client. The wrapper consumes ``tool_enforced``
out of the response body for the trace summary (call_wrapper.py).

Scope (NO-GSD):
  * No MCP / registry / planner changes.
  * No filtering changes (PR14 lives in ``_tool_filter.py``).
  * No execution / retry changes (PR10–PR13 untouched).
  * Pure prompt + cheap regex validation.
"""
from __future__ import annotations

import re

# A response is "tool-enforced" when the filtered tool set is small enough
# that the model has effectively no excuse not to pick the right tool.
PR15_TOOL_ENFORCED_THRESHOLD = 3

# Single tool — the only valid response is a call to it.
PR15_HARD_TOOL_MODE_THRESHOLD = 1

PR15_ENFORCEMENT_PROMPT = """\
You are a tool-using agent.

You MUST follow these rules:
1. If a relevant tool is available → YOU MUST CALL IT.
2. Do NOT answer from memory if a tool can provide the answer.
3. Do NOT output text that looks like a tool call.
4. ONLY return a tool call in structured format when using tools.
5. If no tool is relevant → respond normally.

A tool is relevant if:
- the tool name matches the request, or
- the tool description matches the request.

When calling a tool:
- return ONLY a structured tool call (no text wrapping it).
- if you must emit text instead, do NOT include explanations, markdown,
  extra text, <|im_start|> tokens, or code fences shaped like a tool call.

If you fail to call a tool when required, the response is invalid.
"""

PR15_HARD_TOOL_INSTRUCTION = (
    "There is exactly ONE tool available for this request. "
    "You MUST call this tool. No other response is valid."
)


def build_enforcement_system_prompt(
    base_prompt: str | None,
    tools_filtered: int,
) -> str:
    """Compose the system prompt for a tool-call request.

    Stacks (in order):
      1. ``base_prompt`` — the existing pipeline-context prompt (preserved).
      2. ``PR15_ENFORCEMENT_PROMPT`` — the deterministic-tool-calling rules.
      3. ``PR15_HARD_TOOL_INSTRUCTION`` — only when ``tools_filtered == 1``.

    A ``base_prompt`` of None / empty is tolerated so callers can opt out
    of the pipeline assistant context (e.g. tests).
    """
    parts: list[str] = []
    if isinstance(base_prompt, str) and base_prompt.strip():
        parts.append(base_prompt.rstrip())
    parts.append(PR15_ENFORCEMENT_PROMPT.rstrip())
    if tools_filtered == PR15_HARD_TOOL_MODE_THRESHOLD:
        parts.append(PR15_HARD_TOOL_INSTRUCTION)
    return "\n\n".join(parts)


def is_tool_enforced(tools_filtered: int) -> bool:
    """True iff the filtered tool set is ≤ the enforcement threshold (3).

    Surfaces in the chat-handler response body and the wrapper trace summary
    so operators can see when PR15's guard rails were active for a request.
    """
    return tools_filtered <= PR15_TOOL_ENFORCED_THRESHOLD


# ── output validation ────────────────────────────────────────────────────
#
# Detect cases where the model emits text that LOOKS like a tool call
# instead of actually invoking one — the failure mode that motivated PR15.
# Two signals:
#   (a) chat-template token leakage (<|im_start|>, <|im_end|>) — these are
#       never legitimate in a clean assistant response.
#   (b) the response BEGINS with a tool-call-shaped JSON object (i.e. the
#       model wrote the call as text). A legitimate explanation of a tool
#       call buried mid-text is fine; a leading hallucinated object is not.
#
# Conservative on purpose — false positives turn legitimate replies into
# 500s. This regex requires both ``"name"`` and ``"arguments"`` to appear
# at the very start of the (lstripped) response, which is exactly the
# qwen2.5-coder leak we observed.

_PR15_CHAT_TEMPLATE_TOKENS = ("<|im_start|>", "<|im_end|>")

_PR15_LEADING_TOOL_JSON_RE = re.compile(
    r"^\s*(?:```\s*(?:json)?\s*)?\{\s*\"?name\"?\s*:\s*\"?[a-z][a-z0-9_]+\"?"
    r"[\s\S]{0,200}?\"?arguments\"?\s*:",
    re.IGNORECASE,
)


def is_response_text_malformed_tool(text: str) -> bool:
    """Return True if ``text`` is a hallucinated tool-call instead of a real one.

    Triggered by chat-template token leakage OR by a leading JSON object
    whose first two keys are ``name`` and ``arguments`` — the exact pattern
    qwen2.5-coder produced when it tried to call a tool via free text.
    """
    if not isinstance(text, str) or not text:
        return False
    for token in _PR15_CHAT_TEMPLATE_TOKENS:
        if token in text:
            return True
    return bool(_PR15_LEADING_TOOL_JSON_RE.search(text))
