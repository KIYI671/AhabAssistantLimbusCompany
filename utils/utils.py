from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ 内置模块

import cv2
import numpy as np


def get_day_of_week():
    # 直接获取当前东九区时间（Asia/Tokyo）
    now_time = datetime.now(ZoneInfo("Asia/Tokyo"))

    # 提取星期几（中文）、小时、分钟
    day = now_time.isoweekday()  # isoweekday() 返回 1（周一）~7（周日）
    hour = now_time.hour  # 小时（0-23）

    if hour < 6:
        day -= 1

    return day


def calculate_the_teams():
    day = get_day_of_week()
    if day == 1 or day == 2:
        return "1_2"
    if day == 3 or day == 4:
        return "3_4"
    if day == 5 or day == 6:
        return "5_6"
    if day == 7 or day == 8:
        return "7"


def find_skill3(background, known_rgb, threshold=40, min_pixels=10):
    median_rgb = np.median(background, axis=(0, 1)).astype(int)
    blended_rgb = (median_rgb * 0.45 + np.array(known_rgb) * 0.55).astype(int)

    comp = 1

    lower_bound = np.clip(blended_rgb - threshold, 0, 255)
    upper_bound = np.clip(blended_rgb + threshold, 0, 255)
    mask = cv2.inRange(background, lower_bound, upper_bound)

    mask = cv2.erode(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))

    # collecting clusters (colors that are directly connected)
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask)

    cluster_centers = []

    # some pixel value checks (colors in cluster may be disconnected)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        center = centroids[i]

        if min_pixels * comp <= area:
            x = int(center[0])
            x1, x2 = round(max(0, x - 33 * comp)), round(min(background.shape[1], x + 33 * comp))
            y1, y2 = 0, round(13 * comp)

            region_mask = mask[y1:y2, x1:x2]
            similar_pixels = np.count_nonzero(region_mask)

            if similar_pixels >= 26 * comp:
                cluster_centers.append(center)

    # merging neightbouring clusters
    merged = []
    while cluster_centers:
        current = cluster_centers.pop()
        group = [c for c in cluster_centers if np.linalg.norm(current - c) <= 67 * comp]
        cluster_centers = [c for c in cluster_centers if np.linalg.norm(current - c) > 66 * comp]
        merged.append(np.mean([current] + group, axis=0))

    return merged
