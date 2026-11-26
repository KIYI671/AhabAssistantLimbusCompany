"""任务列表（task queue）与定时任务的配置模型。

主界面和每个定时任务各有一份有序的任务列表，列表里每一项是一个任务，
带自己的开关和参数。同一类任务可以出现多次，参数各自独立。
"""

import re
import uuid
from typing import Annotated, Callable, Literal, Union

from pydantic import BaseModel, Field, field_validator

from module.after_completion_types import (
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


def _resolve(task: TaskBase, key: str):
    """支持 "re_claim.mail" 这样的嵌套字段"""
    *parents, name = key.split(".")
    target = task
    for parent in parents:
        target = getattr(target, parent)
    return target, name


def get_field(task: TaskBase, key: str, default=None):
    target, name = _resolve(task, key)
    return getattr(target, name, default)


def set_field(task: TaskBase, key: str, value) -> bool:
    """写入任务字段，值有变化时返回 True"""
    target, name = _resolve(task, key)
    old = getattr(target, name)
    if isinstance(old, int) and not isinstance(old, bool) and isinstance(value, bool):
        value = int(value)  # 困牢等 0/1/2 字段：普通勾选写 1
    if old == value:
        return False
    setattr(target, name, value)
    return True


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
