# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

import rapidocr
import sys

IS_WINDOWS = sys.platform == "win32"
sys.modules['FixTk'] = None

block_cipher = None

package_name = "rapidocr"
install_dir = Path(rapidocr.__file__).resolve().parent

onnx_paths = list(install_dir.rglob("*.onnx"))
yaml_paths = list(install_dir.rglob("*.yaml"))

onnx_add_data = [(str(v.parent), f"{package_name}/{v.parent.name}") for v in onnx_paths]

yaml_add_data = []
for v in yaml_paths:
    if package_name == v.parent.name:
        yaml_add_data.append((str(v.parent / "*.yaml"), package_name))
    else:
        yaml_add_data.append(
            (str(v.parent / "*.yaml"), f"{package_name}/{v.parent.name}")
        )

add_data = list(set(yaml_add_data + onnx_add_data))

# uv 提供的 Python 可能把 Tcl/Tk 放在非标准路径，mouseinfo 运行时需要它们。
tk_binaries = []
if not IS_WINDOWS:
    import sysconfig

    lib_dir = Path(sysconfig.get_config_var("LIBDIR") or "")
    tk_binaries = [(str(path), ".") for pattern in ("libtcl*.so*", "libtk*.so*") for path in lib_dir.glob(pattern)]

    # Python < 3.14 的 py7zr 动态导入 backports.zstd；namespace 包需按目录收集。
    if sys.version_info < (3, 14):
        import importlib.util

        spec = importlib.util.find_spec("backports.zstd")
        if spec is not None and spec.submodule_search_locations:
            add_data.append((str(Path(next(iter(spec.submodule_search_locations))).resolve()), "backports/zstd"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=tk_binaries,
    datas=add_data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Windows 下排除 tk 系列减小体积；Linux 上 mouseinfo(pyautogui 依赖)强制要求
    # tkinter，缺失会直接 sys.exit 导致打包产物静默退出，因此不能排除。
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'] if IS_WINDOWS else [],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AALC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=IS_WINDOWS,
    icon="./assets/logo/my_icon_256X256.ico" if IS_WINDOWS else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AALC",
)
