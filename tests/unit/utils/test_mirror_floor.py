"""
mirror floor helper test

utils/mirror_floor.py 是纯函数模块，不 import 任何 UI / 截图 / 配置依赖，
所以这里可以直接 import 进行验证。

背景（回归用例）：镜牢楼层的"未通关标记"数量与当前层数的换算曾用真值判断写成
    if not_passed_floors:  self.floor = 5 - len(not_passed_floors)
而 Automation.find_element(find_type="image_with_multiple_targets") 在未匹配到时返回 []
而不是 None，于是"标记数为 0"（即位于第 5 层，全部楼层已通过）被判成识别失败，
当前层数永远取不到 5。配合 mirror.py 里"5 个楼层时间戳必须齐全"的门禁，
编队统计次数与平均用时因此永远不更新。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from utils.mirror_floor import (  # noqa: E402
    FLOOR_COUNT,
    floor_from_clear_markers,
    floor_from_not_passed_markers,
)


def test_floor_count_is_five() -> None:
    assert FLOOR_COUNT == 5


def test_clear_markers_map_to_floor() -> None:
    """每个 CLEAR 标记代表一层已通关，当前层数 = 标记数 + 1"""
    assert [floor_from_clear_markers(n) for n in range(FLOOR_COUNT)] == [1, 2, 3, 4, 5]


def test_not_passed_markers_map_to_floor() -> None:
    """未通关标记统计的是当前层之后的楼层，当前层数 = 5 - 标记数"""
    assert [floor_from_not_passed_markers(n) for n in range(FLOOR_COUNT)] == [5, 4, 3, 2, 1]


def test_last_floor_is_reachable_with_zero_markers() -> None:
    """回归：标记数为 0 必须能推出第 5 层（原实现用真值判断，永远取不到 5）"""
    assert floor_from_not_passed_markers(0) == 5
    assert floor_from_not_passed_markers(0) != floor_from_not_passed_markers(1)


def test_helper_tables_are_inverse() -> None:
    """两种标记的换算应互为对方的逆映射"""
    for floor in range(1, FLOOR_COUNT + 1):
        from_clear = floor_from_clear_markers(floor - 1)
        from_not_passed = floor_from_not_passed_markers(FLOOR_COUNT - floor)
        assert from_clear == floor
        assert from_not_passed == floor


def test_helpers_cover_all_floors() -> None:
    """取值范围应恰好覆盖 1..5，不应越界"""
    floors = {floor_from_clear_markers(n) for n in range(FLOOR_COUNT)}
    floors |= {floor_from_not_passed_markers(n) for n in range(FLOOR_COUNT)}
    assert floors == {1, 2, 3, 4, 5}


def test_out_of_range_marker_counts_are_clamped() -> None:
    """识别异常导致的越界标记数应被收敛到合法楼层，避免 floor_times 负索引取错槽位"""
    # 标记数多于楼层数（模板误匹配）不应产生超过 5 的层数
    assert floor_from_clear_markers(FLOOR_COUNT) == FLOOR_COUNT
    assert floor_from_clear_markers(99) == FLOOR_COUNT
    # not_passed 标记多于楼层数会让 5 - n 变成 0 或负数，必须收敛到 1
    assert floor_from_not_passed_markers(FLOOR_COUNT) == 1
    assert floor_from_not_passed_markers(99) == 1
    # 负数输入同样收敛
    assert floor_from_clear_markers(-5) == 1
    assert floor_from_not_passed_markers(-5) == FLOOR_COUNT
