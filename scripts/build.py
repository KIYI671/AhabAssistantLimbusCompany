import argparse
import os
import shutil
import subprocess
import sys

import PyInstaller.__main__

IS_WINDOWS = sys.platform == "win32"

# 读取版本号
parser = argparse.ArgumentParser(description="Build AALC")
parser.add_argument("--version", default="dev", help="AALC Version")
args = parser.parse_args()
version = args.version

# 清理旧的构建文件
shutil.rmtree("./dist", ignore_errors=True)

# 构建应用程序
PyInstaller.__main__.run(
    [
        "main.spec",
        "--noconfirm",
    ]
)

PyInstaller.__main__.run(
    [
        "updater.spec",
        "--noconfirm",
    ]
)

# 移动更新程序到主程序目录
updater_binary = "AALC Updater.exe" if IS_WINDOWS else "AALC-Updater"
shutil.move(os.path.join("dist", updater_binary), os.path.join("dist", "AALC"))

# 拷贝必要的文件到dist目录
shutil.copy("README.md", os.path.join("dist", "AALC", "README.md"))
shutil.copy("LICENSE", os.path.join("dist", "AALC", "LICENSE"))
shutil.copytree("assets", os.path.join("dist", "AALC", "assets"), dirs_exist_ok=True)

# 生成翻译文件
os.makedirs(os.path.join("dist", "AALC", "i18n"), exist_ok=True)
for ts_file in os.listdir("./i18n"):
    if ts_file.endswith(".ts"):
        qm_path = os.path.join("./i18n", ts_file.replace(".ts", ".qm"))
        subprocess.run(["pyside6-lrelease", os.path.join("./i18n", ts_file), "-qm", qm_path])
        print(f"Generated: {qm_path}")
        shutil.move(qm_path, os.path.join("dist", "AALC", "i18n", ts_file.replace(".ts", ".qm")))

# 注入版本号到./dist/AALC/assets/config/version.txt
os.makedirs(os.path.join("dist", "AALC", "assets", "config"), exist_ok=True)
with open(
    os.path.join("dist", "AALC", "assets", "config", "version.txt"),
    "w",
    encoding="utf-8",
) as f:
    f.write(version)

# 裁剪多余的文件
bundled_internal_dir = os.path.join("dist", "AALC", "_internal")
if IS_WINDOWS:
    redundant_files = [
        # qt6自带的翻译文件，体积较大且不需要
        "PySide6/translations",
        # QML相关，我们用的是QtWidgets并不需要
        "PySide6/Qt6Qml.dll",
        "PySide6/Qt6Quick.dll",
        "PySide6/Qt6QmlModels.dll",
        "PySide6/Qt6QmlWorkerScript.dll",
        "PySide6/Qt6QmlMeta.dll",
        # opengl相关，我们用的是QtWidgets并不需要
        "PySide6/Qt6OpenGL.dll",
        "PySide6/opengl32sw.dll",  # 软件渲染库，没GPU的机器才需要
        # 其他不需要的Qt模块
        "PySide6/Qt6Pdf.dll",  # pdf文件
        "PySide6/Qt6Network.dll",  # 网络相关
        "PySide6/QtNetwork.pyd",
        # rapidocr自带的模型文件，我们只用PPV4模型，可以删掉V5的
        "rapidocr/models/ch_PP-OCRv5_rec_mobile_infer.onnx",
        "rapidocr/models/ch_PP-OCRv5_mobile_det.onnx",
        # opencv的videoio插件，我们不需要
        "cv2/opencv_videoio_ffmpeg4110_64.dll",
    ]
else:
    redundant_files = [
        # qt6自带的翻译文件，体积较大且不需要
        "PySide6/translations",
        # QML/Quick 相关，我们用的是QtWidgets并不需要
        # （PyInstaller 6.x 将部分 Qt 库直接放在 _internal/ 根，部分在 PySide6/Qt/lib/）
        "libQt6Qml.so.6",
        "libQt6QmlModels.so.6",
        "libQt6Quick.so.6",
        "libQt6Pdf.so.6",
        "libQt6Network.so.6",
        "PySide6/Qt/translations",
        "PySide6/Qt/lib/libQt6Qml.so.6",
        "PySide6/Qt/lib/libQt6QmlMeta.so.6",
        "PySide6/Qt/lib/libQt6QmlWorkerScript.so.6",
        "PySide6/Qt/lib/libQt6QmlModels.so.6",
        "PySide6/Qt/lib/libQt6Quick.so.6",
        "PySide6/Qt/lib/libQt6QuickWidgets.so.6",
        "PySide6/Qt/lib/libQt6QuickParticles.so.6",
        "PySide6/Qt/lib/libQt6QuickShapes.so.6",
        "PySide6/Qt/lib/libQt6QuickTemplates2.so.6",
        "PySide6/Qt/lib/libQt6QuickControls2.so.6",
        "PySide6/Qt/lib/libQt6QuickDialogs2.so.6",
        "PySide6/Qt/lib/libQt6QuickDialogs2QuickImpl.so.6",
        "PySide6/Qt/lib/libQt6QuickLayouts.so.6",
        "PySide6/Qt/lib/libQt6VirtualKeyboardQml.so.6",
        # 其他不需要的Qt模块
        "libQt6Pdf.so.6",
        "libQt6Network.so.6",
    ]

for rel_path in redundant_files:
    abs_path = os.path.join(bundled_internal_dir, rel_path)
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path, ignore_errors=True)
    elif os.path.isfile(abs_path):
        os.remove(abs_path)
    else:
        print(f"Warning: {abs_path} not found.")

# 确保可执行权限（PyInstaller 通常已设置，这里兜底）
for binary in ("AALC", updater_binary):
    binary_path = os.path.join("dist", "AALC", binary)
    if os.path.isfile(binary_path):
        os.chmod(binary_path, 0o755)

# 压缩为发布包：Windows 用 7z，Linux 优先 7z，缺失时退回 tar.gz
archive_base = f"AALC_{version}_linux" if not IS_WINDOWS else f"AALC_{version}"
if shutil.which("7z"):
    ext = "7z"
    subprocess.run(["7z", "a", "-mx=7", f"{archive_base}.7z", "AALC/*"], cwd="./dist", check=False)
else:
    ext = "tar.gz"
    shutil.make_archive(
        os.path.join("dist", archive_base),
        "gztar",
        root_dir="./dist",
        base_dir="AALC",
    )
print(f"打包完成: dist/{archive_base}.{ext}")
