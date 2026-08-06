import time
from enum import Enum
from functools import lru_cache
from time import sleep

import numpy as np

from module.automation import auto
from module.config import cfg
from module.logger import log
from module.my_error.my_error import InputAttributeError
from tasks.base.retry import retry
from tasks.mirror.road_detection import decode_node_detections, detect_roads, prepare_node_model_input
from tasks.mirror.route_planning import (
    find_best_route,
    find_furthest_class_targets,
    map_road_groups_to_layers,
)

NODE_FEATURE_WEIGHTS = (
    ("mirror/road_in_mir/shop.png", 50, 3),
    ("mirror/road_in_mir/event.png", 8, 3),
    ("mirror/road_in_mir/battle.png", 8, 2),
    ("mirror/road_in_mir/risky_encounter.png", 8, 1),
    ("mirror/road_in_mir/focused_encounter.png", 8, 0),
)
NODE_FEATURE_TARGETS = tuple((target, min_matches) for target, min_matches, _ in NODE_FEATURE_WEIGHTS)
NODE_FEATURE_WEIGHT_BY_TARGET = {target: weight for target, _, weight in NODE_FEATURE_WEIGHTS}


@lru_cache(maxsize=1)
def _get_node_detector():
    """复用模型会话，避免每次重新解析 12 MB ONNX 模型。"""
    import onnxruntime as ort

    session = ort.InferenceSession("./assets/model/best.onnx")
    return session, session.get_inputs()[0].name


def _capture_road_map_frame():
    """截取一张彩色地图帧，同时保留自动化模块惯用的灰度截图状态。"""
    screenshot = auto.take_screenshot(gray=False)
    if screenshot is None:
        return None
    frame = np.array(screenshot)
    auto.screenshot = screenshot.convert("L")
    return frame


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
            if self.floor_map is True and self.floor_nodes is True:
                return True
            if not isinstance(self.floor_map, list):
                self.floor_map = list(self.floor_map)
            self.map[f"floor{self.floor}"] = [self.floor_map[:], self.floor_nodes[:]]

        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            return next_step
        else:
            return False

    def enter_next_node(self, next_step):
        if cfg.mirror_keyboard_navigation:
            log.debug(f"通过键盘按键寻路: {next_step}")
            if next_step == "U":
                auto.key_press("up")
            elif next_step == "D":
                auto.key_press("down")
            elif next_step == "M":
                auto.key_press("right")
            sleep(0.5)
            auto.key_press("enter")
            sleep(1.25)
            return _keyboard_enter_succeeded()

        if next_position := self._get_next_position(next_step):
            auto.mouse_click(next_position[0], next_position[1])
            sleep(1.25)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        if auto.click_element("mirror/mybus_default_distance.png", take_screenshot=True):
            sleep(1.25)
            if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
                return True
        return False

    def _get_next_position(self, direction):
        scale = cfg.set_win_size / 1440
        three_roads = [
            [500 * scale, 50 * scale],
            [500 * scale, 450 * scale],
            [500 * scale, -400 * scale],
        ]
        if direction == "M":
            position = 0
        elif direction == "D":
            position = 1
        elif direction == "U":
            position = 2
        for _ in range(3):
            if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
                return [
                    bus_position[0] + three_roads[position][0],
                    bus_position[1] + three_roads[position][1],
                ]
            sleep(1)
        return None

    def refresh_floor(self, floor):
        if self.floor == floor:
            return
        log.debug(f"镜牢地图楼层缓存更新: {self.floor} -> {floor}")
        self.floor = floor
        self.floor_map = []


def get_node_weight(x, y):
    scale = cfg.set_win_size / 1440
    road_node_bbox = (
        x - 125 * scale,
        y - 125 * scale,
        x + 125 * scale,
        y + 125 * scale,
    )
    matched_target = auto.find_first_feature_element(
        NODE_FEATURE_TARGETS,
        pic_crop=road_node_bbox,
        additional_stack=1,
    )
    if matched_target is None:
        return -5
    return NODE_FEATURE_WEIGHT_BY_TARGET[matched_target]


def _keyboard_enter_succeeded() -> bool:
    """检测键盘寻路按键后是否成功进入下一节点。

    成功条件：点击到"进入"按钮，或地图图例消失（已离开节点选择界面）。
    """
    if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
        return True
    if not auto.find_element("mirror/road_in_mir/legend_assets.png"):
        return True
    return False


# 简单键盘寻路：始终按↑选择第一个节点，完全避免鼠标拖动
def search_road_simple_keyboard():
    """最简单寻路策略：不进行路线规划/相机对齐/节点识别，仅按↑键选择第一个节点后回车。

    适用于 Steam 环境下鼠标拖动地图导致卡死的场景，依赖 mirror_keyboard_navigation。
    """
    if not cfg.mirror_keyboard_navigation:
        log.warning("简单键盘寻路需要启用键盘寻路模式")
        return False

    auto.mouse_to_blank()
    sleep(0.3)

    for attempt in range(2):
        log.debug(f"简单键盘寻路: 第 {attempt + 1} 次尝试按↑+回车")
        auto.key_press("up")
        sleep(0.5)
        auto.key_press("enter")
        sleep(1.25)

        if _keyboard_enter_succeeded():
            return True

    log.debug("简单键盘寻路失败，需回退到常规寻路")
    return False


# 在默认缩放情况下，进行镜牢寻路
def search_road_default_distance():
    start_time = time.time()
    scale = cfg.set_win_size / 1440
    three_roads = [
        [500 * scale, 50 * scale],
        [500 * scale, 450 * scale],
        [500 * scale, -400 * scale],
    ]

    auto.mouse_to_blank()
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
            if check_times(start_time, logs=False):
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
    if not auto.mouse_scroll():
        raise InputAttributeError("后台输入不支持滚轮操作!")
    while auto.take_screenshot() is None:
        continue
    if retry() is False:
        return False
    three_roads = [
        [250 * scale, -200 * scale],
        [250 * scale, 0],
        [250 * scale, 225 * scale],
    ]
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

    if auto.click_element("mirror/mybus_default_distance.png", take_screenshot=True):
        sleep(0.75)
        if auto.click_element("mirror/road_in_mir/enter_assets.png", take_screenshot=True):
            return True, True

    if bus_position := auto.find_element("mirror/mybus_default_distance.png", take_screenshot=True):
        from tasks.base.retry import check_times

        change_times = 5
        while True:
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if check_times(start_time, logs=False):
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
            change_times -= 1
            if change_times <= 0:
                bus = bus_position
                break

    bus_pos = auto.find_element("mirror/mybus_default_distance.png")
    if bus is None:
        bus = bus_pos
    if bus is None:
        log.warning("未能定位镜牢地图上的巴士位置")
        return [], []
    if bus_pos is None:
        bus_pos = bus
    map_frame = _capture_road_map_frame()
    all_nodes = identify_nodes(bus[0], screenshot=map_frame)
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
        all_road = divide_the_area_by_x(identify_road(bus[0], screenshot=map_frame))
        if len(all_road) == 0:
            road = ["M"]
        else:
            if all_road[0][0][0] == "DOWN":
                road = ["D"]
            else:
                road = ["U"]
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
                if check_times(start_time, logs=False):
                    from tasks.base.back_init_menu import back_init_menu

                    back_init_menu()
                    return False, []
                if (
                    set_y_position - 50 * scale < bus_position[1] < set_y_position + 50 * scale
                    and 500 * scale < bus_position[0] < 600 * scale
                ):
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
        map_frame = _capture_road_map_frame()
        all_nodes = identify_nodes(bus[0], screenshot=map_frame)

    if len(road) != 0:
        return road, ["unknown"]

    all_nodes_layer = divide_the_area_by_x(all_nodes)
    all_road = divide_the_area_by_x(identify_road(bus[0], screenshot=map_frame))

    route_graph = RouteGraph(all_nodes_layer, initial_bus_pos=initial_bus_pos, hard_mode=hard_mode)
    route_graph.init_road(all_road, bus[0], bus[1])

    min_weight, path = route_graph.find_min_weight_route()

    if path:
        # 生成方向列表
        directions, road_class_list = route_graph.get_path_directions(path)
        log.debug(f"最小权重: {min_weight}")
        log.debug(f"路径方向: {directions}")
        log.debug(f"行走路径: {road_class_list}")
        return directions, road_class_list
    else:
        log.warning("未能检测到有效路径")

    return [], []


# battle 是常规遭遇战，boss_battle 是 Boss 战，event 是事件，focused_encounter 是集中遭遇战（链式战）
# risky_encounter 是精锐遭遇战（链式战），shop 是商店，abnormality_focused_encounter 是异想体集中遭遇战


def identify_nodes(bus_x, screenshot=None):
    """识别地图节点；允许与道路检测复用同一张彩色截图。"""
    if screenshot is None:
        screenshot = _capture_road_map_frame()
    if screenshot is None:
        return []

    original_image = np.asarray(screenshot)
    blob, scale = prepare_node_model_input(original_image)

    session, input_name = _get_node_detector()
    outputs = session.run(None, {input_name: blob})
    detections = decode_node_detections(outputs[0], scale)

    node_list = []
    bus_margin = 50 * original_image.shape[0] / 1440
    for detection in detections:
        x1, y1, width, height = detection["box"]
        center_x = int((x1 + width / 2) * scale)
        center_y = int((y1 + height / 2) * scale)
        if center_x < bus_x + bus_margin:
            continue
        node_list.append([detection["class_name"], (center_x, center_y)])
    return node_list


def identify_road(bus_x, min_length=160, merge_distance=230, screenshot=None):
    """识别镜牢地图道路；高分辨率截图会先降至 1440p 再执行 LSD。"""
    if screenshot is None:
        if auto.take_screenshot() is None:
            return []
        screenshot = auto.get_screenshot_array()
    return detect_roads(
        np.asarray(screenshot),
        bus_x,
        min_length=min_length,
        merge_distance=merge_distance,
    )


def divide_the_area_by_y(data):
    # 步骤1：按y坐标从小到大排序（确保相近的y相邻）
    sorted_by_y = sorted(data, key=lambda item: item[1][1])  # item[1]是坐标元组，item[1][1]是y值

    # 步骤2：分组（y相近的归为一组，阈值可根据需求调整）
    tolerance = 20 * cfg.set_win_size / 1440
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
    tolerance = 80 * cfg.set_win_size / 1440
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

    log.debug(f"识别到的节点/线段分组后：{groups}")

    return groups


all_node_weight = {
    "battle": 4,
    "boss_battle": 6,
    "event": 1,
    "focused_encounter": 6,
    "risky_encounter": 7,
    "shop": 2,
    "abnormality_focused_encounter": 6,
}

DEFAULT_WEIGHT = 999  # 默认不可达权重
MID_LINE_THRESHOLD = 100  # 中间线偏移阈值


class Position(Enum):
    TOP = 1  # 上层位置
    MID = 0  # 中层位置
    BOTTOM = -1  # 下层位置


class Node:
    def __init__(self, node_class: str = None, weight: float = DEFAULT_WEIGHT, center=None):
        self.node_class = node_class  # 节点标识
        self.weight = weight  # 节点权重
        self.center = center  # 地图坐标，用于把道路匹配到真实的相邻节点
        self.next_nodes = []  # 指向的下一层节点列表（Node对象）

    def add_next_node(self, next_node) -> None:
        """添加下一层节点（自动去重）"""
        if next_node not in self.next_nodes:
            self.next_nodes.append(next_node)

    def __repr__(self):
        return f"Node({self.node_class}, 权重={self.weight}, 指向={self.next_nodes})"


class RouteGraph:
    def __init__(
        self,
        all_nodes: list,
        initial_bus_pos=Position.MID,
        mid_line=560,
        hard_mode=False,
    ):
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
        self.layers[f"layer{self.layer_nums + 1}"] = {
            Position.TOP: Node(),
            Position.MID: Node(),
            Position.BOTTOM: Node(),
        }
        self.layer_nums += 1

    def _set_node(self, layer_nums, position, class_name, weight, center=None):
        this_layer = self.layers[f"layer{layer_nums}"]
        this_layer[position].node_class = class_name
        this_layer[position].weight = weight
        if center is not None:
            this_layer[position].center = (float(center[0]), float(center[1]))

    def _init_node(self, all_nodes, mid_line):
        for layer_data in all_nodes:
            self._add_new_layer()
            for node_entry in layer_data:
                vertical_pos = Position.MID
                if node_entry[1][1] < mid_line - MID_LINE_THRESHOLD * cfg.set_win_size / 1440:
                    vertical_pos = Position.TOP
                elif node_entry[1][1] > mid_line + MID_LINE_THRESHOLD * cfg.set_win_size / 1440:
                    vertical_pos = Position.BOTTOM
                self._set_node(
                    self.layer_nums,
                    vertical_pos,
                    node_entry[0],
                    all_node_weight[node_entry[0]],
                    node_entry[1],
                )

        for i in range(1, self.layer_nums):
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if (
                    self.layers[f"layer{i}"][j].weight != DEFAULT_WEIGHT
                    and self.layers[f"layer{i + 1}"][j].weight != DEFAULT_WEIGHT
                ):
                    self.layers[f"layer{i}"][j].add_next_node(self.layers[f"layer{i + 1}"][j])

        if self.hard_mode is False:
            exit_flag = False
            for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                if self.layers[f"layer{self.layer_nums}"][j].node_class in [
                    "shop",
                    "boss_battle",
                ]:
                    exit_flag = True
                    break
            if exit_flag is False:
                self._add_new_layer()
                self._set_node(self.layer_nums, Position.MID, "shop", 1)
                for j in [Position.TOP, Position.MID, Position.BOTTOM]:
                    self.layers[f"layer{self.layer_nums - 1}"][j].add_next_node(
                        self.layers[f"layer{self.layer_nums}"][Position.MID]
                    )

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
                        self.layers[f"layer{self.layer_nums}"][Position.MID]
                    )

    def _layer_x_coordinates(self) -> dict[int, float]:
        layer_x = {}
        for layer_number in range(1, self.layer_nums + 1):
            centers = [
                node.center
                for node in self.layers[f"layer{layer_number}"].values()
                if node.center is not None
            ]
            if centers:
                layer_x[layer_number] = sum(center[0] for center in centers) / len(centers)
        return layer_x

    def _connect_diagonal_road(self, road_layer: int, road) -> None:
        if road_layer < 1 or road_layer >= self.layer_nums:
            return
        direction = road[0]
        if direction not in {"UP", "DOWN"}:
            return

        position_delta = 1 if direction == "UP" else -1
        candidates = []
        current_layer = self.layers[f"layer{road_layer}"]
        next_layer = self.layers[f"layer{road_layer + 1}"]
        for current_pos in Position:
            try:
                next_pos = Position(current_pos.value + position_delta)
            except ValueError:
                continue
            current_node = current_layer[current_pos]
            next_node = next_layer[next_pos]
            if current_node.weight == DEFAULT_WEIGHT or next_node.weight == DEFAULT_WEIGHT:
                continue
            if current_node.center is None or next_node.center is None:
                continue
            expected_y = (current_node.center[1] + next_node.center[1]) * 0.5
            candidates.append((abs(float(road[1][1]) - expected_y), current_node, next_node))

        if not candidates:
            return
        _, current_node, next_node = min(candidates, key=lambda candidate: candidate[0])
        current_node.add_next_node(next_node)

    def init_road(self, all_road, bus_x, bus_y):
        self.layers["layer1"][self.initial_bus_pos].center = (float(bus_x), float(bus_y))
        if self.hard_mode is True:
            if len(all_road) > 2:
                all_road = all_road[:2]
        road_groups = [
            layer_road
            for layer_road in all_road
            if layer_road and layer_road[0][1][0] >= bus_x
        ]
        roads_by_layer = map_road_groups_to_layers(
            road_groups,
            self._layer_x_coordinates(),
        )
        for road_layer, roads in roads_by_layer.items():
            for road in roads:
                self._connect_diagonal_road(road_layer, road)

    def get_node_layer_info(self, node: Node) -> tuple:
        """辅助方法：获取节点所在的层号、层内位置"""
        for layer_key, layer_nodes in self.layers.items():
            for pos, n in layer_nodes.items():
                if n == node:
                    layer_number = int(layer_key.replace("layer", ""))
                    return layer_key, layer_number, pos
        return None, None, None

    def find_min_weight_route(self) -> tuple[float, list[Node]]:
        """从入口到目标节点选择最优路线；原权重优先，同权重时减少战斗。"""
        start_node = self.layers["layer1"][self.initial_bus_pos]
        end_nodes = find_furthest_class_targets(
            [list(layer.values()) for layer in self.layers.values()],
            "boss_battle",
        )

        if not end_nodes:
            target_layer_num = min(self.layer_nums, 3)
            target_layer = self.layers.get(f"layer{target_layer_num}")
            if target_layer is None:
                return float("inf"), []
            end_nodes = list(target_layer.values())

        return find_best_route(start_node, end_nodes)

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
                directions.append("U")  # 下一层更上层
            elif next_pos.value < current_pos.value:
                directions.append("D")  # 下一层更下层
            else:
                directions.append("M")  # 同一层

        return directions, class_list
