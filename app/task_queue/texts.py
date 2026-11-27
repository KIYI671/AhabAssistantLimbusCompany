"""任务列表用到的显示文字：任务类型名、任务标题（翻译 context 为 "TaskQueue"）。"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from module.config.task_queue import TaskBase
from module.task_queue import operations

CONTEXT = "TaskQueue"

TASK_TYPE_NAMES = {
    "daily": QT_TRANSLATE_NOOP("TaskQueue", "日常任务"),
    "reward": QT_TRANSLATE_NOOP("TaskQueue", "领取奖励"),
    "enkephalin": QT_TRANSLATE_NOOP("TaskQueue", "狂气换体"),
    "mirror": QT_TRANSLATE_NOOP("TaskQueue", "镜牢"),
}


def tr(text: str) -> str:
    return QCoreApplication.translate(CONTEXT, text)


def task_type_name(task_type: str) -> str:
    return tr(TASK_TYPE_NAMES.get(task_type, task_type))


def task_title(task: TaskBase) -> str:
    return operations.task_title(task, task_type_name)
