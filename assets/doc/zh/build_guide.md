# 构建指南

## 配置python环境

依赖python3.12版本

python库依赖见[requirements.txt](/requirements.txt)

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## 构建可执行文件

```bash
python scripts/build.py --version 1.0.9
```

默认生成可直接运行的 `dist/AALC` 目录，包含主程序、更新器、依赖库、资源和翻译文件，不压缩发布包。Linux 运行 `dist/AALC/AALC`，Windows 运行 `dist/AALC/AALC.exe`。运行或复制程序时需保留整个 `dist/AALC` 目录。

`--version` 用于设置构建版本，省略时使用 `dev`。

GitHub Actions 中默认额外压缩发布包，以兼容现有发布工作流。

## 压缩发布包

```bash
python scripts/build.py --version 1.0.9 --package
```

添加 `--package` 后，构建完成时额外压缩发布包：Windows 为 `dist/AALC_<版本>.7z`，Linux 为 `dist/AALC_<版本>_linux.7z`。未找到 `7z` 或 `7zz` 时回退到 `.tar.gz`。
