"""
mirror 统计写入回归测试

背景（issue）：编队统计的"镜牢次数 / 平均用时"恒为 0。

原因：tasks/mirror/mirror.py 里更新统计的代码块被包在
    if all(self.floor_times[i] > 0 for i in range(5)):   # 判断是否完整走了五层
内部，而 floor_times 只在 get_which_floor() 识别出楼层后才会赋值
（self.floor_times[self.floor - 1] = time.time()）。

楼层识别失败时（clear_floor 模板匹配不到、兜底模板也匹配不到），
floor_times 最多只有 4 个槽位被写过，第 5 个永远是初始值 -9999.0，
于是该条件恒为 False，统计永不更新。

这里用 AST 静态检查，确保统计写入不再受"楼层时间戳是否齐全"约束，
并且确实挂在"本局已正常结算"之后（failed 检查之后）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

REPO_ROOT: Path = Path(__file__).resolve().parents[3]
MIRROR_PATH: Path = REPO_ROOT / "tasks" / "mirror" / "mirror.py"

COUNT_FIELDS = ("mirror_hard_count", "mirror_normal_count")


def _mirror_run_fn() -> ast.FunctionDef:
    """取出 mirror.py 中 Mirror.run 的函数节点"""
    tree = ast.parse(MIRROR_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Mirror":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "run":
                    return item
    raise AssertionError("tasks/mirror/mirror.py 里找不到 Mirror.run")


def _assignment_targets(fn: ast.FunctionDef) -> List[str]:
    """收集函数体内所有赋值语句的目标名（含属性访问的 attr 名）"""
    names: List[str] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
                elif isinstance(target, ast.Attribute):
                    names.append(target.attr)
                elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                    names.append(target.value.id)
    return names


def _floor_times_gate_nodes(fn: ast.FunctionDef) -> List[ast.If]:
    """找出所有以 floor_times 作为"是否走满五层"判断条件的 if 语句"""
    found: List[ast.If] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        if "floor_times" in ast.dump(node.test):
            found.append(node)
    return found


def test_mirror_run_exists() -> None:
    assert _mirror_run_fn() is not None


def test_floor_times_does_not_gate_stats_update() -> None:
    """统计写入不得再被 floor_times 条件包裹

    原实现的问题就是 floor_times 依赖楼层识别，识别失败即计数失效。
    若有人重新引入该门禁，此测试会失败。
    """
    fn = _mirror_run_fn()
    for gate in _floor_times_gate_nodes(fn):
        body_targets: List[str] = []
        for stmt in gate.body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            body_targets.append(target.id)
                        elif isinstance(target, ast.Attribute):
                            body_targets.append(target.attr)
                        elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                            body_targets.append(target.value.id)
        overlapping = sorted(set(body_targets) & set(COUNT_FIELDS))
        assert not overlapping, (
            f"Mirror.run 中 mirror.py:{gate.lineno} 的 floor_times 条件仍在包裹统计写入：{overlapping}。"
            "楼层识别失败时该条件恒为 False，会导致编队统计次数与平均用时永不更新。"
        )


def test_stats_update_still_present() -> None:
    """确保统计写入逻辑本身没有被误删"""
    fn = _mirror_run_fn()
    targets = _assignment_targets(fn)
    for field in COUNT_FIELDS:
        assert field in targets, f"Mirror.run 里找不到对 {field} 的赋值，统计写入可能被误删"


def test_stats_update_follows_failed_guard() -> None:
    """统计写入必须位于 `if failed: return False` 之后

    这样"统计写入会在失败局执行"才不成立：失败局已在前面提前返回。
    """
    fn = _mirror_run_fn()
    failed_guard_line: Optional[int] = None
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        if "failed" not in ast.dump(node.test):
            continue
        if any(isinstance(stmt, ast.Return) for stmt in node.body):
            failed_guard_line = node.lineno
            break

    assert failed_guard_line is not None, "找不到 `if failed: return False` 守卫"

    stats_lines = [
        node.lineno
        for node in ast.walk(fn)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and target.value.id == "team_history"
    ]
    assert stats_lines, "找不到 team_history 的统计写入"
    assert min(stats_lines) > failed_guard_line, (
        "统计写入应在 `if failed: return False` 之后，否则失败局也会被计入统计"
    )
