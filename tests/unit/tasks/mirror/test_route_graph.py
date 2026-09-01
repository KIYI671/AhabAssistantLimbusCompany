from tasks.mirror.search_road import RouteGraph, Row


def test_template_connections_keep_their_actual_column_numbers() -> None:
    graph = RouteGraph(
        [
            [["event", (300, 560)]],
            [["event", (820, 560)]],
            [["boss_battle", (1340, 123)]],
        ],
        bus_row=Row.MID,
        bus_position=(100, 560),
    )

    graph.init_road(
        [
            (1, Row.MID, Row.MID),
            (2, Row.MID, Row.MID),
            (3, Row.MID, Row.TOP),
        ]
    )

    weight, path = graph.find_min_weight_route()

    assert weight != float("inf")
    assert [node.node_class for node in path] == ["bus", "event", "event", "boss_battle"]


def test_internal_boss_misclassification_is_not_used_as_terminal() -> None:
    graph = RouteGraph(
        [
            [["boss_battle", (300, 560)]],
            [["battle", (820, 560)]],
            [["boss_battle", (1340, 560)]],
        ],
        bus_row=Row.MID,
        bus_position=(100, 560),
    )
    graph.init_road(
        [
            (1, Row.MID, Row.MID),
            (2, Row.MID, Row.MID),
            (3, Row.MID, Row.MID),
        ]
    )

    _, path = graph.find_min_weight_route()

    assert [node.node_class for node in path] == ["bus", "boss_battle", "battle", "boss_battle"]
