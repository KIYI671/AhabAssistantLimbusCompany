from time import sleep

from module.automation import auto
from module.config import cfg, theme_list
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.back_init_menu import back_init_menu


@begin_and_finish_time_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack(hard_switch=False):
    loop_count = 30
    auto.model = 'clam'
    scale = cfg.set_win_size / 1080
    theme_pack_list = theme_list.get_value("theme_pack_list")
    if hard_switch:
        theme_pack_list.update(theme_list.get_value("theme_pack_list_hard"))
    if cfg.language == 'zh_cn':
        theme_pack_list.update(theme_list.get_value("theme_pack_list_cn"))
        if hard_switch:
            theme_pack_list.update(theme_list.get_value("theme_pack_list_hard_cn"))
    refresh_times = 3
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if auto.find_element("mirror/theme_pack/normal_assets.png") is None and auto.find_element(
                "mirror/theme_pack/hard_assets.png") is None:
            continue

        # 切换难度
        if hard_switch:
            if auto.click_element("mirror/theme_pack/normal_assets.png"):
                continue
        else:
            if auto.click_element("mirror/theme_pack/hard_assets.png"):
                continue

        try:
            weight_list = []
            pack_name = []
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
                    result = auto.find_text_element(theme_pack_list, crop)
                    if (isinstance(result, list) or isinstance(result, tuple)) and len(result) > 1:
                        theme_pack_weight = result[0]
                        theme_pack_name = result[1]
                    else:
                        theme_pack_weight = -2
                        theme_pack_name = "unknown"

                    weight_list.append(theme_pack_weight)  # 采用最大值的形式，权重越大，优先级越高
                    pack_name.append(theme_pack_name)

                # 选择权重最大的主题包
                max_weight = max(weight_list)
                # 如果存在权重最大值大于等于优选阈值的主题包，则选择该主题包
                if max_weight >= theme_list.preferred_thresholds:
                    max_index = weight_list.index(max_weight)
                    pack = all_theme_pack[max_index]
                    auto.mouse_drag_down(pack[0], pack[1])
                    sleep(3)
                    msg = f"此次选择卡包关键词：{pack_name[max_index]}"
                    log.INFO(msg)
                    return

        except Exception as e:
            log.ERROR(e)
            continue

        if auto.click_element("mirror/theme_pack/refresh_assets.png") and refresh_times > 0:
            refresh_times -= 1
            auto.mouse_to_blank()
            sleep(1)
            continue

        # 如果多次刷新仍无达到优选阈值的主题包，则选择权重最大的主题包
        if refresh_times <= 0:
            try:
                max_weight = max(weight_list)
                # 如果存在权重最大值大于等于优选阈值的主题包，则选择该主题包
                if max_weight >= theme_list.preferred_thresholds:
                    max_index = weight_list.index(max_weight)
                    pack = all_theme_pack[max_index]
                    auto.mouse_drag_down(pack[0], pack[1])
                    sleep(3)
                    log.DEBUG("无匹配最低阈值的主题包，选择最高权重主题包")
                    msg = f"无匹配最低阈值的主题包，选择最高权重主题包\n此次选择卡包关键词：{pack_name[max_index]}"
                    log.INFO(msg)
                    return
            except Exception as e:
                log.ERROR(f"选择主题包出错:{e},尝试回到初始界面")
                back_init_menu()
                break

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法选取主题包,尝试回到初始界面")
            back_init_menu()
            break
