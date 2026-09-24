"""按序号选队前，编队列表必须先滚到最顶端。

"第 n 个队伍"是从列表最上面数起的第 n 行；列表停在当前所选队伍附近时（游戏打开
界面时会滚到当前队伍），同样的点击位置就变成了"从当前队伍数起"。这里用假截图锁定：
下拉必须持续到列表不再变化（到顶部被夹住），并且不会因为手势没生效而死循环。
"""

import numpy as np
from PIL import Image

from tasks.teams import team_formation

VIEW_BBOX = (0, 0, 80, 200)


class _ScrollingAuto:
    """用一张随滚动偏移变化的假截图模拟编队列表。"""

    def __init__(self, offset: int, rows_per_swipe: int):
        self.offset = offset
        self.rows_per_swipe = rows_per_swipe
        self.swipes = 0

    def mouse_swipe_for_team_scroll(self, x, y, dy=0, duration=0.3):
        self.swipes += 1
        self.offset = max(0, self.offset - self.rows_per_swipe)

    def take_screenshot(self):
        return self.screenshot

    @property
    def screenshot(self):
        pixels = np.zeros((200, 80), dtype=np.uint8)
        pixels[: min(self.offset, 200)] = 200
        return Image.fromarray(pixels)


def _reset(monkeypatch, fake):
    monkeypatch.setattr(team_formation, "auto", fake)
    monkeypatch.setattr(team_formation, "sleep", lambda *_: None)
    team_formation._reset_team_list_to_top([100, 500], 400, VIEW_BBOX)


def test_reset_swipes_until_list_reaches_top(monkeypatch):
    fake = _ScrollingAuto(offset=30, rows_per_swipe=8)

    _reset(monkeypatch, fake)

    assert fake.offset == 0
    # 30 行偏移、每次 8 行：至少 4 次才到顶，还要一次确认不再变化
    assert fake.swipes >= 5


def test_reset_stops_when_list_never_moves(monkeypatch):
    """手势没生效（列表不动）时不应一直下拉：看到两次相同画面就停。"""
    fake = _ScrollingAuto(offset=30, rows_per_swipe=0)

    _reset(monkeypatch, fake)

    assert fake.swipes == 2


def test_reset_ignores_small_rendering_noise(monkeypatch):
    """到顶后相邻两帧只差一点渲染噪声时，也要判定为已到顶。"""
    frame = {"index": 0}

    class _NoisyAuto(_ScrollingAuto):
        @property
        def screenshot(self):
            pixels = np.asarray(super().screenshot).copy()
            pixels[0, 0] = frame["index"] % 2  # 相邻两帧仅差 1 个灰度级
            frame["index"] += 1
            return Image.fromarray(pixels)

    noisy = _NoisyAuto(offset=4, rows_per_swipe=4)

    _reset(monkeypatch, noisy)

    assert noisy.offset == 0
    assert noisy.swipes == 2
