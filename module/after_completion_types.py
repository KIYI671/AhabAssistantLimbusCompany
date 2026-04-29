"""结束后动作系统的类型与兼容常量。

内部可以使用 Enum/Flag 表达语义，配置层仍统一落为字符串协议。
"""

from collections.abc import Iterable
from enum import IntFlag, StrEnum


class ExitAction(StrEnum):
    EXIT_GAME = "exit_game"
    EXIT_EMULATOR = "exit_emulator"
    EXIT_AALC = "exit_aalc"


class ExitActionFlag(IntFlag):
    NONE = 0
    EXIT_GAME = 1
    EXIT_EMULATOR = 2
    EXIT_AALC = 4


class PowerAction(StrEnum):
    NONE = "none"
    SLEEP = "sleep"
    HIBERNATE = "hibernate"
    SHUTDOWN = "shutdown"
    LOCK = "lock"


ACTION_EXIT_GAME = ExitAction.EXIT_GAME
ACTION_EXIT_EMULATOR = ExitAction.EXIT_EMULATOR
ACTION_EXIT_AALC = ExitAction.EXIT_AALC

POWER_ACTION_NONE = PowerAction.NONE
POWER_ACTION_SLEEP = PowerAction.SLEEP
POWER_ACTION_HIBERNATE = PowerAction.HIBERNATE
POWER_ACTION_SHUTDOWN = PowerAction.SHUTDOWN
POWER_ACTION_LOCK = PowerAction.LOCK

AFTER_ACTIONS_ORDER: tuple[ExitAction, ...] = (
    ACTION_EXIT_GAME,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_AALC,
)

POWER_ACTIONS: tuple[PowerAction, ...] = (
    POWER_ACTION_NONE,
    POWER_ACTION_SLEEP,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_LOCK,
)

_EXIT_ACTION_TO_FLAG: dict[ExitAction, ExitActionFlag] = {
    ACTION_EXIT_GAME: ExitActionFlag.EXIT_GAME,
    ACTION_EXIT_EMULATOR: ExitActionFlag.EXIT_EMULATOR,
    ACTION_EXIT_AALC: ExitActionFlag.EXIT_AALC,
}

# 引入版本：v1772205660 (PR #593)
# 旧数字配置的兼容映射集中维护在这里，避免业务层各自复制一份协议。
LEGACY_AFTER_COMPLETION_TO_CONFIG: dict[int, tuple[tuple[ExitAction, ...], PowerAction]] = {
    0: ((), POWER_ACTION_NONE),
    1: ((), POWER_ACTION_SLEEP),
    2: ((), POWER_ACTION_HIBERNATE),
    3: ((), POWER_ACTION_SHUTDOWN),
    4: ((ACTION_EXIT_GAME,), POWER_ACTION_NONE),
    5: ((ACTION_EXIT_AALC,), POWER_ACTION_NONE),
    6: ((ACTION_EXIT_GAME, ACTION_EXIT_AALC), POWER_ACTION_NONE),
    7: ((ACTION_EXIT_EMULATOR,), POWER_ACTION_NONE),
    8: ((ACTION_EXIT_EMULATOR, ACTION_EXIT_AALC), POWER_ACTION_NONE),
}


def parse_exit_action(value: str | ExitAction | None) -> ExitAction | None:
    if isinstance(value, ExitAction):
        return value
    if isinstance(value, str):
        try:
            return ExitAction(value)
        except ValueError:
            return None
    return None


def build_exit_action_flag(
    actions: Iterable[str | ExitAction] | str | ExitAction | None,
) -> ExitActionFlag:
    if actions is None:
        return ExitActionFlag.NONE

    candidates = [actions] if isinstance(actions, str) else actions
    flags = ExitActionFlag.NONE
    for raw_action in candidates:
        action = parse_exit_action(raw_action)
        if action is not None:
            flags |= _EXIT_ACTION_TO_FLAG[action]
    return flags


def normalize_after_actions(
    actions: Iterable[str | ExitAction] | str | ExitAction | None,
) -> list[ExitAction]:
    flags = build_exit_action_flag(actions)
    return [action for action in AFTER_ACTIONS_ORDER if flags & _EXIT_ACTION_TO_FLAG[action]]


def serialize_after_actions(actions: Iterable[str | ExitAction] | str | ExitAction | None) -> list[str]:
    return [action.value for action in normalize_after_actions(actions)]


def normalize_power_action(action: str | PowerAction | None) -> PowerAction:
    if isinstance(action, PowerAction):
        return action
    if isinstance(action, str):
        try:
            return PowerAction(action)
        except ValueError:
            return POWER_ACTION_NONE
    return POWER_ACTION_NONE


def serialize_power_action(action: str | PowerAction | None) -> str:
    return normalize_power_action(action).value


def normalize_after_completion_config(
    actions: Iterable[str | ExitAction] | str | ExitAction | None,
    power_action: str | PowerAction | None,
) -> tuple[list[str], str]:
    # 对外统一返回可持久化的字符串结构，避免把 Enum 直接写入配置。
    return serialize_after_actions(actions), serialize_power_action(power_action)
