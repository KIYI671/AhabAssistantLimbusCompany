"""任务列表配置模型与旧配置迁移的测试。"""

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLE_PATH = REPO_ROOT / "assets" / "config" / "config.example.yaml"


@pytest.fixture(scope="module")
def tq(isolated_import):
    """返回 (task_queue 模块, config_typing 模块)"""
    return isolated_import("module.config.task_queue"), isolated_import("module.config.config_typing")


@pytest.fixture(scope="module")
def legacy(isolated_import):
    return isolated_import("module.config.task_queue_legacy")


def _example() -> dict:
    return YAML().load(EXAMPLE_PATH.read_text(encoding="utf-8"))


# 一份旧版配置（取自上游 #515 的日志，去掉无关字段）
LEGACY = {
    "keep_after_completion": True,
    "after_completion_actions": ["exit_game"],
    "after_completion_power_action": "none",
    "autodaily": False,
    "autodaily_task": [True, True, True, False],
    "autodaily_task_exit": [True, True, False, False, False],
    "autodaily_time": "13:30",
    "autodaily2": True,
    "autodaily2_task": [False, False, True, False],
    "autodaily2_task_exit": [True, False, False, False, True, False, True],
    "autodaily_time2": "23:52",
    "autodaily3": False,
    "autodaily3_task": [False, False, False, False],
    "autodaily3_task_exit": [False, False, False, False, False],
    "autodaily_time3": "00:00",
    "default_page": 4,
    "daily_task": True,
    "set_EXP_count": 1,
    "set_thread_count": 3,
    "daily_teams": 5,
    "targeted_teaming_EXP": False,
    "EXP_day_1_2": 1,
    "EXP_day_3_4": 2,
    "EXP_day_5_6": 3,
    "EXP_day_7": 4,
    "targeted_teaming_thread": True,
    **{f"thread_day_{i}": i for i in range(1, 8)},
    "use_continuous_combat": True,
    "use_continuous_combat_select": 0,
    "get_reward": True,
    "claim_mission_rewards": True,
    "claim_battle_pass_rewards": False,
    "claim_mail_rewards": True,
    "buy_enkephalin": 1,
    "set_lunacy_to_enkephalin": 2,
    "Dr_Grandet_mode": False,
    "mirror": False,
    "set_mirror_count": 2,
    "hard_mirror": 2,
    "no_weekly_bonuses": 1,
    "floor_3_exit": False,
    "infinite_dungeons": False,
    "save_rewards": False,
    "hard_mirror_single_bonuses": True,
    "select_event_pack": False,
    "skip_event_pack": True,
    "re_claim_rewards": True,
    "not_skip_whitegossypium": False,
    "fight_to_last_man": True,
}


def _migrated(legacy_module, extra: dict | None = None) -> dict:
    old = {**LEGACY, **(extra or {})}
    legacy_module.migrate_legacy_config(old)
    return old


def test_example_defaults_validate(tq):
    _, config_typing = tq
    model = config_typing.ConfigModel(**_example())
    assert [t.type for t in model.task_queue] == ["daily", "reward", "enkephalin", "mirror"]
    assert all(t.enabled is False for t in model.task_queue)
    assert model.schedules == []
    assert len({t.id for t in model.task_queue}) == 4


def test_main_queue_keeps_order_switches_and_params(tq, legacy):
    task_queue, config_typing = tq
    model = config_typing.ConfigModel(**{**_example(), **_migrated(legacy)})
    daily, reward, enkephalin, mirror = model.task_queue

    assert [t.id for t in model.task_queue] == ["daily", "reward", "enkephalin", "mirror"]
    assert (daily.enabled, reward.enabled, enkephalin.enabled, mirror.enabled) == (True, True, True, False)

    assert (daily.exp_count, daily.thread_count, daily.team) == (1, 3, 5)
    assert daily.continuous_combat is True and daily.continuous_combat_max == 1
    assert daily.exp_targeted is False and daily.exp_team_3_4 == 2 and daily.exp_team_7 == 4
    assert daily.thread_targeted is True
    assert [getattr(daily, f"thread_team_{i}") for i in range(1, 8)] == list(range(1, 8))

    assert (reward.missions, reward.battle_pass, reward.mail) == (True, False, True)
    assert enkephalin.lunacy_times == 2 and enkephalin.dr_grandet is False

    assert mirror.count == 2
    assert mirror.hard_mirror == 2  # 右键永久
    assert mirror.no_weekly_bonuses == 1  # 左键仅本次，启动时由 reset_session_flags 清掉
    assert mirror.hard_single_bonuses and mirror.skip_event_pack and mirror.fight_to_last_man
    assert mirror.re_claim_rewards is True
    assert (mirror.re_claim.missions, mirror.re_claim.battle_pass, mirror.re_claim.mail) == (True, False, True)


def test_schedules_copy_params_and_use_own_switches(tq, legacy):
    task_queue, config_typing = tq
    model = config_typing.ConfigModel(**{**_example(), **_migrated(legacy)})

    assert [s.id for s in model.schedules] == ["autodaily", "autodaily2", "autodaily3", "autodaily4"]
    first, second, third, fourth = model.schedules
    assert (first.enabled, first.time) == (False, "13:30")
    assert [t.enabled for t in first.tasks] == [True, True, True, False]
    assert (second.enabled, second.time) == (True, "23:52")
    assert [t.enabled for t in second.tasks] == [False, False, True, False]
    # 旧版本没有 autodaily4 字段
    assert (fourth.enabled, fourth.time) == (False, "00:00")
    assert all(not t.enabled for t in fourth.tasks)

    # 参数是主界面的副本
    assert second.tasks[0].team == 5 and second.tasks[3].count == 2
    # 定时任务每次都是新启动 AALC：旧版「仅本次」的勾选（1）在定时运行时本来就已失效，迁移成关闭；永久（2）保留
    assert (second.tasks[3].hard_mirror, second.tasks[3].no_weekly_bonuses) == (2, 0)

    # 5 位旧格式：退出游戏 → 同时退出模拟器；退出 AALC
    assert first.after_completion.actions == ["exit_game", "exit_emulator", "exit_aalc"]
    assert first.after_completion.power_action == "none"
    # 7 位格式：退出游戏 + 关机 + 退出模拟器
    assert second.after_completion.actions == ["exit_game", "exit_emulator"]
    assert second.after_completion.power_action == "shutdown"
    assert third.after_completion.actions == [] and third.after_completion.power_action == "none"

    # 每个定时任务的任务 id 各不相同，也不和主界面重复
    ids = [t.id for s in model.schedules for t in s.tasks] + [t.id for t in model.task_queue]
    assert len(ids) == len(set(ids))


def test_old_keys_removed_and_selection_mapped(legacy):
    migrated = _migrated(legacy)
    for key in ("daily_task", "set_mirror_count", "autodaily2_task", "autodaily_time3", "keep_after_completion"):
        assert key not in migrated
    assert migrated["last_selected_task"] == "mirror"
    assert migrated["after_completion_actions"] == ["exit_game"]


def test_unsaved_after_completion_resets_to_nothing(legacy):
    migrated = _migrated(
        legacy,
        {
            "keep_after_completion": False,
            "after_completion_actions": ["exit_game"],
            "after_completion_power_action": "shutdown",
        },
    )
    assert migrated["after_completion_actions"] == []
    assert migrated["after_completion_power_action"] == "none"


def test_migration_does_not_overwrite_new_fields(legacy):
    existing = [{"id": "x", "type": "mirror", "count": 9}]
    migrated = _migrated(legacy, {"task_queue": existing, "schedules": []})
    assert migrated["task_queue"] is existing
    assert migrated["schedules"] == []


def test_minimal_legacy_config_uses_old_defaults(tq, legacy):
    task_queue, config_typing = tq
    old: dict = {}
    legacy.migrate_legacy_config(old)
    model = config_typing.ConfigModel(**{**_example(), **old})
    daily, reward, enkephalin, mirror = model.task_queue
    assert not any(t.enabled for t in model.task_queue)
    assert (daily.exp_count, daily.thread_count, enkephalin.lunacy_times, mirror.count) == (1, 3, 2, 1)
    assert len(model.schedules) == 4


def test_reset_session_flags(tq):
    task_queue, _ = tq
    tasks = [
        task_queue.MirrorTask(hard_mirror=1, no_weekly_bonuses=2),
        task_queue.MirrorTask(hard_mirror=2, no_weekly_bonuses=1),
        task_queue.DailyTask(),
    ]
    task_queue.reset_session_flags(tasks)
    assert (tasks[0].hard_mirror, tasks[0].no_weekly_bonuses) == (0, 2)
    assert (tasks[1].hard_mirror, tasks[1].no_weekly_bonuses) == (2, 0)


def test_copy_task_is_independent(tq):
    task_queue, _ = tq
    original = task_queue.MirrorTask(name="困牢", count=3)
    clone = task_queue.copy_task(original)
    assert clone.id != original.id
    assert (clone.name, clone.count, clone.type) == ("困牢", 3, "mirror")
    clone.re_claim.mail = False
    assert original.re_claim.mail is True


def test_schedule_time_validated(tq):
    task_queue, _ = tq
    assert task_queue.Schedule(time="7:5").time == "00:00"
    assert task_queue.Schedule(time="07:05").time == "07:05"
    assert task_queue.Schedule().id.startswith("autodaily_")


def test_dump_is_plain_yaml(tq, legacy):
    task_queue, config_typing = tq
    model = config_typing.ConfigModel(**{**_example(), **_migrated(legacy)})
    buffer = io.StringIO()
    YAML().dump(model.model_dump(), buffer)
    reloaded = YAML(typ="safe").load(buffer.getvalue())
    assert reloaded["schedules"][1]["after_completion"]["power_action"] == "shutdown"
    assert reloaded["task_queue"][3]["re_claim"]["battle_pass"] is False
    again = config_typing.ConfigModel(**reloaded)
    assert again.model_dump() == model.model_dump()


def test_new_objects_dump_as_plain_yaml(tq):
    """新建的定时任务 / 任务的默认值也必须是普通类型，否则整份配置写盘失败"""
    task_queue, _ = tq
    schedule = task_queue.Schedule(tasks=task_queue.default_task_queue())
    buffer = io.StringIO()
    YAML().dump(schedule.model_dump(), buffer)
    assert "power_action: none" in buffer.getvalue()


def test_session_flags_only_reset_main_queue(tq, legacy):
    """定时任务没有「仅本次运行」的说法，勾选值 1 也表示一直有效，启动时不清零"""
    task_queue, config_typing = tq
    data = {**_example(), **_migrated(legacy)}
    data["schedules"][0]["tasks"][3]["hard_mirror"] = 1
    data["task_queue"][3]["hard_mirror"] = 1
    model = config_typing.ConfigModel(**data)
    task_queue.start_session(model)
    assert model.task_queue[3].hard_mirror == 0
    assert model.schedules[0].tasks[3].hard_mirror == 1
