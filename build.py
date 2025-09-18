import PyInstaller.__main__
import os
import shutil
import sys
import subprocess
import argparse

# 读取版本号
parser = argparse.ArgumentParser(description="Build AALC")
parser.add_argument("--version", default="dev", help="AALC Version")
args = parser.parse_args()
version = args.version

# 清理旧的构建文件
shutil.rmtree("./dist", ignore_errors=True)

# 构建应用程序
PyInstaller.__main__.run([
    'main.spec',
    '--noconfirm',
])

PyInstaller.__main__.run([
    'AALC Updater.spec',
    '--noconfirm',
])

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
        subprocess.run(["pyside6-lrelease", os.path.join("./i18n", ts_file), "-qm", qm_path])
        print(f"Generated: {qm_path}")
        shutil.move(qm_path, os.path.join("dist", "AALC", "i18n", ts_file.replace(".ts", ".qm")))

# 注入版本号到./dist/AALC/assets/config/version.txt
os.makedirs(os.path.join("dist", "AALC", "assets", "config"), exist_ok=True)
with open(os.path.join("dist", "AALC", "assets", "config", "version.txt"), "w", encoding="utf-8") as f:
    f.write(version)

# 压缩为7z文件
subprocess.run([
    "7z", "a", "-mx=7", f"AALC_{version}.7z", "AALC/*"
], cwd="./dist")