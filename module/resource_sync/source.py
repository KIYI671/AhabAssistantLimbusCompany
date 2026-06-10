"""资源源定义与选择逻辑。"""

from __future__ import annotations

from dataclasses import dataclass

# GitHub 资源清单地址。
RESOURCE_MANIFEST_URL_GITHUB = "https://raw.githubusercontent.com/KIYI671/AALCImageResources/main/manifest.json"
# Gitee 资源清单地址。
RESOURCE_MANIFEST_URL_GITEE = "https://gitee.com/KIYI/AALCImageResources/raw/master/manifest.json"


@dataclass(frozen=True, slots=True)
class ResourceSource:
    """描述单个图片资源源的访问地址集合。"""

    # 资源源的人类可读名称，会显示在日志与状态里。
    name: str
    # 资源清单文件的完整 URL。
    manifest_url: str


def get_default_sources() -> dict[str, ResourceSource]:
    """返回默认的双源配置字典。

    返回:
        以资源源名称为键的默认资源源映射。
    """
    # 统一在这里维护默认源定义，便于服务层和配置层复用同一份来源列表。
    return {
        "GitHub": ResourceSource("GitHub", RESOURCE_MANIFEST_URL_GITHUB),
        "Gitee": ResourceSource("Gitee", RESOURCE_MANIFEST_URL_GITEE),
    }
