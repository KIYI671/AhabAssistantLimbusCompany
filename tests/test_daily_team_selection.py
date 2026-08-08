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


def test_daily_groups_initialize_after_each_enabled_group(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            set_EXP_count=2,
            set_thread_count=1,
            config=SimpleNamespace(use_continuous_combat=False),
            use_continuous_combat_select=1,
        ),
    )
    monkeypatch.setattr(scheme, "back_init_menu", lambda: calls.append("home"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: calls.append("enkephalin"))
    monkeypatch.setattr(scheme, "onetime_EXP_process", lambda: calls.append("exp"))
    monkeypatch.setattr(scheme, "onetime_thread_process", lambda: calls.append("thread"))

    scheme.Daily_task_wrapper()()

    assert calls == [
        "home",
        "enkephalin",
        "exp",
        "exp",
        "home",
        "enkephalin",
        "thread",
        "home",
        "enkephalin",
    ]


@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_successful_daily_process_keeps_current_navigation(
    monkeypatch,
    process_name: str,
    entrypoint_name: str,
) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            targeted_teaming_EXP=False,
            targeted_teaming_thread=False,
            daily_teams=1,
        ),
    )
    def enter_dungeon(count: int) -> bool:
        calls.append(entrypoint_name)
        return True

    monkeypatch.setattr(scheme, entrypoint_name, enter_dungeon)
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: True)
    monkeypatch.setattr(scheme.battle, "to_battle", lambda: None)
    monkeypatch.setattr(scheme.battle, "fight", lambda **kwargs: calls.append("fight"))
    monkeypatch.setattr(scheme, "back_init_menu", lambda: pytest.fail("单场完成后不应返回主界面"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: pytest.fail("单场完成后不应重复换饼"))

    getattr(scheme, process_name)()

    assert calls == [entrypoint_name, "fight"]


@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_daily_process_stops_when_dungeon_entry_fails(
    monkeypatch,
    process_name: str,
    entrypoint_name: str,
) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            targeted_teaming_EXP=False,
            targeted_teaming_thread=False,
            daily_teams=1,
        ),
    )
    monkeypatch.setattr(scheme, entrypoint_name, lambda count: False)
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: pytest.fail("进本失败后不应选队"))
    monkeypatch.setattr(scheme.battle, "to_battle", lambda: pytest.fail("进本失败后不应开始战斗"))

    assert getattr(scheme, process_name)() is False
