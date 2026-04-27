"""TEMPORARY RED test for 15-01 Task 2 — assert learning/sanitize.py is a shim.

This file is the failing test before the constants in
forge_bridge/learning/sanitize.py become a re-export of
forge_bridge._sanitize_patterns. It will be DELETED in 15-01 Task 3 once
the permanent TestSanitizePatternsShim class lands in tests/test_sanitize.py.
"""
from __future__ import annotations


def test_learning_sanitize_injection_markers_is_hoisted_object():
    """Same-object identity: shim must re-export, not redeclare."""
    from forge_bridge._sanitize_patterns import INJECTION_MARKERS as hoisted
    from forge_bridge.learning.sanitize import INJECTION_MARKERS as shimmed
    assert hoisted is shimmed


def test_learning_sanitize_control_char_re_is_hoisted_object():
    from forge_bridge._sanitize_patterns import _CONTROL_CHAR_RE as hoisted
    from forge_bridge.learning.sanitize import _CONTROL_CHAR_RE as shimmed
    assert hoisted is shimmed
