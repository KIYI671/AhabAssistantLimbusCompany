"""
utils.mirror_floor: 由镜牢楼层设置面板的标记数量推导当前层数

这里的函数都是纯函数，便于单元测试（见 tests/unit/utils/test_mirror_floor.py），
不依赖截图、OCR 与配置文件。

镜牢内点开右上角齿轮后会展开楼层设置面板，面板用两种标记表示进度：

- ``CLEAR``：已通关标记，每个标记代表一层已经打完，故当前层数 = 标记数 + 1
- ``not_passed``：未通关标记，统计的是“当前层之后”还有几层没打，
  故当前层数 = 总层数 - 标记数。位于第 1 层时有 4 个标记，
  位于第 5 层（最后一层）时标记数为 0。

注意：``Automation.find_element(find_type="image_with_multiple_targets")``
在没有匹配到目标时返回空列表 ``[]`` 而不是 ``None``，
因此调用方不能用真值判断来区分“标记数为 0”和“识别失败”——
对 ``not_passed`` 而言，标记数为 0 恰恰表示已经位于最后一层。
"""

FLOOR_COUNT = 5
"""镜牢的楼层总数。"""


def _clamp_floor(floor: int) -> int:
    """把层数收敛到 [1, FLOOR_COUNT]。

    理论上不会越界，但模板匹配在画面异常时可能多计标记。
    层数一旦为 0 或负数，调用方 `self.floor_times[self.floor - 1]` 会因 Python 的负索引
    取到末尾槽位而不报错，属于会静默污染数据的隐患，故在这里统一兜住。
    """
    return max(1, min(FLOOR_COUNT, floor))


def floor_from_clear_markers(marker_count: int) -> int:
    """由 CLEAR 标记数量推导当前层数。

    每个 CLEAR 标记代表一层已通关，因此当前层数为标记数加一。

    Args:
        marker_count: 识别到的 CLEAR 标记数量，取值 [0, FLOOR_COUNT - 1]。

    Returns:
        当前层数，取值 [1, FLOOR_COUNT]。
    """
    return _clamp_floor(marker_count + 1)


def floor_from_not_passed_markers(marker_count: int) -> int:
    """由“未通关”标记数量推导当前层数。

    未通关标记统计的是当前层之后的楼层，所以当前层数为总层数减去标记数：

    ====  ==========  ==========
    层数  标记数      计算
    ====  ==========  ==========
    1     4           5 - 4 = 1
    2     3           5 - 3 = 2
    3     2           5 - 2 = 3
    4     1           5 - 1 = 4
    5     0           5 - 0 = 5
    ====  ==========  ==========

    Args:
        marker_count: 识别到的未通关标记数量，取值 [0, FLOOR_COUNT - 1]。

    Returns:
        当前层数，取值 [1, FLOOR_COUNT]。
    """
    return _clamp_floor(FLOOR_COUNT - marker_count)
