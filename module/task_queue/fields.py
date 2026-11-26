"""按字段名读写任务参数（不依赖 Qt）。任务设置页的控件通过它读写当前选中的任务。"""

from module.config.task_queue import TaskBase


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
