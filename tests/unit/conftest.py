import importlib
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def isolated_import():
    """在不执行 `module/config/__init__.py` 的情况下 import 模块。

    `module.config` 包在 import 时会创建全局 cfg，并读写仓库根目录的 config.yaml。
    纯逻辑测试只需要它下面的子模块，这里临时放一个空的包壳代替它，测试结束后移除。
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    before = set(sys.modules)
    if "module.config" not in sys.modules:
        importlib.import_module("module")
        shell = types.ModuleType("module.config")
        shell.__path__ = [str(REPO_ROOT / "module" / "config")]
        sys.modules["module.config"] = shell

    yield importlib.import_module

    for name in set(sys.modules) - before:
        sys.modules.pop(name, None)
