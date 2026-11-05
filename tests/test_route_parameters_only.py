"""Custom weights change node costs, while navigation flow stays upstream."""
from upstream_reference import REFERENCE, original_source

import ast
import copy
import subprocess

import pytest
from unittest.mock import Mock

from test_optional_integration import ROOT
from test_optional_route_event import load_policy


def function(source, name, cls=None):
    body = ast.parse(source).body
    if cls:
        body = next(n.body for n in body if isinstance(n, ast.ClassDef) and n.name == cls)
    return next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)


@pytest.mark.parametrize("relative,cls,name", [
    ("tasks/mirror/mirror.py", "Mirror", "search_road"),
    ("tasks/mirror/search_road.py", "MirrorMap", "enter_next_node"),
    ("tasks/mirror/search_road.py", "MirrorMap", "refresh_floor"),
    ("tasks/mirror/search_road.py", None, "identify_nodes"),
    ("tasks/mirror/search_road.py", None, "search_road_simple_keyboard"),
    ("tasks/mirror/search_road.py", None, "search_road_default_distance"),
    ("tasks/mirror/search_road.py", None, "search_road_farthest_distance"),
    ("tasks/mirror/search_road.py", "RouteGraph", "find_min_weight_route"),
    ("tasks/mirror/search_road.py", "RouteGraph", "init_road"),
])
def test_navigation_and_recovery_control_flow_match_original(relative, cls, name):
    current = (ROOT / relative).read_text(encoding="utf-8")
    assert ast.dump(function(current, name, cls)) == ast.dump(function(original_source(relative), name, cls))


def test_map_planning_diff_is_only_the_weight_parameter_and_forwarding():
    relative = "tasks/mirror/search_road.py"
    current = copy.deepcopy(function((ROOT / relative).read_text(encoding="utf-8"), "search_road_from_road_map"))
    assert current.args.args[-1].arg == "node_weights"
    current.args.args.pop()
    current.args.defaults.pop()
    constructor = next(n for n in ast.walk(current) if isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Name) and n.func.id == "RouteGraph")
    assert constructor.keywords[-1].arg == "node_weights"
    constructor.keywords.pop()
    assert ast.dump(current) == ast.dump(function(original_source(relative), "search_road_from_road_map"))


@pytest.mark.parametrize("weights", [None, {"event": 50, "risky_encounter": 999}])
def test_bus_quick_entry_is_not_disabled_by_weight_parameters(weights):
    module, auto, _ = load_policy("route_bus_original", "tasks/mirror/search_road.py")
    module.sleep = Mock()
    auto.click_element.return_value = True
    module.identify_nodes = Mock()
    assert module.search_road_from_road_map(node_weights=weights) == (True, True)
    module.identify_nodes.assert_not_called()
    assert [c.args[0] for c in auto.click_element.call_args_list] == [
        "mirror/mybus_default_distance.png", "mirror/road_in_mir/enter_assets.png",
    ]


@pytest.mark.parametrize("keyboard", [False, True])
@pytest.mark.parametrize("weights", [None, {"event": 50}])
def test_failed_node_execution_keeps_original_cache_and_mouse_retry(keyboard, weights):
    module, auto, cfg = load_policy("route_failed_original", "tasks/mirror/search_road.py")
    module.sleep = Mock()
    cfg.mirror_keyboard_navigation = keyboard
    auto.find_element.return_value = (80, 690)
    auto.click_element.return_value = False
    road = module.MirrorMap(node_weights=weights)
    road.floor_map = ["U", "D"]
    assert road.get_next_step() == "U"
    assert not road.enter_next_node("U")
    assert road.floor_map == ["D"]
    if not keyboard:
        assert auto.click_element.call_count == 2
        assert auto.click_element.call_args.args == ("mirror/mybus_default_distance.png",)


@pytest.mark.parametrize("weights", [None, {"event": 50}])
def test_official_bus_entry_clears_boolean_cache_before_next_route(weights):
    module, auto, cfg = load_policy("official_bus_cache", "tasks/mirror/search_road.py")
    module.search_road_from_road_map = Mock(side_effect=[(True,True), (["U"],["battle"])])
    road = module.MirrorMap(node_weights=weights)
    assert road.get_next_step() is True
    assert road.floor_map == [] and road.floor_nodes == []
    assert road.get_next_step() == "U"
