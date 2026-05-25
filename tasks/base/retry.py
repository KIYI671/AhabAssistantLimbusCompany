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
    saved_hwnd = screen.handle.hwnd
    while True:
        if screen.handle.hwnd != saved_hwnd:
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
            auto.mouse_click_blank()
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
