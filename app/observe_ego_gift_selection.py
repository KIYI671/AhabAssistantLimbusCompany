from __future__ import annotations

"""观测 EGO 饰品控件组的轻量数据模型与新格式读写工具。

当前文件只服务 GUI 侧的控件组回显、补空行和保存逻辑。
配置格式固定为: system_level_row_col，例如 ``burn_3_2_5``。
"""

import re
from dataclasses import dataclass

# 体系值与下拉框选项保持一致，用于校验配置是否合法。
OBSERVE_SYSTEM_KEYS = (
    "burn",
    "bleed",
    "tremor",
    "rupture",
    "sinking",
    "poise",
    "charge",
    "slash",
    "pierce",
    "blunt",
    "general",
)
OBSERVE_LEVEL_VALUES = (1, 2, 3)
OBSERVE_ROW_VALUES = tuple(range(1, 11))
OBSERVE_COL_VALUES = tuple(range(1, 9))
MAX_OBSERVE_GIFT_SELECTIONS = 3

_NEW_FORMAT_PATTERN = re.compile(r"^([a-z]+)_(\d+)_(\d+)_(\d+)$")


@dataclass(eq=True)
class ObserveGiftSelection:
    """一行观测 EGO 控件组的选择结果。"""

    system: str | None = None
    level: int | None = None
    row: int | None = None
    col: int | None = None

    def is_blank(self) -> bool:
        """判断这一行是否还是完全空白。"""
        return self.system is None and self.level is None and self.row is None and self.col is None

    def is_complete(self) -> bool:
        """判断这一行是否已经形成可保存的完整选择。"""
        return (
            self.system in OBSERVE_SYSTEM_KEYS
            and self.level in OBSERVE_LEVEL_VALUES
            and self.row in OBSERVE_ROW_VALUES
            and self.col in OBSERVE_COL_VALUES
        )


def parse_observe_ego_gift_value(value: str) -> ObserveGiftSelection | None:
    """将单个配置字符串解析为一行选择；非法值直接忽略。"""

    value = value.strip()
    if not value:
        return None

    new_match = _NEW_FORMAT_PATTERN.match(value)
    if not new_match:
        return None

    selection = ObserveGiftSelection(
        system=new_match.group(1),
        level=int(new_match.group(2)),
        row=int(new_match.group(3)),
        col=int(new_match.group(4)),
    )
    return selection if selection.is_complete() else None


def serialize_observe_ego_gift_value(selection: ObserveGiftSelection) -> str:
    """将完整行选择序列化为配置字符串。"""

    if not selection.is_complete():
        msg = f"Cannot serialize incomplete selection: {selection!r}"
        raise ValueError(msg)
    return f"{selection.system}_{selection.level}_{selection.row}_{selection.col}"


def ensure_placeholder_row(
    rows: list[ObserveGiftSelection],
    max_completed: int = MAX_OBSERVE_GIFT_SELECTIONS,
) -> list[ObserveGiftSelection]:
    """规范化控件组列表，确保 GUI 始终满足展示规则。

    规则:
    1. 丢弃完全空白的冗余行
    2. 已完成行最多保留 ``max_completed`` 条
    3. 未满上限且当前没有空白行时，自动补一条空白行
    4. 如果列表最终为空，至少补一条空白行
    """

    normalized = [
        ObserveGiftSelection(row.system, row.level, row.row, row.col)
        for row in rows
        if row.is_complete() or not row.is_blank()
    ]

    completed_count = sum(1 for row in normalized if row.is_complete())
    if completed_count >= max_completed:
        normalized = [row for row in normalized if row.is_complete()][:max_completed]
    elif not any(not row.is_complete() for row in normalized):
        normalized.append(ObserveGiftSelection())

    if not normalized:
        normalized.append(ObserveGiftSelection())

    return normalized


def parse_observe_ego_gift_values(values: list[str]) -> list[ObserveGiftSelection]:
    """将配置中的字符串列表恢复成 GUI 需要的控件组列表。"""

    parsed: list[ObserveGiftSelection] = []
    for value in values:
        selection = parse_observe_ego_gift_value(value)
        if selection is not None:
            parsed.append(selection)
        if len(parsed) >= MAX_OBSERVE_GIFT_SELECTIONS:
            break
    return ensure_placeholder_row(parsed)


def serialize_observe_ego_gift_values(rows: list[ObserveGiftSelection]) -> list[str]:
    """提取所有已完成行，并写回配置使用的字符串列表。"""

    return [serialize_observe_ego_gift_value(row) for row in rows if row.is_complete()]
