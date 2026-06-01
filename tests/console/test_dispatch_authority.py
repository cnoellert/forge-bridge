from __future__ import annotations

from types import SimpleNamespace

from forge_bridge.console._authority import dispatch_authority


def test_dispatch_authority_read_only_true_is_not_mutating():
    tool = SimpleNamespace(
        annotations=SimpleNamespace(readOnlyHint=True),
    )

    assert dispatch_authority(tool) is False


def test_dispatch_authority_false_is_mutating():
    tool = SimpleNamespace(
        annotations=SimpleNamespace(readOnlyHint=False),
    )

    assert dispatch_authority(tool) is True


def test_dispatch_authority_absent_annotations_is_mutating():
    tool = SimpleNamespace()

    assert dispatch_authority(tool) is True


def test_dispatch_authority_unknown_shape_is_mutating():
    tool = {"annotations": {"readOnlyHint": True}}

    assert dispatch_authority(tool) is True
