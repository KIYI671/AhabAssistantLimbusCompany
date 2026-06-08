"""构建图片资源清单与整包资源的脚本。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

# 兼容直接执行 python scripts/xxx.py 的场景，主动补上项目根目录导入路径。
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from module.resource_sync.manifest import (
    RESOURCE_SYNC_SCHEMA_VERSION,
    ResourceFileEntry,
    ResourceManifest,
    ResourcePackageEntry,
)
from utils.archive_7z import create_7z_archive

# 默认扫描源代码仓库中的图片资源目录。
DEFAULT_SOURCE_DIR = Path("assets/images")
# 默认将构建产物输出到 logs 目录，避免污染仓库跟踪文件。
DEFAULT_OUTPUT_ROOT = Path("logs/image_resource_build")
# 默认的清单输出路径。
DEFAULT_OUTPUT_MANIFEST_PATH = DEFAULT_OUTPUT_ROOT / "manifest.json"
# 默认的资源包输出路径。
DEFAULT_OUTPUT_PACKAGE_PATH = DEFAULT_OUTPUT_ROOT / Path("packages/images.7z")


def _normalize_relative_path(relative_path: Path) -> str:
    """将相对路径统一为带正斜杠的稳定字符串格式。

    参数:
        relative_path: 相对于资源根目录的路径对象。

    返回:
        适合写入清单的稳定路径字符串。
    """
    # 统一用正斜杠，避免不同平台路径分隔符导致 manifest_id 抖动。
    return relative_path.as_posix()


def calculate_file_sha256(file_path: Path) -> str:
    """计算单个文件的 SHA-256 特征码。

    参数:
        file_path: 待计算哈希的文件路径。

    返回:
        文件内容的 SHA-256 十六进制摘要。
    """
    hasher = hashlib.sha256()
    # 采用分块读取，避免较大资源文件一次性加载到内存。
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def iter_resource_files(source_dir: Path) -> list[Path]:
    """按稳定顺序返回资源目录下的全部文件。

    参数:
        source_dir: 资源根目录。

    返回:
        按相对路径排序后的资源文件路径列表。
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source resource directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source resource path is not a directory: {source_dir}")

    # 先扫描全部文件，再按归一化相对路径排序，保证每次构建顺序一致。
    files = [path for path in source_dir.rglob("*") if path.is_file()]
    return sorted(files, key=lambda path: _normalize_relative_path(path.relative_to(source_dir)))


def collect_resource_entries(source_dir: Path) -> list[ResourceFileEntry]:
    """扫描资源目录并收集清单条目。

    参数:
        source_dir: 资源根目录。

    返回:
        可直接写入 manifest 的文件条目列表。
    """
    entries: list[ResourceFileEntry] = []
    # 逐个文件计算相对路径、哈希和大小，生成清单条目。
    for file_path in iter_resource_files(source_dir):
        relative_path = _normalize_relative_path(file_path.relative_to(source_dir))
        entries.append(
            ResourceFileEntry(
                path=relative_path,
                sha256=calculate_file_sha256(file_path),
                size=file_path.stat().st_size,
            )
        )
    return entries


def _build_manifest_id(entries: list[ResourceFileEntry]) -> str:
    """根据协议关键字段生成稳定的清单标识。

    参数:
        entries: 已收集好的资源文件条目列表。

    返回:
        当前清单内容对应的稳定标识字符串。
    """
    # 先构造只包含协议关键字段的规范化载荷，避免无关字段影响标识。
    canonical_payload = {
        "schema_version": RESOURCE_SYNC_SCHEMA_VERSION,
        "files": [entry.to_dict() for entry in entries],
    }
    # 再对规范化 JSON 求哈希，得到可用于增量判断的 manifest_id。
    canonical_json = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def default_generated_at() -> str:
    """生成默认的 UTC 时间戳字符串。

    返回:
        ISO 8601 格式的 UTC 时间文本。
    """
    # 统一去掉微秒并保留 Z 后缀，便于清单比对与人工阅读。
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_resource_manifest(source_dir: Path, generated_at: str | None = None) -> ResourceManifest:
    """根据源资源目录构建完整清单模型。

    参数:
        source_dir: 资源根目录。
        generated_at: 可选的清单生成时间；未提供时自动生成。

    返回:
        尚未附带 package 元数据的资源清单对象。
    """
    # 先收集全部资源条目，再基于条目内容计算稳定清单标识。
    entries = collect_resource_entries(source_dir)
    return ResourceManifest(
        generated_at=generated_at or default_generated_at(),
        manifest_id=_build_manifest_id(entries),
        files=entries,
    )


def build_resource_package(source_dir: Path, output_package_path: Path) -> Path:
    """将完整图片资源目录打包为 7z 资源包。

    参数:
        source_dir: 待打包的资源根目录。
        output_package_path: 资源包输出路径。

    返回:
        生成后的资源包路径。
    """
    # 具体的 7z 打包细节下沉到 utils.archive_7z 模块，这里保留构建脚本入口。
    return create_7z_archive(source_dir, output_package_path)


def build_package_entry(output_manifest_path: Path, output_package_path: Path) -> ResourcePackageEntry:
    """根据已生成的资源包构建清单中的 package 元数据。

    参数:
        output_manifest_path: manifest 文件输出路径。
        output_package_path: 资源包输出路径。

    返回:
        可直接挂到 manifest.package 上的元数据对象。
    """
    try:
        # 资源包路径必须相对 manifest 所在目录可表达，客户端才能稳定推导下载地址。
        package_relative_path = output_package_path.relative_to(output_manifest_path.parent).as_posix()
    except ValueError as exc:
        raise ValueError(
            "Package output path must be located under the manifest output directory "
            "so a stable relative path can be written."
        ) from exc

    # 同步记录资源包相对路径、哈希、大小和格式，供客户端整包校验使用。
    return ResourcePackageEntry(
        path=package_relative_path,
        sha256=calculate_file_sha256(output_package_path),
        size=output_package_path.stat().st_size,
        format="7z",
    )


def write_manifest(manifest: ResourceManifest, output_manifest_path: Path) -> Path:
    """将清单写入目标文件路径。

    参数:
        manifest: 待写入的资源清单对象。
        output_manifest_path: 清单输出路径。

    返回:
        实际写入的清单路径。
    """
    # 先确保输出目录存在，再写入稳定 JSON 文本。
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    return output_manifest_path


def build_manifest_artifacts(
    source_dir: Path,
    output_manifest_path: Path,
    output_package_path: Path,
    generated_at: str | None = None,
) -> ResourceManifest:
    """一次性生成清单文件和完整资源包。

    参数:
        source_dir: 资源根目录。
        output_manifest_path: 清单输出路径。
        output_package_path: 资源包输出路径。
        generated_at: 可选的清单生成时间。

    返回:
        已写入 package 元数据并完成落盘的资源清单对象。
    """
    # 第一步：构建不含 package 字段的基础清单对象。
    manifest = build_resource_manifest(source_dir=source_dir, generated_at=generated_at)
    # 第二步：打包完整资源目录，并反向生成 package 元数据。
    package_path = build_resource_package(source_dir, output_package_path)
    manifest.package = build_package_entry(output_manifest_path, package_path)
    # 第三步：把完整 manifest 写入磁盘，供 CI 和资源仓库同步复用。
    write_manifest(manifest, output_manifest_path)
    return manifest


def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。

    返回:
        配置好默认参数的命令行解析器对象。
    """
    # 统一集中定义命令行参数，便于本地调试和 CI 任务共用。
    parser = argparse.ArgumentParser(description="构建图片资源清单与完整资源包")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="图片资源源目录，默认值为 assets/images",
    )
    parser.add_argument(
        "--output-manifest-path",
        type=Path,
        default=DEFAULT_OUTPUT_MANIFEST_PATH,
        help="清单输出文件路径，默认值为 logs/image_resource_build/manifest.json",
    )
    parser.add_argument(
        "--output-package-path",
        type=Path,
        default=DEFAULT_OUTPUT_PACKAGE_PATH,
        help="资源包输出文件路径，默认值为 logs/image_resource_build/packages/images.7z",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="可选的清单生成时间，未提供时自动使用当前 UTC 时间",
    )
    return parser


def main() -> int:
    """脚本命令行入口。

    返回:
        进程退出码，成功时返回 0。
    """
    # 第一步：解析命令行参数，确定源目录与输出位置。
    parser = create_argument_parser()
    args = parser.parse_args()

    # 第二步：生成 manifest 与 7z 资源包两类构建产物。
    manifest = build_manifest_artifacts(
        source_dir=args.source_dir,
        output_manifest_path=args.output_manifest_path,
        output_package_path=args.output_package_path,
        generated_at=args.generated_at,
    )


    return 0


if __name__ == "__main__":
    raise SystemExit(main())
