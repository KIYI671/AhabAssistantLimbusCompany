import time
from time import sleep

import cv2

from module.automation import auto
from module.config import cfg
from module.logger import log
from tasks.base.retry import retry


class MirrorMap:
    def __init__(self, floor=1, hard_mode=False):
        self.floor = floor
        self.floor_map = []
        self.map = {}
        self.hard_mode = hard_mode

    def get_next_step(self):
        re_identify = False
        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            if next_step is not None:
                return next_step
            else:
                re_identify = True
        else:
            re_identify = True

        if re_identify is True:
            self.floor_map, self.floor_nodes = search_road_from_road_map(hard_mode=self.hard_mode)
            if not isinstance(self.floor_map, list):
                self.floor_map = list(self.floor_map)
            self.map[f"floor{self.floor}"] = [self.floor_map[:], self.floor_nodes[:]]

        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            return next_step
        else:
            return False

    def enter_next_node(self, next_step):
        if next_position := self._get_next_position(next_step):
            auto.mouse_click(next_position[0], next_position[1])
            sleep(0.75)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        if auto.click_element("mirror/mybus_default_distance.png", take_screenshot=True):
            sleep(0.75)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        return False

    def _get_next_position(self, direction):
        scale = cfg.set_win_size / 1440
        three_roads = [[500 * scale, 50 * scale],
                       [500 * scale, 450 * scale],
                       [500 * scale, -400 * scale]]
        if direction == "M":
            position = 0
        elif direction == "D":
            position = 1
        elif direction == "U":
            position = 2
        for _ in range(3):
            if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
                return [bus_position[0] + three_roads[position][0], bus_position[1] + three_roads[position][1]]
            sleep(1)
        return None

    def next_floor(self):
        self.floor += 1
        self.floor_map = []

    def refresh_floor(self, floor):
        self.floor = floor


def get_node_weight(x, y):
    scale = cfg.set_win_size / 1440
    road_node_bbox = (x - 125 * scale, y - 125 * scale, x + 125 * scale, y + 125 * scale)
    if auto.find_feature_element("mirror/road_in_mir/shop.png", road_node_bbox, 50):
        return 3
    elif auto.find_feature_element("mirror/road_in_mir/event.png", road_node_bbox):
        return 3
    elif auto.find_feature_element("mirror/road_in_mir/battle.png", road_node_bbox, ):
        return 2
    elif auto.find_feature_element("mirror/road_in_mir/hard_battle.png", road_node_bbox):
        return 1
    elif auto.find_feature_element("mirror/road_in_mir/hard_battle2.png", road_node_bbox):
        return 0
    return -5


# 在默认缩放情况下，进行镜牢寻路
def search_road_default_distance():
    start_time = time.time()
    scale = cfg.set_win_size / 1440
    three_roads = [[500 * scale, 50 * scale],
                   [500 * scale, 450 * scale],
                   [500 * scale, -400 * scale]]

    while auto.take_screenshot() is None:
        continue
    if retry() is False:
        return False
    # 判断中、下两个节点是否有权重3的节点，有的话直接选择进入
    node_weight = {}
    if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
        for road in three_roads[:2]:
            node_x = bus_position[0] + road[0]
            node_y = bus_position[1] + road[1]
            weight = get_node_weight(node_x, node_y)
            node_weight[(node_x, node_y)] = weight
        max_weight = max(node_weight.values())
        if max_weight == 3:
            road_list = sorted(node_weight, key=node_weight.get, reverse=True)
            road = road_list[0]
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
    # 如果中、下两个节点没有权重3的节点，查看所有节点的权重，选择权重最大的节点进入
    if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
        from tasks.base.retry import check_times
        while True:
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if check_times(start_time):
                from tasks.base.back_init_menu import back_init_menu
                back_init_menu()
                return False
            if 600 * scale < bus_position[1] < 700 * scale:
                break
            dy = 650 * scale - bus_position[1]
            auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=0, dy=dy)
            sleep(1)
            auto.mouse_to_blank()

            bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
            if bus_position is None:
                break

    node_list = []
    if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
        for road in three_roads[:2]:
            node_x = bus_position[0] + road[0]
            node_y = bus_position[1] + road[1]
            node_list.append((node_x, node_y))
        old_weight = node_weight.values()
        all_node_weight = dict(zip(node_list, old_weight))
        for road in three_roads[2:]:
            node_x = bus_position[0] + road[0]
            node_y = bus_position[1] + road[1]
            weight = get_node_weight(node_x, node_y)
            all_node_weight[(node_x, node_y)] = weight
        all_node_weight[bus_position[0], bus_position[1]] = -6
        # 根据all_node_weight，按照各个键的值，从大到小以生成只有键的新的列表
        road_list = sorted(all_node_weight, key=all_node_weight.get, reverse=True)
        for road in road_list:
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
    return False


# 如果默认缩放无法镜牢寻路，进行滚轮缩放后继续寻路
def search_road_farthest_distance():
    scale = cfg.set_win_size / 1440
    auto.mouse_click_blank()
    auto.mouse_scroll()
    while auto.take_screenshot() is None:
        continue
    if retry() is False:
        return False
    three_roads = [[250 * scale, -200 * scale],
                   [250 * scale, 0],
                   [250 * scale, 225 * scale]]
    if bus_position := auto.find_element("mirror/mybus_maximum_distance.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < cfg.set_win_size * 16 / 9 and 0 < road[1] < cfg.set_win_size:
                auto.mouse_click(road[0], road[1])
                sleep(0.75)
                if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                    return True
        auto.mouse_click(bus_position[0], bus_position[1])
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True
    return False


def search_road_from_road_map(hard_mode=False):
    start_time = time.time()
    scale = cfg.set_win_size / 1440
    road = []
    bus = None

    if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
        from tasks.base.retry import check_times
        while True:
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if check_times(start_time):
                from tasks.base.back_init_menu import back_init_menu
                back_init_menu()
                return False, []
            if 675 * scale < bus_position[1] < 700 * scale and 150 * scale > bus_position[0]:
                bus = bus_position
                break
            dx = 80 * scale - bus_position[0]
            dy = 690 * scale - bus_position[1]
            auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=dx, dy=dy)
            sleep(0.5)
            auto.mouse_to_blank()

            bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
            if bus_position is None:
                break

    bus_pos = auto.find_element("mirror/mybus_default_distance.png")
    all_nodes = identify_nodes(bus[0])
    y_area = divide_the_area_by_y(all_nodes)
    reset_position = False
    initial_bus_pos = Position.MID
    if len(y_area) == 2:
        if bus_pos[1] > y_area[0][0][1][1] + 50 * scale:
            reset_position = "Bottom"
            initial_bus_pos = Position.BOTTOM
        else:
            reset_position = "Top"
            initial_bus_pos = Position.TOP
    elif len(y_area) == 1:
        all_road = divide_the_area_by_x(identify_road(bus[0]))
        if len(all_road) == 0:
            road = ['M']
        else:
            if all_road[0][0][0] == "DOWN":
                road = ['D']
            else:
                road = ['U']
    if reset_position is not False:
        if reset_position == "Bottom":
            set_y_position = 1100 * scale
        else:
            set_y_position = 250 * scale
        if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
            from tasks.base.retry import check_times
            while True:
                if auto.get_restore_time() is not None:
                    start_time = max(start_time, auto.get_restore_time())
                if check_times(start_time):
                    from tasks.base.back_init_menu import back_init_menu
                    back_init_menu()
                    return False, []
                if set_y_position - 50 * scale < bus_position[1] < set_y_position + 50 * scale and 500 * scale < \
                        bus_position[0] < 600 * scale:
                    bus = bus_position
                    break
                dx = 550 * scale - bus_position[0]
                dy = set_y_position - bus_position[1]
                auto.mouse_drag(bus_position[0], bus_position[1], drag_time=1.5, dx=dx, dy=dy)
                sleep(0.5)
                auto.mouse_to_blank()

                bus_position = auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True)
                if bus_position is None:
                    break
        all_nodes = identify_nodes(bus[0])

    if len(road) != 0:
        return road, ["unknown"]

    all_nodes_layer = divide_the_area_by_x(all_nodes)
    all_road = divide_the_area_by_x(identify_road(bus[0]))

    route_graph = RouteGraph(all_nodes_layer, initial_bus_pos=initial_bus_pos, hard_mode=hard_mode)
    route_graph.init_road(all_road, bus[0], bus_pos[1])

    min_weight, path = route_graph.find_min_weight_route()

    if path:
        # 生成方向列表
        directions, road_class_list = route_graph.get_path_directions(path)
        log.DEBUG(f"最小权重: {min_weight}")
        log.DEBUG(f"路径方向: {directions}")
        log.DEBUG(f"行走路径: {road_class_list}")
        return directions, road_class_list
    else:
        log.WARNING("未能检测到有效路径")

    return [], []


# battle 是常规遭遇战，boss_battle 是boss战，event 是事件，hard_battle 是集中遭遇战（非拉链），hard_battle_2 是精锐遭遇战（有拉链）
# shop 是商店，small_boss_battle 是异想体遭遇战

def identify_nodes(bus_x):
    import numpy as np
    import onnxruntime as ort

    # 定义检测目标的类别标签（与模型训练时的类别一致）
    CLASSES = ['battle', 'boss_battle', 'event', 'hard_battle', 'hard_battle_2', 'shop', 'small_boss_battle']

    no_flag = False  # 标记是否检测到目标（初始为 False，未检测到时设为 True）

    # 加载 ONNX 格式的目标检测模型
    session = ort.InferenceSession("./assets/model/best.onnx")

    # 读取原始图像（BGR 格式，由 OpenCV 读取）
    auto.take_screenshot(gray=False)
    original_image: np.ndarray = np.array(auto.screenshot)
    [height, width, _] = original_image.shape  # 获取原始图像的高、宽、通道数

    # 创建正方形空白图像（边长为原始图像的最大边），用于保持图像比例并避免变形
    length = max((height, width))  # 正方形边长取原始图像的高或宽的最大值
    image = np.zeros((length, length, 3), np.uint8)  # 初始化全黑正方形图像
    image[0:height, 0:width] = original_image  # 将原始图像粘贴到正方形的左上角区域

    # 计算缩放比例（正方形边长 → 模型输入尺寸 640 的缩放因子）
    scale = length / 640

    # 将图像转换为模型所需的输入格式（blob）
    # blobFromImage 参数说明：
    # - image: 输入图像（正方形）
    # - scalefactor=1/255: 像素值归一化（0-255 → 0-1）
    # - size=(640, 640): 模型输入的尺寸（宽高均为 640）
    # - swapRB=True: 交换 RGB 通道（OpenCV 读取的是 BGR，模型可能需要 RGB）
    blob = cv2.dnn.blobFromImage(image, scalefactor=1 / 255, size=(640, 640), swapRB=True)

    # 执行模型推理（输入为 blob）
    outputs = session.run(None, {session.get_inputs()[0].name: blob})  # 输出为模型预测结果

    outputs = outputs[0]  # 提取第一个输出（YOLO 通常输出一个包含所有检测结果的数组）
    outputs = np.array([cv2.transpose(outputs[0])])  # 转置维度（适配后续处理逻辑）
    rows = outputs.shape[1]  # 获取检测结果的数量（每行对应一个目标的预测信息）

    boxes = []  # 存储边界框坐标（格式：[x_center, y_center, width, height]）
    scores = []  # 存储检测置信度
    class_ids = []  # 存储类别 ID

    # 遍历所有检测结果（每行对应一个目标的预测信息）
    for i in range(rows):
        # 提取类别置信度（前 4 列是边界框坐标，第 5 列及之后是各分类得分）
        classes_scores = outputs[0][i][4:]

        # 找到当前目标的最大类别置信度及其对应的类别索引
        (minScore, maxScore, minClassLoc, (x, maxClassIndex)) = cv2.minMaxLoc(classes_scores)

        # 若最大置信度超过阈值（0.25），则保留该检测结果
        if maxScore >= 0.25:
            # 计算边界框的左上角坐标和宽高（YOLO 输出为中心点坐标 + 宽高，需转换）
            box = [
                outputs[0][i][0] - (0.5 * outputs[0][i][2]),  # 左上角 x = 中心点 x - 半宽
                outputs[0][i][1] - (0.5 * outputs[0][i][3]),  # 左上角 y = 中心点 y - 半高
                outputs[0][i][2],  # 宽度（中心点 x 到右边界点的距离）
                outputs[0][i][3],  # 高度（中心点 y 到下边界点的距离）
            ]
            boxes.append(box)  # 保存边界框
            scores.append(maxScore)  # 保存置信度
            class_ids.append(maxClassIndex)  # 保存类别 ID

    # 使用 NMS 抑制重叠的边界框（保留置信度高的框）
    # 参数说明：
    # - boxes: 边界框列表（格式：[x1, y1, w, h]）
    # - scores: 置信度列表
    # - score_threshold=0: 置信度阈值（此处未过滤低分，因前面已过滤）
    # - nms_threshold=0.4: 重叠框的交并比（IoU）阈值（>0.4 则抑制）
    result_boxes = cv2.dnn.NMSBoxes(boxes, scores, 0, 0.4, 0.5)

    detections = []  # 存储最终的检测结果（字典列表）

    if len(result_boxes) > 0:  # 若有有效检测结果
        for i in range(len(result_boxes)):
            index = result_boxes[i]  # 获取当前框在原始列表中的索引（NMS 输出为二维数组）
            box = boxes[index]  # 获取对应的边界框

            # 构造检测结果字典（包含类别、置信度、边界框等信息）
            detection = {
                "class_id": class_ids[index],
                "class_name": CLASSES[class_ids[index]],
                "confidence": scores[index],
                "box": box,  # 原始边界框（基于 640x640 输入尺寸）
                "scale": scale,  # 缩放比例（用于还原到原始图像尺寸）
            }
            detections.append(detection)  # 添加到结果列表
    else:
        no_flag = True  # 无检测结果时标记为 True

    if no_flag:
        return None

    node_list = []

    # 遍历每个字典并处理
    for d in detections:
        # 提取class_name
        class_name = d['class_name']

        # 提取box并计算中心点（转换为Python浮点数）
        box = d['box']
        x1 = box[0].item()  # 左上角x（转换为Python float）
        y1 = box[1].item()  # 左上角y（转换为Python float）
        w = box[2].item()  # 宽度（转换为Python float）
        h = box[3].item()  # 高度（转换为Python float）
        center_x = int((x1 + w / 2) * scale)
        center_y = int((y1 + h / 2) * scale)

        if center_x < bus_x + 50:
            continue

        # 组成子列表并添加到节点总列表
        node_list.append([class_name, (center_x, center_y)])  # 中心点用元组存储，也可改为列表

    return node_list


def identify_road(bus_x, min_length=160, merge_distance=230):
    """
    增强版LSD对角线检测，完整输出模块，显示方向标记和中心点

    参数：
        image_path (str): 输入图像路径
        min_length (int): 线段最小长度阈值（用于筛选有效线段）
        merge_distance (int): 线段合并的最大距离阈值（用于合并相近线段）
    """
    import numpy as np
    import math

    min_length = min_length * (cfg.set_win_size / 1440)

    # === 可靠检测阶段 ===
    def get_detected_lines(img):
        """获取检测到的所有线段"""
        lsd = cv2.createLineSegmentDetector(0)
        detected = lsd.detect(img)
        if detected and detected[0] is not None:
            return detected[0]

    auto.take_screenshot()
    screenshot = np.array(auto.screenshot)
    raw_lines = get_detected_lines(screenshot)  # 调用检测函数获取原始线段数据
    if raw_lines is None or len(raw_lines) == 0:  # 检测结果为空
        log.WARNING("⚠️ 未检测到任何线段")  # 提示无结果
        return []  # 返回空列表

    # 数据格式标准化（统一不同算法的输出格式）
    segments_data = []
    for line_info in raw_lines:
        try:
            # 提取线段坐标（不同算法返回格式可能不同，统一为[x1,y1,x2,y2]）
            coords = line_info[0] if hasattr(line_info, '__len__') else line_info  # 处理数组或元组
            x1, y1, x2, y2 = map(float, coords[:4])  # 转换为浮点数（保留精度）

            # 计算线段基础参数
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)  # 线段长度（欧氏距离）
            center_x = (x1 + x2) / 2  # 中心点x坐标
            center_y = (y1 + y2) / 2  # 中心点y坐标

            # 计算斜率和角度（角度范围0-180度，避免重复）
            dx, dy = x2 - x1, y2 - y1  # 坐标差
            slope = dy / dx if dx != 0 else float('inf')  # 斜率（dx=0时为无穷大，即垂直线）
            angle = math.degrees(math.atan2(dy, dx)) % 180  # 角度（弧度转角度，取模180消除方向歧义）

            # 存储为字典（结构化数据，方便后续处理）
            segments_data.append({
                'line': [int(x1), int(y1), int(x2), int(y2)],  # 整数坐标的线段端点
                'length': length,  # 长度
                'center': (center_x, center_y),  # 中心点（浮点数精度）
                'slope': slope,  # 斜率
                'angle': angle,  # 角度（0-180度）
                'dx': dx,  # x坐标差（原始值）
                'dy': dy  # y坐标差（原始值）
            })
        except:
            continue  # 跳过格式错误的线段（异常处理）

    # 筛选长度大于min_length的线段
    diagonal_candidates = [s for s in segments_data if min_length <= s['length'] < 1000]  # 初始长度范围

    if not diagonal_candidates:  # 若初始筛选无结果，放宽长度下限
        diagonal_candidates = [s for s in segments_data if 50 <= s['length'] < 1000]  # 放宽到50px
        if not diagonal_candidates:  # 若仍无结果，返回空
            return []

    # 按斜率合并（将同一方向、相近位置的线段合并为一条）
    merged_records = []
    directions = ['45°', '135°']  # 目标方向：45度和135度（常见对角线方向）

    for direction_name in directions:
        # 定义方向对应的角度范围（45度对应30-60度，135度对应120-150度，覆盖误差）
        angle_limits = (30, 60) if direction_name == '45°' else (120, 150)
        # 筛选当前方向的候选线段（角度在范围内的线段）
        group = [s for s in diagonal_candidates if angle_limits[0] <= s['angle'] <= angle_limits[1]]

        if not group:  # 当前方向无线段，跳过
            continue

        # 按线段长度降序排序（优先保留长线段作为基准）
        group.sort(key=lambda x: x['length'], reverse=True)
        used = set()  # 记录已合并的线段索引（避免重复合并）

        for i, base_info in enumerate(group):  # 遍历每条线段作为基准
            if i in used:  # 已被合并过，跳过
                continue

            cluster = [base_info]  # 当前线段的合并组（初始包含基准线段）
            base_slope = base_info['slope']  # 基准线段斜率
            base_center = base_info['center']  # 基准线段中心点

            for j, other in enumerate(group):  # 遍历其他线段，寻找可合并的
                if j <= i or j in used:  # 跳过自身或已合并的线段
                    continue

                # 条件1：斜率差异检查（允许±8度误差，垂直线特殊处理）
                slope_diff = abs(base_slope - other['slope']) if base_slope != float('inf') else 0
                if slope_diff > 8 and base_slope != float('inf'):
                    continue  # 斜率差异过大，不合并

                # 条件2：中心点距离检查（不超过merge_distance）
                distance = math.sqrt(
                    (base_center[0] - other['center'][0]) ** 2 + (base_center[1] - other['center'][1]) ** 2)
                if distance <= merge_distance:
                    cluster.append(other)  # 加入合并组
                    used.add(j)  # 标记为已合并

            # 合并组内线段，生成新的代表线段（基于所有点的最小二乘拟合）
            # 提取组内所有线段的端点坐标（用于拟合）
            all_x = [pt[0] for info in cluster for pt in [info['line'][:2], info['line'][2:]]]  # 所有点的x坐标
            all_y = [pt[1] for info in cluster for pt in [info['line'][:2], info['line'][2:]]]  # 所有点的y坐标

            if len(set(all_x)) > 1:  # 非垂直线（x坐标有变化），用线性拟合
                slope, intercept = np.polyfit(all_x, all_y, 1)  # 最小二乘拟合直线（y = slope*x + intercept）
                min_x, max_x = int(min(all_x)), int(max(all_x))  # 拟合直线的x范围（端点）
                y_min = int(slope * min_x + intercept)  # 起点y坐标
                y_max = int(slope * max_x + intercept)  # 终点y坐标
                new_line = [min_x, y_min, max_x, y_max]  # 合并后的线段端点
                new_center = ((min_x + max_x) / 2, (y_min + y_max) / 2)  # 合并后的中心点
                new_slope = slope  # 合并后的斜率
            else:  # 垂直线（x坐标不变），直接使用基准线段
                new_line = cluster[0]['line']
                new_center = cluster[0]['center']
                new_slope = cluster[0]['slope']

            # 仅保留长度≥min_length的合并结果（避免合并后线段过短）
            if math.sqrt((new_line[2] - new_line[0]) ** 2 + (new_line[3] - new_line[1]) ** 2) >= min_length:
                merged_records.append({
                    'line': new_line,  # 合并后的线段端点
                    'center': new_center,  # 合并后的中心点
                    'slope': new_slope,  # 合并后的斜率
                    'direction': direction_name,  # 方向（45°或135°）
                    'length': math.sqrt((new_line[2] - new_line[0]) ** 2 + (new_line[3] - new_line[1]) ** 2),
                    # 合并后的长度
                    'merged_from': len(cluster)  # 合并的原始线段数量
                })

    segment_list = []

    # 遍历每个字典并处理
    for segment in merged_records:
        # 提取class_name
        class_name = segment['direction']
        if class_name == '45°':
            class_name = 'DOWN'
        elif class_name == '135°':
            class_name = 'UP'
        center = segment['center']
        if center[0] < bus_x + 50 * (cfg.set_win_size / 1440):
            continue

        # 组成子列表并添加到节点总列表
        segment_list.append([class_name, center])

    # 返回结构化数据
    return segment_list


def divide_the_area_by_y(data):
    # 步骤1：按y坐标从小到大排序（确保相近的y相邻）
    sorted_by_y = sorted(data, key=lambda item: item[1][1])  # item[1]是坐标元组，item[1][1]是y值

    # 步骤2：分组（y相近的归为一组，阈值可根据需求调整）
    tolerance = 20  # y差值小于等于20视为相近（可根据实际数据调整）
    groups = []
    for item in sorted_by_y:
        current_y = item[1][1]
        if not groups:
            # 第一个元素，新建组
            groups.append([item])
        else:
            # 检查当前元素与最后一个组的最后一个元素的y差值
            last_group_last_y = groups[-1][-1][1][1]
            if current_y - last_group_last_y <= tolerance:
                # 加入最后一个组
                groups[-1].append(item)
            else:
                # 新建组
                groups.append([item])
    return groups


def divide_the_area_by_x(data):
    # 步骤1：按x坐标从小到大排序（确保相近的x相邻）
    sorted_by_x = sorted(data, key=lambda item: item[1][0])

    # 步骤2：分组（x相近的归为一组，阈值可根据需求调整）
    tolerance = 80  # x差值小于等于tolerance视为相近
    groups = []
    for item in sorted_by_x:
        current_x = item[1][0]
        if not groups:
            # 第一个元素，新建组
            groups.append([item])
        else:
            # 检查当前元素与最后一个组的最后一个元素的x差值
            last_group_last_x = groups[-1][-1][1][0]
            if current_x - last_group_last_x <= tolerance:
                # 加入最后一个组
                groups[-1].append(item)
            else:
                # 新建组
                groups.append([item])

    # 步骤3：每个组内按y坐标从小到大排序
    for group in groups:
        group.sort(key=lambda item: item[1][1])

    log.DEBUG(f"识别到的节点/线段分组后：{groups}")

    return groups


import heapq
from enum import Enum

all_node_weight = {'battle': 30, 'boss_battle': 1, 'event': 18, 'hard_battle': 75, 'hard_battle_2': 100, 'shop': 1,
                   'small_boss_battle': 999}

DEFAULT_WEIGHT = 999  # 默认不可达权重
MID_LINE_THRESHOLD = 100  # 中间线偏移阈值


class Position(Enum):
    TOP = 1  # 上层位置
    MID = 0  # 中层位置
    BOTTOM = -1  # 下层位置


class Node:
    def __init__(self, node_class: str = None, weight: float = DEFAULT_WEIGHT):
        self.node_class = node_class  # 节点标识
        self.weight = weight  # 节点权重
        self.next_nodes = []  # 指向的下一层节点列表（Node对象）

    def add_next_node(self, next_node) -> None:
        """添加下一层节点（自动去重）"""
        if next_node not in self.next_nodes:
            self.next_nodes.append(next_node)

    def __repr__(self):
        return f"Node({self.node_class}, 权重={self.weight}, 指向={self.next_nodes})"


class RouteGraph:
    def __init__(self, all_nodes: list, initial_bus_pos=Position.MID, mid_line=560, hard_mode=False):
        """
        初始化路线图
        """
        self.initial_bus_pos = initial_bus_pos  # 保存初始公交位置
        self.layer_nums = 0
        self.layers = {}  # 存储各层节点
        self._add_new_layer()
        self._set_node(1, initial_bus_pos, "bus", 1)
        self.mid_line = mid_line * cfg.set_win_size / 1080
        self.hard_mode = hard_mode

        self._init_node(all_nodes, self.mid_line)

    def _add_new_layer(self):
        self.layers[f"layer{self.layer_nums + 1}"] = {Position.TOP: Node(), Position.MID: Node(),
                                                      Position.BOTTOM: Node()}
        self.layer_nums += 1

    def _set_node(self, layer_nums, position, class_name, weight):
        this_layer = self.layers[f"layer{layer_nums}"]
        this_layer[position].node_class = class_name
        this_layer[position].weight = weight

    def _init_node(self, all_nodes, mid_line):
        for layer_data in all_nodes:
            self._add_new_layer()
            for node_entry in layer_data:
                vertical_pos = Position.MID
                if node_entry[1][1] < mid_line - MID_LINE_THRESHOLD * cfg.set_win_size / 1440:
                    vertical_pos = Position.TOP
                elif node_entry[1][1] > mid_line + MID_LINE_THRESHOLD * cfg.set_win_size / 1440:
                    vertical_pos = Position.BOTTOM
                self._set_node(self.layer_nums, vertical_pos, node_entry[0], all_node_weight[node_entry[0]])

        for i in range(1, self.layer_nums):
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{i}"][j].weight != DEFAULT_WEIGHT and self.layers[f"layer{i + 1}"][
                    j].weight != DEFAULT_WEIGHT:
                    self.layers[f"layer{i}"][j].add_next_node(self.layers[f"layer{i + 1}"][j])

        if self.hard_mode is False:
            exit_flag = False
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{self.layer_nums}"][j].node_class in ["shop", "boss_battle"]:
                    exit_flag = True
                    break
            if exit_flag is False:
                self._add_new_layer()
                self._set_node(self.layer_nums, Position.MID, "shop", 1)
                for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                    self.layers[f"layer{self.layer_nums - 1}"][j].add_next_node(
                        self.layers[f"layer{self.layer_nums}"][Position.MID])

            exit_flag = False
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{self.layer_nums}"][j].node_class in ["boss_battle"]:
                    exit_flag = True
                    break
            if exit_flag is False:
                self._add_new_layer()
                self._set_node(self.layer_nums, Position.MID, "boss_battle", 1)
                for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                    self.layers[f"layer{self.layer_nums - 1}"][j].add_next_node(
                        self.layers[f"layer{self.layer_nums}"][Position.MID])

    def init_road(self, all_road, bus_x, bus_y):
        if self.hard_mode is True:
            if len(all_road)>2:
                all_road = all_road[:2]
        road_layer = 1
        for layer_road in all_road:
            if layer_road[0][1][0] < bus_x:
                continue
            for road in layer_road:
                if road[0] == "UP":
                    vertical_pos = Position.MID if bus_y > road[1][1] else Position.BOTTOM
                    if self.layers[f"layer{road_layer}"][vertical_pos].weight != DEFAULT_WEIGHT and \
                            self.layers[f"layer{road_layer + 1}"][
                                Position(vertical_pos.value + 1)].weight != DEFAULT_WEIGHT:
                        self.layers[f"layer{road_layer}"][vertical_pos].add_next_node(
                            self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value + 1)])
                elif road[0] == "DOWN":
                    vertical_pos = Position.TOP if bus_y > road[1][1] else Position.MID
                    if self.layers[f"layer{road_layer}"][vertical_pos].weight != DEFAULT_WEIGHT and \
                            self.layers[f"layer{road_layer + 1}"][
                                Position(vertical_pos.value - 1)].weight != DEFAULT_WEIGHT:
                        self.layers[f"layer{road_layer}"][vertical_pos].add_next_node(
                            self.layers[f"layer{road_layer + 1}"][Position(vertical_pos.value - 1)])
            road_layer += 1

    def get_node_layer_info(self, node: Node) -> tuple:
        """辅助方法：获取节点所在的层号、层内位置"""
        for layer_key, layer_nodes in self.layers.items():
            for pos, n in layer_nodes.items():
                if n == node:
                    layer_number = int(layer_key.replace("layer", ""))
                    return layer_key, layer_number, pos
        return None, None, None

    def find_min_weight_route(self) -> tuple[float, list[Node]]:
        """
        使用Dijkstra算法计算从入口到出口的最小权重路径
        返回：(最小总权重, 路径节点列表)
        """
        # 确定起点节点（layer1的初始公交位置）
        start_node = self.layers["layer1"][self.initial_bus_pos]

        # 收集所有终点节点（boss_battle）
        end_nodes = []
        for layer in self.layers.values():
            for pos_node in layer.values():
                if pos_node.node_class in ["boss_battle"]:
                    end_nodes.append(pos_node)

        if not end_nodes:
            # 确定目标层：至多三层，取当前最大层（不超过3）
            current_max_layer = self.layer_nums
            target_layer_num = min(current_max_layer, 3)
            target_layer = f"layer{target_layer_num}"

            # 检查目标层是否存在
            if target_layer not in self.layers:
                return float('inf'), []  # 目标层不存在，无法到达

            # 收集目标层的所有节点
            target_nodes = list(self.layers[target_layer].values())
            if not target_nodes:
                return float('inf'), []  # 目标层无节点，无法到达

            # 初始化距离字典，所有节点初始距离为无穷大，起点距离为自身权重
            distances = {node: float('inf') for layer in self.layers.values() for pos_node in layer.values() for node in
                         [pos_node]}
            distances[start_node] = start_node.weight

            # 优先队列：(当前总权重, 节点唯一标识（避免比较Node）, 当前节点, 路径列表)
            heap = []
            heapq.heappush(heap, (start_node.weight, id(start_node), start_node, [start_node]))

            # 记录已处理的节点
            processed = set()

            min_total = float('inf')
            min_path = []

            while heap:
                current_total, _, current_node, current_path = heapq.heappop(heap)

                if current_node in processed:
                    continue
                processed.add(current_node)

                # 检查是否是目标节点（目标层的节点）
                if current_node in target_nodes:
                    # 更新最小路径
                    if current_total < min_total:
                        min_total = current_total
                        min_path = current_path.copy()

                # 遍历所有邻接节点
                for next_node in current_node.next_nodes:
                    if next_node in processed:
                        continue  # 已处理过，跳过

                    new_total = current_total + next_node.weight
                    new_path = current_path + [next_node]

                    # 如果找到更短路径，更新距离并加入队列
                    if new_total < distances[next_node]:
                        distances[next_node] = new_total
                        heapq.heappush(heap, (new_total, id(next_node), next_node, new_path))

            # 返回找到的最小路径，若没有则返回无穷大和空列表
            return (min_total, min_path) if min_total != float('inf') else (float('inf'), [])

        # 初始化距离字典，所有节点初始距离为无穷大，起点距离为自身权重
        distances = {node: float('inf') for layer in self.layers.values() for pos_node in layer.values() for node in
                     [pos_node]}
        distances[start_node] = start_node.weight

        # 优先队列：(当前总权重, 节点唯一标识（避免比较Node）, 当前节点, 路径列表)
        heap = []
        heapq.heappush(heap, (start_node.weight, id(start_node), start_node, [start_node]))

        # 记录已处理的节点（优化：当节点第一次弹出时，已找到最短路径）
        processed = set()

        while heap:
            current_total, _, current_node, current_path = heapq.heappop(heap)  # 忽略辅助标识

            if current_node in processed:
                continue
            processed.add(current_node)

            # 到达终点，返回结果
            if current_node in end_nodes:
                return current_total, current_path

            # 遍历所有邻接节点
            for next_node in current_node.next_nodes:
                if next_node in processed:
                    continue  # 已处理过，跳过

                new_total = current_total + next_node.weight
                new_path = current_path + [next_node]

                # 如果找到更短路径，更新并加入队列
                if new_total < distances[next_node]:
                    distances[next_node] = new_total
                    # 添加辅助标识（id(next_node)）确保堆能正确排序
                    heapq.heappush(heap, (new_total, id(next_node), next_node, new_path))

        # 无可达路径
        return float('inf'), []

    def get_path_directions(self, path: list[Node]) -> tuple[list[str], list[str]]:
        """
        根据路径节点列表生成移动方向列表（U/D/M）和节点类别列表
        U: 下一个节点在当前节点上方，D: 下方，M: 同一层
        返回：(方向列表, 节点类别列表)
        """
        directions = []
        # 提取路径中所有节点的类别
        class_list = [node.node_class for node in path]

        if len(path) < 2:
            return directions, class_list  # 路径长度不足，无方向，但仍返回类别列表

        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]

            # 获取当前节点和下一个节点的层内位置
            _, _, current_pos = self.get_node_layer_info(current_node)
            _, _, next_pos = self.get_node_layer_info(next_node)

            if next_pos.value > current_pos.value:
                directions.append('U')  # 下一层更上层
            elif next_pos.value < current_pos.value:
                directions.append('D')  # 下一层更下层
            else:
                directions.append('M')  # 同一层

        return directions, class_list
