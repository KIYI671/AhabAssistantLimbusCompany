import io
from os import environ

import cv2
import numpy as np

from command.get_grey_normalized_pic import get_grey_normalized_pic
from command.get_pic import win_cap
from command.get_position import get_pic_position
from command.mouse_activity import mouse_click
from command.use_yaml import get_black_list_keyword_yaml
from my_error.my_error import withOutPicError
from my_log.my_log import my_log
from my_ocr.PPOCR_api import GetOcrApi


def compare_the_blacklist(pic_byte_stream, language="models/config_chinese.txt"):
    # 使用的识别语言配置文件
    # 之前的OCR使用"models/config_en.txt"
    my_argument = {"config_path": language}
    # 初始化识别器对象，传入 PaddleOCR-json.exe
    ocr = GetOcrApi("./3rdparty/PaddleOCR-json_v.1.3.1/PaddleOCR-json.exe", my_argument)
    # 读取图片字节流进行OCR
    res = ocr.runBytes(pic_byte_stream)
    # 提取文本块数据
    text_blocks = res["data"]
    # 只获取文本块中的文本
    text_values = [d.get("text", "") for d in text_blocks]
    # 获取黑名单
    black_list = get_black_list_keyword_yaml()
    keywords = black_list["keys"]

    # 与黑名单进行比对
    for key in keywords:
        # 如果出现黑名单关键词，则跳过
        if any(key in strs.lower() for strs in text_values):
            msg = f"此次识别主题包包含关键词{key}，为黑名单主题包，即将略过"
            my_log("debug", msg)
            return False
    return True


def get_theme_pack(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    scale_factors2 = [1, 1.333, 0.667, 0.833, 1.667, 2]
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

    # 遍历所有超过阈值的区域
    loc = np.where(res >= precision)
    points = zip(*loc[::-1])

    # 对匹配结果进行排序，根据匹配度得分从高到低
    sorted_points = sorted(points, key=lambda x: res[x[1], x[0]], reverse=True)

    # 非极大值抑制（NMS）的最小距离
    min_dist = 10
    # 存储所有匹配位置的中心点
    center_points = []
    # 遍历排序后的匹配位置
    if sorted_points:
        for pt in sorted_points:
            # 检查当前匹配点是否与已保留的匹配点太近
            if all(np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist for kept_pt in center_points):
                # 如果没有太近的匹配点，保留当前匹配点
                center_points.append(pt)
        for point in range(len(center_points)):
            center_points[point] = (int(center_points[point][0] + w / 2), int(center_points[point][1] + h / 2))

    # 存储所有字节流
    all_byte_stream = []
    # 如果找到了匹配，且匹配度大于阈值
    for point in center_points:

        # 计算获取主题包的矩形区域用来截图
        top_left = (
        max(point[0] - int(210 * scale_factors2[scale]), 0), max(point[1] - int(60 * scale_factors2[scale]), 0))
        bottom_right = (min(point[0] + w + int(60 * scale_factors2[scale]), my_screenshot.shape[1]),
                        min(point[1] + h + int(390 * scale_factors2[scale]), my_screenshot.shape[0]))

        # 截取主题包图片
        roi = my_screenshot[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

        # 将图片转为字节流
        is_success, encoded_image = cv2.imencode('.png', roi)
        if not is_success:
            raise Exception("Could not encode image.")

        # encoded_image是numpy数组，本身并不是一个流对象
        # 转为字节对象，并将其写入到一个流对象中
        byte_stream = io.BytesIO(encoded_image.tobytes())

        # 转为可用于ocr的字节流
        byte_stream_read = byte_stream.read()

        # 同时存储字节流和对应点位
        temp = [byte_stream_read, point]

        # 将ocr字节流存储进列表中
        all_byte_stream.append(temp)

    return all_byte_stream


def search_team_number(pic_byte_stream, number, language="models/config_chinese.txt"):
    # 使用的识别语言配置文件
    my_argument = {"config_path": language}
    # 初始化识别器对象，传入 PaddleOCR-json.exe
    ocr = GetOcrApi("./3rdparty/PaddleOCR-json_v.1.3.1/PaddleOCR-json.exe", my_argument)
    # 读取图片字节流进行OCR
    res = ocr.runBytes(pic_byte_stream)
    # 提取文本块数据
    data_blocks = res["data"]
    team_num = "TEAMS#" + str(number)
    my_position = None
    for data in data_blocks:
        if data['text'] == team_num:
            position = get_pic_position("./pic/teams/teams.png")
            my_position = data["box"][0]
            my_position[0] += position[0]
            my_position[1] += position[1]
    if my_position is not None:
        return my_position
    else:
        return None


def get_all_team(img_model_path, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    scale_factors2 = [1, 1.333, 0.667, 0.833, 1.667, 2]
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

    # 遍历所有超过阈值的区域
    loc = np.where(res >= precision)
    points = zip(*loc[::-1])

    # 对匹配结果进行排序，根据匹配度得分从高到低
    sorted_points = sorted(points, key=lambda x: res[x[1], x[0]], reverse=True)

    # 非极大值抑制（NMS）的最小距离
    min_dist = 10
    # 存储所有匹配位置的中心点
    center_points = []
    # 遍历排序后的匹配位置
    if sorted_points:
        for pt in sorted_points:
            # 检查当前匹配点是否与已保留的匹配点太近
            if all(np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist for kept_pt in center_points):
                # 如果没有太近的匹配点，保留当前匹配点
                center_points.append(pt)
        for point in range(len(center_points)):
            center_points[point] = (int(center_points[point][0] + w / 2), int(center_points[point][1] + h / 2))

    # 存储所有字节流
    all_byte_stream = []
    # 如果找到了匹配，且匹配度大于阈值
    for point in center_points:

        # 计算获取图片的矩形区域用来截图
        top_left = (
        max(point[0] - int(100 * scale_factors2[scale]), 0), max(point[1] - int(25 * scale_factors2[scale]), 0))
        bottom_right = (min(point[0] + int(100 * scale_factors2[scale]), my_screenshot.shape[1]),
                        min(point[1] + h + int(300 * scale_factors2[scale]), my_screenshot.shape[0]))

        # 截取图片
        roi = my_screenshot[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

        # 将图片转为字节流
        is_success, encoded_image = cv2.imencode('.png', roi)
        if not is_success:
            raise Exception("Could not encode image.")

        # encoded_image是numpy数组，本身并不是一个流对象
        # 转为字节对象，并将其写入到一个流对象中
        byte_stream = io.BytesIO(encoded_image.tobytes())

        # 转为可用于ocr的字节流
        byte_stream_read = byte_stream.read()

        # 将ocr字节流和点位存储进列表中
        all_byte_stream.append(byte_stream_read)

    return all_byte_stream


def commom_all_ocr(scale=0, screenshot="./screenshot.png"):
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

    # 存储所有字节流
    all_byte_stream = []

    # 将图片转为字节流
    is_success, encoded_image = cv2.imencode('.png', my_screenshot)
    if not is_success:
        raise Exception("Could not encode image.")

    # encoded_image是numpy数组，本身并不是一个流对象
    # 转为字节对象，并将其写入到一个流对象中
    byte_stream = io.BytesIO(encoded_image.tobytes())

    # 转为可用于ocr的字节流
    byte_stream_read = byte_stream.read()

    # 将ocr字节流和点位存储进列表中
    all_byte_stream.append(byte_stream_read)

    return all_byte_stream


def commom_ocr(img_model_path, width=50, height=50, precision=0.8, scale=0, screenshot="./screenshot.png"):
    # 对当前页面进行截图
    win_cap()
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    # 设置缩放比例
    scale_factors2 = [1, 1.333, 0.667, 0.833, 1.667, 2]
    scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
    width = int(width*scale_factors2[scale])
    height = int(height*scale_factors2[scale])
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

    # 遍历所有超过阈值的区域
    loc = np.where(res >= precision)
    points = zip(*loc[::-1])

    # 对匹配结果进行排序，根据匹配度得分从高到低
    sorted_points = sorted(points, key=lambda x: res[x[1], x[0]], reverse=True)

    # 非极大值抑制（NMS）的最小距离
    min_dist = 10
    # 存储所有匹配位置的中心点
    center_points = []
    # 遍历排序后的匹配位置
    if sorted_points:
        for pt in sorted_points:
            # 检查当前匹配点是否与已保留的匹配点太近
            if all(np.linalg.norm(np.array(pt) - np.array(kept_pt)) > min_dist for kept_pt in center_points):
                # 如果没有太近的匹配点，保留当前匹配点
                center_points.append(pt)

    # 存储所有字节流
    all_byte_stream = []
    # 如果找到了匹配，且匹配度大于阈值
    for point in center_points:

        # 计算获取的矩形区域用来截图
        top_left = (max(point[0], 0), max(point[1], 0))
        bottom_right = (min(point[0] + width, my_screenshot.shape[1]), min(point[1] + height, my_screenshot.shape[0]))

        # 截取区域图片
        roi = my_screenshot[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

        # 将图片转为字节流
        is_success, encoded_image = cv2.imencode('.png', roi)
        if not is_success:
            raise Exception("Could not encode image.")

        # encoded_image是numpy数组，本身并不是一个流对象
        # 转为字节对象，并将其写入到一个流对象中
        byte_stream = io.BytesIO(encoded_image.tobytes())

        # 转为可用于ocr的字节流
        byte_stream_read = byte_stream.read()

        # 将ocr字节流和点位存储进列表中
        all_byte_stream.append(byte_stream_read)

    return all_byte_stream


def commom_range_ocr(upper_left_corner, lower_right_corner, hight=0, width=0, precision=0.8, scale=0,
                     screenshot="./screenshot.png"):
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

    new_model = my_screenshot[upper_left_corner[1]:lower_right_corner[1], upper_left_corner[0]:lower_right_corner[0]]

    # 将图片转为字节流
    is_success, encoded_image = cv2.imencode('.png', new_model)
    if not is_success:
        raise Exception("Could not encode image.")

    # encoded_image是numpy数组，本身并不是一个流对象
    # 转为字节对象，并将其写入到一个流对象中
    byte_stream = io.BytesIO(encoded_image.tobytes())

    # 转为可用于ocr的字节流
    byte_stream_read = byte_stream.read()

    return byte_stream_read


def commom_gain_text(pic_byte_stream, language="models/config_chinese.txt"):
    # 使用的识别语言配置文件
    my_argument = {"config_path": language}
    # 初始化识别器对象，传入 PaddleOCR-json.exe
    ocr = GetOcrApi("./3rdparty/PaddleOCR-json_v.1.3.1/PaddleOCR-json.exe", my_argument)
    # 读取图片字节流进行OCR
    res = ocr.runBytes(pic_byte_stream)
    # 提取文本块数据
    data_blocks = res["data"]
    return data_blocks


def find_and_click_text(word):
    leave = commom_gain_text(commom_all_ocr()[0])
    p = []
    if "No text found in image." in leave:
        return None
    for b in leave:
        if word in b['text'].lower():
            box = b['box']
            p = [(box[0][0] + box[2][0]) // 2, (box[0][1] + box[2][1]) // 2]
            break
    if p:
        mouse_click(p)
    else:
        msg = f"OCR没有检测到单词{word}"
        my_log("debug", msg)
    return p
