"""一次运行要执行的任务（RunPlan）以及执行时用到的纯逻辑。

这里不依赖 Qt、游戏窗口或全局配置对象，方便单独测试。
"""

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Protocol, Sequence

from module.config.task_queue import AfterCompletion, DailyTask, MirrorTask, Schedule, TaskBase


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


def daily_team(task: DailyTask, kind: str, day) -> int:
    """日常本用哪一队。kind 为 "exp" 或 "thread"；开了针对性配队时按星期选，否则用默认编队。

    day：经验本是 calculate_the_teams() 的返回值（1_2 / 3_4 / 5_6 / 7），纽本是星期几（1 = 周一 … 7 = 周日）
    """
    if getattr(task, f"{kind}_targeted"):
        return getattr(task, f"{kind}_team_{day}", task.team)
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


class TeamLike(Protocol):
    sinners_be_select: int
    fixed_team_use: bool
    fixed_team_use_select: int


@dataclass(frozen=True)
class Problem:
    """启动前检查发现的问题，界面负责把 kind 换成提示文字"""

    kind: str
    """no_tasks / no_team / team_without_sinners / no_team_for_hard / no_team_for_normal"""

    team: int | None = None
    """team_without_sinners 时是哪一队（从 1 开始）"""


def plan_problem(
    plan: RunPlan,
    selected_teams: Mapping[int, TeamLike],
    *,
    auto_hard_mirror: bool,
    hard_mirror_chance: int,
) -> Problem | None:
    """检查这次运行能不能开始；selected_teams 是启用的镜牢队伍 {队伍编号: 队伍设置}"""
    if not plan.tasks:
        return Problem("no_tasks")
    mirror_tasks = [task for task in plan.tasks if isinstance(task, MirrorTask)]
    if not mirror_tasks:
        return None
    return team_problem(selected_teams) or difficulty_problem(
        mirror_tasks, selected_teams, auto_hard_mirror, hard_mirror_chance
    )


def team_problem(selected_teams: Mapping[int, TeamLike]) -> Problem | None:
    """镜牢至少要启用一队，且每队都选了罪人"""
    if not selected_teams:
        return Problem("no_team")
    for number, team in selected_teams.items():
        if team.sinners_be_select == 0:
            return Problem("team_without_sinners", number)
    return None


def difficulty_problem(
    mirror_tasks: list[MirrorTask],
    selected_teams: Mapping[int, TeamLike],
    auto_hard_mirror: bool,
    hard_mirror_chance: int,
) -> Problem | None:
    """每个镜牢任务按自己的难度，看有没有能用的队伍"""
    team_uses = [(team.fixed_team_use, team.fixed_team_use_select) for team in selected_teams.values()]
    for task in mirror_tasks:
        hard = is_hard_mirror(task, auto_hard_mirror, hard_mirror_chance)
        if not any_team_usable(team_uses, hard):
            return Problem("no_team_for_hard" if hard else "no_team_for_normal")
    return None


def plan_for_request(
    request,
    task_queue: Iterable[TaskBase],
    schedules: Iterable[Schedule],
    once: AfterCompletion | None,
) -> tuple[RunPlan | None, Schedule | None]:
    """命令行 / 定时启动请求对应的运行计划和定时任务。

    - 定时任务：用它自己的任务列表和结束后操作；找不到这个定时任务时返回 (None, None)
    - 命令行指定了结束后操作：主界面任务列表 + 指定的结束后操作
    - 其他：主界面任务列表 + 「仅本次生效」的结束后操作（once，None 表示用默认设置）
    """
    if request is not None and request.schedule_id:
        schedule = next((s for s in schedules if s.id == request.schedule_id), None)
        if schedule is None:
            return None, None
        return RunPlan.from_queue(schedule.tasks, schedule.after_completion, source=f"schedule:{schedule.id}"), schedule
    after = request.after_completion if request is not None else None
    if after is None:
        after = once
    return RunPlan.from_queue(task_queue, after, source="cli"), None
