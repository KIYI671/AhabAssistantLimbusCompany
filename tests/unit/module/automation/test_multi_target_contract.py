"""
Automation.find_element 多目标查找的返回值契约测试

回归背景（issue：编队统计次数恒为 0）：

``find_element(find_type="image_with_multiple_targets")`` 在**未匹配到任何目标时返回 `[]`**，
而不是 `None`。调用方若用真值判断区分"数量为 0"与"识别失败"，就会把两者混为一谈。

镜牢楼层的"未通关标记"正是这种情况：标记数为 0 表示已经位于最后一层（第 5 层），
但 ``if not_passed_floors:`` 会把它当成识别失败，导致当前层数永远取不到 5，
进而使"5 个楼层时间戳齐全"的条件恒不成立，统计永不更新。

这里用 AST 静态校验该返回值契约，避免上游改成 `None` 后调用方的判断失效。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
AUTOMATION_PATH: Path = REPO_ROOT / "module" / "automation" / "automation.py"


def _fn(name: str) -> ast.FunctionDef:
    tree = ast.parse(AUTOMATION_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{AUTOMATION_PATH.name} 里找不到 {name}")


def _returned_values(fn: ast.FunctionDef) -> List[ast.expr]:
    return [stmt.value for stmt in ast.walk(fn) if isinstance(stmt, ast.Return) and stmt.value is not None]


def _is_empty_list(node: ast.expr) -> bool:
    return isinstance(node, ast.List) and len(node.elts) == 0


def test_multi_target_lookup_returns_empty_list_not_none() -> None:
    """多目标查找未命中时必须返回 []（而不是 None），调用方依赖该契约判断"数量为 0"。"""
    fn = _fn("find_image_with_multiple_targets")
    returns = _returned_values(fn)

    empty_list_returns = [node for node in returns if _is_empty_list(node)]
    none_returns = [node for node in returns if isinstance(node, ast.Constant) and node.value is None]

    assert empty_list_returns, "find_image_with_multiple_targets 应当存在返回 [] 的分支（未命中）"
    assert not none_returns, (
        "find_image_with_multiple_targets 不应返回 None："
        "调用方（如 mirror.py 的楼层兜底识别）依赖 [] 表示「标记数为 0」，"
        "改成 None 会让「位于最后一层」被误判为识别失败。"
    )


def test_find_element_forwards_multi_target_result_directly() -> None:
    """find_element 对 image_with_multiple_targets 类型应直接透传结果，不得把 [] 归一成 None。"""
    fn = _fn("find_element")
    forwarded: List[ast.Return] = []
    for stmt in ast.walk(fn):
        if not isinstance(stmt, ast.Return) or stmt.value is None:
            continue
        call = stmt.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
            if call.func.attr == "find_image_with_multiple_targets":
                forwarded.append(stmt)

    assert forwarded, "find_element 里应直接 return find_image_with_multiple_targets(...)"

    for stmt in forwarded:
        value = stmt.value
        assert not (isinstance(value, ast.BoolOp) or isinstance(value, ast.IfExp)), (
            f"automation.py:{stmt.lineno} 对多目标查找结果做了真值/条件包装，"
            "会把 [] 归一成其他值，破坏「数量为 0」的语义。"
        )
