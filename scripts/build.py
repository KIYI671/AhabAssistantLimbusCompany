import argparse
import os
import shutil
import subprocess

import PyInstaller.__main__

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
shutil.move(os.path.join("dist", "AALC Updater.exe"), os.path.join("dist", "AALC"))

# 拷贝必要的文件到dist目录
shutil.copy("README.md", os.path.join("dist", "AALC", "README.md"))
shutil.copy("LICENSE", os.path.join("dist", "AALC", "LICENSE"))
shutil.copytree("assets", os.path.join("dist", "AALC", "assets"), dirs_exist_ok=True)

# 生成翻译文件
os.makedirs(os.path.join("dist", "AALC", "i18n"), exist_ok=True)
for ts_file in os.listdir("./i18n"):
    if ts_file.endswith(".ts"):
        qm_path = os.path.join("./i18n", ts_file.replace(".ts", ".qm"))
        subprocess.run(
            ["pyside6-lrelease", os.path.join("./i18n", ts_file), "-qm", qm_path]
        )
        print(f"Generated: {qm_path}")
        shutil.move(
            qm_path, os.path.join("dist", "AALC", "i18n", ts_file.replace(".ts", ".qm"))
        )

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
    # rapidocr用来可视化识别结果的字体，我们不用这个功能
    # 但是因为rapidocr代码耦合的问题，即使不用可视化也会强制下载这个文件，所以还是留着吧...
    # "rapidocr/models/FZYTK.TTF",
    # opencv的videoio插件，我们不需要
    "cv2/opencv_videoio_ffmpeg4110_64.dll",
]

for rel_path in redundant_files:
    abs_path = os.path.join(bundled_internal_dir, rel_path)
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path, ignore_errors=True)
    elif os.path.isfile(abs_path):
        os.remove(abs_path)
    else:
        print(f"Warning: {abs_path} not found.")

# 压缩为7z文件
subprocess.run(["7z", "a", "-mx=7", f"AALC_{version}.7z", "AALC/*"], cwd="./dist")
