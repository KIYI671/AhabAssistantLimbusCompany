import ctypes
import os
from collections.abc import Iterable
from enum import IntFlag

from module.config import cfg
from module.logger import log

# Windows API constants
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002

# 退出类动作（建议使用 IntFlag 管理，当前通过字符串映射以保持配置兼容性）
class ExitAction(IntFlag):
    NONE = 0
    EXIT_GAME = 1
    EXIT_EMULATOR = 2
    EXIT_AALC = 4

# 字符串映射常量（保持原有引用）
ACTION_EXIT_GAME = "exit_game"
ACTION_EXIT_EMULATOR = "exit_emulator"
ACTION_EXIT_AALC = "exit_aalc"

# 电源类动作（单选，最终执行）
POWER_ACTION_NONE = "none"
POWER_ACTION_SLEEP = "sleep"
POWER_ACTION_HIBERNATE = "hibernate"
POWER_ACTION_SHUTDOWN = "shutdown"
POWER_ACTION_LOCK = "lock"

AFTER_ACTIONS_ORDER = [
    ACTION_EXIT_GAME,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_AALC,
]

POWER_ACTIONS = [
    POWER_ACTION_NONE,
    POWER_ACTION_SLEEP,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_LOCK,
]

LEGACY_AFTER_COMPLETION_TO_CONFIG: dict[int, tuple[list[str], str]] = {
    0: ([], POWER_ACTION_NONE),
    1: ([], POWER_ACTION_SLEEP),
    2: ([], POWER_ACTION_HIBERNATE),
    3: ([], POWER_ACTION_SHUTDOWN),
    4: ([ACTION_EXIT_GAME], POWER_ACTION_NONE),
    5: ([ACTION_EXIT_AALC], POWER_ACTION_NONE),
    6: ([ACTION_EXIT_GAME, ACTION_EXIT_AALC], POWER_ACTION_NONE),
    7: ([ACTION_EXIT_EMULATOR], POWER_ACTION_NONE),
    8: ([ACTION_EXIT_EMULATOR, ACTION_EXIT_AALC], POWER_ACTION_NONE),
}


def _normalize_after_actions(actions: Iterable[str] | None) -> list[str]:
    if not actions:
        return []
    normalized: list[str] = []
    for name in AFTER_ACTIONS_ORDER:
        if name in actions and name not in normalized:
            normalized.append(name)
    return normalized


def _normalize_power_action(action: str | None) -> str:
    if action in POWER_ACTIONS:
        return action
    return POWER_ACTION_NONE


def get_after_completion_config() -> tuple[list[str], str]:
    actions = _normalize_after_actions(cfg.get_value("after_completion_actions", []))
    power_action = _normalize_power_action(cfg.get_value("after_completion_power_action", POWER_ACTION_NONE))
    return actions, power_action


def set_after_completion_config(actions: Iterable[str] | None, power_action: str | None) -> None:
    normalized_actions = _normalize_after_actions(actions)
    normalized_power = _normalize_power_action(power_action)
    cfg.set_value("after_completion_actions", normalized_actions)
    cfg.set_value("after_completion_power_action", normalized_power)


def autodaily_exit_to_after_completion_config(exit_setting: list[bool] | tuple[bool, ...]) -> tuple[list[str], str]:
    """
    将 autodaily_task_exit([exit_game, exit_aalc, sleep, hibernate, shutdown, lock]) 转换为统一动作配置。
    """
    values = list(exit_setting) if isinstance(exit_setting, (list, tuple)) else []
    while len(values) < 6:
        values.append(False)

    actions: list[str] = []
    if values[0]:
        actions.append(ACTION_EXIT_GAME)
    if values[1]:
        actions.append(ACTION_EXIT_AALC)

    power_action = POWER_ACTION_NONE
    if values[5]:
        power_action = POWER_ACTION_LOCK
    elif values[4]:
        power_action = POWER_ACTION_SHUTDOWN
    elif values[3]:
        power_action = POWER_ACTION_HIBERNATE
    elif values[2]:
        power_action = POWER_ACTION_SLEEP

    return actions, power_action


def apply_power_keep_awake(enable: bool) -> None:
    """
    使用 SetThreadExecutionState 阻止系统/显示器休眠；关闭时恢复默认策略。
    说明：该 API 只影响调用线程；需要在任务线程中启用并在同一线程关闭。
    """
    if os.name != "nt":
        return
    try:
        if enable:
            ret = ctypes.windll.kernel32.SetThreadExecutionState(
                _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED
            )
            if ret == 0:
                log.warning("启用防息屏失败：SetThreadExecutionState 返回 0")
            else:
                log.info("已启用运行时防息屏")
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
            log.info("已恢复系统默认息屏策略")
    except Exception as e:
        log.error(f"设置防息屏状态失败: {e}")


def _action_exit_game() -> None:
    from module.game_and_screen import game_process, screen

    if os.name != "nt":
        log.info("跳过退出游戏：仅支持 Windows")
        return

    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            if MumuControl.connection_device is not None:
                MumuControl.connection_device.close_current_app()
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            if SimulatorControl.connection_device is not None:
                SimulatorControl.connection_device.close_current_app()
        log.info("已执行：退出游戏（模拟器）")
        return

    if not game_process.check_game_alive():
        log.info("跳过退出游戏：游戏进程未运行")
        return

    try:
        hwnd = getattr(screen.handle, "hwnd", 0)
        if hwnd:
            try:
                import win32process
            except ImportError:
                win32process = None
            if win32process is not None:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                ret = os.system(f"taskkill /F /PID {pid}")
                if ret == 0:
                    log.info("已执行：退出游戏")
                    return
        # 兜底：按进程名结束
        ret = os.system(f"taskkill /F /IM {cfg.game_process_name}")
        if ret == 0:
            log.info("已执行：退出游戏（进程名兜底）")
        else:
            log.warning("退出游戏失败：未找到可关闭进程或权限不足")
    except Exception as e:
        log.error(f"退出游戏失败: {e}")


def _action_exit_emulator() -> None:
    if not cfg.simulator:
        log.info("跳过退出模拟器：当前未启用模拟器模式")
        return
    if cfg.simulator_type == 0:
        from module.automation.input_handlers.simulator.mumu_control import (
            MumuControl,
        )

        if MumuControl.connection_device is not None:
            MumuControl.connection_device.close_simulator()
            log.info("已执行：退出 MuMu 模拟器")
        else:
            log.info("跳过退出 MuMu：未建立连接")
    else:
        log.error("退出模拟器失败：暂不支持非 MuMu 模拟器的整机关闭")


def _action_power(power_action: str) -> None:
    if power_action == POWER_ACTION_NONE:
        return
    if power_action == POWER_ACTION_SLEEP:
        os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
        return
    if power_action == POWER_ACTION_HIBERNATE:
        os.system("rundll32.exe powrprof.dll,SetSuspendState Hibernate")
        return
    if power_action == POWER_ACTION_SHUTDOWN:
        os.system("shutdown /s /t 30")
        return
    if power_action == POWER_ACTION_LOCK:
        ctypes.windll.user32.LockWorkStation()
        return
    log.warning(f"未知电源动作: {power_action}")


def execute_after_completion(actions: Iterable[str], power_action: str) -> bool:
    """
    执行结束后动作。
    返回值表示是否需要退出 AALC（由 exit_aalc 动作决定）。
    """
    if os.name != "nt":
        return False

    normalized_actions = _normalize_after_actions(actions)
    normalized_power = _normalize_power_action(power_action)
    should_exit_aalc = ACTION_EXIT_AALC in normalized_actions

    for action in normalized_actions:
        if action == ACTION_EXIT_GAME:
            _action_exit_game()
        elif action == ACTION_EXIT_EMULATOR:
            _action_exit_emulator()
        elif action == ACTION_EXIT_AALC:
            # 在 finally 中统一退出，避免提前中断后续动作执行
            continue

    try:
        _action_power(normalized_power)
    except Exception as e:
        log.error(f"执行电源动作失败: {e}")

    return should_exit_aalc
