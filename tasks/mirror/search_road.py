import time
from time import sleep

import cv2

from module.automation import auto
from module.config import cfg
from module.logger import log
from tasks.base.retry import retry


class MirrorMap:
    def __init__(self, floor=1):
        self.floor = floor
        self.floor_map = []
        self.map = {}

    def get_next_step(self):
        if len(self.floor_map) > 0:
            next_step = self.floor_map.pop(0)
            return next_step
        else:
            self.floor_map, self.floor_nodes = search_road_from_road_map()
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
MID_LINE_THRESHOLD = 50  # 中间线偏移阈值


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
    def __init__(self, all_nodes: list, initial_bus_pos=Position.MID, mid_line=560):
        """
        初始化路线图
        """
        self.initial_bus_pos = initial_bus_pos  # 保存初始公交位置
        self.layer_nums = 0
        self.layers = {}  # 存储各层节点
        self._add_new_layer()
        self._set_node(1, initial_bus_pos, "bus", 1)
        self.mid_line = mid_line * cfg.set_win_size / 1080

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
            return float('inf'), []  # 无出口

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
