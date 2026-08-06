from tasks.mirror.search_road import Position, RouteGraph


def test_road_x_mapping_connects_the_actual_later_layers() -> None:
    graph = RouteGraph(
        [
            [["event", (300, 560)]],
            [["event", (600, 560)]],
            [["boss_battle", (900, 300)]],
        ],
        initial_bus_pos=Position.MID,
        hard_mode=True,
    )

    # 第一、二段均为直路；只检测到第三段斜线时，不应把它错配给第一段。
    graph.init_road([[['UP', (750, 430)]]], bus_x=100, bus_y=560)

    weight, path = graph.find_min_weight_route()

    assert weight != float("inf")
    assert [node.node_class for node in path] == ["bus", "event", "event", "boss_battle"]


def test_internal_boss_misclassification_is_not_used_as_terminal() -> None:
    graph = RouteGraph(
        [
            [["boss_battle", (300, 560)]],
            [["battle", (600, 560)]],
            [["boss_battle", (900, 560)]],
        ],
        initial_bus_pos=Position.MID,
        hard_mode=True,
    )
    graph.init_road([], bus_x=100, bus_y=560)

    _, path = graph.find_min_weight_route()

    assert [node.node_class for node in path] == ["bus", "boss_battle", "battle", "boss_battle"]
