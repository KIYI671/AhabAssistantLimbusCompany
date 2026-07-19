from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.ocr import ocr


# 清队
def clean_team():
    scale = cfg.set_win_size / 1440
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("teams/clear_selection_confirm_assets.png"):
            break
        if (identify_position := auto.find_element("teams/identify_assets.png")) and auto.mouse_action_with_pos(
            [identify_position[0], identify_position[1] + 600 * scale]):
            sleep(0.5)
            auto.take_screenshot()
            if auto.find_element("teams/clear_selection_confirm_assets.png") is None:
                break


@begin_and_finish_time_log(task_name="罪人编队")
# 编队
def team_formation(sinner_team):
    scale = cfg.set_win_size / 1440

    clean_team()
    while auto.take_screenshot() is None:
        continue
    if reset_team := auto.find_element("teams/identify_assets.png"):
        first_sinner = [reset_team[0] - 1800 * scale, reset_team[1] + 130 * scale]
    else:
        log.error("无法找到罪人编队的起始位置")
        return
    sleep(0.5)

    for i in range(1, 13):
        if i in sinner_team:
            sinner = sinner_team.index(i)
        else:
            return
        if sinner <= 5:
            auto.mouse_click(first_sinner[0] + 270 * sinner * scale, first_sinner[1])
        else:
            auto.mouse_click(
                first_sinner[0] + 270 * (sinner - 6) * scale,
                first_sinner[1] + 500 * scale,
            )
        sleep(cfg.mouse_action_interval)


@begin_and_finish_time_log(task_name="寻找队伍")
# 找队
def select_battle_team(num):
    # 相邻编队高度差是75px（确信
    # num 1 - 20
    # 如果会拖动到顶部或底部，sleep等待回正
    scale = cfg.set_win_size / 1440
    while auto.take_screenshot() is None:
        continue
    # 关闭首次进入队伍界面时的提示
    identify_position = None
    if auto.find_element("home/first_prompt_assets.png", model="clam") and auto.find_element(
        "home/back_assets.png", model="normal"
    ):
        auto.click_element("home/back_assets.png")
        identify_position = auto.find_element("teams/identify_assets.png", take_screenshot=True)
    else:
        identify_position = auto.find_element("teams/identify_assets.png")

    if identify_position:
        first_team_pos = (int(250 * scale), int(625 * scale))
        second_team_pos = (int(250 * scale), int(700 * scale))
        auto.mouse_click(1, 1)
        auto.mouse_action_with_pos(second_team_pos)

        # 复位
        for _ in range(3):
            auto.mouse_drag(second_team_pos[0], second_team_pos[1], dy=1333 * scale, drag_time=0.3)
        sleep(0.75)
        if cfg.select_team_by_order:
            team_range = (num - 1) // 5
            team_order = (num - 1) % 5
            for _ in range(team_range):
                auto.mouse_drag(
                    first_team_pos[0],
                    first_team_pos[1] + 375 * scale,
                    dy=-375 * scale,
                    drag_time=0.3,
                )
            if num <= 15:
                auto.mouse_action_with_pos((first_team_pos[0], first_team_pos[1] + 75 * team_order * scale))
            else:
                
                sleep(0.5) # 滑3次，等待编队条触底后的回正
                auto.mouse_action_with_pos(
                    (first_team_pos[0],
                    first_team_pos[1] + 100 * scale + 75 * team_order * scale)
                )
            log.info(f"成功找到队伍 # {num}")
            return True
        else:
            team_name_zh = "编队#" + str(num)
            team_name_en = [f"TEAMS #{num}", f"TEAMS#{num}", f"TFAMS#{num}"]
            position_bbox = (
                0,
                0,
                int(first_team_pos[0] + 130 * scale),
                int(first_team_pos[1] + 545 * scale),
            )
            for attempt in range(10):
                while auto.take_screenshot() is None:
                    continue
                if team_position := auto.find_language_text(team_name_zh, team_name_en, my_crop=position_bbox):
                    auto.mouse_action_with_pos(team_position, offset=False)
                    log.info(f"成功找到队伍 # {num}")
                    return True
                if attempt == 9:
                    break
                auto.mouse_drag(
                    first_team_pos[0],
                    first_team_pos[1] + 375 * scale,
                    dy=-375 * scale,
                    drag_time=0.3,
                )
                sleep(0.5)
            log.info(f"找不到队伍 # {num}")
            return False


def deal_with_spills():
    import cv2
    import numpy as np

    from module.ocr import ocr
    from utils.image_utils import ImageUtils

    scale = cfg.set_win_size / 1440
    sinner_nums_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/normal_to_battle_assets.png"))
    sinner_nums_bbox = (
        sinner_nums_bbox[0],
        sinner_nums_bbox[1] - 115 * scale,
        sinner_nums_bbox[2],
        sinner_nums_bbox[3] - 115 * scale,
    )
    sc = ImageUtils.crop(np.array(auto.screenshot), sinner_nums_bbox)
    sc = cv2.bitwise_not(sc)
    mask = cv2.inRange(sc, 220, 255)
    mask = cv2.bitwise_not(mask)
    background = np.zeros((300, 300), dtype=np.uint8)
    h, w = mask.shape[:2]
    y_off = (300 - h) // 2
    x_off = (300 - w) // 2
    background[y_off : y_off + h, x_off : x_off + w] = mask
    try:
        result = ocr.run(background)
        ocr_result = [result.txts[i] for i in range(len(result.txts))]
        ocr_result = "".join(ocr_result)
        log.debug(f"对于配队人数OCR得到：{ocr_result}")
        if "/" in ocr_result:
            result = ocr_result.split("/")
            result = [i.strip() for i in result]
            import re

            now = int(re.sub(r"\D", "", result[-2]))
            max = int(re.sub(r"\D", "", result[-1]))
            if now > max:
                all_selected = auto.find_element("teams/selected.png", find_type="image_with_multiple_targets")
                kernel = np.ones((3, 3), np.uint8)
                for selected in all_selected:
                    try:
                        order_bbox = (
                            selected[0] - 40 * scale,
                            selected[1] - 120 * scale,
                            selected[0] + 40 * scale,
                            selected[1] - 30 * scale,
                        )
                        sc2 = ImageUtils.crop(np.array(auto.screenshot), order_bbox)
                        background2 = np.zeros((300, 300), dtype=np.uint8)
                        h, w = sc2.shape[:2]
                        y_off = (300 - h) // 2
                        x_off = (300 - w) // 2
                        background2[y_off : y_off + h, x_off : x_off + w] = sc2
                        result = ocr.run(background2)
                        ocr_result = [result.txts[i] for i in range(len(result.txts))]
                        ocr_result = "".join(ocr_result)
                        if ocr_result == "G":
                            ocr_result = "6"
                        if int(ocr_result) == 1:
                            # 再腐蚀 3 次
                            background2 = cv2.erode(background2, kernel, iterations=3)
                            # 再膨胀 2 次
                            background2 = cv2.dilate(background2, kernel, iterations=2)
                            result = ocr.run(background2)
                            ocr_result = [result.txts[i] for i in range(len(result.txts))]
                            ocr_result = "".join(ocr_result)
                        if int(ocr_result) > max:
                            auto.mouse_click(selected[0], selected[1])
                    except:
                        continue
    except:
        pass


_MONEY_OCR_TRANSLATION = str.maketrans(
    {
        "O": "0",
        "o": "0",
        "D": "0",
        "Q": "0",
        "I": "1",
        "l": "1",
        "Z": "2",
        "S": "5",
        "G": "6",
        "B": "8",
        "h": "4",
    }
)


@begin_and_finish_time_log(task_name="检查队伍剩余战斗力")
def check_team():
    # 只要还有至少1人可以战斗就继续
    scale = cfg.set_win_size / 1440
    # 选中罪人数量
    sinner_nums_bbox = tuple(
        int(value * scale)
        for value in (2260, 1020, 2333, 1080)
    )
    result = ocr.run(auto.screenshot.crop(sinner_nums_bbox), use_det=False)
    if not result.txts:
        return False
    recognized_text = result.txts[0].strip().translate(_MONEY_OCR_TRANSLATION)
    return recognized_text.isdigit() and 1 <= int(recognized_text) <= 12


@begin_and_finish_time_log(task_name="加载编队码")
def load_team_code_in_game(team_code: str) -> bool:
    """在游戏中加载编队码

    Args:
        team_code: 编队码字符串

    Returns:
        成功返回 True，失败返回 False
    """
    # 验证当前在队伍选择界面
    if not auto.find_element("mirror/road_to_mir/select_team_confirm_assets.png"):
        log.warning("未在队伍选择界面，跳过编队码加载")
        return False

    # 最多重试3次
    max_retries = 3
    for _ in range(1, max_retries + 1):
        # 截图
        while auto.take_screenshot() is None:
            continue

        # 点击队伍代码按钮
        auto.click_element("teams/team_code_assets.png")
        sleep(1)

        # 查找并点击加载编队码按钮
        auto.click_element("teams/load_team_code_button_assets.png", take_screenshot=True)
        sleep(1)

        # 查找根据取消按钮判断输入框是否出现
        if not auto.find_element("teams/team_code_cancel_button_assets.png", take_screenshot=True):
            # 尝试点击取消按钮返回
            auto.mouse_click_blank()
            sleep(1)
            continue

        # 使用 input_text(text) 直接输入编队码
        auto.input_text(team_code)
        sleep(0.5)  # 等待输入完成

        # 点击确认按钮，最多重试 3 次
        for _ in range(3):
            if auto.click_element("teams/team_code_confirm_button_assets.png", take_screenshot=True):
                sleep(1)
            else:
                break

        # 验证返回队伍选择界面
        if auto.find_element("teams/team_code_assets.png", take_screenshot=True):
            return True
        else:
            auto.click_element("teams/team_code_cancel_button_assets.png")
            sleep(1)

    auto.mouse_click(100, 100)  # 点击左上角关闭
    log.warning(f"加载编队码失败，已重试{max_retries}次: {team_code}")
    return False
