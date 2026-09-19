# 构建指南

## 配置python环境

依赖python3.12版本

python库依赖见[requirements.txt](/requirements.txt)

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

## 一键打包（推荐，CI 用的就是它）

```bash
uv run python ./scripts/build.py --version Vx.x.x
```

打包脚本按当前平台产出发布包：

- Windows：`dist/AALC_<version>.7z`，内含 `AALC/`（含 `AALC Updater.exe`）
- macOS：`dist/AALC_<version>_macos_<arch>.zip`，内含 `AALC.app`（<arch> 为 `arm64` 或 `x86_64`）

## 构建可执行文件

### Windows

```bash
pyinstaller main.spec
```

### macOS

PyInstaller 不支持交叉编译，macOS 的包必须在 macOS 上构建：

```bash
pyinstaller main_mac.spec
```

生成 `dist/AALC.app` 之后还需要做完打包脚本里那几步（`scripts/build.py` 已经全部包含，单独手动构建时按需照做）：

1. 把 `README.md`、`LICENSE`、`assets/` 复制到 `AALC.app/Contents/MacOS/`（程序运行时的工作目录就是这里），用 `pyside6-lrelease` 生成 `i18n/*.qm` 放进去，并把版本号写入 `assets/config/version.txt`。
2. 重新签名：往包内补文件会破坏 PyInstaller 打的 ad-hoc 签名封印，而「辅助功能」「屏幕录制」授权是按签名记录的，必须重新签一次：
   `codesign --force --deep --sign - dist/AALC.app`
3. 压缩要用 `ditto`（`zip` 命令会破坏 `.app` 内的软链接）：
   `ditto -c -k --sequesterRsrc --keepParent AALC.app AALC_<version>_macos_$(uname -m).zip`

macOS 包没有签名与公证，用户首次打开前需要去掉下载隔离标记（`xattr -dr com.apple.quarantine AALC.app`）。

打包版的运行时数据目录是 `~/Library/Application Support/AALC`（见 `utils/app_data_dir.py`）：包内只放只读资源，配置、日志、图片资源都写到数据目录，因此替换 `AALC.app` 升级不丢配置，应用也不能往包内写文件（写包内文件会破坏签名封印，导致系统授权反复失效）。

## 添加其他附属文件

```bash
mkdir dist_release
mv dist/* dist_release/
cp -r 3rdparty dist_release/AALC/
cp -r assets dist_release/AALC/
cp LICENSE dist_release/AALC/
cp README.md dist_release/AALC/
```
