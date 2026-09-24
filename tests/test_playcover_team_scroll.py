"""PlayCover 编队列表滚动必须逐点慢速上报并在松手前静止。

编队列表按行滚动来定位队伍，而普通 swipe 只发 3 个触摸点，游戏会丢事件：列表几乎
不动或滚动量随机（实测同一次翻页能差一行），按序号选队就会选错。这里用假触摸原语
锁定三个关键点：远多于 3 个插值点、相邻点间距受限、松手前有一段静止尾段消除惯性。
"""

from module.automation.input_handlers.macos.playcover_control import (
    _TEAM_SCROLL_POINT_SPACING_AT_1080P,
    _TEAM_SCROLL_SETTLE_DURATION,
    _TEAM_SCROLL_SETTLE_STEP,
    PlayCoverControl,
)
from module.config import cfg

SETTLE_STEPS = int(_TEAM_SCROLL_SETTLE_DURATION / _TEAM_SCROLL_SETTLE_STEP)


def _record(x, y, dy):
    ctrl = object.__new__(PlayCoverControl)  # 不建立真实连接
    events = []
    ctrl._touch_down = lambda px, py, *a, **k: events.append(("down", round(px), round(py)))
    ctrl._touch_move = lambda px, py, *a, **k: events.append(("move", round(px), round(py)))
    ctrl._touch_up = lambda px, py, *a, **k: events.append(("up", round(px), round(py)))
    ctrl._sleep_step = lambda *_: None

    ctrl.mouse_swipe_for_team_scroll(x, y, duration=0.3, dy=dy)

    downs = [e for e in events if e[0] == "down"]
    moves = [e for e in events if e[0] == "move"]
    ups = [e for e in events if e[0] == "up"]
    return events, downs, moves, ups


def test_team_scroll_reports_every_point_between_endpoints():
    events, downs, moves, ups = _record(200, 700, -300)

    assert downs == [("down", 200, 700)]
    assert ups == [("up", 200, 400)]
    assert events[0] == ("down", 200, 700)
    assert events[-1] == ("up", 200, 400)
    # 逐点上报：远多于普通滑动的 3 个点
    assert len(moves) >= 20
    # 相邻点间距受限：移动太快会被游戏丢事件，滚动量就不可重复
    spacing = max(_TEAM_SCROLL_POINT_SPACING_AT_1080P * cfg.set_win_size / 1080, 1.0)
    interp = moves[: len(moves) - SETTLE_STEPS]
    assert len(interp) >= 20
    for (_, _, y1), (_, _, y2) in zip(interp, interp[1:]):
        assert abs(y2 - y1) <= spacing + 1


def test_team_scroll_holds_still_before_release():
    _, _, moves, ups = _record(200, 700, -300)

    tail = moves[len(moves) - SETTLE_STEPS :]
    assert len(tail) == SETTLE_STEPS
    # 松手前反复上报终点，让游戏把速度判定归零（否则松手后惯性会把位移冲成未知行数）
    assert all(move == ("move", 200, 400) for move in tail)
    assert ups == [("up", 200, 400)]


def test_team_scroll_long_drag_still_ends_on_target():
    """下拉重置的距离大于上限步数时，仍要正好落在终点。"""
    _, _, moves, ups = _record(200, 700, 495)

    assert ups == [("up", 200, 1195)]
    assert moves[-1] == ("move", 200, 1195)


def test_team_scroll_without_distance_does_nothing():
    ctrl = object.__new__(PlayCoverControl)
    events = []
    ctrl._touch_down = lambda *a, **k: events.append("down")
    ctrl._touch_move = lambda *a, **k: events.append("move")
    ctrl._touch_up = lambda *a, **k: events.append("up")
    ctrl._sleep_step = lambda *_: None

    ctrl.mouse_swipe_for_team_scroll(200, 700, dy=0)

    assert events == []
