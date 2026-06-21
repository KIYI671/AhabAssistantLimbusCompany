import importlib
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) in sys.path:
    sys.path.remove(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))


def unload_logger_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "module":
            sys.modules.pop(module_name)
        elif module_name == "module.logger" or module_name.startswith("module.logger."):
            sys.modules.pop(module_name)


def py_side_modules() -> set[str]:
    return {module_name for module_name in sys.modules if module_name.startswith("PySide6")}


def test_importing_logger_package_does_not_import_qt_logger_module() -> None:
    unload_logger_modules()
    py_side_before = py_side_modules()

    logger_package = importlib.import_module("module.logger")

    assert logger_package.log is logging.getLogger("AALC")
    assert "module.logger.my_log" not in sys.modules
    assert py_side_modules() == py_side_before
