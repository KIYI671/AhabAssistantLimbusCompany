"""旧版配置（主界面四个开关 + autodaily / autodaily2..4）迁移成任务列表和定时任务。

只在读取配置时由 module.config.config 调用一次。
"""

from module.after_completion_types import (
    POWER_ACTION_NONE,
    autodaily_exit_to_after_completion_config,
    serialize_after_actions,
    serialize_power_action,
)

# 旧版 config.example.yaml 的默认值；迁移时旧字段缺失就用这些
_LEGACY_DEFAULTS: dict = {
    "daily_task": False,
    "set_EXP_count": 1,
    "set_thread_count": 3,
    "daily_teams": 1,
    "targeted_teaming_EXP": False,
    "EXP_day_1_2": 1,
    "EXP_day_3_4": 1,
    "EXP_day_5_6": 1,
    "EXP_day_7": 1,
    "targeted_teaming_thread": False,
    "use_continuous_combat": False,
    "use_continuous_combat_select": 1,
    "get_reward": False,
    "claim_mission_rewards": True,
    "claim_battle_pass_rewards": True,
    "claim_mail_rewards": True,
    "buy_enkephalin": False,
    "set_lunacy_to_enkephalin": 2,
    "Dr_Grandet_mode": False,
    "mirror": False,
    "set_mirror_count": 1,
    "hard_mirror": False,
    "no_weekly_bonuses": False,
    "floor_3_exit": False,
    "infinite_dungeons": False,
    "save_rewards": False,
    "hard_mirror_single_bonuses": False,
    "select_event_pack": False,
    "skip_event_pack": False,
    "re_claim_rewards": False,
    "not_skip_whitegossypium": False,
    "fight_to_last_man": False,
}
_LEGACY_DEFAULTS.update({f"thread_day_{i}": 1 for i in range(1, 8)})

LEGACY_TASK_KEYS: tuple[str, ...] = tuple(_LEGACY_DEFAULTS)

# autodaily{N}_task 的下标顺序
_LEGACY_ORDER = ("daily", "reward", "enkephalin", "mirror")

LEGACY_SCHEDULE_SUFFIXES = ("", "2", "3", "4")


def legacy_schedule_keys(suffix: str) -> tuple[str, str, str, str]:
    """(开关, 勾选, 结束后, 时间) 四个旧字段名；注意时间字段是 autodaily_time2 而不是 autodaily2_time"""
    return (
        f"autodaily{suffix}",
        f"autodaily{suffix}_task",
        f"autodaily{suffix}_task_exit",
        f"autodaily_time{suffix}",
    )


def _legacy_flag(value) -> int:
    """旧的 hard_mirror / no_weekly_bonuses：False/0、True/1（仅本次）、2（永久）"""
    try:
        return min(2, max(0, int(value or 0)))
    except (TypeError, ValueError):
        return 0


def legacy_tasks(old: dict) -> list[dict]:
    """把旧版主界面的四个开关和全局参数转成任务列表（顺序同旧版执行顺序）。

    id 固定为任务类型名，和 config.example.yaml 的默认列表一致。
    """

    def get(key: str):
        value = old.get(key)
        return _LEGACY_DEFAULTS[key] if value is None else value

    reward = {
        "missions": bool(get("claim_mission_rewards")),
        "battle_pass": bool(get("claim_battle_pass_rewards")),
        "mail": bool(get("claim_mail_rewards")),
    }
    daily = {
        "id": "daily",
        "type": "daily",
        "enabled": bool(get("daily_task")),
        "exp_count": int(get("set_EXP_count")),
        "thread_count": int(get("set_thread_count")),
        "team": int(get("daily_teams")),
        "continuous_combat": bool(get("use_continuous_combat")),
        "continuous_combat_max": max(1, int(get("use_continuous_combat_select"))),
        "exp_targeted": bool(get("targeted_teaming_EXP")),
        "exp_team_1_2": int(get("EXP_day_1_2")),
        "exp_team_3_4": int(get("EXP_day_3_4")),
        "exp_team_5_6": int(get("EXP_day_5_6")),
        "exp_team_7": int(get("EXP_day_7")),
        "thread_targeted": bool(get("targeted_teaming_thread")),
        **{f"thread_team_{i}": int(get(f"thread_day_{i}")) for i in range(1, 8)},
    }
    mirror = {
        "id": "mirror",
        "type": "mirror",
        "enabled": bool(get("mirror")),
        "count": int(get("set_mirror_count")),
        "infinite": bool(get("infinite_dungeons")),
        "hard_mirror": _legacy_flag(get("hard_mirror")),
        "no_weekly_bonuses": _legacy_flag(get("no_weekly_bonuses")),
        "hard_single_bonuses": bool(get("hard_mirror_single_bonuses")),
        "save_rewards": bool(get("save_rewards")),
        "floor_3_exit": bool(get("floor_3_exit")),
        "select_event_pack": bool(get("select_event_pack")),
        "skip_event_pack": bool(get("skip_event_pack")),
        "re_claim_rewards": bool(get("re_claim_rewards")),
        "re_claim": dict(reward),
        "not_skip_whitegossypium": bool(get("not_skip_whitegossypium")),
        "fight_to_last_man": bool(get("fight_to_last_man")),
    }
    return [
        daily,
        {"id": "reward", "type": "reward", "enabled": bool(get("get_reward")), **reward},
        {
            "id": "enkephalin",
            "type": "enkephalin",
            "enabled": bool(get("buy_enkephalin")),
            "lunacy_times": min(3, max(0, int(get("set_lunacy_to_enkephalin")))),
            "dr_grandet": bool(get("Dr_Grandet_mode")),
        },
        mirror,
    ]


def legacy_schedules(old: dict) -> list[dict]:
    """把 autodaily / autodaily2..4 转成定时任务。

    任务参数复制主界面的（旧版定时任务本来就读全局参数），开关取 autodaily{N}_task。
    id 沿用旧名字，已注册的 Windows 计划任务 `start --exit autodaily2` 不需要重新注册。
    """
    schedules = []
    for n, suffix in enumerate(LEGACY_SCHEDULE_SUFFIXES, start=1):
        enabled_key, task_key, exit_key, time_key = legacy_schedule_keys(suffix)
        flags = list(old.get(task_key) or [])
        flags += [False] * (len(_LEGACY_ORDER) - len(flags))
        tasks = legacy_tasks(old)
        for item, flag in zip(tasks, flags):
            item["enabled"] = bool(flag)
            item.pop("id", None)
            # 旧版定时运行时 AALC 是新启动的，「仅本次」（1）的困牢 / 不用每周加成已经失效
            for key in ("hard_mirror", "no_weekly_bonuses"):
                if item.get(key) == 1:
                    item[key] = 0
        actions, power_action = autodaily_exit_to_after_completion_config(old.get(exit_key) or [])
        schedules.append(
            {
                "id": enabled_key,
                "name": None,
                "enabled": bool(old.get(enabled_key, False)),
                "time": old.get(time_key) or "00:00",
                "tasks": tasks,
                "after_completion": {
                    "actions": serialize_after_actions(actions),
                    "power_action": serialize_power_action(power_action),
                },
            }
        )
    return schedules


# 旧版 default_page（右侧设置页下标）→ last_selected_task
LEGACY_PAGE_TO_SELECTION = ("set_windows", "daily", "reward", "enkephalin", "mirror")


def migrate_legacy_config(old: dict) -> None:
    """就地把旧版字段迁移成 task_queue / schedules，并删掉旧字段。已有新字段时不覆盖。"""
    if "task_queue" not in old:
        old["task_queue"] = legacy_tasks(old)
    if "schedules" not in old:
        old["schedules"] = legacy_schedules(old)

    page = old.pop("default_page", None)
    if "last_selected_task" not in old:
        try:
            old["last_selected_task"] = LEGACY_PAGE_TO_SELECTION[int(page)]
        except (TypeError, ValueError, IndexError):
            old["last_selected_task"] = "set_windows"

    # 旧版「仅本次生效」的收尾设置会被意外写盘：keep_after_completion=False 时
    # 启动会把收尾动作清空，所以用户实际的默认收尾就是「什么也不做」。
    if old.pop("keep_after_completion", True) is False:
        old["after_completion_actions"] = []
        old["after_completion_power_action"] = serialize_power_action(POWER_ACTION_NONE)

    for key in LEGACY_TASK_KEYS:
        old.pop(key, None)
    for suffix in LEGACY_SCHEDULE_SUFFIXES:
        for key in legacy_schedule_keys(suffix):
            old.pop(key, None)
