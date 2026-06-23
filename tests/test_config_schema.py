"""
config schema single source of truth test

config 默认值的唯一来源是 assets/config/config.example.yaml
ConfigModel (module/config/config_typing.py) 只声明类型、不带 default
用 AST + ruamel 静态比对 ConfigModel 里声明的字段和 example.yaml 里定义的字段完全一致（不多也不少）
如果不一致了，说明改 config 相关代码时忘了同步修改某个地方，测试会报错提醒开发者检查并修正
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set

from ruamel.yaml import YAML

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
EXAMPLE_PATH: Path = REPO_ROOT / "assets" / "config" / "config.example.yaml"
TYPING_PATH: Path = REPO_ROOT / "module" / "config" / "config_typing.py"


def _example_keys() -> Set[str]:
    """从 example.yaml 里加载 config 字段名集合"""
    data = YAML().load(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"example.yaml 顶层应为 mapping，实际为 {type(data).__name__}"
    return set(data.keys())


def _config_model_fields() -> List[ast.AnnAssign]:
    """
    从 ConfigModel 的 AST 里提取出所有字段声明（AnnAssign）
    """
    tree: ast.Module = ast.parse(TYPING_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ConfigModel":
            return [s for s in node.body if isinstance(s, ast.AnnAssign)]
    raise AssertionError("config_typing.py 里找不到 ConfigModel")


def _field_name(stmt: ast.AnnAssign) -> str:
    """
    从 ConfigModel AST 解析出的赋值语句里获取字段名
    """
    assert isinstance(stmt.target, ast.Name)
    return stmt.target.id


def test_model_fields_match_example_keys() -> None:
    model_keys: Set[str] = {_field_name(s) for s in _config_model_fields()}
    example_keys: Set[str] = _example_keys()
    assert model_keys == example_keys, (
        "ConfigModel 和 example.yaml 的 key 不一致：\n"
        f"  只在 model:   {sorted(model_keys - example_keys)}\n"
        f"  只在 example: {sorted(example_keys - model_keys)}"
    )


def test_config_model_has_no_hardcoded_defaults() -> None:
    # ConfigModel 是纯 typing：默认值只准放 example.yaml，不在 model 里硬编码
    # 保证 single source of truth，避免改 config 相关代码时忘了同步修改某个地方
    with_default: List[str] = [
        _field_name(s) for s in _config_model_fields() if s.value is not None
    ]
    assert (
        with_default == []
    ), f"下列 ConfigModel field 带有 default：{with_default}"
