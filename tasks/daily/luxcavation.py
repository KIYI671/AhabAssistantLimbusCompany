from time import sleep

from module.automation import auto
from module.logger import log
from module.config import cfg


def EXP_luxcavation():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("battle/teams_assets.png"):
            break
        if auto.find_element("home/first_prompt_assets.png", model="clam") and auto.find_element(
                "home/back_assets.png", model="normal"):
            auto.click_element("home/back_assets.png")
            continue
        if auto.find_element("luxcavation/exp_enter.png", threshold=0.85, take_screenshot=True):
            if level := auto.find_element("luxcavation/exp_enter.png", find_type="image_with_multiple_targets"):
                level = sorted(level, key=lambda x: x[0], reverse=True)
                for lv in level:
                    auto.mouse_click(lv[0], lv[1])
                    sleep(1)
                    auto.mouse_to_blank()
                    select_team = False
                    for _ in range(3):
                        if auto.find_element("battle/teams_assets.png", take_screenshot=True) or auto.find_element(
                            "home/first_prompt_assets.png", model="clam", take_screenshot=True):
                            select_team = True
                            break
                    if select_team:
                        break
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
                "home/drive_assets.png",
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
            log.error("无法进入经验本,不能进行下一步,此次经验本无效")
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
        if auto.find_element("home/first_prompt_assets.png", model="clam") and auto.find_element(
                "home/back_assets.png", model="normal"):
            auto.click_element("home/back_assets.png")
            continue
        if auto.click_element("luxcavation/thread_enter_assets.png", threshold=0.78):
            if pos := auto.find_element("luxcavation/thread_consume.png", threshold=0.85, take_screenshot=True):
                if scroll_bar := auto.find_element("luxcavation/thread_scroll_bar.png"):
                    auto.mouse_drag_down(scroll_bar[0], scroll_bar[1], reverse=2)
                else:
                    log.debug("未找到滚动条，通过滑动下滑")
                    auto.mouse_drag_down(pos[0], pos[1], reverse=-2)

                if level := not auto.find_element("luxcavation/thread_consume.png", find_type="image_with_multiple_targets", take_screenshot=True):
                    level = sorted(level, key=lambda y: y[1], reverse=True)
                    for lv in level:
                        auto.mouse_click(lv[0], lv[1])
                        sleep(1)
                        auto.mouse_to_blank()
                        if auto.find_element("battle/teams_assets.png", take_screenshot=True):
                            break
                else:
                    # 处理下方所有关卡未解锁的情况
                    level = None
                    slide_times = 0
                    scale = cfg.set_win_size / 1440
                    x = int(1300 * scale)
                    y = int(960 * scale)
                    dy = int(200 * scale)

                    while level is None:
                        auto.mouse_drag(x, y, drag_time=0.5, dy=dy)
                        level = auto.find_element("luxcavation/thread_consume.png", find_type="image_with_multiple_targets", take_screenshot=True)
                        if level:
                            break
                        slide_times += 1
                        if slide_times > 10:
                            break
                    if level is None:
                        continue

                    level = sorted(level, key=lambda y: y[1], reverse=True)
                    for lv in level:
                        auto.mouse_click(lv[0], lv[1])
                        sleep(1)
                        auto.mouse_to_blank()
                        if auto.find_element("battle/teams_assets.png", take_screenshot=True):
                            break

            continue
        if auto.click_element("luxcavation/thread_assets.png"):
            continue
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
                "home/drive_assets.png",
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
            log.error("无法进入纽本,不能进行下一步,此次纽本无效")
            break
