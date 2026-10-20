"""PlayCover 触摸端用双指捏合模拟滚轮缩放（镜牢地图"最远距离法"寻路依赖它）。

协议依据 PlayTools ``MaaTools.swift`` 的 ``toucherDispatch``：TUCH 载荷末字节是 contact
编号，服务端为每个 contact 维护独立的触摸 id，因此同时发 contact 0/1 就是双指手势。
这里用假触摸原语锁定：两个触点各有 began/moved/ended、间距单调变化到目标值、
中点固定，且方向与 PC 滚轮一致（负=缩小/双指靠拢，正=放大/双指分开）。
"""

import pytest

from module.automation.input_handlers.macos.playcover_control import (
    _PINCH_NARROW_RATIO,
    _PINCH_STEPS,
    _PINCH_WIDE_RATIO,
    PlayCoverControl,
)

_PHASE_DOWN = 0
_PHASE_MOVE = 1
_PHASE_UP = 3


def _record(direction: int):
    """执行一次捏合，返回 (画布尺寸, down 事件, move 事件, up 事件)。"""
    ctrl = object.__new__(PlayCoverControl)  # 不建立真实连接
    events = []
    ctrl._touch = lambda phase, x, y, contact=0: events.append(
        (phase, float(x), float(y), contact)
    )
    ctrl._sleep_step = lambda *_: None

    assert ctrl.mouse_scroll(direction) is True

    downs = [e for e in events if e[0] == _PHASE_DOWN]
    moves = [e for e in events if e[0] == _PHASE_MOVE]
    ups = [e for e in events if e[0] == _PHASE_UP]
    return ctrl._canvas_size(), downs, moves, ups


def _gesture(downs, moves, ups):
    """把 down → 逐步 move 还原成间距轨迹，并单列抬起时的终点。"""
    assert {e[3] for e in downs} == {0, 1}
    assert {e[3] for e in ups} == {0, 1}
    assert len(moves) == 2 * _PINCH_STEPS

    steps = [(downs[0], downs[1])]
    for left, right in zip(moves[::2], moves[1::2]):
        assert left[3] == 0 and right[3] == 1  # contact 0 在左、1 在右，交替发送
        steps.append((left, right))

    gaps = [right[1] - left[1] for left, right in steps]
    midpoints = [(left[1] + right[1]) / 2 for left, right in steps]
    end_gap = ups[1][1] - ups[0][1]
    end_midpoint = (ups[0][1] + ups[1][1]) / 2
    return gaps, midpoints, end_gap, end_midpoint


def test_scroll_negative_pinches_in_to_zoom_out():
    """滚轮远离界面（<=0）→ 双指靠拢：间距从宽单调收缩到窄。"""
    (canvas_w, _), downs, moves, ups = _record(-3)
    gaps, _, end_gap, _ = _gesture(downs, moves, ups)

    assert gaps[0] == pytest.approx(canvas_w * _PINCH_WIDE_RATIO)
    assert gaps[-1] == pytest.approx(canvas_w * _PINCH_NARROW_RATIO)
    assert end_gap == pytest.approx(gaps[-1])
    assert all(later < earlier for earlier, later in zip(gaps, gaps[1:]))


def test_scroll_positive_pinches_out_to_zoom_in():
    """滚轮拉近界面（>0）→ 双指分开：间距从窄单调扩大到宽。"""
    (canvas_w, _), downs, moves, ups = _record(3)
    gaps, _, end_gap, _ = _gesture(downs, moves, ups)

    assert gaps[0] == pytest.approx(canvas_w * _PINCH_NARROW_RATIO)
    assert gaps[-1] == pytest.approx(canvas_w * _PINCH_WIDE_RATIO)
    assert end_gap == pytest.approx(gaps[-1])
    assert all(later > earlier for earlier, later in zip(gaps, gaps[1:]))


def test_scroll_pinch_keeps_midpoint_fixed():
    """捏合过程中点固定在画布中心，避免地图被顺带拖走。"""
    (canvas_w, canvas_h), downs, moves, ups = _record(-3)
    _, midpoints, _, end_midpoint = _gesture(downs, moves, ups)

    assert all(x == pytest.approx(canvas_w / 2) for x in [*midpoints, end_midpoint])
    assert all(move[2] == pytest.approx(canvas_h / 2) for move in moves)
    assert all(up[2] == pytest.approx(canvas_h / 2) for up in ups)
