"""PlayCover 触摸拉链必须按距离插值补点。

游戏把"只发顶点"的拖拽当成瞬移、整条丢弃（实机实测：只发顶点时技能卡行/守备行画面
零变化、回合不开始；补点后拉链生效）。这里用假触摸原语锁定"每段都补点且步长受限"。
"""

from module.automation.input_handlers.macos.playcover_control import PlayCoverControl

STEP_LEN = 10  # 与实现里的 step_len 一致（画布像素）


def test_drag_link_interpolates_between_waypoints():
    ctrl = object.__new__(PlayCoverControl)  # 不建立真实连接
    events = []
    ctrl._touch_down = lambda x, y, *a, **k: events.append(("down", round(x), round(y)))
    ctrl._touch_move = lambda x, y, *a, **k: events.append(("move", round(x), round(y)))
    ctrl._touch_up = lambda x, y, *a, **k: events.append(("up", round(x), round(y)))
    ctrl._sleep_step = lambda *a: None

    waypoints = [(571, 812), (722, 1000), (1085, 1000), (960, 600)]
    ctrl.mouse_drag_link(waypoints)

    moves = [e for e in events if e[0] == "move"]
    assert events[0] == ("down", 571, 812)
    assert events[-1] == ("up", 960, 600)
    # 每段都要补点：顶点数远小于发点数
    assert len(moves) >= 3 * len(waypoints)
    # 相邻发点间距不超过一个插值步长（允许 1px 取整误差）
    for (_, x1, y1), (_, x2, y2) in zip(moves, moves[1:]):
        assert max(abs(x2 - x1), abs(y2 - y1)) <= STEP_LEN + 1


def test_drag_link_handles_empty_position():
    ctrl = object.__new__(PlayCoverControl)
    events = []
    ctrl._touch_down = lambda *a, **k: events.append("down")
    ctrl._touch_move = lambda *a, **k: events.append("move")
    ctrl._touch_up = lambda *a, **k: events.append("up")
    ctrl._sleep_step = lambda *a: None

    ctrl.mouse_drag_link([])

    assert events == []
