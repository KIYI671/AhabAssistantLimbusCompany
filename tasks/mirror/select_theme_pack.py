from time import sleep

from module.automation import TextMatchResult, auto
from module.config import cfg, theme_list
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.back_init_menu import back_init_menu
from utils.path_manager import path_manager


def get_theme_pack_difficulty():
    if auto.find_element("mirror/theme_pack/normal_assets.png", take_screenshot=True):
        return "normal"
    if auto.find_element("mirror/theme_pack/hard_assets.png"):
        return "hard"


def switch_theme_pack_difficulty(hard_mode=False):
    target = "hard" if hard_mode else "normal"
    current = get_theme_pack_difficulty()
    if current is None:
        log.info("无法确认当前镜牢主题包难度，继续选择主题包")
        return
    if current == target:
        return
    if not auto.click_element(f"mirror/theme_pack/{current}_assets.png"):
        log.info("无法确认当前镜牢主题包难度，继续选择主题包")
        return
    sleep(2)  # 等待难度切换动画结束及主题包重新加载
    switched = get_theme_pack_difficulty()
    log.info(f"镜牢主题包难度切换{'成功' if switched == target else '失败'}: {current} -> {switched}")


@begin_and_finish_time_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack(hard_mode=False, floor=None, team_num=None, use_custom_theme_pack_weight=False):
    loop_count = 30
    auto.model = "clam"
    scale = cfg.set_win_size / 1080
    if path_manager.current_language == "zh_cn":
        theme_pack_list_zh = theme_list.get_effective_theme_pack_list(
            hard_mode, "zh_cn", team_num, use_custom_theme_pack_weight
        )
        theme_pack_list_en = {}
    elif path_manager.current_language == "en":
        theme_pack_list_zh = {}
        theme_pack_list_en = theme_list.get_effective_theme_pack_list(
            hard_mode, "en", team_num, use_custom_theme_pack_weight
        )
    else:
        theme_pack_list_zh = theme_list.get_effective_theme_pack_list(
            hard_mode, "zh_cn", team_num, use_custom_theme_pack_weight
        )
        theme_pack_list_en = theme_list.get_effective_theme_pack_list(
            hard_mode, "en", team_num, use_custom_theme_pack_weight
        )
    # 游戏更新后新增的主题包尚未收录时的兜底权重，取自「未知 / unknown」配置项
    unknown_weight = int(theme_pack_list_zh.get("未知", theme_pack_list_en.get("unknown", -5)))
    refresh_times = 3
    if auto.find_element("mirror/road_in_mir/legend_assets.png", take_screenshot=True):
        return
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        try:
            if floor == 5 and cfg.select_event_pack:
                if all_theme_pack := auto.find_element(
                    "mirror/theme_pack/theme_pack_features.png",
                    find_type="image_with_multiple_targets",
                ):
                    all_theme_pack.sort(key=lambda pos: (pos[0], pos[1]))
                    auto.mouse_drag_down(all_theme_pack[0][0], all_theme_pack[0][1])
                    log.debug(f"选择卡包: {all_theme_pack[0]}")
                    sleep(3)
                    msg = "此次主题包选择了最左边的（活动）卡包"
                    log.info(msg)
                    return
            weight_list = []
            pack_name = []
            if all_theme_pack := auto.find_element(
                "mirror/theme_pack/theme_pack_features.png",
                find_type="image_with_multiple_targets",
                take_screenshot=True,
            ):
                if floor == 5 and cfg.skip_event_pack:
                    all_theme_pack.sort(key=lambda pos: (pos[0], pos[1]))
                    all_theme_pack.pop(0)  # 删除最左边的卡包
                for pack in all_theme_pack:
                    top_left = (
                        max(pack[0] - 210 * scale, 0),
                        max(pack[1] - 60 * scale, 0),
                    )
                    bottom_right = (
                        min(pack[0] + 60 * scale, cfg.set_win_size * 16 / 9),
                        min(pack[1] + 390 * scale, cfg.set_win_size),
                    )
                    crop = (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
                    result = auto.find_language_text(theme_pack_list_zh, theme_pack_list_en, crop)
                    if isinstance(result, TextMatchResult):
                        theme_pack_weight = result.value
                        theme_pack_name = result.text
                    else:
                        theme_pack_weight = unknown_weight
                        theme_pack_name = "unknown"

                    weight_list.append(theme_pack_weight)  # 采用最大值的形式，权重越大，优先级越高
                    pack_name.append(theme_pack_name)

                # 选择权重最大的主题包
                max_weight = max(weight_list)
                log.debug(f"当前主题包权重列表：{list(zip(pack_name, weight_list))}")
                # 如果存在权重最大值大于等于优选阈值的主题包，则选择该主题包
                if max_weight >= int(theme_list.preferred_thresholds):
                    max_index = weight_list.index(max_weight)
                    pack = all_theme_pack[max_index]
                    auto.mouse_drag_down(pack[0], pack[1])
                    log.debug(f"选择卡包: {pack}")
                    sleep(3)
                    msg = f"此次选择卡包关键词：{pack_name[max_index]}"
                    log.info(msg)
                    return

        except Exception as e:
            log.error(f"识别主题包出错:{e}")
            continue

        if refresh_times >= 0 and auto.click_element("mirror/theme_pack/refresh_assets.png"):
            refresh_times -= 1
            auto.mouse_to_blank()
            sleep(1)
            continue
        if refresh_times >= 0 and loop_count < 15:
            auto.mouse_to_blank(move_back=False)

        # 如果多次刷新仍无达到优选阈值的主题包，则选择权重最大的主题包
        if refresh_times <= 0:
            try:
                max_weight = max(weight_list)
                max_index = weight_list.index(max_weight)
                pack = all_theme_pack[max_index]
                auto.mouse_drag_down(pack[0], pack[1])
                log.debug(f"选择卡包: {pack}")
                sleep(3)
                log.debug("无匹配最低阈值的主题包，选择最高权重主题包")
                msg = f"无匹配最低阈值的主题包，选择最高权重主题包\n此次选择卡包关键词：{pack_name[max_index]}"
                log.info(msg)
                return
            except Exception as e:
                log.error(f"选择主题包出错:{e},尝试回到初始界面")
                back_init_menu()
                break

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法选取主题包,尝试回到初始界面")
            back_init_menu()
            break
    log.error("无法选取主题包,尝试回到初始界面")
    back_init_menu()
