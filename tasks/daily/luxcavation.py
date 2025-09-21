from time import sleep

from module.automation import auto
from module.logger import log


def EXP_luxcavation():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("battle/teams_assets.png"):
            break
        if auto.find_element("luxcavation/exp_enter.png", threshold=0.85, take_screenshot=True):
            if level := auto.find_element("luxcavation/exp_enter.png", find_type="image_with_multiple_targets"):
                level = sorted(level, key=lambda x: x[0], reverse=True)
                for lv in level:
                    auto.mouse_click(lv[0], lv[1])
                    sleep(0.5)
                    if auto.find_element("battle/teams_assets.png", take_screenshot=True):
                        break
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element("home/drive_assets.png",
                                                                                              model="normal"):
            auto.click_element("base/renew_confirm_assets.png")
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            continue
        if auto.click_element("home/drive_assets.png"):
            sleep(0.5)
            continue
        auto.mouse_to_blank()

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法进入经验本,不能进行下一步,此次经验本无效")
            break


def thread_luxcavation():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("battle/teams_assets.png"):
            break
        if auto.click_element("luxcavation/thread_enter_assets.png", threshold=0.78):
            if auto.find_element("luxcavation/thread_lv.png", threshold=0.85, take_screenshot=True):
                if level := auto.find_element("luxcavation/thread_lv.png", find_type="image_with_multiple_targets"):
                    level = sorted(level, key=lambda y: y[1], reverse=True)
                    for lv in level:
                        auto.mouse_click(lv[0], lv[1])
                        sleep(0.5)
                        if auto.find_element("battle/teams_assets.png", take_screenshot=True):
                            break
            continue
        if auto.click_element("luxcavation/thread_assets.png"):
            continue
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element("home/drive_assets.png",
                                                                                              model="normal"):
            auto.click_element("base/renew_confirm_assets.png")
            from tasks.base.back_init_menu import back_init_menu
            back_init_menu()
            continue
        if auto.click_element("home/drive_assets.png"):
            sleep(0.5)
            continue
        auto.mouse_to_blank()
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法进入纽本,不能进行下一步,此次纽本无效")
            break
