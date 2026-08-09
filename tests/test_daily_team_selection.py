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


@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_daily_process_propagates_battle_failure(
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
    monkeypatch.setattr(scheme, entrypoint_name, lambda count: True)
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: True)
    monkeypatch.setattr(scheme.battle, "to_battle", lambda: None)
    monkeypatch.setattr(scheme.battle, "fight", lambda **kwargs: False)

    assert getattr(scheme, process_name)() is False


def test_daily_group_stops_after_a_failed_single_battle(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    outcomes = iter((True, False, True))

    monkeypatch.setattr(scheme, "back_init_menu", lambda: calls.append("home"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: calls.append("enkephalin"))

    def process() -> bool:
        calls.append("battle")
        return next(outcomes)

    assert scheme._run_daily_group(process, 3, 1, False) is False
    assert calls == ["battle", "battle"]


def test_daily_wrapper_stops_before_thread_after_exp_group_fails(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            set_EXP_count=1,
            set_thread_count=1,
            config=SimpleNamespace(use_continuous_combat=False),
            use_continuous_combat_select=1,
        ),
    )
    monkeypatch.setattr(scheme, "back_init_menu", lambda: calls.append("home"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: calls.append("enkephalin"))
    monkeypatch.setattr(scheme, "onetime_EXP_process", lambda: calls.append("exp") or False)
    monkeypatch.setattr(scheme, "onetime_thread_process", lambda: pytest.fail("经验本失败后不应继续纽本"))

    assert scheme.Daily_task_wrapper()() is False
    assert calls == ["home", "enkephalin", "exp"]


def test_daily_wrapper_stops_when_initial_home_recovery_fails(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            set_EXP_count=1,
            set_thread_count=1,
            config=SimpleNamespace(use_continuous_combat=False),
            use_continuous_combat_select=1,
        ),
    )
    monkeypatch.setattr(scheme, "back_init_menu", lambda: False)
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: pytest.fail("主页恢复失败后不应换饼"))
    monkeypatch.setattr(scheme, "onetime_EXP_process", lambda: pytest.fail("主页恢复失败后不应进经验本"))
    monkeypatch.setattr(scheme, "onetime_thread_process", lambda: pytest.fail("主页恢复失败后不应进纽本"))

    assert scheme.Daily_task_wrapper()() is False


def test_daily_group_stops_when_final_home_recovery_fails(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(scheme, "back_init_menu", lambda: calls.append("home") or False)
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: pytest.fail("回主页失败后不应换饼"))

    assert scheme._run_daily_group(lambda: calls.append("battle") or True, 1, 1, False) is False
    assert calls == ["battle", "home"]


def test_run_task_sequence_stops_after_terminal_daily_failure() -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []

    assert (
        scheme._run_task_sequence(
            [
                ("日常", lambda: calls.append("daily") or False),
                ("领奖", lambda: calls.append("reward") or True),
                ("换饼", lambda: calls.append("enkephalin") or True),
                ("镜牢", lambda: calls.append("mirror") or True),
            ]
        )
        is False
    )
    assert calls == ["daily"]


def test_run_task_sequence_keeps_legacy_none_success() -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []

    assert (
        scheme._run_task_sequence(
            [
                ("日常", lambda: calls.append("daily")),
                ("领奖", lambda: calls.append("reward") or True),
            ]
        )
        is True
    )
    assert calls == ["daily", "reward"]


def test_script_task_stops_when_existing_battle_fails(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(scheme, "init_game", lambda: None)
    monkeypatch.setattr(scheme, "_warn_if_game_monitor_hdr_enabled", lambda: None)
    monkeypatch.setattr(scheme.path_manager, "initialize_paths", lambda: None)
    monkeypatch.setattr(scheme.auto, "clear_img_cache", lambda: None)
    monkeypatch.setattr(scheme.auto, "click_element", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(scheme.battle, "fight", lambda: False)
    monkeypatch.setattr(scheme, "_run_task_sequence", lambda _tasks: pytest.fail("战斗失败后不应开始日常任务"))
    monkeypatch.setattr(scheme, "send_toast", lambda *_args, **_kwargs: calls.append("toast"))
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            skip_enkephalin=False,
            simulator=True,
            resonate_with_Ahab=False,
            daily_task=True,
            get_reward=False,
            buy_enkephalin=False,
            mirror=False,
            set_reduce_miscontact=False,
        ),
    )

    assert scheme.script_task() is False
    assert calls == []


def test_script_task_stops_before_completion_actions_when_task_sequence_fails(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(scheme, "init_game", lambda: None)
    monkeypatch.setattr(scheme, "_warn_if_game_monitor_hdr_enabled", lambda: None)
    monkeypatch.setattr(scheme, "_get_game_rendering_scale", lambda: None)
    monkeypatch.setattr(scheme, "send_toast", lambda *_args, **_kwargs: calls.append("toast"))
    monkeypatch.setattr(scheme, "execute_after_completion", lambda *_args: calls.append("complete"))
    monkeypatch.setattr(scheme, "get_after_completion_config", lambda: ([], None))
    monkeypatch.setattr(scheme, "_run_task_sequence", lambda _tasks: False)
    monkeypatch.setattr(scheme.path_manager, "initialize_paths", lambda: None)
    monkeypatch.setattr(scheme.auto, "clear_img_cache", lambda: None)
    monkeypatch.setattr(scheme.auto, "click_element", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            skip_enkephalin=False,
            simulator=False,
            set_win_size=1080,
            resonate_with_Ahab=False,
            daily_task=False,
            get_reward=False,
            buy_enkephalin=False,
            mirror=False,
            set_reduce_miscontact=False,
        ),
    )

    assert scheme.script_task() is False
    assert calls == []
