"""将图片资源构建产物同步到目标资源仓库的脚本。"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

# 兼容直接执行 python scripts/xxx.py 的场景，主动补上项目根目录导入路径。
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 默认将资源构建产物输出到 logs 目录，并与构建脚本保持一致。
DEFAULT_OUTPUT_ROOT = Path("logs/image_resource_build")
# 默认的清单输出路径。
DEFAULT_OUTPUT_MANIFEST_PATH = DEFAULT_OUTPUT_ROOT / "manifest.json"
# 默认的资源包输出路径。
DEFAULT_OUTPUT_PACKAGE_PATH = DEFAULT_OUTPUT_ROOT / Path("packages/images.7z")

# 目标资源仓库中默认的清单相对路径。
DEFAULT_REPO_MANIFEST_RELATIVE_PATH = Path("manifest.json")
# 目标资源仓库中默认的资源包目录相对路径。
DEFAULT_REPO_PACKAGES_RELATIVE_DIR = Path("packages")


def sync_resource_repo(
    artifact_manifest_path: Path,
    artifact_package_path: Path,
    repo_root: Path,
    repo_manifest_relative_path: Path = DEFAULT_REPO_MANIFEST_RELATIVE_PATH,
    repo_packages_relative_dir: Path = DEFAULT_REPO_PACKAGES_RELATIVE_DIR,
) -> tuple[Path, Path]:
    """将清单和资源包同步到目标资源仓库。

    参数:
        artifact_manifest_path: 本地构建产物中的 manifest 路径。
        artifact_package_path: 本地构建产物中的资源包路径。
        repo_root: 目标资源仓库根目录。
        repo_manifest_relative_path: manifest 在目标仓库中的相对路径。
        repo_packages_relative_dir: 资源包目录在目标仓库中的相对路径。

    返回:
        同步后的目标 manifest 路径和目标资源包路径。
    """
    if not artifact_manifest_path.is_file():
        raise FileNotFoundError(f"Manifest file does not exist in build artifacts: {artifact_manifest_path}")
    if not artifact_package_path.is_file():
        raise FileNotFoundError(f"Resource package does not exist in build artifacts: {artifact_package_path}")
    if not repo_root.exists():
        raise FileNotFoundError(f"Target resource repository directory does not exist: {repo_root}")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Target resource repository path is not a directory: {repo_root}")

    target_manifest_path = repo_root / repo_manifest_relative_path
    target_packages_dir = repo_root / repo_packages_relative_dir
    target_package_path = target_packages_dir / artifact_package_path.name

    # 第一步：整体替换目标资源包目录，确保仓库中的过期资源包不会残留。
    if target_packages_dir.exists():
        shutil.rmtree(target_packages_dir)
    target_packages_dir.parent.mkdir(parents=True, exist_ok=True)
    target_packages_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact_package_path, target_package_path)

    # 第二步：单独覆盖 manifest 文件，保持目标仓库中的协议内容始终为最新版本。
    target_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact_manifest_path, target_manifest_path)
    return target_manifest_path, target_package_path


def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。

    返回:
        配置好同步参数的命令行解析器对象。
    """
    # 统一集中定义同步脚本参数，便于 workflow 与本地手动执行共用。
    parser = argparse.ArgumentParser(description="同步图片资源构建产物到目标资源仓库")
    parser.add_argument(
        "--artifact-manifest-path",
        type=Path,
        default=DEFAULT_OUTPUT_MANIFEST_PATH,
        help="构建产物中的清单文件路径",
    )
    parser.add_argument(
        "--artifact-package-path",
        type=Path,
        default=DEFAULT_OUTPUT_PACKAGE_PATH,
        help="构建产物中的资源包文件路径",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="目标资源仓库工作目录",
    )
    parser.add_argument(
        "--repo-manifest-path",
        type=Path,
        default=DEFAULT_REPO_MANIFEST_RELATIVE_PATH,
        help="目标资源仓库中的清单相对路径，默认值为 manifest.json",
    )
    parser.add_argument(
        "--repo-packages-dir",
        type=Path,
        default=DEFAULT_REPO_PACKAGES_RELATIVE_DIR,
        help="目标资源仓库中的资源包目录相对路径，默认值为 packages",
    )
    return parser


def main() -> int:
    """脚本命令行入口。

    返回:
        进程退出码，成功时返回 0。
    """
    # 第一步：读取命令行参数，确定构建产物与目标仓库路径。
    parser = create_argument_parser()
    args = parser.parse_args()

    # 第二步：执行构建产物同步，拿到目标仓库中的最终落盘位置。
    sync_resource_repo(
        artifact_manifest_path=args.artifact_manifest_path,
        artifact_package_path=args.artifact_package_path,
        repo_root=args.repo_root,
        repo_manifest_relative_path=args.repo_manifest_path,
        repo_packages_relative_dir=args.repo_packages_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
