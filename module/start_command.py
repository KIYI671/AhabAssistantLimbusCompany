"""命令行启动参数解析（不依赖 Qt，方便测试）。

支持的形式：
- `start`：按主界面的任务列表执行，结束后操作用用户默认设置
- `start --exit <数字>`：同上，结束后操作用旧版数字协议（0~8），仅本次有效
- `start --exit <定时任务 id>`：执行该定时任务自己的任务列表和结束后操作（Windows 计划任务使用这种形式，
  迁移来的定时任务 id 是 autodaily / autodaily2..4，新建的是 autodaily_<随机串>）
"""

from dataclasses import dataclass

from module.after_completion_types import LEGACY_AFTER_COMPLETION_TO_CONFIG, POWER_ACTION_NONE
from module.config.task_queue import AfterCompletion
from module.logger import log

DEFAULT_EXIT_TYPE = 5  # --exit 后缺少值时的旧版默认：退出 AALC


@dataclass(frozen=True)
class StartRequest:
    start: bool = False
    schedule_id: str | None = None
    """不为 None 时执行该定时任务"""

    after_completion: AfterCompletion | None = None
    """命令行指定的一次性结束后操作；None 表示没有指定"""


def is_schedule_id(value: str) -> bool:
    return value.startswith("autodaily")


def legacy_exit_to_after_completion(exit_type: int) -> AfterCompletion:
    actions, power_action = LEGACY_AFTER_COMPLETION_TO_CONFIG.get(exit_type, ((), POWER_ACTION_NONE))
    return AfterCompletion(actions=list(actions), power_action=power_action)


def parse_exit_value(value: str | None) -> tuple[int, bool]:
    """--exit 后面的旧版数字协议，返回 (退出类型, 是否消耗了这个参数)。

    值是可选的：缺少或不是数字时不消耗这个参数，按旧版默认退出 AALC；越界时为 0。
    """
    try:
        exit_type = int(value)
    except (TypeError, ValueError):
        log.info("命令行参数 --exit 后缺少退出类型，默认为5, 即退出AALC")
        return DEFAULT_EXIT_TYPE, False
    if not 0 <= exit_type <= 8:
        log.error(f'命令行参数 --exit 后输入值"{value}"越界')
        return 0, True
    return exit_type, True


def parse_start_command(argv: list[str]) -> StartRequest:
    """argv[0] 是程序路径；--exit 只在 start 之后才有效"""
    start = False
    schedule_id = None
    after_completion = None
    args = list(argv[1:])
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg == "start":
            start = True
        elif arg == "--exit" and start:
            value = args[index] if index < len(args) else None
            if value is not None and is_schedule_id(value):
                schedule_id = value
                index += 1
                continue
            exit_type, consumed = parse_exit_value(value)
            index += int(consumed)
            after_completion = legacy_exit_to_after_completion(exit_type)
    return StartRequest(start=start, schedule_id=schedule_id, after_completion=after_completion)
