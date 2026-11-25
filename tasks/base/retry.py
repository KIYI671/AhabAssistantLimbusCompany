import os
import platform
import time
from time import sleep

import psutil

try:
    import win32process
except ImportError:  # 非 Windows 平台没有 pywin32
    win32process = None

from module.automation import auto
from module.config import cfg
from module.game_and_screen import screen
from module.logger import log
from utils.utils import check_game_running

_last_title_screen_tap_time = 0.0
_last_simulator_alive_check_time = 0.0
DEFAULT_TASK_STALL_TIMEOUT = 90
MIN_TASK_STALL_TIMEOUT = 30


def ensure_simulator_game_started() -> bool:
    """模拟器模式下确认游戏仍在前台，不在时尝试拉起游戏。"""
    global _last_simulator_alive_check_time
    if not cfg.simulator:
        return False

    now = time.time()
    if now - _last_simulator_alive_check_time < 5:
        return False
    _last_simulator_alive_check_time = now

    if cfg.simulator_type == 0:
        from module.automation.input_handlers.simulator.mumu_control import (
            MumuControl,
        )

        connection_device = MumuControl.connection_device
    else:
        from module.automation.input_handlers.simulator.simulator_control import (
            SimulatorControl,
        )

        connection_device = SimulatorControl.connection_device

    if connection_device is None:
        return False

    if connection_device.check_game_alive():
        return False

    log.info("检测到游戏未运行或不在前台，尝试自动启动游戏")
    connection_device.start_game()
    sleep(3)
    return True


def click_title_screen_safely() -> None:
    """标题页点击入口，避开账号、清缓存和中间弹窗区域。"""
    global _last_title_screen_tap_time
    if not cfg.simulator:
        auto.mouse_click_blank()
        return

    now = time.time()
    if now - _last_title_screen_tap_time < 15:
        return
    _last_title_screen_tap_time = now

    height = int(cfg.set_win_size or 1080)
    width = int(height * 16 / 9)
    tap_points = ((0.86, 0.80), (0.74, 0.83), (0.91, 0.58))
    index = int(now // 10) % len(tap_points)
    x_ratio, y_ratio = tap_points[index]
    auto.mouse_click(int(width * x_ratio), int(height * y_ratio))


def _game_processes():
    """遍历名字含 cfg.game_process_name 的进程（与下面的退出等待同一判据）。"""
    for proc in psutil.process_iter(["name"]):
        try:
            proc_name = proc.info["name"] or ""
            if proc_name and cfg.game_process_name.lower() in proc_name.lower():
                yield proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def _alive_game_processes(procs):
    """过滤掉已退出/僵尸的进程对象（psutil 的状态查询本身也会抛异常）。"""
    alive = []
    for proc in procs:
        try:
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                alive.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return alive


def _terminate_game_processes(grace: float = 10.0) -> int:
    """非 Windows 平台的结束游戏：先 SIGTERM，宽限期内没退出再 SIGKILL。

    返回被处理的进程数（0 = 本来就没在跑，属正常情况）。
    """
    procs = list(_game_processes())
    if not procs:
        return 0
    for proc in procs:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    deadline = time.time() + grace
    while time.time() < deadline and _alive_game_processes(procs):
        sleep(1)
    lingering = _alive_game_processes(procs)
    for proc in lingering:
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    if lingering:
        log.warning(f"游戏进程未在 {grace:.0f}s 内退出，已强制结束 {len(lingering)} 个")
    return len(procs)


def kill_game():
    """关闭游戏"""
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            connection_device = MumuControl.connection_device
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            connection_device = SimulatorControl.connection_device
        if connection_device is None:
            log.warning("模拟器连接当前不可用，跳过关闭游戏；后续初始化将重建连接")
            return
        connection_device.close_current_app()
        return
    if platform.system() == "Windows":
        from module.game_and_screen import screen

        _, pid = win32process.GetWindowThreadProcessId(screen.handle.hwnd)
        os.system(f"taskkill /F /PID {pid}")
    else:
        # 非 Windows：此前这里直接落到 sleep(10)，进程根本没被结束，
        # 下面 30 s 的退出等待必然超时（Linux + Proton / 模拟器外置进程均命中）
        _terminate_game_processes()
    sleep(10)
    wait_start = time.time()
    while True:
        # 仅当遍历后找不到任何游戏进程时，才认为游戏已退出
        if not list(_game_processes()):
            break
        if time.time() - wait_start > 30:
            log.warning("等待游戏进程退出超时(30s)，继续后续流程")
            break
        sleep(1)


def get_task_stall_timeout() -> int:
    """读取页面卡死等待时间，并为异常配置提供安全下限。"""
    try:
        configured_timeout = int(cfg.get_value("task_stall_timeout", DEFAULT_TASK_STALL_TIMEOUT))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_TASK_STALL_TIMEOUT
    return max(MIN_TASK_STALL_TIMEOUT, configured_timeout)


def check_times(start_time, timeout=None, logs=True):
    """检查是否卡死超时，若是则尝试关闭重启游戏"""
    if timeout is None:
        timeout = get_task_stall_timeout()
    now_time = time.time()
    if logs and int(now_time - start_time) > 9 and int(now_time - start_time) % 10 == 0:
        log.info(
            f"初始时间为{time.strftime('%H:%M:%S', time.localtime(start_time))}，"
            f"此刻时间为{time.strftime('%H:%M:%S', time.localtime(now_time))}，"
            f"已卡死{int(now_time - start_time)}秒"
        )
        sleep(1)
    if now_time - start_time > timeout:
        log.info(f"已卡死超过{timeout}秒，尝试关闭重启游戏")
        kill_game()
        restart_game()
        return True
    else:
        return False


def retry():
    """重试连接。

    为保证稳定性，retry 内循环始终刷新截图，避免复用旧帧导致误判。
    """
    start_time = time.time()
    is_windows = not cfg.config.simulator
    if is_windows:
        saved_hwnd = screen.handle.hwnd
    while True:
        if ensure_simulator_game_started():
            start_time = time.time()
            continue
        if is_windows and screen.handle.hwnd != saved_hwnd:
            # 句柄发生变化则重置初始时间, 以免误判卡死
            saved_hwnd = screen.handle.hwnd
            start_time = time.time()
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time):
            return False
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("base/connecting_assets.png"):
            continue
        if position := auto.find_element("base/retry_countdown.png"):
            sleep(5)
            auto.mouse_click(position[0], position[1], times=3)
            continue
        if auto.click_element("base/retry.png", threshold=0.9):
            auto.mouse_to_blank()
            continue
        if (
            auto.find_element("base/retry_countdown.png")
            or auto.find_element("base/retry.png")
            or auto.find_element("base/try_again.png")
        ):
            auto.click_element("base/retry.png", threshold=0.9)
            continue
        if auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            if auto.click_element("base/update_confirm_assets.png"):
                continue
            click_title_screen_safely()
            continue
        if auto.click_element("base/only_option_assets.png", model="clam"):
            sleep(5)
            if not check_game_running():
                log.debug("检测到游戏未运行，调用 init_game() 重新初始化")
                from tasks.base.script_task_scheme import init_game

                init_game()
            continue
        break


def restart_game():
    """重启游戏"""
    from tasks.base.back_init_menu import back_init_menu
    from tasks.base.script_task_scheme import init_game

    init_game()
    sleep(3)
    back_init_menu()
