from math import hypot

WINDOWS_SCROLL_BRAKE_DISTANCE = 30
WINDOWS_SCROLL_BRAKE_DURATION = 0.5
WINDOWS_SCROLL_SETTLE_DURATION = 0.3


def build_scroll_swipe_plan(
    x,
    y,
    dx=0,
    dy=0,
    duration=0.3,
    escape_distance=30,
    escape_duration=0.01,
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


def build_windows_scroll_swipe_plan(
    x,
    y,
    dx=0,
    dy=0,
    duration=0.3,
):
    """为 Windows 滚动追加低速尾段，并返回松手前等待时间。"""
    plan = build_scroll_swipe_plan(x, y, dx, dy, duration)
    if len(plan) <= 1:
        return plan, 0

    start = plan[0][0]
    end, move_duration = plan[-1]
    move_x = end[0] - start[0]
    move_y = end[1] - start[1]
    distance = hypot(move_x, move_y)
    if distance <= WINDOWS_SCROLL_BRAKE_DISTANCE:
        return plan, 0

    ratio = WINDOWS_SCROLL_BRAKE_DISTANCE / distance
    brake = end[0] - move_x * ratio, end[1] - move_y * ratio
    braked_plan = [
        *plan[:-1],
        (brake, move_duration),
        (end, WINDOWS_SCROLL_BRAKE_DURATION),
    ]
    return braked_plan, WINDOWS_SCROLL_SETTLE_DURATION
