from os import environ

import cv2
import numpy as np

from command.get_grey_normalized_pic import get_grey_normalized_pic
from command.get_pic import win_cap
from my_error.my_error import withOutPicError
from my_log.my_log import my_log


def get_pic_position(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    # 初始化目标截图
    try:
        my_screenshot = get_grey_normalized_pic(screenshot)
    except:
        my_log("error", "无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")

    if screenshot != "./screenshot.png":
        my_screenshot = cv2.resize(my_screenshot, None, fx=scale_factors[scale], fy=scale_factors[scale],
                                   interpolation=cv2.INTER_AREA)
    # 初始化匹配模板图片,并将图片适配缩放
    try:
        my_model = get_grey_normalized_pic(img_model_path)
    except:
        my_log("error", "无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")

    my_model = cv2.resize(my_model, None, fx=scale_factors[scale], fy=scale_factors[scale],
                          interpolation=cv2.INTER_AREA)
    # 获取模板图片的宽度和高度
    w, h = my_model.shape[::-1]
    # 使用matchTemplate对图片进行模板匹配
    res = cv2.matchTemplate(my_screenshot, my_model, cv2.TM_CCOEFF_NORMED)
    # 使用minMaxLoc获取最匹配的位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 如果找到了匹配，且匹配度大于阈值
    if max_val > precision:
        # 获取匹配区域的中心点
        top_left = max_loc
        center_pos = (int(top_left[0] + w / 2), int(top_left[1] + h / 2))

        msg = f"获取到图片{img_model_path}的中心点在截屏的位置:({center_pos[0]},{center_pos[1]}),相似度为{max_val}"
        my_log("debug", msg)
        return center_pos
    msg = f"未能获取到图片{img_model_path}的位置,最大相似度{max_val}"
    my_log("debug", msg)
    return None


def get_pic_temp_position(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    # 初始化目标截图
    try:
        my_screenshot = get_grey_normalized_pic(screenshot)
    except:
        my_log("error", "无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")

    # 初始化匹配模板图片,并将图片适配缩放
    try:
        my_model = get_grey_normalized_pic(img_model_path)
    except:
        my_log("error", "无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
    my_model = cv2.resize(my_model, None, fx=scale_factors[scale], fy=scale_factors[scale],
                          interpolation=cv2.INTER_AREA)
    # 获取模板图片的宽度和高度
    w, h = my_model.shape[::-1]
    # 使用matchTemplate对图片进行模板匹配
    res = cv2.matchTemplate(my_screenshot, my_model, cv2.TM_CCOEFF_NORMED)
    # 使用minMaxLoc获取最匹配的位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 如果找到了匹配，且匹配度大于阈值
    if max_val > precision:
        # 获取匹配区域的中心点
        top_left = max_loc
        msg = f"获取到图片{img_model_path}的左上角在截屏的位置:({top_left[0]},{top_left[1]}),相似度为{max_val}"
        my_log("debug", msg)
        return top_left
    msg = f"未能获取到图片{img_model_path}的位置,最大相似度{max_val}"
    my_log("debug", msg)
    return None


def get_all_pic_position(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    # 初始化目标截图
    try:
        my_screenshot = get_grey_normalized_pic(screenshot)
    except:
        my_log("error", "无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")

    if screenshot != "./screenshot.png":
        my_screenshot = cv2.resize(my_screenshot, None, fx=scale_factors[scale], fy=scale_factors[scale],
                                   interpolation=cv2.INTER_AREA)
    # 初始化匹配模板图片,并将图片适配缩放
    try:
        my_model = get_grey_normalized_pic(img_model_path)
    except:
        my_log("error", "无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
    my_model = cv2.resize(my_model, None, fx=scale_factors[scale], fy=scale_factors[scale],
                          interpolation=cv2.INTER_AREA)
    # 获取模板图片的宽度和高度
    w, h = my_model.shape[::-1]
    # 存储所有匹配位置的中心点
    center_points = []
    # 使用matchTemplate对图片进行模板匹配
    res = cv2.matchTemplate(my_screenshot, my_model, cv2.TM_CCOEFF_NORMED)
    # 使用minMaxLoc获取最匹配的位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 遍历所有超过阈值的区域
    loc = np.where(res >= precision)
    points = zip(*loc[::-1])

    # 对匹配结果进行排序，根据匹配度得分从高到低
    sorted_points = sorted(points, key=lambda x: res[x[1], x[0]], reverse=True)

    # 非极大值抑制（NMS）的最小距离
    min_dist = 10
    # 遍历排序后的匹配位置
    if sorted_points:
        for pt in sorted_points:
            # 检查当前匹配点是否与已保留的匹配点太近
            if all(np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist for kept_pt in center_points):
                # 如果没有太近的匹配点，保留当前匹配点
                center_points.append(pt)
        for point in range(len(center_points)):
            center_points[point] = (int(center_points[point][0] + w / 2), int(center_points[point][1] + h / 2))
        msg = f"获取到图片{img_model_path}的在截屏的位置:{center_points}"
        my_log("debug", msg)
        return center_points
    msg = f"未能获取到图片{img_model_path}的位置"
    my_log("debug", msg)
    return None


# 本来用来找镜牢中的巴士，但是用不上了
def get_pic_keypoints_position(img_model_path, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    # 初始化目标截图
    my_screenshot = cv2.imread(screenshot, cv2.IMREAD_GRAYSCALE)
    my_model = cv2.imread(img_model_path, cv2.IMREAD_GRAYSCALE)

    # 创建SIFT检测器
    sift = cv2.SIFT_create()

    # 计算图片1和图片2的 keypoints 和 descriptors
    kp1, des1 = sift.detectAndCompute(my_screenshot, None)
    kp2, des2 = sift.detectAndCompute(my_model, None)

    # 创建BFMatcher对象
    bf = cv2.BFMatcher()

    # 使用欧氏距离进行匹配
    matches = bf.knnMatch(des1, des2, k=2)

    # 应用比率测试
    good_matches = []
    for m, n in matches:
        if m.distance < 0.5 * n.distance:
            good_matches.append(m)

    if len(good_matches) < 10:  # 假设至少需要10个好的匹配
        return None

    # 使用RANSAC过滤误匹配
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    matches_mask = mask.ravel().tolist()

    # 只保留RANSAC认为的内点
    good_matches_ransac = [m for i, m in enumerate(good_matches) if matches_mask[i]]

    # 找出最佳匹配
    best_match = None
    min_distance = float('inf')
    for match in good_matches:
        if match.distance < min_distance:
            min_distance = match.distance
            best_match = match

    # 如果找到了最佳匹配
    if best_match:
        # 获取最佳匹配的关键点坐标
        query_idx = best_match.queryIdx
        train_idx = best_match.trainIdx
        pt1 = kp1[query_idx].pt
        center = (int(pt1[0]), int(pt1[1]))
        # 打印最佳匹配的中心点位置
        return center

    return None


def get_pic_position_without_cap(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    # 初始化目标截图
    try:
        my_screenshot = get_grey_normalized_pic(screenshot)
    except:
        my_log("error", "无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + screenshot + "\"图片文件很可能被删除，或主程序被移动")

    if screenshot != "./screenshot.png":
        my_screenshot = cv2.resize(my_screenshot, None, fx=scale_factors[scale], fy=scale_factors[scale],
                                   interpolation=cv2.INTER_AREA)
    # 初始化匹配模板图片,并将图片适配缩放
    try:
        my_model = get_grey_normalized_pic(img_model_path)
    except:
        my_log("error", "无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
        raise withOutPicError("无法读取图片文件\"" + img_model_path + "\"图片文件很可能被删除，或主程序被移动")
    my_model = cv2.resize(my_model, None, fx=scale_factors[scale], fy=scale_factors[scale],
                          interpolation=cv2.INTER_AREA)
    # 获取模板图片的宽度和高度
    w, h = my_model.shape[::-1]
    # 使用matchTemplate对图片进行模板匹配
    res = cv2.matchTemplate(my_screenshot, my_model, cv2.TM_CCOEFF_NORMED)
    # 使用minMaxLoc获取最匹配的位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 如果找到了匹配，且匹配度大于阈值
    if max_val > precision:
        # 获取匹配区域的中心点
        top_left = max_loc
        center_pos = (int(top_left[0] + w / 2), int(top_left[1] + h / 2))
        msg = f"获取到图片{img_model_path}的中心点在截屏的位置:({center_pos[0]},{center_pos[1]})"
        my_log("debug", msg)
        return center_pos
    msg = f"未能获取到图片{img_model_path}的位置)"
    my_log("debug", msg)
    return None
