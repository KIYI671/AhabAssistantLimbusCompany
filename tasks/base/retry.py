import time
from time import sleep

import pyautogui

from module.automation import auto
from module.logger import log


def retry():
    start_time = time.time()
    while True:
        now_time = time.time()
        if now_time - start_time > 45:
            log.INFO("已卡死在retry超过45秒，尝试关闭重启游戏")
            pyautogui.hotkey('alt', 'f4')
            sleep(10)
            restart_game()
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
        if clear_all_caches := auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            auto.mouse_click(clear_all_caches[0], clear_all_caches[1] - 100)
            continue
        break


def restart_game():
    from tasks.base.script_task_scheme import init_game
    from tasks.base.back_init_menu import back_init_menu
    init_game()
    back_init_menu()
