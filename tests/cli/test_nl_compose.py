"""Unit tests for the NL composer in the `fbridge exec` REPL.

NL is a COMPOSER/form-filler: free text -> (verb, sequence, seg_index, value),
handed to the SAME `_run_verb` path. These tests mock `router.acomplete` with
canned JSON (no real model) and prove:
  - good JSON -> the right (verb, sequence, seg_index, value_raw) tuple
  - the extraction schema is DERIVED from the verb registry (not hardcoded)
  - unknown verb / junk JSON / model failure -> clean fallback, NO _run_verb call
  - NL hands off to _run_verb (the confirm gate stays downstream — NL never runs)
  - the REPL routes slash/meta as commands and free text to NL
"""
from __future__ import annotations

import pytest

from forge_bridge.cli import interactive
from forge_bridge.cli import verbs


class _FakeCon:
    def __init__(self):
        self.lines: list[str] = []

    def print(self, *a, **k):
        self.lines.append(" ".join(str(x) for x in a))


class _FakeRouter:
    """Returns canned text; records that acomplete was called with sensitive=True."""

    def __init__(self, reply: str = "", *, boom: bool = False):
        self.reply = reply
        self.boom = boom
        self.calls: list[dict] = []

    async def acomplete(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        if self.boom:
            raise RuntimeError("ollama down")
        return self.reply


# -- _nl_compose: JSON -> (verb, sequence, seg_index, value_raw) ---------------


@pytest.mark.asyncio
async def test_compose_full_rename():
    router = _FakeRouter(
        '{"verb": "rename", "sequence": "MyCut", "segment_index": 3, "value": "BG_010"}'
    )
    verb, seq, idx, val, err = await interactive._nl_compose("…", router=router)
    assert err is None
    assert verb is verbs.REGISTRY["rename"]
    assert (seq, idx, val) == ("MyCut", 3, "BG_010")
    # routed local (sensitive) — no data egress for the composer
    assert router.calls[0]["sensitive"] is True


@pytest.mark.asyncio
async def test_compose_trim_head_signed_offset_value_becomes_str():
    # trim is a SIGNED RELATIVE offset (value_kind="offset"): positive trims off,
    # negative extends. A JSON number must reach _run_verb as a string so it feeds
    # the SAME trust-boundary parse the prompts use.
    router = _FakeRouter(
        '{"verb": "trim_head", "sequence": "CUT", "segment_index": 5, "value": -10}'
    )
    verb, seq, idx, val, err = await interactive._nl_compose("…", router=router)
    assert err is None and verb is verbs.REGISTRY["trim_head"]
    assert (seq, idx, val) == ("CUT", 5, "-10")
    # the str feeds the SAME trust-boundary parse the prompts use; offsets are
    # signed ints (negative = extend) and 0 is rejected as a no-op.
    typed, perr = verbs.parse_value(verb, val)
    assert typed == -10 and perr is None


@pytest.mark.asyncio
async def test_compose_trim_tail_positive_offset():
    # positive offset on the tail verb trims off; value arrives as a JSON number.
    router = _FakeRouter(
        '{"verb": "trim_tail", "sequence": "CUT", "segment_index": 2, "value": 12}'
    )
    verb, seq, idx, val, err = await interactive._nl_compose("…", router=router)
    assert err is None and verb is verbs.REGISTRY["trim_tail"]
    assert (seq, idx, val) == ("CUT", 2, "12")
    typed, perr = verbs.parse_value(verb, val)
    assert typed == 12 and perr is None


@pytest.mark.asyncio
async def test_compose_partial_leaves_unknowns_none():
    # only the verb is clear -> the rest stay None so _run_verb prompts for them
    router = _FakeRouter(
        '{"verb": "rename", "sequence": null, "segment_index": null, "value": null}'
    )
    verb, seq, idx, val, err = await interactive._nl_compose("…", router=router)
    assert err is None and verb is verbs.REGISTRY["rename"]
    assert (seq, idx, val) == (None, None, None)


@pytest.mark.asyncio
async def test_compose_bool_index_is_not_treated_as_int():
    # bool is an int subclass; true/false must NOT become segment #1/#0
    router = _FakeRouter(
        '{"verb": "rename", "sequence": "C", "segment_index": true, "value": "x"}'
    )
    _, _, idx, _, err = await interactive._nl_compose("…", router=router)
    assert err is None and idx is None


@pytest.mark.asyncio
async def test_compose_strips_code_fences():
    router = _FakeRouter(
        '```json\n{"verb": "rename", "sequence": "C", "segment_index": 1, "value": "y"}\n```'
    )
    verb, seq, idx, val, err = await interactive._nl_compose("…", router=router)
    assert err is None and verb is verbs.REGISTRY["rename"] and (seq, idx, val) == ("C", 1, "y")


@pytest.mark.asyncio
async def test_compose_unknown_verb_is_clean_fallback():
    router = _FakeRouter('{"verb": "explode", "sequence": "C"}')
    verb, _, _, _, err = await interactive._nl_compose("…", router=router)
    assert verb is None and err is not None and "couldn't map" in err.lower()


@pytest.mark.asyncio
async def test_compose_null_verb_is_clean_fallback():
    router = _FakeRouter('{"verb": null, "sequence": null}')
    verb, _, _, _, err = await interactive._nl_compose("…", router=router)
    assert verb is None and err is not None


@pytest.mark.asyncio
async def test_compose_junk_json_is_clean_fallback():
    router = _FakeRouter("I'm not sure what you mean, friend.")
    verb, _, _, _, err = await interactive._nl_compose("…", router=router)
    assert verb is None and err is not None


@pytest.mark.asyncio
async def test_compose_model_failure_is_swallowed_to_error():
    router = _FakeRouter(boom=True)
    verb, _, _, _, err = await interactive._nl_compose("…", router=router)
    assert verb is None and err is not None and "language model" in err


def test_system_prompt_is_registry_derived():
    # every registered verb name + label + value_label appears (no hardcoded list)
    sys = interactive._nl_system_prompt()
    for v in verbs.list_verbs():
        assert v.name in sys and v.label in sys and v.value_label in sys


# -- _nl_dispatch: hands off to _run_verb; never runs anything itself ----------


@pytest.mark.asyncio
async def test_dispatch_feeds_run_verb_and_does_not_execute(monkeypatch):
    monkeypatch.setattr(interactive, "_nl_router",
                        lambda: _FakeRouter(
                            '{"verb": "rename", "sequence": "MyCut", '
                            '"segment_index": 3, "value": "BG_010"}'))
    captured = {}

    async def fake_run_verb(con, *, verb, sequence, seg_index, value_raw):
        captured["args"] = (verb.name, sequence, seg_index, value_raw)

    # NL must NOT touch preview/stage/apply — wire them to explode if reached
    async def boom(*a, **k):
        raise AssertionError("NL must not preview/stage/apply — it stops at form-fill")

    monkeypatch.setattr(interactive, "_run_verb", fake_run_verb)
    monkeypatch.setattr(interactive, "_preview_mutation", boom)
    monkeypatch.setattr(interactive, "_stage_mutation", boom)
    monkeypatch.setattr(interactive, "_apply_held", boom)

    con = _FakeCon()
    await interactive._nl_dispatch(con, "rename the 3rd shot on MyCut to BG_010")
    assert captured["args"] == ("rename", "MyCut", 3, "BG_010")
    # the extraction is echoed for transparency (visible, not magic)
    assert any("understood" in line for line in con.lines)


@pytest.mark.asyncio
async def test_dispatch_trim_offset_reaches_run_verb_still_gated(monkeypatch):
    # a composed SIGNED OFFSET ("-10" = extend the head) must reach _run_verb as a
    # string and stop there — NL never previews/stages/applies (the gate is downstream).
    monkeypatch.setattr(interactive, "_nl_router",
                        lambda: _FakeRouter(
                            '{"verb": "trim_head", "sequence": "MyCut", '
                            '"segment_index": 2, "value": -10}'))
    captured = {}

    async def fake_run_verb(con, *, verb, sequence, seg_index, value_raw):
        captured["args"] = (verb.name, sequence, seg_index, value_raw)

    async def boom(*a, **k):
        raise AssertionError("NL must not preview/stage/apply — it stops at form-fill")

    monkeypatch.setattr(interactive, "_run_verb", fake_run_verb)
    monkeypatch.setattr(interactive, "_preview_mutation", boom)
    monkeypatch.setattr(interactive, "_stage_mutation", boom)
    monkeypatch.setattr(interactive, "_apply_held", boom)

    con = _FakeCon()
    await interactive._nl_dispatch(con, "extend the head of shot 2 on MyCut by 10")
    assert captured["args"] == ("trim_head", "MyCut", 2, "-10")
    # the offset string parses to a signed int at the SAME trust boundary _run_verb uses
    typed, perr = verbs.parse_value(verbs.REGISTRY["trim_head"], captured["args"][3])
    assert typed == -10 and perr is None


@pytest.mark.asyncio
async def test_dispatch_unknown_verb_skips_run_verb(monkeypatch):
    monkeypatch.setattr(interactive, "_nl_router", lambda: _FakeRouter('{"verb": "nope"}'))

    async def must_not_run(*a, **k):
        raise AssertionError("_run_verb must not run when NL can't map a verb")

    monkeypatch.setattr(interactive, "_run_verb", must_not_run)
    con = _FakeCon()
    await interactive._nl_dispatch(con, "do a barrel roll")
    assert any("couldn't map" in line.lower() for line in con.lines)


# -- REPL routing: slash/meta = commands, free text = NL -----------------------


@pytest.mark.asyncio
async def test_repl_routes_freetext_to_nl_and_slash_to_verb(monkeypatch):
    async def _noop():
        return None
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    lines = iter([
        "rename the third shot to BG",   # free text -> NL
        "/rename CUT #1 NEWNAME",          # slash -> verb dispatch (inline args)
        "/quit",                            # meta -> quit
    ])
    monkeypatch.setattr(interactive.Prompt, "ask", lambda *a, **k: next(lines))

    nl_calls: list[str] = []
    verb_calls: list[tuple] = []

    async def fake_nl_dispatch(con, text):
        nl_calls.append(text)

    async def fake_run_verb(con, *, verb, sequence, seg_index, value_raw):
        verb_calls.append((verb.name, sequence, seg_index, value_raw))

    monkeypatch.setattr(interactive, "_nl_dispatch", fake_nl_dispatch)
    monkeypatch.setattr(interactive, "_run_verb", fake_run_verb)

    await interactive.run_interactive()

    assert nl_calls == ["rename the third shot to BG"]
    assert verb_calls == [("rename", "CUT", 1, "NEWNAME")]


@pytest.mark.asyncio
async def test_repl_bare_meta_words_still_route_as_commands(monkeypatch):
    async def _noop():
        return None
    monkeypatch.setattr(interactive, "_bootstrap", _noop)

    lines = iter(["help", "quit"])  # no slash — must NOT go to NL
    monkeypatch.setattr(interactive.Prompt, "ask", lambda *a, **k: next(lines))

    async def nl_boom(con, text):
        raise AssertionError("bare meta words must route as commands, not NL")

    monkeypatch.setattr(interactive, "_nl_dispatch", nl_boom)

    # run_interactive builds its own console; just assert it returns cleanly
    await interactive.run_interactive()
