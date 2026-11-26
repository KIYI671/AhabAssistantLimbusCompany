"""定时任务的增删，以及和 Windows 计划任务保持一致（不依赖 Qt）。

每个启用的定时任务对应一个每天运行 `AALC.exe start --exit <定时任务 id>` 的系统计划任务。
改动定时任务后调用 sync：先删掉旧的计划任务，启用时再按当前时间注册，重复调用结果相同。
"""

from typing import Callable, Protocol

from module.config.task_queue import AfterCompletion, Schedule, TaskBase, copy_task, default_task_queue, time_is_valid
from module.logger import log


class Scheduler(Protocol):
    """utils.schedule_helper.ScheduleHelper 的接口；测试里换成假的"""

    def register_daily_task(self, name: str, args: str, hour: int, minute: int) -> None: ...

    def unregister_task(self, name: str) -> None: ...


def system_scheduler() -> Scheduler:
    from utils.schedule_helper import ScheduleHelper

    return ScheduleHelper()


def scheduler_task_name(schedule: Schedule) -> str:
    """迁移来的定时任务沿用旧的计划任务名，已注册的任务不用重新注册"""
    suffix = schedule.id[len("autodaily") :]
    if suffix == "" or suffix.isdigit():
        return f"AALC Daily Task{suffix}"
    return f"AALC Schedule {suffix.lstrip('_')}"


def sync(schedule: Schedule, scheduler: Scheduler) -> bool:
    """让系统计划任务和这个定时任务一致；注册失败时记日志并返回 False"""
    name = scheduler_task_name(schedule)
    try:
        scheduler.unregister_task(name)
        if schedule.enabled:
            hour, minute = (int(part) for part in schedule.time.split(":"))
            scheduler.register_daily_task(name, f"start --exit {schedule.id}", hour, minute)
    except Exception as e:
        log.error(f"同步定时任务 {schedule.id} 到系统计划任务失败: {e}")
        return False
    return True


def set_enabled(schedule: Schedule, enabled: bool, scheduler: Scheduler) -> bool:
    schedule.enabled = enabled
    return sync(schedule, scheduler)


def set_time(schedule: Schedule, time: str, scheduler: Scheduler) -> bool:
    """time 为 HH:mm；格式不对时不修改"""
    if not time_is_valid(time):
        return False
    schedule.time = time
    return sync(schedule, scheduler) if schedule.enabled else True


def add(schedules: list[Schedule]) -> Schedule:
    """新建一个关闭状态的定时任务，任务列表为四类任务各一项（全部不勾选）"""
    schedule = Schedule(tasks=default_task_queue())
    schedules.append(schedule)
    return schedule


def remove(schedules: list[Schedule], schedule: Schedule, scheduler: Scheduler) -> bool:
    if schedule not in schedules:
        return False
    schedule.enabled = False
    sync(schedule, scheduler)
    schedules.remove(schedule)
    return True


def number(schedule: Schedule, schedules: list[Schedule]) -> int:
    """没有自定义名称时显示「定时执行 N」用的 N"""
    if schedule in schedules:
        return schedules.index(schedule) + 1
    suffix = schedule.id[len("autodaily") :]
    return int(suffix) if suffix.isdigit() else 1


class ScheduleBook:
    """设置页对定时任务的操作。每个操作改完数据后，需要时同步系统计划任务，然后保存配置。

    schedules、main_tasks 是配置里的 list 本身（只会被就地修改）；get_scheduler 每次操作时
    才调用，这样只有用户真的改定时任务时才连接 Windows 计划任务服务。
    """

    def __init__(
        self,
        schedules: list[Schedule],
        main_tasks: list[TaskBase],
        get_scheduler: Callable[[], Scheduler],
        save: Callable[[], None],
    ):
        self.schedules = schedules
        self._main_tasks = main_tasks
        self._get_scheduler = get_scheduler
        self._save = save

    def add(self) -> Schedule:
        schedule = add(self.schedules)
        self._save()
        return schedule

    def remove(self, schedule: Schedule) -> bool:
        if not remove(self.schedules, schedule, self._get_scheduler()):
            return False
        self._save()
        return True

    def set_time(self, schedule: Schedule, time: str) -> None:
        set_time(schedule, time, self._get_scheduler())
        self._save()

    def set_enabled(self, schedule: Schedule, enabled: bool) -> None:
        set_enabled(schedule, enabled, self._get_scheduler())
        self._save()

    def apply_edit(
        self, schedule: Schedule, name: str, tasks: list[TaskBase], after_completion: AfterCompletion
    ) -> None:
        """保存编辑框的结果；名称去掉首尾空白，为空时用默认的「定时执行 N」"""
        schedule.name = name.strip() or None
        schedule.tasks = tasks
        schedule.after_completion = after_completion
        self._save()

    def copy_main_tasks(self) -> list[TaskBase]:
        """主界面任务列表的副本（含参数和勾选，id 重新生成）"""
        return [copy_task(task) for task in self._main_tasks]
