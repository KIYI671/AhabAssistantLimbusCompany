from collections import deque
from dataclasses import dataclass
from math import ceil, floor

import numpy as np

Point = tuple[int, int]
MAP_AREA = (64, 148, 2496, 1160)  # 2560×1440，排除顶栏和队伍栏。
GRID_SPACING = 328


@dataclass(frozen=True)
class MapNode:
    kind: str
    point: Point
    highlighted: bool


@dataclass
class MapView:
    nodes: dict[Point, MapNode]
    # 每条边只记录一次。True 是本骰点亮的连线，False 是可见的普通连线。
    roads: dict[tuple[Point, Point], bool]


def _road(frame, a, b, scale):
    """检查两格之间的线段，避免把并排但没有道路的节点连起来。"""
    x, y = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
    length, width = round(48 * scale), max(2, round(6 * scale))
    horizontal = a[1] == b[1]
    rx, ry = (length, width) if horizontal else (width, length)
    if frame.blue_fraction((x - rx, y - ry, x + rx, y + ry)) > 0.60:
        return True
    # 灰白色道路也是实边，中心笔画应当连续且比两侧背景亮。
    gray = frame.gray if horizontal else frame.gray.T
    along, across = (x // 2, y // 2) if horizontal else (y // 2, x // 2)
    strip = gray[:, along - length // 2 : along + length // 2]
    offset = max(4, round(9 * scale))
    center = strip[across - 1 : across + 2].mean(axis=0)
    upper, lower = strip[across - offset], strip[across + offset]
    sides = (upper.astype(float) + lower) / 2
    if center.mean() > max(upper.mean(), lower.mean()) + 8 and np.mean(center > sides + 10) > 0.70:
        return False
    return None


def read_map(frame, current: Point) -> MapView | None:
    """以玩家图标对齐格位。拖动画面只改变点击坐标，不改变本层格位。"""
    for scale in (1, 0.9, 0.8, 0.7, 0.6, 0.5):
        players = frame.find("player_marker", MAP_AREA, threshold=0.72, scale=scale)
        if players:
            px, py = players[0]
            break
    else:
        return None

    spacing = GRID_SPACING * scale
    kinds = {}
    for kind, threshold in (
        ("event_node", 0.48),
        ("respite_node", 0.60),
        ("regular_encounter_node", 0.50),
        ("boss_node", 0.51),
        ("cleared_node", 0.5),
    ):
        for x, y in frame.find(kind, MAP_AREA, threshold=threshold, scale=scale):
            dx, dy = round((x - px) / spacing), round((y - py) / spacing)
            if max(abs(x - px - dx * spacing), abs(y - py - dy * spacing)) < spacing * 0.13:
                kinds[dx, dy] = kind

    left, top, right, bottom = MAP_AREA
    radius = round(45 * scale)
    nodes = {}
    for dy in range(ceil((top - py) / spacing), floor((bottom - py) / spacing) + 1):
        for dx in range(ceil((left - px) / spacing), floor((right - px) / spacing) + 1):
            x, y = round(px + dx * spacing), round(py + dy * spacing)
            if x >= 1950 and y >= 1040:  # 骰子按钮盖住的格子不能点击。
                continue
            highlighted = frame.blue_fraction((x - radius, y - radius, x + radius, y + radius)) > 0.35
            kind = "cleared_node" if (dx, dy) == (0, 0) else kinds.get((dx, dy))
            if kind or highlighted:
                nodes[current[0] + dx, current[1] + dy] = MapNode(kind or "new", (x, y), highlighted)

    roads = {}
    for (x, y), node in nodes.items():
        for other in ((x + 1, y), (x, y + 1)):
            if other in nodes:
                lit = _road(frame, node.point, nodes[other].point, scale)
                if lit is not None:
                    roads[((x, y), other)] = lit
    return MapView(nodes, roads)


class FloorMap:
    def __init__(self):
        self.current = (0, 0)
        self.kinds = {self.current: "cleared_node"}
        self.roads: dict[Point, set[Point]] = {}
        self.surveyed: set[Point] = set()
        self.target: Point | None = None
        self.entered = False
        self.rejected: set[Point] = set()

    def reject_target(self):
        if self.target is not None:
            self.rejected.add(self.target)
        self.target = None
        self.entered = False

    def arrive(self):
        # 点开详情不算移动。确认进入并回到地图后才更新当前位置。
        if self.entered and self.target is not None:
            self.current = self.target
            self.kinds[self.current] = "cleared_node"
            self.rejected.clear()
            self.target = None
            self.entered = False

    def choose(self, view: MapView) -> Point | None:
        for cell, node in view.nodes.items():
            if cell not in self.kinds or (self.kinds[cell] != "cleared_node" and node.kind != "new"):
                self.kinds[cell] = node.kind
        lit_roads: dict[Point, set[Point]] = {}
        for (a, b), lit in view.roads.items():
            self.roads.setdefault(a, set()).add(b)
            self.roads.setdefault(b, set()).add(a)
            if lit:
                lit_roads.setdefault(a, set()).add(b)
                lit_roads.setdefault(b, set()).add(a)

        # 首领可跨格直达，整条路线都须由本次投掷点亮。
        reachable = {self.current}
        queue = deque([self.current])
        while queue:
            cell = queue.popleft()
            node = view.nodes.get(cell)
            if node and node.kind == self.kinds[cell] == "boss_node" and node.highlighted and cell not in self.rejected:
                return cell
            neighbors = lit_roads.get(cell, set()) - reachable
            reachable.update(neighbors)
            queue.extend(neighbors)

        available = {
            cell
            for cell in lit_roads.get(self.current, ())
            if cell not in self.rejected and (view.nodes[cell].highlighted or self.kinds[cell] == "cleared_node")
        }
        if not available:
            return None
        self.surveyed.add(self.current)
        # 按实际连线逐层搜索，保存到每个目的地的第一步。只在同一距离内优先普通战。
        queue = deque((cell, cell) for cell in sorted(available))
        seen = {self.current, *available, *self.rejected}
        unexplored_exit = None
        while queue:
            targets = []
            for _ in range(len(queue)):
                cell, first = queue.popleft()
                if self.kinds[cell] != "cleared_node":
                    targets.append((self.kinds[cell] != "regular_encounter_node", cell, first))
                    continue
                if unexplored_exit is None and cell not in self.surveyed:
                    unexplored_exit = first
                for other in sorted(self.roads.get(cell, ())):
                    if other not in seen:
                        seen.add(other)
                        queue.append((other, first))
            if targets:
                return min(targets)[2]
        # 中途接手续局时，已通关的岔口也可能还有本次运行未看见的出口。
        return unexplored_exit
