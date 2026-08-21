import time
from time import sleep

from module.automation import TextMatchResult, auto
from module.config import cfg, theme_list
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.back_init_menu import back_init_menu
from utils.image_utils import ImageUtils
from utils.path_manager import path_manager


def _wait_for_theme_pack_transition(timeout: float = 3.0) -> bool:
    """等待主题包界面离开；截图器负责限速，超时后交还主状态机兜底。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            return True
        if not auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
            return True
    log.debug("主题包选择后的界面转换等待超时，交由镜牢主循环继续识别")
    return False


def _theme_pack_positions_are_stable(previous, current, tolerance: float) -> bool:
    if previous is None or len(previous) != len(current):
        return False
    return all(
        abs(old[0] - new[0]) <= tolerance and abs(old[1] - new[1]) <= tolerance
        for old, new in zip(previous, current)
    )


def _wait_for_theme_pack_ready(expected_difficulty_asset: str, timeout: float = 4.0) -> bool:
    """等待难度切换完成且卡包停止移动，避免动画中误选旧位置。"""
    deadline = time.monotonic() + timeout
    previous_positions = None
    tolerance = max(2.0, 4.0 * cfg.set_win_size / 1440)
    while time.monotonic() < deadline:
        if auto.take_screenshot() is None:
            continue
        if not auto.find_element(expected_difficulty_asset):
            previous_positions = None
            continue
        positions = auto.find_image_with_multiple_targets(
            "mirror/theme_pack/theme_pack_features.png",
            0.8,
        )
        if not positions:
            previous_positions = None
            continue
        positions = sorted(positions, key=lambda pos: (pos[0], pos[1]))
        if _theme_pack_positions_are_stable(previous_positions, positions, tolerance):
            return True
        previous_positions = positions
    log.warning("主题包难度切换后长时间未稳定，交由主循环重新识别")
    return False


@begin_and_finish_time_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack(hard_switch=False, floor=None, team_num=None, use_custom_theme_pack_weight=False):
    loop_count = 30
    auto.model = "clam"
    scale = cfg.set_win_size / 1080
    if path_manager.current_language == "zh_cn":
        theme_pack_list_zh = theme_list.get_effective_theme_pack_list(
            hard_switch, "zh_cn", team_num, use_custom_theme_pack_weight
        )
        theme_pack_list_en = {}
    elif path_manager.current_language == "en":
        theme_pack_list_zh = {}
        theme_pack_list_en = theme_list.get_effective_theme_pack_list(
            hard_switch, "en", team_num, use_custom_theme_pack_weight
        )
    else:
        theme_pack_list_zh = theme_list.get_effective_theme_pack_list(
            hard_switch, "zh_cn", team_num, use_custom_theme_pack_weight
        )
        theme_pack_list_en = theme_list.get_effective_theme_pack_list(
            hard_switch, "en", team_num, use_custom_theme_pack_weight
        )
    # 游戏更新后新增的主题包尚未收录时的兜底权重，取自「未知 / unknown」配置项
    unknown_weight = int(theme_pack_list_zh.get("未知", theme_pack_list_en.get("unknown", -5)))
    refresh_times = 3
    difficulty = None
    if auto.find_element("mirror/road_in_mir/legend_assets.png", take_screenshot=True):
        return
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if (
            difficulty is None
            and auto.find_element("mirror/theme_pack/normal_assets.png") is None
            and auto.find_element("mirror/theme_pack/hard_assets.png") is None
        ):
            if loop_count < 0:
                break
            if loop_count < 5:
                normal_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/normal_assets.png"))
                hard_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/hard_assets.png"))
                difficulty_bbox = [
                    min(normal_bbox[0], hard_bbox[0]),
                    min(normal_bbox[1], hard_bbox[1]),
                    max(normal_bbox[2], hard_bbox[2]),
                    max(normal_bbox[3], hard_bbox[3]),
                ]
                ocr_result = auto.find_text_element(None, my_crop=difficulty_bbox, only_text=True)
                if not isinstance(ocr_result, str):
                    if auto.find_element("mirror/road_in_mir/legend_assets.png", take_screenshot=True):
                        return
                    continue
                if "normal" in ocr_result:
                    difficulty = "normal"
                elif "hard" in ocr_result:
                    difficulty = "hard"
            loop_count -= 1
            sleep(1)
            continue

        # 切换难度
        if hard_switch:
            if auto.click_element("mirror/theme_pack/normal_assets.png"):
                _wait_for_theme_pack_ready("mirror/theme_pack/hard_assets.png")
                difficulty = "hard"
                continue
            elif difficulty == "normal":
                normal_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/normal_assets.png"))
                auto.mouse_click(
                    (normal_bbox[0] + normal_bbox[2]) // 2,
                    (normal_bbox[1] + normal_bbox[3]) // 2,
                )
                _wait_for_theme_pack_ready("mirror/theme_pack/hard_assets.png")
                difficulty = "hard"
                continue
        else:
            if auto.click_element("mirror/theme_pack/hard_assets.png"):
                _wait_for_theme_pack_ready("mirror/theme_pack/normal_assets.png")
                difficulty = "normal"
                continue
            elif difficulty == "hard":
                hard_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/theme_pack/hard_assets.png"))
                auto.mouse_click(
                    (hard_bbox[0] + hard_bbox[2]) // 2,
                    (hard_bbox[1] + hard_bbox[3]) // 2,
                )
                _wait_for_theme_pack_ready("mirror/theme_pack/normal_assets.png")
                difficulty = "normal"
                continue

        try:
            if floor == 4 and cfg.select_event_pack:
                if all_theme_pack := auto.find_element(
                    "mirror/theme_pack/theme_pack_features.png",
                    find_type="image_with_multiple_targets",
                ):
                    all_theme_pack.sort(key=lambda pos: (pos[0], pos[1]))
                    auto.mouse_drag_down(all_theme_pack[0][0], all_theme_pack[0][1])
                    log.debug(f"选择卡包: {all_theme_pack[0]}")
                    _wait_for_theme_pack_transition()
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
                if floor == 4 and cfg.skip_event_pack:
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
                    _wait_for_theme_pack_transition()
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
                _wait_for_theme_pack_transition()
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
