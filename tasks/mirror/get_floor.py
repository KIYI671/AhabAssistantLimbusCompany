from time import sleep

import numpy as np

from module.automation import auto
from module.logger import log

# 楼层进度条横带 ROI
FLOOR_BAND_ROI = (760, 495, 1860, 590)

# 1440p ，设置的clear图片，处理后连在一起的红色区域至少包含 300 个像素，认为匹配成功
FLOOR_CLEAR_MIN_AREA = 300


def clear_badge_mask(roi_rgb):
    """输入：RGB 图像区域，形状为（高，宽，3）。
    输出：同样宽高的 uint8 二维掩码，符合红色条件的像素为 255（白），其余为 0（黑）。
    """
    r = roi_rgb[:, :, 0].astype(np.int16)
    g = roi_rgb[:, :, 1].astype(np.int16)
    b = roi_rgb[:, :, 2].astype(np.int16)

    # 排除黄色，排除不够亮的红色
    red_dom_min, red_r_min = 60, 190
    m = ((r - np.maximum(g, b)) >= red_dom_min) & (r >= red_r_min)

    return m.astype(np.uint8) * 255


# 说明：
# - 设置页面：未进入的层都是暗菱形，进入的层是金色菱形，通过的层会在金色菱形中添加 红色CLEAR
#   -> 计数+1=当前层，精确。
#   卡包界面每次识别，地图页仅在楼层未知时识别。


def get_floor(previous_floor=0, setting_assets="mirror/road_in_mir/setting_assets.png") -> int:
    """识别当前楼层；失败时记录错误并返回 0，表示楼层未知。"""
    current_floor = 0
    setting_button = auto.find_element(setting_assets, take_screenshot=True)
    if setting_button:
        auto.mouse_action_with_pos(setting_button)
        sleep(1)  # 等待楼层设置面板展开
        if auto.find_element("mirror/road_in_mir/to_window_assets.png", threshold=0.75, take_screenshot=True):
            clear_regions = auto.find_regions_by_color(
                FLOOR_BAND_ROI,
                min_area=FLOOR_CLEAR_MIN_AREA,
                min_dist=80,
                mask_fn=clear_badge_mask,
            )
            if clear_regions is not None:
                current_floor = len(clear_regions) + 1
                if current_floor != previous_floor + 1:
                    log.info(
                        f"楼层识别异常：上一层为 {previous_floor}，预计当前为 {previous_floor + 1}，"
                        f"实际识别为 {current_floor}，使用识别结果继续"
                    )
        auto.mouse_click_blank()
        sleep(1)  # 等待设置窗口关闭
    if current_floor == 0:
        log.error("楼层识别异常：未能确认当前楼层，标记为 0（未知）")
    else:
        log.info(f"楼层识别结果：当前为第{current_floor}层")
    return current_floor
