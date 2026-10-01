import argparse
import os
import shutil
import subprocess
import sys
import threading
import time

import PyInstaller.__main__

IS_WINDOWS = sys.platform == "win32"

# 读取版本号
parser = argparse.ArgumentParser(description="Build AALC")
parser.add_argument("--version", default="dev", help="AALC Version")
parser.add_argument(
    "--package",
    action="store_true",
    default=os.environ.get("GITHUB_ACTIONS") == "true",
    help="Compress the build into a release archive (enabled by default in GitHub Actions)",
)
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
    # PyInstaller 在根目录及 Qt/lib 中收集共享库（含软链接）。
    qt_modules = (
        "Qml", "QmlMeta", "QmlWorkerScript", "QmlModels", "Quick", "QuickWidgets",
        "QuickParticles", "QuickShapes", "QuickTemplates2", "QuickControls2",
        "QuickDialogs2", "QuickDialogs2QuickImpl", "QuickLayouts", "VirtualKeyboardQml",
        "Pdf", "Network",
    )
    redundant_files = ["PySide6/translations", "PySide6/Qt/translations"] + [
        f"{prefix}libQt6{module}.so.6"
        for prefix in ("", "PySide6/Qt/lib/")
        for module in qt_modules
    ]

removed_count = 0
skipped_count = 0
for rel_path in redundant_files:
    abs_path = os.path.join(bundled_internal_dir, rel_path)
    if os.path.isdir(abs_path) and not os.path.islink(abs_path):
        shutil.rmtree(abs_path)
        removed_count += 1
    elif os.path.isfile(abs_path) or os.path.islink(abs_path):
        os.remove(abs_path)
        removed_count += 1
    else:
        skipped_count += 1
print(f"清理完成：删除 {removed_count} 项，跳过 {skipped_count} 项（不存在，无需删除）。", flush=True)

# 确保可执行权限（PyInstaller 通常已设置，这里兜底）
for binary in ("AALC", updater_binary):
    binary_path = os.path.join("dist", "AALC", binary)
    if os.path.isfile(binary_path):
        os.chmod(binary_path, 0o755)

app_binary = "AALC.exe" if IS_WINDOWS else "AALC"
print(f"构建完成，可执行文件：{os.path.join('dist', 'AALC', app_binary)}", flush=True)
if not args.package:
    print("如需压缩发布包，请添加 --package 参数。", flush=True)
    sys.exit(0)

# 压缩为发布包：优先 7z/7zz，缺失时退回 tar.gz
archive_base = f"AALC_{version}_linux" if not IS_WINDOWS else f"AALC_{version}"
archive_tool = shutil.which("7z") or shutil.which("7zz")
ext = "7z" if archive_tool else "tar.gz"
archive_path = os.path.join("dist", f"{archive_base}.{ext}")
archive_started = time.monotonic()
if archive_tool:
    print(f"开始压缩：{archive_path}（使用 {archive_tool}）", flush=True)
    archive_command = [archive_tool, "a", "-mx=7", "-bsp1"]
    if not IS_WINDOWS:
        # 保留 PyInstaller 的共享库软链接，避免重复压缩其指向的文件。
        archive_command.append("-snl")
    archive_command.extend([f"{archive_base}.7z", "AALC/*"])
    subprocess.run(archive_command, cwd="./dist", check=True)
else:
    print(f"未找到 7z/7zz，开始 gzip 压缩：{archive_path}（可能需要几分钟）", flush=True)
    compression_done = threading.Event()

    def report_compression_progress():
        while not compression_done.wait(10):
            elapsed = time.monotonic() - archive_started
            size = os.path.getsize(archive_path) if os.path.isfile(archive_path) else 0
            print(f"压缩中：已用时 {elapsed:.0f} 秒，当前压缩包 {size / 1024**2:.1f} MiB", flush=True)

    progress_thread = threading.Thread(target=report_compression_progress, daemon=True)
    progress_thread.start()
    try:
        shutil.make_archive(
            os.path.join("dist", archive_base),
            "gztar",
            root_dir="./dist",
            base_dir="AALC",
        )
    finally:
        compression_done.set()
        progress_thread.join()
print(
    f"打包完成：{archive_path}，{os.path.getsize(archive_path) / 1024**2:.1f} MiB，"
    f"压缩耗时 {time.monotonic() - archive_started:.0f} 秒",
    flush=True,
)
