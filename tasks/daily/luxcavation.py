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
        if auto.click_element("luxcavation/exp_enter_1_assets.png", model='normal'):
            sleep(1)
            continue
        if auto.click_element("luxcavation/exp_enter_2_assets.png", model='normal'):
            sleep(1)
            continue
        if auto.click_element("luxcavation/exp_enter_3_assets.png", model='normal'):
            sleep(1)
            continue
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.click_element("home/drive_assets.png"):
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
        if auto.click_element("luxcavation/thread_lv50.png", threshold=0.93):
            sleep(1)
            continue
        if auto.click_element("luxcavation/thread_lv40.png"):
            sleep(1)
            continue
        if auto.click_element("luxcavation/thread_lv30.png", threshold=0.93):
            sleep(1)
            continue
        if auto.click_element("luxcavation/thread_lv20.png", threshold=0.93):
            sleep(1)
            continue
        if auto.click_element("luxcavation/thread_enter_assets.png"):
            continue
        if auto.click_element("luxcavation/thread_assets.png"):
            continue
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.click_element("home/drive_assets.png"):
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
