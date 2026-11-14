"""打包 AALC。

Windows：PyInstaller 产出 dist/AALC/（含 AALC Updater.exe），打包为 dist/AALC_<version>.7z
macOS：PyInstaller 产出 dist/AALC.app，打包为 dist/AALC_<version>_macos_<arch>.zip
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]

# Windows 上多余的文件（相对 dist/AALC/_internal）
WINDOWS_REDUNDANT_FILES = [
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

# macOS 上多余的文件（相对 dist/AALC.app/Contents/Frameworks），与 Windows 列表一一对应
MACOS_REDUNDANT_FILES = [
    # qt6自带的翻译文件，体积较大且不需要
    "PySide6/Qt/translations",
    # QML相关，我们用的是QtWidgets并不需要
    "PySide6/Qt/lib/QtQml.framework",
    "PySide6/Qt/lib/QtQmlModels.framework",
    "PySide6/Qt/lib/QtQmlMeta.framework",
    "PySide6/Qt/lib/QtQmlWorkerScript.framework",
    "PySide6/Qt/lib/QtQuick.framework",
    # opengl相关，我们用的是QtWidgets并不需要
    "PySide6/Qt/lib/QtOpenGL.framework",
    # 其他不需要的Qt模块
    "PySide6/Qt/lib/QtPdf.framework",  # pdf文件
    "PySide6/Qt/lib/QtNetwork.framework",  # 网络相关
    "PySide6/QtNetwork.abi3.so",
    # 上面这些框架二进制在 Contents/Frameworks 根目录还各有一个软链接，裁剪后统一清理（见 remove_dangling_symlinks）
    # rapidocr自带的模型文件，我们只用PPV4模型，可以删掉V5的
    "rapidocr/models/ch_PP-OCRv5_rec_mobile_infer.onnx",
    "rapidocr/models/ch_PP-OCRv5_mobile_det.onnx",
    # opencv 的 ffmpeg 动态库不能删：cv2.abi3.so 直接链接了 libavcodec/libavformat/libswscale，
    # 不是 Windows 上那种按需加载的插件。
]


def remove_redundant(root: Path, relative_paths: list[str]) -> None:
    """删除打包结果里多余的资源，缺失的文件只提示不报错。"""
    for relative_path in relative_paths:
        target = root / relative_path
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            target.unlink()
        else:
            print(f"Warning: {target} not found.")


def remove_dangling_symlinks(root: Path) -> None:
    """清掉指向已删文件的软链接。

    PyInstaller 会在 Contents/Resources 下给包内文件再建一份软链接，裁剪掉 Frameworks 里的
    文件后这些链接就悬空了；包里有悬空链接会让 ditto 等工具复制整包时报错。
    """
    for path in root.rglob("*"):
        if path.is_symlink() and not path.exists():
            path.unlink()


def generate_translations(dest_dir: Path) -> None:
    """用 pyside6-lrelease 把 i18n/*.ts 编译成 .qm 放进程序目录。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for ts_file in sorted(Path("i18n").glob("*.ts")):
        qm_path = ts_file.with_suffix(".qm")
        subprocess.run(
            ["pyside6-lrelease", str(ts_file), "-qm", str(qm_path)],
            check=True,
        )
        print(f"Generated: {qm_path}")
        shutil.move(str(qm_path), dest_dir / qm_path.name)


def write_version_file(app_dir: Path, version: str) -> None:
    """把版本号写进 assets/config/version.txt，程序启动时读取这里判断版本。"""
    version_path = app_dir / "assets" / "config" / "version.txt"
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(version, encoding="utf-8")


def copy_extra_files(app_dir: Path) -> None:
    """把程序目录下随包分发的附属文件（文档、协议、资源）复制过去。"""
    shutil.copy("README.md", app_dir / "README.md")
    shutil.copy("LICENSE", app_dir / "LICENSE")
    shutil.copytree("assets", app_dir / "assets", dirs_exist_ok=True)


def build_windows(version: str) -> None:
    PyInstaller.__main__.run(["main.spec", "--noconfirm"])
    PyInstaller.__main__.run(["updater.spec", "--noconfirm"])

    app_dir = Path("dist/AALC")
    # 移动更新程序到主程序目录
    shutil.move("dist/AALC Updater.exe", app_dir / "AALC Updater.exe")

    copy_extra_files(app_dir)
    generate_translations(app_dir / "i18n")
    write_version_file(app_dir, version)
    remove_redundant(app_dir / "_internal", WINDOWS_REDUNDANT_FILES)

    # 压缩为7z文件
    subprocess.run(["7z", "a", "-mx=7", f"AALC_{version}.7z", "AALC/*"], cwd="dist", check=True)


def build_macos(version: str) -> None:
    # 版本号通过环境变量传给 main_mac.spec，写进 Info.plist
    os.environ["AALC_BUILD_VERSION"] = version
    PyInstaller.__main__.run(["main_mac.spec", "--noconfirm"])

    app_bundle = Path("dist/AALC.app")
    if not app_bundle.is_dir():
        raise SystemExit(f"未找到打包产物 {app_bundle}，请确认 PyInstaller 执行成功。")

    # Contents/MacOS 是主程序所在目录，也是程序运行时的 cwd（main.py 会 chdir 到这里）
    app_dir = app_bundle / "Contents" / "MacOS"
    copy_extra_files(app_dir)
    generate_translations(app_dir / "i18n")
    write_version_file(app_dir, version)

    frameworks_dir = app_bundle / "Contents" / "Frameworks"
    remove_redundant(frameworks_dir, MACOS_REDUNDANT_FILES)
    remove_dangling_symlinks(frameworks_dir)
    remove_dangling_symlinks(app_bundle / "Contents" / "Resources")

    # 往包内补文件（assets、i18n、README）以及裁剪 Qt 都会破坏 PyInstaller 打的 ad-hoc 签名封印，
    # 而 macOS 的「辅助功能」「屏幕录制」授权是按签名记录的，所以最后要重新签一次。
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_bundle.name], cwd="dist", check=True)

    # 用 ditto 打包，保留 .app 内的符号链接与扩展属性（zip 命令会破坏应用包结构）
    archive_name = f"AALC_{version}_macos_{platform.machine()}.zip"
    subprocess.run(
        ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app_bundle.name, archive_name],
        cwd="dist",
        check=True,
    )
    print(f"Generated: dist/{archive_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build AALC")
    parser.add_argument("--version", default="dev", help="AALC Version")
    args = parser.parse_args()

    # 打包产物的相对路径都基于仓库根目录
    os.chdir(ROOT)
    # 清理旧的构建文件
    shutil.rmtree("./dist", ignore_errors=True)

    if sys.platform == "darwin":
        build_macos(args.version)
    elif sys.platform == "win32":
        build_windows(args.version)
    else:
        raise SystemExit(f"暂不支持在 {sys.platform} 上打包 AALC。")


if __name__ == "__main__":
    main()
