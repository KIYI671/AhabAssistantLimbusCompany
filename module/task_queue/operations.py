"""一份任务列表的编辑操作：增删、复制、排序、改名、勾选（不依赖 Qt）。

主界面和定时任务编辑框的任务列表控件都只调用这里，数据怎么变由这里决定。
"""

from typing import Callable

from module.config.task_queue import TaskBase, copy_task, new_task


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
