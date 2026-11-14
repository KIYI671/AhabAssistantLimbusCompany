# -*- mode: python ; coding: utf-8 -*-
"""macOS 打包配置：onedir 收集 + BUNDLE 生成 dist/AALC.app。

与 main.spec（Windows）保持一致的分析参数，差别只在产物形态：
Windows 是 dist/AALC/ 目录，macOS 是 dist/AALC.app 应用包（可双击启动、
能被「系统设置 → 隐私与安全性」列为可授权的应用）。
"""

import os
from pathlib import Path

import rapidocr

block_cipher = None

# 构建脚本通过环境变量注入版本号（scripts/build.py）
app_version = os.environ.get("AALC_BUILD_VERSION", "0.0.0")

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

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=add_data,
    hiddenimports=[
        # macOS 后台按键注入（module/automation/input_handlers/macos/macos_keyboard.py）依赖
        # ApplicationServices.AXIsProcessTrusted。它在条件导入里出现，PyInstaller 只会当成
        # 可选子模块，不会收集包本体，缺失后按键能力会静默降级为触摸，所以显式声明。
        "ApplicationServices",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
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
    icon="./assets/logo/my_icon.png",
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

app = BUNDLE(
    coll,
    name="AALC.app",
    icon="./assets/logo/my_icon.png",
    bundle_identifier="com.kiyi671.aalc",
    version=app_version,
    info_plist={
        "CFBundleName": "AALC",
        "CFBundleDisplayName": "AALC",
        # 脚本按 1080p 及以上分辨率识别图片，Retina 下需要真实像素
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "AGPL-3.0-or-later",
    },
)
