from time import sleep

from module.automation import auto
from module.config import cfg
from module.logger import log


def _prepare_continuous_combat_count(
    combat_count: int,
    log_prefix: str,
    box_position: tuple[int, int] | None = None,
) -> bool:
    if box_position is not None:
        auto.mouse_click(box_position[0], box_position[1])
    else:
        if not (pos := auto.click_element(
            "luxcavation/thread_continuous_combat_show_box.png",
            threshold=0.85,
            click=False,
        )):
            log.debug(f"{log_prefix}未找到连续战斗设置入口")
            return False
        auto.mouse_click(pos[0], pos[1])

    up_button = None
    for attempt in range(2):
        sleep(0.4 if attempt == 0 else 0.2)
        up_button = auto.find_element(
            "luxcavation/continuous_combat_up_box.png",
            threshold=0.85,
            take_screenshot=True
        )
        if up_button:
            break

    if not up_button:
        log.debug(f"{log_prefix}未找到连续战斗增加按钮")
        return False

    for _ in range(combat_count - 1):
        auto.mouse_click(up_button[0], up_button[1])
        sleep(0.1)

    log.debug(f"{log_prefix}连续战斗次数已设置为 {combat_count} 次")
    return True


def EXP_luxcavation(combat_count: int = 1):
    loop_count = 30
    auto.model = "clam"
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("teams/identify_assets.png"):
            break
        if (
            auto.find_element("home/first_prompt_assets.png", model="clam")
            and auto.find_element("home/back_assets.png", model="normal")
            and not auto.find_element("luxcavation/exp_enter.png", threshold=0.85)
        ):
            auto.key_press("esc")
            continue
        if auto.find_element("luxcavation/exp_enter.png", threshold=0.85, take_screenshot=True):
            if level := auto.find_element("luxcavation/exp_enter.png", find_type="image_with_multiple_targets"):
                level = sorted(level, key=lambda x: x[0], reverse=True)
                scale = cfg.set_win_size / 1440
                log.debug(f"经验本检测到 {len(level)} 个关卡入口: {level}")
                for lv_idx, lv in enumerate(level):
                    if combat_count > 1:
                        box_position = (lv[0] + 300 * scale, lv[1] - 450 * scale)
                        if not _prepare_continuous_combat_count(combat_count, "EXP", box_position):
                            log.debug(f"经验本第 {lv_idx + 1} 关连续战斗设置失败，降级尝试下一关")
                            continue

                    select_team = False
                    for retry in range(3):
                        log.debug(f"经验本尝试第 {lv_idx + 1} 关 (x={lv[0]}, y={lv[1]}), 第 {retry + 1}/3 次")
                        auto.mouse_click(lv[0], lv[1])
                        sleep(1)
                        auto.mouse_to_blank()
                        for _ in range(3):
                            if auto.find_element("teams/identify_assets.png", take_screenshot=True) or auto.find_element(
                                "home/first_prompt_assets.png",
                                model="clam",
                                take_screenshot=True,
                            ):
                                log.debug(f"经验本第 {lv_idx + 1} 关点击成功，已进入编队界面")
                                select_team = True
                                break
                        if select_team:
                            break
                    if select_team:
                        break
                    log.debug(f"经验本第 {lv_idx + 1} 关 3 次尝试均未进入编队，降级尝试下一关")
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("home/inferno_bus_assets.png") and not auto.find_element("home/luxcavation_assets.png"):
            sleep(1)
            if not auto.find_element("home/luxcavation_assets.png"):
                auto.click_element("home/window_assets.png")
                continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
            "home/drive_assets.png", model="normal"
        ):
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
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法进入经验本,不能进行下一步,此次经验本无效")
            break


def thread_luxcavation(combat_count: int = 1):
    def _click_level_targets(level: list, log_prefix: str) -> bool:
        for lv_idx, lv in enumerate(level):
            for retry in range(3):
                log.debug(f"{log_prefix}尝试第 {lv_idx + 1} 关 (x={lv[0]}, y={lv[1]}), 第 {retry + 1}/3 次")
                auto.mouse_click(lv[0], lv[1])
                sleep(1)
                auto.mouse_to_blank()
                for _ in range(3):
                    if auto.find_element("teams/identify_assets.png", take_screenshot=True) or auto.find_element(
                            "home/first_prompt_assets.png", model="clam", take_screenshot=True
                    ):
                        log.debug(f"{log_prefix}第 {lv_idx + 1} 关点击成功，已进入编队界面")
                        return True
            log.debug(f"{log_prefix}第 {lv_idx + 1} 关 3 次尝试均未进入编队，降级尝试下一关")
        return False
    loop_count = 30
    continuous_combat_set = False
    auto.model = "clam"
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("teams/identify_assets.png"):
            break
        if (
            auto.find_element("home/first_prompt_assets.png", model="clam")
            and auto.find_element("home/back_assets.png", model="normal")
            and not auto.find_element("luxcavation/thread_enter_assets.png", threshold=0.78)
            and not auto.find_element("luxcavation/thread_consume.png", threshold=0.85)
        ):
            auto.key_press("esc")
            continue
        if thread_enter := auto.click_element("luxcavation/thread_enter_assets.png", threshold=0.78, click=False):
            # 纽本连战次数框位于外层纺锤卡片，需在进入关卡列表前设置。
            if combat_count > 1 and not continuous_combat_set:
                if not _prepare_continuous_combat_count(combat_count, "Thread"):
                    log.debug("纽本连续战斗设置失败，重新检测")
                    continue
                continuous_combat_set = True
            auto.mouse_click(thread_enter[0], thread_enter[1])
            sleep(0.5)
            if pos := auto.find_element("luxcavation/thread_consume.png", threshold=0.85,take_screenshot=True):
                if scroll_bar := auto.find_element("luxcavation/thread_scroll_bar.png"):
                    auto.mouse_drag_down(scroll_bar[0], scroll_bar[1], reverse=2)
                else:
                    log.debug("未找到滚动条，通过滑动下滑")
                    auto.mouse_drag_down(pos[0], pos[1], reverse=-2)

                level = auto.find_element(
                    "luxcavation/thread_consume.png",
                    find_type="image_with_multiple_targets",
                    take_screenshot=True,
                )
                scale = cfg.set_win_size / 1440
                # 只识别右半屏幕
                min_x = cfg.set_win_size / 2
                level = sorted([(x, y) for x, y in level if x >= min_x], key=lambda p: p[1], reverse=True)
                if level:
                    log.debug(f"纽本检测到 {len(level)} 个关卡入口: {level}")
                    _click_level_targets(level, "纽本")
                else:
                    # 处理下方所有关卡未解锁的情况
                    level = None
                    slide_times = 0
                    x = int(1300 * scale)
                    y = int(960 * scale)
                    dy = int(200 * scale)

                    while not level:
                        auto.mouse_drag(x, y, drag_time=0.5, dy=dy)
                        level = auto.find_element(
                            "luxcavation/thread_consume.png",
                            find_type="image_with_multiple_targets",
                            take_screenshot=True,
                        )
                        if level:
                            min_x = cfg.set_win_size / 2
                            level = sorted([(x, y) for x, y in level if x >= min_x], key=lambda p: p[1], reverse=True)
                        else:
                            level = []
                        if level:
                            break
                        slide_times += 1
                        if slide_times > 10:
                            break
                    if not level:
                        continue

                    log.debug(f"纽本(滑动后)检测到 {len(level)} 个关卡入口: {level}")
                    _click_level_targets(level, "纽本(滑动后)")

            else:
                log.debug("纽本未找到关卡消耗锚点")
            continue
        if auto.click_element("luxcavation/thread_assets.png"):
            sleep(0.5)
            continue
        if auto.click_element("home/luxcavation_assets.png"):
            continue
        if auto.find_element("home/inferno_bus_assets.png") and not auto.find_element("home/luxcavation_assets.png"):
            sleep(1)
            if not auto.find_element("home/luxcavation_assets.png"):
                auto.click_element("home/window_assets.png")
                continue
        if auto.find_element("base/renew_confirm_assets.png", model="clam") and auto.find_element(
            "home/drive_assets.png", model="normal"
        ):
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
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法进入纽本,不能进行下一步,此次纽本无效")
            break
