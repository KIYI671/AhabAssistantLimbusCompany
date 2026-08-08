from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_daily_process_does_not_start_battle_when_team_selection_fails(
    monkeypatch,
    process_name: str,
    entrypoint_name: str,
) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[object] = []

    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            targeted_teaming_EXP=False,
            targeted_teaming_thread=False,
            daily_teams=1,
        ),
    )
    monkeypatch.setattr(scheme, entrypoint_name, lambda count: calls.append((entrypoint_name, count)))
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: False)
    monkeypatch.setattr(
        scheme.battle,
        "to_battle",
        lambda: pytest.fail("选队失败后不应尝试开始战斗"),
    )

    assert getattr(scheme, process_name)() is False
    assert calls == [(entrypoint_name, 1)]
