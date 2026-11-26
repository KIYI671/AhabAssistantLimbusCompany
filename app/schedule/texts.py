"""设置页「定时执行」和主界面用到的显示文字：结束后操作、定时任务摘要和名称。"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from app.task_queue.queue_list import task_title
from module.after_completion_types import (
    ACTION_EXIT_AALC,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_GAME,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_LOCK,
    POWER_ACTION_NONE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_SLEEP,
)
from module.config.task_queue import AfterCompletion, Schedule
from module.schedule.book import number as schedule_number

CONTEXT = "ScheduleEditor"


def tr(text: str) -> str:
    return QCoreApplication.translate(CONTEXT, text)


EXIT_ACTIONS = [
    (ACTION_EXIT_GAME, QT_TRANSLATE_NOOP("ScheduleEditor", "退出游戏")),
    (ACTION_EXIT_EMULATOR, QT_TRANSLATE_NOOP("ScheduleEditor", "退出模拟器")),
    (ACTION_EXIT_AALC, QT_TRANSLATE_NOOP("ScheduleEditor", "退出AALC")),
]
POWER_ACTIONS = [
    (POWER_ACTION_NONE, QT_TRANSLATE_NOOP("ScheduleEditor", "无")),
    (POWER_ACTION_SLEEP, QT_TRANSLATE_NOOP("ScheduleEditor", "睡眠")),
    (POWER_ACTION_HIBERNATE, QT_TRANSLATE_NOOP("ScheduleEditor", "休眠")),
    (POWER_ACTION_LOCK, QT_TRANSLATE_NOOP("ScheduleEditor", "锁屏")),
    (POWER_ACTION_SHUTDOWN, QT_TRANSLATE_NOOP("ScheduleEditor", "关机")),
]


def after_completion_text(after: AfterCompletion) -> str:
    actions, power_action = after.normalized()
    parts = [tr(text) for action, text in EXIT_ACTIONS if action in actions]
    if power_action != POWER_ACTION_NONE:
        parts.append(tr(dict(POWER_ACTIONS)[power_action]))
    return "、".join(parts) if parts else tr(QT_TRANSLATE_NOOP("ScheduleEditor", "什么也不做"))


def schedule_summary(schedule: Schedule) -> str:
    names = [task_title(task) for task in schedule.tasks if task.enabled]
    tasks = "、".join(names) if names else tr(QT_TRANSLATE_NOOP("ScheduleEditor", "没有启用的任务"))
    return tr(QT_TRANSLATE_NOOP("ScheduleEditor", "{0}；结束后：{1}")).format(
        tasks, after_completion_text(schedule.after_completion)
    )


def schedule_title(schedule: Schedule, schedules: list | None = None) -> str:
    """定时任务显示名：自定义名称，否则「定时执行 N」"""
    if schedule.name:
        return schedule.name
    number = schedule_number(schedule, schedules or [])
    # 翻译 context 沿用原来的 "TaskQueue"
    return QCoreApplication.translate("TaskQueue", QT_TRANSLATE_NOOP("TaskQueue", "定时执行 {0}")).format(number)
