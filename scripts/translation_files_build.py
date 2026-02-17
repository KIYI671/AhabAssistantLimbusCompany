import subprocess

"""生成翻译文件的脚本, 需要在项目根目录下运行"""
# 生成翻译文件
subprocess.run(["pyside6-project", "lupdate"])
