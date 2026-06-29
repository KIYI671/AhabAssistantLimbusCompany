import os
import platform
import time
from time import sleep

import psutil
import win32process

from module.automation import auto
from module.config import cfg
from module.game_and_screen import screen
from module.logger import log
from utils.utils import check_game_running

_last_title_screen_tap_time = 0.0
_last_simulator_alive_check_time = 0.0
_pending_simulator_launch_probe = False


def _get_simulator_connection_device():
    if cfg.simulator_type == 0:
        from module.automation.input_handlers.simulator.mumu_control import MumuControl

        return MumuControl.connection_device

    from module.automation.input_handlers.simulator.simulator_control import SimulatorControl

    return SimulatorControl.connection_device


def _is_main_menu_visible() -> bool:
    return bool(auto.find_element("home/window_assets.png") and auto.find_element("home/mail_assets.png", model="normal"))


def _is_runtime_ui_visible() -> bool:
    return bool(
        auto.find_element("battle/setting_assets.png")
        or auto.find_element("battle/battle_finish_confirm_assets.png")
        or auto.find_element("base/retry_countdown.png")
        or auto.find_element("base/retry.png")
        or auto.find_element("base/try_again.png")
        or auto.find_element("home/back_assets.png", model="normal")
        or auto.find_element("base/back_assets.png", model="normal", threshold=0.6)
        or auto.find_element("base/notification_close_assets.png")
        or auto.find_element("scenes/story_skip_confirm_assets.png")
        or auto.find_element("scenes/story_skip_assets.png")
        or auto.find_element("scenes/story_meun_assets.png")
        or auto.find_element("home/close_anniversary_event_assets.png")
        or auto.find_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png", threshold=0.75)
        or auto.find_element("mirror/road_in_mir/to_window_assets.png", threshold=0.75)
        or auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png")
        or auto.find_element("mirror/road_in_mir/legend_assets.png")
        or auto.find_element("mirror/road_to_mir/enter_assets.png")
        or auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png")
    )


def should_wait_for_main_menu_after_simulator_start() -> bool:
    global _pending_simulator_launch_probe

    if not _pending_simulator_launch_probe:
        return False
    _pending_simulator_launch_probe = False

    from tasks.base.back_init_menu import handle_launch_state_once

    deadline = time.time() + 3
    had_model = hasattr(auto, "model")
    previous_model = getattr(auto, "model", None)
    auto.model = "clam"
    try:
        while time.time() <= deadline:
            auto.ensure_not_stopped()
            if auto.take_screenshot() is None:
                continue
            if _is_main_menu_visible():
                return True
            if handle_launch_state_once():
                return True
            if _is_runtime_ui_visible():
                return False
            sleep(0.5)
    finally:
        if had_model:
            auto.model = previous_model

    return True


def ensure_simulator_game_started() -> bool:
    """模拟器模式下确认游戏仍在前台，不在时尝试拉起游戏。"""
    global _last_simulator_alive_check_time, _pending_simulator_launch_probe

    _pending_simulator_launch_probe = False
    if not cfg.simulator:
        return False

    now = time.time()
    if now - _last_simulator_alive_check_time < 5:
        return False
    _last_simulator_alive_check_time = now

    connection_device = _get_simulator_connection_device()
    if connection_device is None:
        return False

    if connection_device.check_game_alive():
        return False

    log.info("检测到游戏未运行或不在前台，尝试自动启动游戏")
    connection_device.start_game()
    _pending_simulator_launch_probe = True
    sleep(3)
    return True


def click_title_screen_safely() -> None:
    """标题页点击入口，避开账号、清缓存和中间弹窗区域。"""
    global _last_title_screen_tap_time
    if not cfg.simulator:
        auto.mouse_click_blank()
        return

    now = time.time()
    if now - _last_title_screen_tap_time < 5:
        return
    _last_title_screen_tap_time = now

    height = int(cfg.set_win_size or 1080)
    width = int(height * 16 / 9)
    tap_points = ((0.86, 0.80), (0.74, 0.83), (0.91, 0.58))
    index = int(now // 10) % len(tap_points)
    x_ratio, y_ratio = tap_points[index]
    auto.mouse_click(int(width * x_ratio), int(height * y_ratio))


def kill_game():
    """关闭游戏"""
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            MumuControl.connection_device.close_current_app()
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            SimulatorControl.connection_device.close_current_app()
        return
    if platform.system() == "Windows":
        from module.game_and_screen import screen

        _, pid = win32process.GetWindowThreadProcessId(screen.handle.hwnd)
        os.system(f"taskkill /F /PID {pid}")
    sleep(10)
    wait_start = time.time()
    while True:
        game_running = False
        for proc in psutil.process_iter(["name"]):
            try:
                # 获取进程的可执行文件名（如 "notepad.exe"）
                proc_name = proc.info["name"]
                # 仅当遍历后找不到任何游戏进程时，才认为游戏已退出
                if proc_name and cfg.game_process_name.lower() in proc_name.lower():
                    game_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略已终止、无权限或僵尸进程
                continue
        if not game_running:
            break
        if time.time() - wait_start > 30:
            log.warning("等待游戏进程退出超时(30s)，继续后续流程")
            break
        sleep(1)


def check_times(start_time, timeout=90, logs=True):
    """检查是否卡死超时，若是则尝试关闭重启游戏"""
    now_time = time.time()
    if logs and int(now_time - start_time) > 9 and int(now_time - start_time) % 10 == 0:
        log.info(f"初始时间为{time.strftime('%H:%M:%S', time.localtime(start_time))}，此刻时间为{time.strftime('%H:%M:%S', time.localtime(now_time))}，已卡死{int(now_time - start_time)}秒")
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
            if should_wait_for_main_menu_after_simulator_start():
                from tasks.base.back_init_menu import wait_until_main_menu_after_launch

                return wait_until_main_menu_after_launch() == "main_menu"
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


def restart_game() -> bool:
    """重启游戏"""
    from tasks.base.back_init_menu import wait_until_main_menu_after_launch
    from tasks.base.script_task_scheme import init_game

    init_game()
    sleep(3)
    return wait_until_main_menu_after_launch() == "main_menu"
