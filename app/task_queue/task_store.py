"""设置控件和「当前选中的任务」之间的一层，作用同 MAA 的 GetTaskConfig<T>() / SetTaskConfig<T>()。

Base* 控件按字段名读写 store；任务设置页把 store.task 换成选中的任务，再让控件 load()。
字段怎么读写由 module.task_queue.fields 决定，这里只多发一个 changed 信号给界面刷新。
"""

from PySide6.QtCore import QObject, Signal

from module.config.task_queue import TaskBase
from module.task_queue.fields import get_field, set_field


class TaskStore(QObject):
    """给 Base* 控件用的 ValueStore：读写当前绑定的任务。没有绑定任务时读到 None，控件不会写入"""

    changed = Signal(str)  # 被修改的字段名

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task: TaskBase | None = None

    def get_value(self, key: str, default=None):
        if self.task is None:
            return default
        return get_field(self.task, key, default)

    def set_value(self, key: str, value) -> None:
        if self.task is not None and set_field(self.task, key, value):
            self.changed.emit(key)
