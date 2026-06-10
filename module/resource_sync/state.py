"""本地图片资源同步状态协议模型。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from .manifest import RESOURCE_SYNC_SCHEMA_VERSION, _reject_unknown_keys

# 显式声明状态文件路径，统一落到 assets/config 目录，便于与其他本地配置文件集中管理。
LOCAL_STATE_PATH = "./assets/config/image_resource_state.json"


@dataclass(slots=True)
class ResourceSyncState:
    """记录客户端本地的图片资源同步状态。"""

    # 保存与远端清单一致的协议版本，便于未来统一升级。
    schema_version: int = RESOURCE_SYNC_SCHEMA_VERSION
    # 记录本地最近一次成功应用的清单标识。
    last_applied_manifest_id: str | None = None
    # 缓存远端最近一次返回的 Last-Modified，便于后续快速短路检查。
    last_remote_last_modified: str | None = None
    # 缓存远端最近一次返回的 ETag，作用与 Last-Modified 相同。
    last_remote_etag: str | None = None
    # 记录当前本地状态来自哪个资源源。
    last_source: str | None = None
    # 记录上次完成同步后本地图片目录的文件总数，用于轻量判断本地目录是否发生变化。
    last_local_file_count: int | None = None
    # 记录上次完成同步后本地图片目录的轻量快照摘要。
    # 该摘要由相对路径、文件大小和修改时间组合计算而来，用于快速识别本地漂移。
    last_local_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将本地同步状态转换为可直接写入 JSON 的字典。

        返回:
            可序列化的本地状态字典。
        """
        # 明确展开字段，避免未来 dataclass 字段调整时影响落盘结构。
        return {
            "schema_version": self.schema_version,
            "last_applied_manifest_id": self.last_applied_manifest_id,
            "last_remote_last_modified": self.last_remote_last_modified,
            "last_remote_etag": self.last_remote_etag,
            "last_source": self.last_source,
            "last_local_file_count": self.last_local_file_count,
            "last_local_snapshot_id": self.last_local_snapshot_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResourceSyncState":
        """根据字典载荷重建本地同步状态模型。

        参数:
            payload: 从状态文件读取出的字典载荷。

        返回:
            重建后的本地同步状态对象。
        """
        # 第一步：按当前状态文件协议严格拦截未知字段，避免未声明内容混入运行时状态。
        _reject_unknown_keys(
            payload,
            {
                "schema_version",
                "last_applied_manifest_id",
                "last_remote_last_modified",
                "last_remote_etag",
                "last_source",
                "last_local_file_count",
                "last_local_snapshot_id",
            },
        )
        # 第二步：逐个字段做类型归一化，重建当前版本使用的本地资源同步状态对象。
        return cls(
            schema_version=int(payload["schema_version"]),
            last_applied_manifest_id=payload.get("last_applied_manifest_id"),
            last_remote_last_modified=payload.get("last_remote_last_modified"),
            last_remote_etag=payload.get("last_remote_etag"),
            last_source=payload.get("last_source"),
            last_local_file_count=payload.get("last_local_file_count"),
            last_local_snapshot_id=payload.get("last_local_snapshot_id"),
        )

    def to_json(self) -> str:
        """将本地状态序列化为稳定的 JSON 字符串。

        返回:
            可直接写入状态文件的 JSON 文本。
        """
        # 输出稳定 JSON，便于日志排查与仓库差异观察。
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)

    @classmethod
    def from_json(cls, payload: str) -> "ResourceSyncState":
        """根据 JSON 字符串重建本地同步状态模型。

        参数:
            payload: 状态文件中的 JSON 文本。

        返回:
            重建后的本地同步状态对象。
        """
        # 先解析 JSON 文本，再复用字典反序列化逻辑保持入口一致。
        return cls.from_dict(json.loads(payload))
