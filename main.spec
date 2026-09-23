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

# python-build-standalone(uv) 的 tcl/tk 动态库位于非标准 LIBDIR，
# PyInstaller 的 tkinter 钩子不会自动收集，需手动加入，否则冻结后
# import tkinter 失败 -> mouseinfo(pyautogui 依赖) sys.exit 静默退出。
import os as _os
import sysconfig as _sysconfig

tk_binaries = []
if not IS_WINDOWS:
    _libdir = _sysconfig.get_config_var("LIBDIR") or ""
    for _pattern in ("libtcl*.so*", "libtk*.so*"):
        import glob as _glob

        for _lib in _glob.glob(_os.path.join(_libdir, _pattern)):
            tk_binaries.append((_lib, "."))

# py7zr 在 Python 3.13 下经 backports.zstd 支持 zstd 压缩的 7z 包，
# 该导入是动态的，PyInstaller 无法自动侦测，需显式声明。
# py7zr 在 Python 3.13 下经 backports.zstd 支持 zstd 压缩的 7z 包。
# backports 是 PEP420 隐式命名空间包，PyInstaller 的 modulegraph 无法通过
# hiddenimports 收集（会误报 missing），改为按目录整体作为数据文件拷贝；
# 冻结产物的 sys.path 包含 _internal，命名空间包可直接从文件系统导入。
if not IS_WINDOWS:
    import importlib.util

    _bz_spec = importlib.util.find_spec("backports.zstd")
    if _bz_spec is not None and _bz_spec.submodule_search_locations:
        _bz_dir = Path(list(_bz_spec.submodule_search_locations)[0]).resolve()
        add_data.append((str(_bz_dir), "backports/zstd"))

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
