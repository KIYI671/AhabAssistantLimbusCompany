from time import sleep

from module.automation import auto
from module.config import cfg, theme_list
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.back_init_menu import back_init_menu
from utils.image_utils import ImageUtils


@begin_and_finish_time_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack(hard_switch=False, flood=None):
    loop_count = 30
    auto.model = 'clam'
    scale = cfg.set_win_size / 1080
    theme_pack_list = theme_list.get_value("theme_pack_list")
    if hard_switch:
        theme_pack_list.update(theme_list.get_value("theme_pack_list_hard"))
    if cfg.language_in_game == 'zh_cn':
        theme_pack_list.update(theme_list.get_value("theme_pack_list_cn"))
        if hard_switch:
            theme_pack_list.update(theme_list.get_value("theme_pack_list_hard_cn"))
    refresh_times = 3
    difficulty = None
    while True:

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法选取主题包,尝试回到初始界面")
            back_init_menu()
            break

        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if difficulty is None and auto.find_element(
                "mirror/theme_pack/normal_assets.png") is None and auto.find_element(
            "mirror/theme_pack/hard_assets.png") is None:
            if loop_count < 5:
                normal_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/normal_assets.png"))
                hard_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/hard_assets.png"))
                difficulty_bbox = [min(normal_bbox[0], hard_bbox[0]),
                                   min(normal_bbox[1], hard_bbox[1]),
                                   max(normal_bbox[2], hard_bbox[2]),
                                   max(normal_bbox[3], hard_bbox[3])]
                ocr_result = auto.find_text_element(None, my_crop=difficulty_bbox, only_text=True)
                if "normal" in ocr_result:
                    difficulty = "normal"
                elif "hard" in ocr_result:
                    difficulty = "hard"
            continue

        # 切换难度
        if hard_switch:
            if auto.click_element("mirror/theme_pack/normal_assets.png"):
                continue
            elif difficulty == "normal":
                normal_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/normal_assets.png"))
                auto.mouse_click((normal_bbox[0] + normal_bbox[2]) // 2, (normal_bbox[1] + normal_bbox[3]) // 2)
        else:
            if auto.click_element("mirror/theme_pack/hard_assets.png"):
                continue
            elif difficulty == "hard":
                hard_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/hard_assets.png"))
                auto.mouse_click((hard_bbox[0] + hard_bbox[2]) // 2, (hard_bbox[1] + hard_bbox[3]) // 2)

        try:
            if flood == 4 and cfg.select_event_pack:
                if all_theme_pack := auto.find_element("mirror/theme_pack/theme_pack_features.png",
                                                       find_type='image_with_multiple_targets'):
                    all_theme_pack.sort(key=lambda pos: (pos[0], pos[1]))
                    auto.mouse_drag_down(all_theme_pack[0][0], all_theme_pack[0][1])
                    sleep(3)
                    msg = "此次主题包选择了最左边的（活动）卡包"
                    log.INFO(msg)
                    return
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

        if refresh_times >= 0 and auto.click_element("mirror/theme_pack/refresh_assets.png"):
            refresh_times -= 1
            auto.mouse_to_blank()
            sleep(1)
            continue

        # 如果多次刷新仍无达到优选阈值的主题包，则选择权重最大的主题包
        if refresh_times <= 0:
            try:
                max_weight = max(weight_list)
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
