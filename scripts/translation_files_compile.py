import os
import subprocess

"""编译翻译文件的脚本, 需要在项目根目录下运行"""
# 编译翻译文件
os.makedirs(os.path.join("dist", "AALC", "i18n"), exist_ok=True)
for ts_file in os.listdir("./i18n"):
    if ts_file.endswith(".ts"):
        qm_path = os.path.join("./i18n", ts_file.replace(".ts", ".qm"))
        subprocess.run(
            ["pyside6-lrelease", os.path.join("./i18n", ts_file), "-qm", qm_path]
        )
        print(f"Generated: {qm_path}")
