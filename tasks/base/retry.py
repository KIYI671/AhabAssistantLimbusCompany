import os
import platform
import time
from time import sleep

import psutil
import win32process

from module.automation import auto
from module.config import cfg
from module.logger import log


def check_times(start_time, timeout=90, logs=True):
    """检查是否卡死超时，若是则尝试关闭重启游戏"""
    now_time = time.time()
    if logs and int(now_time - start_time) > 9 and int(now_time - start_time) % 10 == 0:
        log.info(f"初始时间为{start_time}，此刻时间为{now_time}，已卡死{int(now_time - start_time)}秒")
        sleep(1)
    if now_time - start_time > timeout:
        log.info(f"已卡死超过{timeout}秒，尝试关闭重启游戏")
        if platform.system() == "Windows":
            from module.game_and_screen import screen
            _, pid = win32process.GetWindowThreadProcessId(screen.handle._hWnd)
            os.system(f'taskkill /F /PID {pid}')
        sleep(10)
        while True:
            kill = False
            for proc in psutil.process_iter(['name']):
                try:
                    # 获取进程的可执行文件名（如 "notepad.exe"）
                    proc_name = proc.info['name']
                    # 精确匹配进程名（区分大小写，取决于系统）
                    if not cfg.game_process_name in proc_name:
                        kill = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 忽略已终止、无权限或僵尸进程
                    continue
            if kill:
                break
        restart_game()
        return True
    else:
        return False


def retry():
    """重试连接"""
    start_time = time.time()
    while True:
        if auto.get_restore_time() is not None:
            start_time = max(start_time, auto.get_restore_time())
        if check_times(start_time):
            return False
        # 自动截图
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
        if auto.find_element("base/retry_countdown.png") \
                or auto.find_element("base/retry.png") \
                or auto.find_element("base/try_again.png"):
            auto.click_element("base/retry.png", threshold=0.9)
            continue
        if auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            auto.mouse_click_blank()
            continue
        break


def restart_game():
    """重启游戏"""
    from tasks.base.script_task_scheme import init_game
    from tasks.base.back_init_menu import back_init_menu
    init_game()
    back_init_menu()
