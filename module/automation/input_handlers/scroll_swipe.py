from math import hypot


def build_scroll_swipe_plan(
    x,
    y,
    dx=0,
    dy=0,
    duration=0.3,
    escape_distance=30,
    escape_duration=0,
):
    """生成规避长按判定的滚动路径，元素为（坐标，到达该点前的耗时）。

    按下后先快速移动 ``escape_distance``，使游戏尽快离开长按判定区域，
    再用剩余时间移动到终点。短距离滑动则直接移动到终点。
    """
    duration = max(0, duration)
    distance = hypot(dx, dy)
    start = (x, y)
    end = (x + dx, y + dy)
    if distance == 0:
        return [(start, 0)]
    if distance <= escape_distance:
        return [(start, 0), (end, duration)]

    ratio = escape_distance / distance
    initial = (x + dx * ratio, y + dy * ratio)
    initial_duration = min(escape_duration, duration)
    return [
        (start, 0),
        (initial, initial_duration),
        (end, duration - initial_duration),
    ]
