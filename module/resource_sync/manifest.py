"""远端图片资源清单协议模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Mapping

# 资源清单协议版本仍保持为 1，并统一承载整包同步所需的元数据字段。
RESOURCE_SYNC_SCHEMA_VERSION = 1


def _reject_unknown_keys(payload: Mapping[str, Any], allowed_keys: set[str]) -> None:
    """校验载荷是否只包含协议允许的字段。

    参数:
        payload: 待校验的字典载荷。
        allowed_keys: 当前协议允许出现的字段名集合。
    """
    # 先找出所有未声明字段，避免后续反序列化默默吞掉脏数据。
    unknown_keys = set(payload) - allowed_keys
    if unknown_keys:
        raise ValueError(f"资源同步载荷中存在未声明字段: {sorted(unknown_keys)}")


@dataclass(slots=True)
class ResourceFileEntry:
    """描述远端清单中的单个受管图片文件。"""

    # 保存相对于 assets/images 的路径，便于客户端按同样结构落盘。
    path: str
    # 保存发布时计算出的 SHA-256 特征码，后续用于完整性校验。
    sha256: str
    # 保存文件字节数，便于后续同步逻辑展示统计信息并识别明显异常。
    size: int

    def to_dict(self) -> dict[str, Any]:
        """将文件条目转换为可直接写入 JSON 的字典。

        返回:
            可序列化的文件条目字典。
        """
        # 直接复用 dataclass 的字段展开结果，保持序列化结构稳定。
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResourceFileEntry":
        """根据字典载荷重建文件条目。

        参数:
            payload: 从 JSON 读取出的单个文件条目字典。

        返回:
            重建后的文件条目对象。
        """
        # 先校验字段范围，避免协议升级或脏数据直接混入运行期对象。
        _reject_unknown_keys(payload, {"path", "sha256", "size"})
        # 再执行类型归一化，确保后续比较逻辑拿到稳定类型。
        return cls(
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            size=int(payload["size"]),
        )


@dataclass(slots=True)
class ResourcePackageEntry:
    """描述完整资源包的下载与校验信息。"""

    # 保存资源包在资源仓库中的相对路径，客户端下载时会基于 manifest_url 推导完整地址。
    path: str
    # 保存资源包文件的 SHA-256，下载后用于整体包校验。
    sha256: str
    # 保存资源包文件字节数，便于快速识别下载不完整等异常。
    size: int
    # 当前整包同步统一使用 7z 格式，显式记录便于协议校验与后续扩展。
    format: str

    def to_dict(self) -> dict[str, Any]:
        """将资源包条目转换为可直接写入 JSON 的字典。

        返回:
            可序列化的资源包条目字典。
        """
        # 统一复用 dataclass 展开结果，减少手写字段遗漏风险。
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResourcePackageEntry":
        """根据字典载荷重建资源包条目。

        参数:
            payload: 从 JSON 读取出的资源包条目字典。

        返回:
            重建后的资源包条目对象。
        """
        # 第一步：先验证载荷字段，确保资源包元数据严格符合当前协议结构。
        _reject_unknown_keys(payload, {"path", "sha256", "size", "format"})
        # 第二步：逐个字段做类型归一化，重建资源包元数据对象。
        return cls(
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            size=int(payload["size"]),
            format=str(payload["format"]),
        )


@dataclass(slots=True)
class ResourceManifest:
    """描述完整的远端图片资源清单。"""

    # 在每份清单中写入协议版本，便于未来做版本校验与迁移。
    schema_version: int = RESOURCE_SYNC_SCHEMA_VERSION
    # 记录清单生成时的 UTC 时间戳。
    generated_at: str = ""
    # 记录稳定的清单标识，供同步层快速判断是否有变化。
    manifest_id: str = ""
    # 记录完整资源包的下载元数据，供客户端整包下载与校验使用。
    package: ResourcePackageEntry | None = None
    # 保存已发布文件列表，并保持写入 JSON 时的顺序结构。
    files: list[ResourceFileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """将完整清单转换为可直接写入 JSON 的字典。

        返回:
            可序列化的完整清单字典。
        """
        # 先写入顶层协议字段，保证序列化结果的键结构固定。
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "manifest_id": self.manifest_id,
            "package": self.package.to_dict() if self.package is not None else None,
            "files": [file_entry.to_dict() for file_entry in self.files],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResourceManifest":
        """根据字典载荷重建完整清单模型。

        参数:
            payload: 从 JSON 读取出的完整清单字典。

        返回:
            重建后的资源清单对象。
        """
        # 第一步：先校验顶层字段，确保清单结构严格符合当前协议。
        _reject_unknown_keys(payload, {"schema_version", "generated_at", "manifest_id", "package", "files"})
        package_payload = payload.get("package")
        # 第二步：再依次重建顶层字段与嵌套对象，保证整份清单都经过同一套校验。
        return cls(
            schema_version=int(payload["schema_version"]),
            generated_at=str(payload["generated_at"]),
            manifest_id=str(payload["manifest_id"]),
            package=ResourcePackageEntry.from_dict(package_payload) if package_payload is not None else None,
            files=[ResourceFileEntry.from_dict(item) for item in payload.get("files", [])],
        )

    def to_json(self) -> str:
        """将清单序列化为稳定的 JSON 字符串。

        返回:
            可直接写入磁盘的 JSON 文本。
        """
        # 统一开启排序与缩进，便于人工审阅和仓库差异比对。
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)
