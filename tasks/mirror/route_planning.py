"""镜牢路线选择的纯算法实现。"""

from __future__ import annotations

import heapq
from collections.abc import Collection, Mapping, Sequence
from itertools import count
from typing import Any, Protocol, TypeVar

BATTLE_CLASSES = frozenset(
    {
        "battle",
        "boss_battle",
        "focused_encounter",
        "risky_encounter",
        "abnormality_focused_encounter",
    }
)


class RouteNode(Protocol):
    node_class: str | None
    weight: float
    next_nodes: list[RouteNode]


NodeT = TypeVar("NodeT", bound=RouteNode)
RouteCost = tuple[float, int, float, int]


def find_furthest_class_targets(
    layers: Sequence[Collection[NodeT]],
    node_class: str,
) -> list[NodeT]:
    """只返回最远一层的目标，避免中途误分类节点被当成路线终点。"""
    for layer in reversed(layers):
        targets = [node for node in layer if node.node_class == node_class]
        if targets:
            return targets
    return []


def map_road_groups_to_layers(
    road_groups: Sequence[Sequence[Sequence[Any]]],
    layer_x_by_number: Mapping[int, float],
    *,
    max_offset_ratio: float = 0.75,
) -> dict[int, list[Sequence[Any]]]:
    """按道路横坐标匹配相邻节点层，避免漏检一组后后续层整体错位。"""
    if max_offset_ratio <= 0:
        raise ValueError("max_offset_ratio 必须大于 0")

    boundaries = []
    for layer_number in sorted(layer_x_by_number):
        next_layer = layer_number + 1
        if next_layer not in layer_x_by_number:
            continue
        left_x = float(layer_x_by_number[layer_number])
        right_x = float(layer_x_by_number[next_layer])
        span = abs(right_x - left_x)
        if span <= 0:
            continue
        boundaries.append((layer_number, (left_x + right_x) * 0.5, span))

    if not boundaries:
        return {}

    mapped: dict[int, list[Sequence[Any]]] = {}
    for group in road_groups:
        valid_roads = [
            road
            for road in group
            if len(road) >= 2 and len(road[1]) >= 2
        ]
        if not valid_roads:
            continue
        group_x = sum(float(road[1][0]) for road in valid_roads) / len(valid_roads)
        layer_number, boundary_x, span = min(
            boundaries,
            key=lambda boundary: abs(group_x - boundary[1]),
        )
        if abs(group_x - boundary_x) > span * max_offset_ratio:
            continue
        mapped.setdefault(layer_number, []).extend(valid_roads)
    return mapped


def _node_cost(node: RouteNode) -> RouteCost:
    is_battle = node.node_class in BATTLE_CLASSES
    return (
        node.weight,
        int(is_battle),
        node.weight if is_battle else 0.0,
        1,
    )


def _add_cost(left: RouteCost, right: RouteCost) -> RouteCost:
    return (
        left[0] + right[0],
        left[1] + right[1],
        left[2] + right[2],
        left[3] + right[3],
    )


def find_best_route(start_node: NodeT, target_nodes: Collection[NodeT]) -> tuple[float, list[NodeT]]:
    """按总权重、战斗数、战斗强度、节点数的顺序选择确定性最优路线。"""
    targets = set(target_nodes)
    if not targets:
        return float("inf"), []

    start_cost = _node_cost(start_node)
    best_cost: dict[NodeT, RouteCost] = {start_node: start_cost}
    sequence = count()
    heap: list[tuple[RouteCost, int, NodeT, list[NodeT]]] = [
        (start_cost, next(sequence), start_node, [start_node])
    ]

    while heap:
        current_cost, _, current_node, current_path = heapq.heappop(heap)
        if current_cost != best_cost.get(current_node):
            continue
        if current_node in targets:
            return current_cost[0], current_path

        for next_node in current_node.next_nodes:
            new_cost = _add_cost(current_cost, _node_cost(next_node))
            if new_cost >= best_cost.get(next_node, (float("inf"),) * 4):
                continue
            best_cost[next_node] = new_cost
            heapq.heappush(
                heap,
                (new_cost, next(sequence), next_node, current_path + [next_node]),
            )

    return float("inf"), []
