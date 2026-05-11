"""Test-resident seed fixture package for PR 9.

Each fixture module exposes one top-level constant ``FIXTURE: dict``
carrying the three PR-8-locked keys (``fixture_id``, ``prompt``,
``expected_narrow``). Per ``A.5.3.2-PR9-FRAMING.md`` §4.1 + §5.1
(Q1) + cleanup-pressure-resistance class member #9 (fixture-
surface-data-discipline; framing §6.1): fixture modules are data +
one orchestration call only. The Layer 2 fixture discipline
(``_FIXTURE_PERMITTED_IMPORTS`` + walker in
``test_pr9_fixture_discipline.py``) enforces mechanically.

This ``__init__.py`` carries no logic; the package marker exists
solely so ``from tests.corpus.fixtures.fix_<name> import FIXTURE``
works from ``test_pr9_fixture_integration.py``.
"""
