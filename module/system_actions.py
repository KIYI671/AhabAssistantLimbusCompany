import ctypes
import os
import subprocess
import threading
from collections.abc import Iterable

from module.after_completion_types import (
    ACTION_EXIT_AALC,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_GAME,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_LOCK,
    POWER_ACTION_NONE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_SLEEP,
    normalize_after_actions,
    normalize_after_completion_config,
    normalize_power_action,
)
from module.config import cfg
from module.logger import log

# SetThreadExecutionState 常量
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002
_power_keep_awake_lock = threading.Lock()
# SetThreadExecutionState 绑定调用线程，因此这里不能用单个全局 depth 表达状态。
_power_keep_awake_depths: dict[int, int] = {}


def _set_thread_execution_state(state: int) -> None:
    result = ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint32(state))
    if result == 0:
        raise ctypes.WinError()


def _update_keep_awake_depth(delta: int) -> tuple[int, int]:
    # 启用与释放必须在同一线程配对，避免误清理其他线程的执行状态。
    thread_id = threading.get_ident()
    with _power_keep_awake_lock:
        previous_depth = _power_keep_awake_depths.get(thread_id, 0)
        current_depth = max(0, previous_depth + delta)
        if current_depth == 0:
            _power_keep_awake_depths.pop(thread_id, None)
        else:
            _power_keep_awake_depths[thread_id] = current_depth
        return previous_depth, current_depth


def _run_command_result(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _run_command(command: list[str]) -> int:
    result = _run_command_result(command)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
        log.warning(f"命令执行失败 {' '.join(command)}: {detail}")
    return result.returncode


def get_after_completion_config() -> tuple[list[str], str]:
    # 统一在这里做规范化，避免 UI/任务层各自处理动作协议。
    return normalize_after_completion_config(
        cfg.get_value("after_completion_actions", []),
        cfg.get_value("after_completion_power_action", POWER_ACTION_NONE),
    )


def set_after_completion_config(actions: Iterable[str] | None, power_action: str | None) -> None:
    normalized_actions, normalized_power = normalize_after_completion_config(actions, power_action)
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
    使用 SetThreadExecutionState 阻止系统休眠和关闭显示器。
    状态绑定在调用线程上，线程结束时由 Windows 自动回收，无需手动 CloseHandle。
    这里按线程维护深度计数，避免跨线程共享全局状态导致错误释放。
    """
    if os.name != "nt":
        return

    try:
        if enable:
            previous_depth, _ = _update_keep_awake_depth(1)
            if previous_depth == 0:
                state = _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED
                _set_thread_execution_state(state)
                log.info("已启用运行时防息屏和保持显示器常亮")
        else:
            previous_depth, current_depth = _update_keep_awake_depth(-1)
            if previous_depth > 0 and current_depth == 0:
                _set_thread_execution_state(_ES_CONTINUOUS)
                log.info("已恢复系统默认息屏策略")
    except Exception:
        log.exception("设置防息屏状态失败")


def _action_exit_game() -> None:
    from module.game_and_screen import game_process, screen

    if os.name != "nt":
        log.info("跳过退出游戏：仅支持 Windows")
        return

    if cfg.get_value("simulator", False):
        if cfg.get_value("simulator_type", 0) == 0:
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
                ret = _run_command(["taskkill", "/F", "/PID", str(pid)])
                if ret == 0:
                    log.info("已执行：退出游戏")
                    return
        # 兜底：按进程名结束
        game_process_name = cfg.get_value("game_process_name", "")
        ret = _run_command(["taskkill", "/F", "/IM", game_process_name])
        if ret == 0:
            log.info("已执行：退出游戏（进程名兜底）")
        else:
            log.warning("退出游戏失败：未找到可关闭进程或权限不足")
    except Exception:
        log.exception("退出游戏失败")


def _action_exit_emulator() -> None:
    if not cfg.get_value("simulator", False):
        log.info("跳过退出模拟器：当前未启用模拟器模式")
        return
    if cfg.get_value("simulator_type", 0) == 0:
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
        if _run_command(["rundll32.exe", "powrprof.dll,SetSuspendState", "Sleep"]) == 0:
            log.info("已执行：睡眠")
        return
    if power_action == POWER_ACTION_HIBERNATE:
        if _run_command(["rundll32.exe", "powrprof.dll,SetSuspendState", "Hibernate"]) == 0:
            log.info("已执行：休眠")
        return
    if power_action == POWER_ACTION_SHUTDOWN:
        if _run_command(["shutdown", "/s", "/t", "30"]) == 0:
            log.info("已执行：关机（30 秒后）")
        return
    if power_action == POWER_ACTION_LOCK:
        if ctypes.windll.user32.LockWorkStation() == 0:
            log.warning("执行锁屏失败：LockWorkStation 返回 0")
        else:
            log.info("已执行：锁屏")
        return
    log.warning(f"未知电源动作: {power_action}")


def execute_after_completion(actions: Iterable[str], power_action: str) -> bool:
    """
    执行结束后动作。
    返回值表示是否需要退出 AALC（由 exit_aalc 动作决定）。
    """
    if os.name != "nt":
        return False

    normalized_actions = normalize_after_actions(actions)
    normalized_power = normalize_power_action(power_action)
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
        _action_power(normalized_power.value)
    except Exception:
        log.exception("执行电源动作失败")

    return should_exit_aalc
