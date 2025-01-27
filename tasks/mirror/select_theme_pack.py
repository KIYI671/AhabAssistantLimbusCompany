from time import sleep

from module.automation import auto
from module.config import cfg, black_list
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.back_init_menu import back_init_menu


@begin_and_finish_time_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack(hard_switch=False):
    loop_count = 30
    auto.model = 'clam'
    scale = cfg.set_win_size / 1080
    black_theme_list = black_list.get_value("blacklist")
    if cfg.language == 'zh_cn':
        black_theme_list.extend(black_list.get_value("blacklist_cn"))

    refresh_times = 3
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if auto.find_element("mirror/theme_pack/normal_assets.png") is None and auto.find_element(
                "mirror/theme_pack/hard_assets.png") is None:
            continue

        # TODO:适配困镜
        # 切换难度
        if hard_switch:
            if auto.click_element("mirror/theme_pack/normal_assets.png"):
                continue
        else:
            if auto.click_element("mirror/theme_pack/hard_assets.png"):
                continue

        try:
            if all_theme_pack := auto.find_element("mirror/theme_pack/theme_pack_features.png",
                                                   find_type='image_with_multiple_targets'):
                for pack in all_theme_pack:
                    top_left = (
                        max(pack[0] - 210 * scale, 0),
                        max(pack[1] - 60 * scale, 0))
                    bottom_right = (
                        min(pack[0] + 60 * scale, cfg.set_win_size * 16 / 9),
                        min(pack[1] + 390 * scale, cfg.set_win_size))
                    crop = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
                    if auto.find_text_element(black_theme_list, crop):
                        continue
                    else:
                        auto.mouse_drag_down(pack[0], pack[1])
                        sleep(3)
                        return 0
        except Exception as e:
            log.ERROR(e)
            continue

        if auto.click_element("mirror/theme_pack/refresh_assets.png") and refresh_times > 0:
            refresh_times -= 1
            sleep(1)
            continue

        if auto.click_element("mirror/theme_pack/theme_pack_features.png", action="drag_down"):
            break

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法获取ego饰品,尝试回到初始界面")
            back_init_menu()
            break
