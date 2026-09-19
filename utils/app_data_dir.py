"""macOS 打包版的运行时数据目录。

打包版在 macOS 上不能把配置、日志、图片资源写进 AALC.app：

1. 被 Gatekeeper 打上隔离标记的 .app，从「访达」打开时会以只读的随机路径运行
   （App Translocation），包内写盘直接失败；
2. .app 在打包时做了 ad-hoc 签名，「系统设置 → 隐私与安全性」里的辅助功能、屏幕录制
   授权是按签名记录的，改动包内文件会破坏签名封印，导致授权反复失效。

所以打包版启动时把程序目录里的运行时文件复制到一个可写目录
（``~/Library/Application Support/AALC``）并 chdir 过去，AALC.app 只当只读资源来源。
版本变化时按程序目录重新同步一次程序文件，用户数据（配置、日志、镜像同步状态）保留，
因此替换 AALC.app 升级不会丢设置。
"""

import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "AALC"
VERSION_FILE = Path("assets/config/version.txt")
VERSION_MARKER = ".bundle_version"

# 运行时产生的用户数据：同步程序文件时保留，绝不覆盖
USER_DATA_ENTRIES = frozenset(
    {
        "config.yaml",
        "config_backup",
        "logs",
        "theme_pack_list.yaml",
        "theme_pack_weight",
        "update_temp",
    }
)

# 位于程序资源目录里、但内容属于用户数据：同步时要还原回去
PRESERVE_FILES = (Path("assets/config/image_resource_state.json"),)


def default_data_dir() -> Path:
    """macOS 上打包版的默认数据目录。"""
    return Path.home() / "Library" / "Application Support" / APP_DIR_NAME


def prepare_macos_data_dir(app_dir: Path, data_dir: Path | None = None) -> Path:
    """准备可写的数据目录并返回它。

    :param app_dir: AALC.app 里主程序所在的目录（Contents/MacOS），只读资源来源。
    :param data_dir: 数据目录，默认 ``~/Library/Application Support/AALC``。
    :return: 可以直接 chdir 过去的数据目录。
    """
    app_dir = Path(app_dir).resolve()
    data_dir = Path(data_dir).resolve() if data_dir is not None else default_data_dir()

    marker = data_dir / VERSION_MARKER
    bundle_version = _read_version(app_dir / VERSION_FILE)
    # 没有标记文件说明数据目录还没建好（也可能是程序目录里没有版本文件），一律同步一次
    if not marker.is_file() or _read_version(marker) != bundle_version:
        _sync_program_files(app_dir, data_dir)
        # 同步成功后再落版本标记，半途失败下次启动会重试
        marker.write_text(bundle_version or "", encoding="utf-8")

    return data_dir


def _read_version(path: Path) -> str | None:
    """读取版本文件，不存在时返回 None（用于区分「没有标记」和「标记为空」）。"""
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def _copy_file(source, target, *, follow_symlinks: bool = True) -> None:
    """复制文件内容，不复制权限位。

    程序目录可能是只读挂载（App Translocation），源文件的权限位若被一起复制过来，
    数据目录里的文件下次就写不进去了。
    """
    source = Path(source)
    target = Path(target)
    if target.exists():
        target.chmod(0o644)
    shutil.copyfile(source, target)


def _copy_tree(source: Path, target: Path) -> None:
    """递归复制目录，内容按程序目录覆盖，本地多出来的文件（如同步下来的图片）保留。

    目录权限同样不能跟随源：数据目录里要有可写目录，镜像同步、配置备份才写得进去。
    """
    shutil.copytree(source, target, dirs_exist_ok=True, copy_function=_copy_file)
    for path in target.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            path.chmod(0o755)


def _sync_program_files(app_dir: Path, data_dir: Path) -> None:
    """把程序目录里的文件同步到数据目录，覆盖旧程序文件、保留用户数据。"""
    data_dir.mkdir(parents=True, exist_ok=True)

    preserved = {
        relative_path: (data_dir / relative_path).read_bytes()
        for relative_path in PRESERVE_FILES
        if (data_dir / relative_path).is_file()
    }

    # 主程序本身不是运行时资源，复制过去既占地方又容易让人误双击
    executable = Path(sys.executable).resolve()

    for entry in sorted(app_dir.iterdir()):
        if entry.name in USER_DATA_ENTRIES or entry.name == VERSION_MARKER:
            continue
        if entry.resolve() == executable:
            continue
        target = data_dir / entry.name
        if entry.is_dir():
            _copy_tree(entry, target)
        else:
            _copy_file(entry, target)

    for relative_path, content in preserved.items():
        target = data_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
