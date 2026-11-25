"""一次运行要执行的任务（RunPlan）以及执行时用到的纯逻辑。

这里不依赖 Qt、游戏窗口或全局配置对象，方便单独测试。
"""

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from module.config.task_queue import AfterCompletion, DailyTask, MirrorTask, TaskBase


@dataclass(frozen=True)
class RunPlan:
    tasks: tuple[TaskBase, ...]
    """本次要执行的任务（已过滤未启用项，深拷贝，运行期间界面修改不影响本次）"""

    after_completion: AfterCompletion | None = None
    """None：使用用户默认的结束后操作；定时任务 / 命令行 / 「仅本次生效」时传入"""

    source: str = "manual"
    """manual / schedule:<id> / cli，只用于日志"""

    @classmethod
    def from_queue(
        cls,
        queue: Iterable[TaskBase],
        after_completion: AfterCompletion | None = None,
        source: str = "manual",
    ) -> "RunPlan":
        tasks = tuple(task.model_copy(deep=True) for task in queue if task.enabled)
        if after_completion is not None:
            after_completion = after_completion.model_copy(deep=True)
        return cls(tasks, after_completion, source)

    def first(self, task_type: type[TaskBase]) -> TaskBase | None:
        return next((task for task in self.tasks if isinstance(task, task_type)), None)


@dataclass
class RunContext:
    finished_battle: str | None = None
    """启动时正在战斗、打完的是哪种日常本（"EXP" / "thread"），由第一个日常任务抵扣一次"""

    extra: dict = field(default_factory=dict)

    def take_finished_battle(self) -> str | None:
        value, self.finished_battle = self.finished_battle, None
        return value


def daily_times(task: DailyTask, finished_battle: str | None) -> tuple[int, int]:
    """返回 (经验本次数, 纽本次数)；启动时打完的那一场从对应次数里扣掉"""
    exp_times = task.exp_count - (1 if finished_battle == "EXP" else 0)
    thread_times = task.thread_count - (1 if finished_battle == "thread" else 0)
    return max(0, exp_times), max(0, thread_times)


def split_combat(times: int, max_times: int) -> list[int]:
    """连续作战：把 times 场拆成每次最多 max_times 场"""
    if times <= 0:
        return []
    max_times = max(1, max_times)
    batches = [max_times] * (times // max_times)
    if times % max_times:
        batches.append(times % max_times)
    return batches


def exp_team(task: DailyTask, day_key: str) -> int:
    """day_key 是 calculate_the_teams() 的返回值：1_2 / 3_4 / 5_6 / 7"""
    if task.exp_targeted:
        return getattr(task, f"exp_team_{day_key}", task.team)
    return task.team


def thread_team(task: DailyTask, weekday: int) -> int:
    """weekday：1 = 周一 … 7 = 周日"""
    if task.thread_targeted:
        return getattr(task, f"thread_team_{weekday}", task.team)
    return task.team


def is_hard_mirror(task: MirrorTask, auto_hard_mirror: bool, hard_mirror_chance: int) -> bool:
    """本次镜牢是否打困难：任务自己勾了困牢，或者开了自动困牢且还有剩余次数"""
    return task.hard_mirror > 0 or (auto_hard_mirror and hard_mirror_chance > 0)


def mirror_times(task: MirrorTask, hard: bool) -> int:
    if task.save_rewards and hard:
        return 1  # 保存困牢奖励：只打一次且不结算
    if task.infinite:
        return 9999
    return task.count


def team_usable(fixed_team_use: bool, fixed_team_use_select: int, hard: bool) -> bool:
    """队伍是否能用于当前难度。fixed_team_use_select：0 只打困牢，1 只打普牢"""
    if not fixed_team_use:
        return True
    return (fixed_team_use_select == 1 and not hard) or (fixed_team_use_select == 0 and hard)


def any_team_usable(teams: Sequence[tuple[bool, int]], hard: bool) -> bool:
    return any(team_usable(fixed, select, hard) for fixed, select in teams)
