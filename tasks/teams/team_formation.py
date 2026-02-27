from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log


# 清队
def clean_team():
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("teams/clear_selection_confirm_assets.png"):
            break
        if auto.click_element("teams/clear_selection_assets.png"):
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
    announcer_position = auto.find_element("teams/announcer_assets.png")
    first_sinner = [announcer_position[0] + 350 * scale, announcer_position[1]]
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
    scale = cfg.set_win_size / 1440
    my_position = [0, 150 * scale]
    find = False
    while auto.take_screenshot() is None:
        continue
    if auto.find_element(
        "home/first_prompt_assets.png", model="clam"
    ) and auto.find_element("home/back_assets.png", model="normal"):
        auto.click_element("home/back_assets.png")
    if position := auto.find_element("battle/teams_assets.png", take_screenshot=True):
        auto.mouse_click(1, 1)
        my_position[0] += position[0]
        my_position[1] += position[1]
        for _ in range(3):
            auto.mouse_drag(
                my_position[0], my_position[1], dy=1333 * scale, drag_time=0.3
            )
        sleep(0.75)
        first_position = [position[0], position[1] + 70 * scale]
        if cfg.select_team_by_order:
            team_range = (num - 1) // 5
            team_order = (num - 1) % 5
            for _ in range(team_range):
                auto.mouse_drag(
                    first_position[0],
                    first_position[1] + 375 * scale,
                    dy=-385 * scale,
                    drag_time=1.5,
                )
                sleep(1)
            if num <= 15:
                auto.mouse_click(
                    first_position[0], first_position[1] + 75 * team_order * scale
                )
            else:
                auto.mouse_click(
                    first_position[0],
                    first_position[1] + 100 * scale + 75 * team_order * scale,
                )
        else:
            if cfg.language_in_game == "en":
                team_name = [f"TEAMS #{num}", f"TEAMS#{num}"]
                team_name_error_correcting = f"TFAMS#{num}"
            elif cfg.language_in_game == "zh_cn":
                team_name = "编队#" + str(num)
                team_name_error_correcting = "编队#" + str(num)
            position_bbox = (0, 0, position[0] + 130 * scale, position[1] + 600 * scale)
            for i in range(10):
                while auto.take_screenshot() is None:
                    continue
                if auto.click_element(
                    team_name, find_type="text", offset=False, my_crop=position_bbox
                ):
                    find = True
                    break
                if auto.click_element(
                    team_name_error_correcting,
                    find_type="text",
                    offset=False,
                    my_crop=position_bbox,
                ):
                    find = True
                    break
                auto.mouse_drag(
                    first_position[0],
                    first_position[1] + 375 * scale,
                    dy=-385 * scale,
                    drag_time=1.5,
                )
                sleep(1)
                while auto.take_screenshot() is None:
                    continue
            if find:
                msg = f"成功找到队伍 # {num}"
                log.info(msg)
                sleep(1)
                return True
            else:
                msg = f"找不到队伍 # {num}"
                log.info(msg)
                return False


def deal_with_spills():
    import cv2
    import numpy as np

    from module.ocr import ocr
    from utils.image_utils import ImageUtils

    scale = cfg.set_win_size / 1440
    sinner_nums_bbox = ImageUtils.get_bbox(
        ImageUtils.load_image("battle/normal_to_battle_assets.png")
    )
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
                all_selected = auto.find_element(
                    "teams/selected.png", find_type="image_with_multiple_targets"
                )
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
                            ocr_result = [
                                result.txts[i] for i in range(len(result.txts))
                            ]
                            ocr_result = "".join(ocr_result)
                        if int(ocr_result) > max:
                            auto.mouse_click(selected[0], selected[1])
                    except:
                        continue
    except:
        pass


@begin_and_finish_time_log(task_name="检查队伍剩余战斗力")
def check_team():
    # 至少还有5人可以战斗
    sinner_nums = [f"{a}/{b}" for b in range(5, 10) for a in range(5, b + 1)]
    if auto.find_element(sinner_nums, find_type="text"):
        return True
    else:
        return False
