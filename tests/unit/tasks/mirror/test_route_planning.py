import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPO_ROOT / "tasks" / "mirror" / "route_planning.py"
SPEC = importlib.util.spec_from_file_location("route_planning_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ROUTE_PLANNING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE_PLANNING)
find_best_route = ROUTE_PLANNING.find_best_route
find_furthest_class_targets = ROUTE_PLANNING.find_furthest_class_targets
map_road_groups_to_layers = ROUTE_PLANNING.map_road_groups_to_layers


class FakeNode:
    def __init__(self, node_class: str, weight: float):
        self.node_class = node_class
        self.weight = weight
        self.next_nodes = []

    def connect(self, *nodes) -> None:
        self.next_nodes.extend(nodes)


def test_equal_primary_weight_prefers_fewer_battles() -> None:
    start = FakeNode("bus", 0)
    first_battle = FakeNode("battle", 4)
    second_battle = FakeNode("battle", 4)
    event = FakeNode("event", 1)
    risky = FakeNode("risky_encounter", 7)
    start.connect(first_battle, event)
    first_battle.connect(second_battle)
    event.connect(risky)

    weight, path = find_best_route(start, [second_battle, risky])

    assert weight == 8
    assert path == [start, event, risky]


def test_primary_weight_still_has_highest_priority() -> None:
    start = FakeNode("bus", 0)
    first_battle = FakeNode("battle", 1)
    second_battle = FakeNode("battle", 1)
    event = FakeNode("event", 1)
    shop = FakeNode("shop", 2)
    start.connect(event, first_battle)
    first_battle.connect(second_battle)
    event.connect(shop)

    weight, path = find_best_route(start, [second_battle, shop])

    assert weight == 2
    assert path == [start, first_battle, second_battle]


def test_equal_battle_count_prefers_lower_battle_severity() -> None:
    start = FakeNode("bus", 0)
    event = FakeNode("event", 1)
    risky = FakeNode("risky_encounter", 7)
    shop = FakeNode("shop", 2)
    focused = FakeNode("focused_encounter", 6)
    start.connect(event, shop)
    event.connect(risky)
    shop.connect(focused)

    weight, path = find_best_route(start, [risky, focused])

    assert weight == 8
    assert path == [start, shop, focused]


def test_unreachable_target_returns_no_route() -> None:
    start = FakeNode("bus", 1)
    unreachable = FakeNode("boss_battle", 6)

    weight, path = find_best_route(start, [unreachable])

    assert weight == float("inf")
    assert path == []


def test_only_furthest_boss_layer_is_used_as_route_target() -> None:
    start = FakeNode("bus", 0)
    misclassified_boss = FakeNode("boss_battle", 6)
    battle = FakeNode("battle", 4)
    real_boss = FakeNode("boss_battle", 6)
    layers = [[start], [misclassified_boss], [battle, real_boss]]

    assert find_furthest_class_targets(layers, "boss_battle") == [real_boss]


def test_missing_road_group_does_not_shift_later_layers() -> None:
    road_groups = [
        [["UP", (500.0, 300.0)]],
        [["DOWN", (800.0, 700.0)]],
    ]
    layer_x = {1: 100.0, 2: 300.0, 3: 700.0, 4: 900.0}

    mapped = map_road_groups_to_layers(road_groups, layer_x)

    assert mapped == {
        2: [["UP", (500.0, 300.0)]],
        3: [["DOWN", (800.0, 700.0)]],
    }


def test_road_group_far_from_every_boundary_is_ignored() -> None:
    road_groups = [[["UP", (1000.0, 300.0)]]]
    layer_x = {1: 100.0, 2: 300.0, 3: 500.0}

    assert map_road_groups_to_layers(road_groups, layer_x) == {}
