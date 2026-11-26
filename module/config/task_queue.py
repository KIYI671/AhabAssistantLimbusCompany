"""任务列表（task queue）与定时任务的配置模型。

主界面和每个定时任务各有一份有序的任务列表，列表里每一项是一个任务，
带自己的开关和参数。同一类任务可以出现多次，参数各自独立。
"""

import re
import uuid
from typing import Annotated, Callable, Literal, Union

from pydantic import BaseModel, Field, field_validator

from module.after_completion_types import (
    POWER_ACTION_NONE,
    autodaily_exit_to_after_completion_config,
    normalize_after_completion_config,
    serialize_after_actions,
    serialize_power_action,
)

TaskType = Literal["daily", "reward", "enkephalin", "mirror"]
TASK_TYPES: tuple[str, ...] = ("daily", "reward", "enkephalin", "mirror")


def new_task_id() -> str:
    return uuid.uuid4().hex[:8]


class TaskBase(BaseModel):
    id: str = Field(default_factory=new_task_id)
    """列表内唯一，用于界面选中、拖动和运行时高亮；复制任务时重新生成"""

    enabled: bool = True
    """是否执行"""

    name: str | None = None
    """自定义名称，None 时显示任务类型名"""


class RewardOptions(BaseModel):
    missions: bool = True
    """领取日常、周常及赛季任务奖励"""

    battle_pass: bool = True
    """领取通行证奖励"""

    mail: bool = True
    """领取邮件奖励"""

    def any(self) -> bool:
        return self.missions or self.battle_pass or self.mail


class DailyTask(TaskBase):
    type: Literal["daily"] = "daily"

    exp_count: int = Field(default=1, ge=0)
    """经验本次数"""

    thread_count: int = Field(default=3, ge=0)
    """纽本次数"""

    team: int = 1
    """使用的编队"""

    continuous_combat: bool = False
    """使用连续作战"""

    continuous_combat_max: int = 1
    """一场连续作战的最大次数"""

    exp_targeted: bool = False
    """经验本按星期指定编队"""

    exp_team_1_2: int = 1
    exp_team_3_4: int = 1
    exp_team_5_6: int = 1
    exp_team_7: int = 1

    thread_targeted: bool = False
    """纽本按星期指定编队"""

    thread_team_1: int = 1
    thread_team_2: int = 1
    thread_team_3: int = 1
    thread_team_4: int = 1
    thread_team_5: int = 1
    thread_team_6: int = 1
    thread_team_7: int = 1

    @field_validator("continuous_combat_max")
    @classmethod
    def _at_least_one(cls, v: int) -> int:
        return max(1, v)


class RewardTask(TaskBase, RewardOptions):
    type: Literal["reward"] = "reward"


class EnkephalinTask(TaskBase):
    type: Literal["enkephalin"] = "enkephalin"

    lunacy_times: int = Field(default=2, ge=0, le=3)
    """用狂气购买体力的次数，0 表示不买"""

    dr_grandet: bool = False
    """葛朗台模式"""


class MirrorTask(TaskBase):
    type: Literal["mirror"] = "mirror"

    count: int = Field(default=1, ge=0)
    """镜牢次数"""

    infinite: bool = False
    """无限坐牢"""

    hard_mirror: int = 0
    """困难镜牢：0 关，1 仅本次运行 AALC 期间有效（重启后清零），2 永久"""

    no_weekly_bonuses: int = 0
    """不使用每周加成：取值含义同 hard_mirror"""

    hard_single_bonuses: bool = False
    """困牢使用单次加成"""

    save_rewards: bool = False
    """保存困牢奖励不领"""

    floor_3_exit: bool = False
    """只打三层"""

    select_event_pack: bool = False
    """第五层选择（最左边）活动卡包"""

    skip_event_pack: bool = False
    """第五层跳过（最左边）活动卡包"""

    re_claim_rewards: bool = False
    """镜牢后再次领取奖励"""

    re_claim: RewardOptions = Field(default_factory=RewardOptions)
    """再次领取奖励时领取哪些"""

    not_skip_whitegossypium: bool = False
    """不跳过白棉花"""

    fight_to_last_man: bool = False
    """战斗直到全灭"""

    @field_validator("hard_mirror", "no_weekly_bonuses", mode="before")
    @classmethod
    def _session_flag(cls, v) -> int:
        return min(2, max(0, int(v or 0)))


TaskItem = Annotated[
    Union[DailyTask, RewardTask, EnkephalinTask, MirrorTask],
    Field(discriminator="type"),
]

TASK_CLASSES: dict[str, type[TaskBase]] = {
    "daily": DailyTask,
    "reward": RewardTask,
    "enkephalin": EnkephalinTask,
    "mirror": MirrorTask,
}


class AfterCompletion(BaseModel):
    actions: list[str] = Field(default_factory=list)
    """前置动作（可多选）：exit_game / exit_emulator / exit_aalc"""

    power_action: str = "none"
    """最终动作（单选）：none / sleep / hibernate / lock / shutdown"""

    @field_validator("actions", mode="before")
    @classmethod
    def _plain_actions(cls, v) -> list[str]:
        return serialize_after_actions(v)

    @field_validator("power_action", mode="before")
    @classmethod
    def _plain_power(cls, v) -> str:
        return serialize_power_action(v)

    def normalized(self) -> tuple[list[str], str]:
        return normalize_after_completion_config(self.actions, self.power_action)


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def time_is_valid(value) -> bool:
    """HH:mm，00:00 ~ 23:59"""
    return isinstance(value, str) and _TIME_RE.match(value) is not None


class Schedule(BaseModel):
    id: str = Field(default_factory=lambda: f"autodaily_{new_task_id()}")
    """也是 Windows 计划任务命令行 `start --exit <id>` 里的标识"""

    name: str | None = None
    enabled: bool = False
    time: str = "00:00"
    """每天执行的时间（HH:mm）"""

    tasks: list[TaskItem] = Field(default_factory=list)
    after_completion: AfterCompletion = Field(default_factory=AfterCompletion)

    @field_validator("time")
    @classmethod
    def _valid_time(cls, v: str) -> str:
        return v if time_is_valid(v) else "00:00"


def default_task_queue() -> list[TaskBase]:
    """新用户的默认任务列表：四类任务各一项，全部关闭"""
    return [cls(enabled=False) for cls in TASK_CLASSES.values()]


def new_task(task_type: str) -> TaskBase:
    return TASK_CLASSES[task_type]()


def copy_task(task: TaskBase) -> TaskBase:
    return task.model_copy(deep=True, update={"id": new_task_id()})


def task_title(task: TaskBase, type_name: Callable[[str], str]) -> str:
    """自定义名称，没有时用类型名"""
    return task.name or type_name(task.type)


class TaskQueue:
    """一份任务列表的编辑操作。直接修改传入的 list，保证 cfg 里的引用不变。

    type_name 把任务类型映射成显示名（界面传入翻译后的名称），用于默认标题、
    复制时的「名称 (2)」和改名时判断是否恢复默认名称。
    """

    def __init__(self, tasks: list[TaskBase], type_name: Callable[[str], str]):
        self.tasks = tasks
        self.type_name = type_name

    def title(self, task: TaskBase) -> str:
        return task_title(task, self.type_name)

    def find(self, task_id: str) -> TaskBase | None:
        return next((task for task in self.tasks if task.id == task_id), None)

    def add(self, task_type: str) -> TaskBase:
        task = new_task(task_type)
        self.tasks.append(task)
        return task

    def duplicate(self, task_id: str) -> TaskBase | None:
        """在原任务后面插入一份参数独立的副本，名称为「原名称 (N)」"""
        source = self.find(task_id)
        if source is None:
            return None
        clone = copy_task(source)
        clone.name = self._copy_name(self.title(source))
        self.tasks.insert(self.tasks.index(source) + 1, clone)
        return clone

    def _copy_name(self, title: str) -> str:
        titles = {self.title(task) for task in self.tasks}
        n = 2
        while f"{title} ({n})" in titles:
            n += 1
        return f"{title} ({n})"

    def remove(self, task_id: str) -> str | None:
        """删除任务，返回之后应选中的任务 id（列表空了返回 ""）；找不到返回 None"""
        task = self.find(task_id)
        if task is None:
            return None
        row = self.tasks.index(task)
        self.tasks.remove(task)
        if not self.tasks:
            return ""
        return self.tasks[min(row, len(self.tasks) - 1)].id

    def move(self, task_id: str, offset: int) -> bool:
        task = self.find(task_id)
        if task is None:
            return False
        row = self.tasks.index(task)
        target = row + offset
        if not 0 <= target < len(self.tasks):
            return False
        self.tasks.insert(target, self.tasks.pop(row))
        return True

    def reorder(self, task_ids: list[str]) -> bool:
        """按 id 顺序重排（拖动后同步用）；id 集合不一致或顺序没变时返回 False"""
        by_id = {task.id: task for task in self.tasks}
        if sorted(task_ids) != sorted(by_id) or task_ids == list(by_id):
            return False
        self.tasks[:] = [by_id[task_id] for task_id in task_ids]
        return True

    def rename(self, task_id: str, text: str) -> bool:
        """改名；清空或改成类型名时恢复默认名称。名称有变化时返回 True"""
        task = self.find(task_id)
        if task is None:
            return False
        text = text.strip()
        name = None if not text or text == self.type_name(task.type) else text
        if name == task.name:
            return False
        task.name = name
        return True

    def toggle(self, task_id: str) -> bool:
        task = self.find(task_id)
        if task is None:
            return False
        task.enabled = not task.enabled
        return True

    def set_all_enabled(self, enabled: bool) -> None:
        for task in self.tasks:
            task.enabled = enabled


def start_session(config) -> None:
    """AALC 启动时调用：主界面任务列表里「仅本次运行有效」的选项失效。

    定时任务每次运行都是新启动的 AALC，没有「本次」的说法，它的勾选一直有效，不清零。
    """
    reset_session_flags(config.task_queue)


def reset_session_flags(tasks: list[TaskBase]) -> None:
    """AALC 启动时调用：「仅本次运行有效」的困牢 / 不用每周加成（值为 1）清零"""
    for task in tasks:
        if isinstance(task, MirrorTask):
            if task.hard_mirror == 1:
                task.hard_mirror = 0
            if task.no_weekly_bonuses == 1:
                task.no_weekly_bonuses = 0


# ---------------------------------------------------------------------------
# 旧配置迁移
# ---------------------------------------------------------------------------

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
