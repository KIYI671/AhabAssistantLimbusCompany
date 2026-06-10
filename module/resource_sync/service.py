"""图片资源同步服务层。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import shutil
from typing import Callable
from urllib.parse import quote, urljoin

import requests

from module.logger import log
from module.resource_sync.manifest import ResourceFileEntry, ResourceManifest, ResourcePackageEntry
from module.resource_sync.source import ResourceSource, get_default_sources
from module.resource_sync.state import LOCAL_STATE_PATH, ResourceSyncState
from utils.archive_7z import extract_7z_archive

# 默认的本地图片资源目录。
DEFAULT_LOCAL_IMAGES_DIR = Path("assets/images")
# 默认的本地同步状态文件路径。
DEFAULT_LOCAL_STATE_PATH = Path(LOCAL_STATE_PATH)
# 默认的下载临时目录。
DEFAULT_TEMP_DIR = Path("update_temp")
# 网络请求超时时间，单位为秒。
DEFAULT_REQUEST_TIMEOUT = 10


class ResourceCheckStatus(Enum):
    """资源更新检查阶段的状态枚举。"""

    UNCONFIGURED = "unconfigured"
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    ERROR = "error"


@dataclass(slots=True)
class ResourceCheckResult:
    """承载远端资源检查结果。"""

    # 检查结果状态。
    status: ResourceCheckStatus
    # 命中的资源源；若未配置或失败则可能为空。
    source: ResourceSource | None = None
    # 下载得到的远端清单；仅在需要进一步比对时存在。
    remote_manifest: ResourceManifest | None = None
    # 远端返回的 Last-Modified 响应头。
    remote_last_modified: str | None = None
    # 远端返回的 ETag 响应头。
    remote_etag: str | None = None
    # 供 UI 与日志使用的说明信息。
    message: str = ""


@dataclass(slots=True)
class ResourceSyncPlan:
    """承载本地与远端清单的比对结果。"""

    # 本地缺失、需要新增下载的文件条目。
    files_to_add: list[ResourceFileEntry] = field(default_factory=list)
    # 本地已存在但特征码不同、需要覆盖更新的文件条目。
    files_to_update: list[ResourceFileEntry] = field(default_factory=list)
    # 本地已存在、但远端清单中已不再记录的文件路径列表。
    files_to_delete: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """返回本次比对是否识别到任何需要处理的变化。"""
        # 将新增、变更、删除三类变化统一折叠为一个布尔结果，便于 UI 快速判断后续动作。
        return any((self.files_to_add, self.files_to_update, self.files_to_delete))

    @property
    def download_entries(self) -> list[ResourceFileEntry]:
        """返回需要从资源包中应用到本地的全部文件条目。"""
        # 整包下载后只需要从解压目录里应用新增与变更文件。
        return [*self.files_to_add, *self.files_to_update]


@dataclass(slots=True)
class ResourceApplyResult:
    """承载资源同步应用阶段的结果。"""

    # 实际写入本地的文件数量。
    downloaded_count: int
    # 实际删除的文件数量。
    deleted_count: int
    # 最终落盘的本地状态。
    state: ResourceSyncState


@dataclass(slots=True)
class LocalImageSnapshot:
    """承载本地图片目录轻量快照结果。"""

    # 当前本地图片目录中的文件总数。
    file_count: int
    # 基于相对路径、大小和修改时间生成的轻量摘要。
    snapshot_id: str


class ResourceSyncService:
    """提供资源更新检查、清单比对与本地同步能力。"""

    def __init__(
        self,
        *,
        session=None,
        assets_dir: Path = DEFAULT_LOCAL_IMAGES_DIR,
        state_path: Path = DEFAULT_LOCAL_STATE_PATH,
        temp_dir: Path = DEFAULT_TEMP_DIR,
        sources: dict[str, ResourceSource] | None = None,
    ):
        """初始化资源同步服务依赖，便于在界面层与验证脚本间复用。

        参数:
            session: 可选的 requests 会话对象，便于复用连接或注入测试替身。
            assets_dir: 本地图片资源目录。
            state_path: 本地资源同步状态文件路径。
            temp_dir: 下载资源包与解压文件使用的临时目录。
            sources: 可选的资源源映射；未传入时使用默认双源配置。
        """
        # 使用可注入会话对象，便于测试或替换网络实现。
        self.session = session or requests.Session()
        # 本地图片资源目录。
        self.assets_dir = Path(assets_dir)
        # 本地状态文件路径。
        self.state_path = Path(state_path)
        # 临时下载与解压目录。
        self.temp_dir = Path(temp_dir)
        # 资源源定义表。
        self.sources = sources or get_default_sources()

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """计算本地文件的 SHA-256 特征码。

        参数:
            file_path: 待计算哈希的文件路径。

        返回:
            文件内容的 SHA-256 十六进制摘要。
        """
        hasher = hashlib.sha256()
        # 采用分块读取，避免大文件一次性读入内存。
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _quote_repository_path(resource_path: str) -> str:
        """将仓库内相对路径转换为可安全拼接到 URL 的格式。

        参数:
            resource_path: 仓库中的相对资源路径。

        返回:
            适合拼接到 URL 中的转义路径字符串。
        """
        # 先统一为正斜杠，再做 URL 转义，保证 GitHub/Gitee 路径都能正确访问。
        return quote(resource_path.replace("\\", "/"), safe="/")

    @staticmethod
    def _is_same_remote_version(
        state: ResourceSyncState,
        source: ResourceSource,
        last_modified: str | None,
        etag: str | None,
    ) -> bool:
        """根据资源源与远端元数据判断远端清单是否大概率未变化。

        参数:
            state: 本地已记录的资源同步状态。
            source: 当前正在检查的资源源。
            last_modified: 远端返回的 Last-Modified 头。
            etag: 远端返回的 ETag 头。

        返回:
            若远端元数据命中本地缓存则返回 True，否则返回 False。
        """
        # 先确认当前检查的资源源与本地缓存来源一致，不同来源不能直接复用旧缓存。
        if state.last_source != source.name:
            return False
        # 优先用 ETag 精确命中，用于快速判断远端大概率未变化。
        if etag and state.last_remote_etag and etag == state.last_remote_etag:
            return True
        # 再回退到 Last-Modified，用于不提供 ETag 的托管源。
        if last_modified and state.last_remote_last_modified and last_modified == state.last_remote_last_modified:
            return True
        return False

    @staticmethod
    def _resolve_package_url(source: ResourceSource, package_path: str) -> str:
        """根据 manifest_url 与清单中的相对路径推导资源包完整下载地址。

        参数:
            source: 命中的资源源对象。
            package_path: 清单中记录的资源包相对路径。

        返回:
            资源包的完整下载地址。
        """
        # 先转义相对路径，再与 manifest_url 组合，兼容带子目录的资源仓库结构。
        return urljoin(source.manifest_url, ResourceSyncService._quote_repository_path(package_path))

    @staticmethod
    def _ensure_package_metadata(manifest: ResourceManifest) -> ResourcePackageEntry:
        """确保远端清单包含整包同步所需的 package 元数据。

        参数:
            manifest: 已解析的远端资源清单对象。

        返回:
            可用于整包同步的资源包元数据对象。
        """
        # 先保证清单真的携带 package 字段，避免后续进入下载阶段才失败。
        if manifest.package is None:
            raise ValueError("远端资源清单缺少资源包元数据，无法执行整包同步")
        # 当前发布链路统一产出 7z 包，这里显式限制格式，防止误吃未支持资源包。
        if manifest.package.format.lower() != "7z":
            raise ValueError(f"暂不支持的资源包格式: {manifest.package.format}")
        return manifest.package

    def resolve_candidate_sources(self, preferred_source: str) -> list[ResourceSource]:
        """根据配置返回资源源候选顺序。

        参数:
            preferred_source: 用户配置的优先资源源，可选 `Auto`、`GitHub` 或 `Gitee`。

        返回:
            按优先顺序排列的资源源对象列表。
        """
        # 先根据用户偏好排列源名称，Auto 场景下优先走 Gitee 再回退 GitHub。
        if preferred_source == "GitHub":
            ordered_names = ["GitHub", "Gitee"]
        elif preferred_source == "Gitee":
            ordered_names = ["Gitee", "GitHub"]
        else:
            ordered_names = ["Gitee", "GitHub"]
        # 再过滤掉当前 sources 中未注册的条目，得到实际可用候选列表。
        return [self.sources[name] for name in ordered_names if name in self.sources]

    def load_state(self) -> ResourceSyncState:
        """读取本地资源同步状态；若文件不存在则返回默认空状态。

        返回:
            本地资源同步状态对象。
        """
        # 先处理首次运行场景，状态文件不存在时直接返回空状态。
        if not self.state_path.exists():
            return ResourceSyncState()
        try:
            # 读取并解析 JSON 状态文件，供本轮远端比对复用。
            return ResourceSyncState.from_json(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            # 状态文件损坏时不阻断主流程，回退为空状态继续检查。
            log.warning(f"读取图片资源同步状态失败，将使用空状态继续: {exc}")
            return ResourceSyncState()

    def save_state(self, state: ResourceSyncState) -> Path:
        """保存本地资源同步状态。

        参数:
            state: 待落盘的本地资源同步状态对象。

        返回:
            实际写入的状态文件路径。
        """
        # 先确保状态文件目录存在，再执行覆盖写入。
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(state.to_json(), encoding="utf-8")
        return self.state_path

    def check_for_updates(self, preferred_source: str, state: ResourceSyncState | None = None) -> ResourceCheckResult:
        """检查远端资源清单是否发生更新。

        参数:
            preferred_source: 用户配置的优先资源源。
            state: 可选的本地状态对象；未传入时自动从磁盘读取。

        返回:
            本轮远端检查结果对象。
        """
        # 第一步：准备本地状态、当前本地轻量快照和候选资源源列表。
        local_state = state or self.load_state()
        local_snapshot = self._build_local_snapshot()
        local_snapshot_unchanged = self._is_same_local_snapshot(local_state, local_snapshot)
        candidates = self.resolve_candidate_sources(preferred_source)

        if not candidates:
            return ResourceCheckResult(
                status=ResourceCheckStatus.UNCONFIGURED,
                message="未找到可用的图片资源源配置",
            )

        # 第二步：按优先顺序逐个检查资源源，前一个失败时自动回退到下一个。
        for source in candidates:
            try:
                log.debug(f"开始检查图片资源清单更新，资源源: {source.name}")
                # 第一步：若本地图片目录未变化，则优先复用远端缓存标记发起条件请求。
                request_headers = self._build_manifest_request_headers(
                    local_state,
                    source,
                    local_snapshot_unchanged=local_snapshot_unchanged,
                )
                manifest_response = self.session.get(
                    source.manifest_url,
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                    headers=request_headers,
                )
                if manifest_response.status_code == requests.codes.not_modified:
                    # 第二步：远端直接返回 304 时，说明远端清单未变且本地也未发生轻量变化。
                    return ResourceCheckResult(
                        status=ResourceCheckStatus.UP_TO_DATE,
                        source=source,
                        remote_last_modified=manifest_response.headers.get("Last-Modified") or local_state.last_remote_last_modified,
                        remote_etag=manifest_response.headers.get("ETag") or local_state.last_remote_etag,
                        message="远端图片资源清单未更新",
                    )

                manifest_response.raise_for_status()
                remote_last_modified = manifest_response.headers.get("Last-Modified")
                remote_etag = manifest_response.headers.get("ETag")
                remote_version_unchanged = self._is_same_remote_version(
                    local_state,
                    source,
                    remote_last_modified,
                    remote_etag,
                )
                remote_manifest = ResourceManifest.from_dict(manifest_response.json())
                self._ensure_package_metadata(remote_manifest)

                # 第三步：若远端清单标识未变化，则先返回“远端已是最新”。
                # 本地是否存在删改，统一交给同步计划构建阶段复用一次完整对账结果判断。
                if remote_manifest.manifest_id == local_state.last_applied_manifest_id:
                    return ResourceCheckResult(
                        status=ResourceCheckStatus.UP_TO_DATE,
                        source=source,
                        remote_manifest=remote_manifest,
                        remote_last_modified=remote_last_modified,
                        remote_etag=remote_etag,
                        message="远端图片资源清单版本一致",
                    )

                if remote_version_unchanged:
                    # 若元数据命中但 manifest_id 未命中，则保守视为远端清单已变化。
                    # 这种情况理论上较少见，但继续走更新流程更安全。
                    log.info("远端图片资源元数据命中缓存，但 manifest_id 已变化，将按更新处理")

                # 第四步：走到这里说明资源清单版本已变化，交给上层继续规划同步动作。
                return ResourceCheckResult(
                    status=ResourceCheckStatus.UPDATE_AVAILABLE,
                    source=source,
                    remote_manifest=remote_manifest,
                    remote_last_modified=remote_last_modified,
                    remote_etag=remote_etag,
                    message="发现图片资源清单更新",
                )
            except requests.RequestException as exc:
                # 仅在网络访问失败时回退到下一个资源源。
                # 协议错误、清单校验错误和本地逻辑错误都应直接暴露，避免被误判成普通源切换。
                log.warning(f"检查资源源 {source.name} 失败，准备尝试下一个资源源: {exc}")

        # 第三步：全部候选源都失败时，统一返回错误状态给 UI 做后续提示。
        return ResourceCheckResult(
            status=ResourceCheckStatus.ERROR,
            message="所有图片资源源均检查失败",
        )

    def _iter_local_files(self) -> list[str]:
        """返回本地图片资源目录中的全部相对路径文件。

        返回:
            按稳定顺序排序后的本地相对路径文件列表。
        """
        if not self.assets_dir.exists():
            return []
        # 先扫描全部文件，再统一转为相对路径，便于与 manifest 直接比较。
        files = [path for path in self.assets_dir.rglob("*") if path.is_file()]
        return sorted(path.relative_to(self.assets_dir).as_posix() for path in files)

    def _build_local_snapshot(self) -> LocalImageSnapshot:
        """扫描本地图片目录，构建基于路径、大小和修改时间的轻量快照。

        返回:
            当前本地图片目录的轻量快照对象。
        """
        # 第一步：遍历当前本地图片目录中的全部文件，并按稳定顺序拼接轻量特征。
        hasher = hashlib.sha256()
        file_count = 0
        for relative_path in self._iter_local_files():
            local_path = self.assets_dir / relative_path
            stat_result = local_path.stat()
            hasher.update(f"{relative_path}\t{stat_result.st_size}\t{stat_result.st_mtime_ns}\n".encode("utf-8"))
            file_count += 1

        # 第二步：输出当前文件总数与摘要，供后续快速判断本地目录是否发生变化。
        return LocalImageSnapshot(
            file_count=file_count,
            snapshot_id=hasher.hexdigest(),
        )

    @staticmethod
    def _is_same_local_snapshot(state: ResourceSyncState, snapshot: LocalImageSnapshot) -> bool:
        """根据已缓存状态与当前轻量快照判断本地图片目录是否保持不变。

        参数:
            state: 本地已记录的资源同步状态。
            snapshot: 当前扫描得到的本地轻量快照。

        返回:
            若当前本地目录与上次同步后的轻量快照一致则返回 True，否则返回 False。
        """
        # 第一步：若历史状态中缺少任一轻量快照字段，则保守视为本地状态未知。
        if state.last_local_file_count is None or state.last_local_snapshot_id is None:
            return False

        # 第二步：同时比对文件总数与轻量摘要，避免仅凭单一字段误判。
        return (
            state.last_local_file_count == snapshot.file_count
            and state.last_local_snapshot_id == snapshot.snapshot_id
        )

    @staticmethod
    def _build_manifest_request_headers(
        state: ResourceSyncState,
        source: ResourceSource,
        *,
        local_snapshot_unchanged: bool,
    ) -> dict[str, str]:
        """为远端 manifest 请求构建条件请求头。

        参数:
            state: 本地已记录的资源同步状态。
            source: 当前准备检查的资源源。
            local_snapshot_unchanged: 当前本地轻量快照是否与上次同步后保持一致。

        返回:
            用于本次 manifest 请求的请求头字典。
        """
        # 第一步：只有本地目录未变化，且当前资源源与历史命中来源一致时，才复用远端缓存标记。
        if not local_snapshot_unchanged or state.last_source != source.name:
            return {}

        headers: dict[str, str] = {}
        # 第二步：优先附带 ETag，再补充 Last-Modified，尽量让远端直接返回 304。
        if state.last_remote_etag:
            headers["If-None-Match"] = state.last_remote_etag
        if state.last_remote_last_modified:
            headers["If-Modified-Since"] = state.last_remote_last_modified
        return headers

    def build_sync_plan(self, remote_manifest: ResourceManifest) -> ResourceSyncPlan:
        """根据远端清单生成同步计划。

        参数:
            remote_manifest: 远端返回的资源清单对象。

        返回:
            本轮资源同步计划对象。
        """
        # 第一步：整理远端条目映射和本地文件集合，准备进入逐项比对。
        remote_entries = {entry.path: entry for entry in remote_manifest.files}
        local_files = set(self._iter_local_files())
        plan = ResourceSyncPlan()

        # 第二步：逐项比较远端清单与本地文件，识别新增和内容变更。
        for relative_path, entry in remote_entries.items():
            local_path = self.assets_dir / relative_path
            if not local_path.exists():
                plan.files_to_add.append(entry)
                continue
            if self._calculate_sha256(local_path) != entry.sha256:
                plan.files_to_update.append(entry)

        # 第三步：本地只要存在“远端清单未记录”的图片，就统一记录为待删除文件。
        plan.files_to_delete = sorted(relative_path for relative_path in local_files if relative_path not in remote_entries)

        # 第四步：输出汇总日志，方便右侧日志栏和问题排查复用。
        log.debug(
            "图片资源清单比对完成：新增 %s，变更 %s，删除 %s",
            len(plan.files_to_add),
            len(plan.files_to_update),
            len(plan.files_to_delete),
        )
        return plan

    @staticmethod
    def _build_state_from_check_result(
        check_result: ResourceCheckResult,
        *,
        local_snapshot: LocalImageSnapshot,
    ) -> ResourceSyncState:
        """根据远端检查结果构建最新的本地资源同步状态对象。

        参数:
            check_result: 已完成的远端检查结果，必须包含资源源与远端清单。
            local_snapshot: 当前本地图片目录的轻量快照。

        返回:
            依据本次远端检查结果构建出的本地资源同步状态对象。
        """
        # 第一步：只有在拿到资源源和远端清单后，才能安全生成新的本地状态。
        if check_result.source is None or check_result.remote_manifest is None:
            raise ValueError("缺少远端资源源或清单，无法构建本地状态")

        # 第二步：统一复用同一套字段映射，避免多个调用点分别手写状态构造逻辑。
        return ResourceSyncState(
            last_applied_manifest_id=check_result.remote_manifest.manifest_id,
            last_remote_last_modified=check_result.remote_last_modified,
            last_remote_etag=check_result.remote_etag,
            last_source=check_result.source.name,
            last_local_file_count=local_snapshot.file_count,
            last_local_snapshot_id=local_snapshot.snapshot_id,
        )

    def accept_remote_state(self, check_result: ResourceCheckResult) -> ResourceSyncState:
        """在本地已与远端一致时，仅更新本地状态文件。

        参数:
            check_result: 本轮远端检查结果，必须包含 `source` 与 `remote_manifest`。

        返回:
            刷新后并已落盘的本地状态对象。
        """
        if check_result.source is None or check_result.remote_manifest is None:
            raise ValueError("缺少远端资源源或清单，无法写入本地状态")

        # 直接以远端最新清单刷新本地状态，避免下次重复提示同一份 manifest。
        state = self._build_state_from_check_result(
            check_result,
            local_snapshot=self._build_local_snapshot(),
        )
        self.save_state(state)
        return state

    def _download_resource_package(self, source: ResourceSource, package_entry: ResourcePackageEntry, target_path: Path) -> Path:
        """下载完整资源包，并在下载过程中完成整体哈希与大小校验。

        参数:
            source: 当前命中的资源源对象。
            package_entry: manifest 中声明的资源包元数据。
            target_path: 本地资源包落盘路径。

        返回:
            下载并校验完成后的资源包路径。
        """
        # 第一步：解析资源包下载地址并发起流式下载请求。
        package_url = self._resolve_package_url(source, package_entry.path)
        with self.session.get(package_url, timeout=DEFAULT_REQUEST_TIMEOUT, stream=True) as response:
            response.raise_for_status()

            # 第二步：边下载边计算哈希与字节数，避免下载后再二次遍历文件。
            target_path.parent.mkdir(parents=True, exist_ok=True)
            hasher = hashlib.sha256()
            total_bytes = 0
            with target_path.open("wb") as package_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    package_file.write(chunk)
                    hasher.update(chunk)
                    total_bytes += len(chunk)

        # 第三步：对照 manifest 元数据校验大小和哈希，确保整包完整可靠。
        if total_bytes != package_entry.size:
            raise ValueError(f"资源包大小校验失败: 期望 {package_entry.size}，实际 {total_bytes}")
        if hasher.hexdigest() != package_entry.sha256:
            raise ValueError("资源包哈希校验失败")
        return target_path

    def _extract_resource_package(self, package_path: Path, extract_dir: Path) -> Path:
        """在校验完成后，将 7z 资源包安全解压到临时目录。

        参数:
            package_path: 已下载完成的资源包路径。
            extract_dir: 解压目标目录。

        返回:
            解压完成后的目录路径。
        """
        # 解压安全策略统一下沉到 utils.archive_7z 模块，这里只保留服务层入口。
        return extract_7z_archive(package_path, extract_dir)

    @staticmethod
    def _refresh_runtime_image_cache() -> None:
        """同步完成后刷新运行时图片缓存。"""
        try:
            from module.automation import auto

            # 资源文件落盘后主动清空运行时缓存，避免脚本继续使用旧图片。
            auto.clear_img_cache()
        except Exception as exc:
            # 刷新缓存失败不应阻塞同步主流程，因此仅记录调试日志。
            log.debug(f"刷新运行时图片缓存时出现非阻塞错误: {exc}")

    def apply_sync_plan(
        self,
        *,
        check_result: ResourceCheckResult,
        sync_plan: ResourceSyncPlan,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> ResourceApplyResult:
        """应用资源同步计划到本地图片目录。

        参数:
            check_result: 已完成的远端检查结果，必须包含源信息与清单对象。
            sync_plan: 本轮清单比对后生成的同步计划。
            progress_callback: 可选的进度回调，参数为当前步骤和总步骤数。

        返回:
            本轮资源同步应用结果。
        """
        if check_result.source is None or check_result.remote_manifest is None:
            raise ValueError("缺少远端资源源或清单，无法应用同步计划")

        # 第一步：整理下载条目和删除目标，为应用阶段做准备。
        download_entries = sync_plan.download_entries
        has_download_entries = bool(download_entries)
        deletion_candidates = list(sync_plan.files_to_delete)
        package_entry = self._ensure_package_metadata(check_result.remote_manifest) if has_download_entries else None

        # 第二步：仅在存在新增或变更文件时，才准备资源包下载与解压环境。
        if has_download_entries:
            log.info("开始图片资源更新")
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.assets_dir.mkdir(parents=True, exist_ok=True)
        else:
            log.info("当前同步计划仅包含删除项，跳过图片资源包下载与解压")

        total_steps = max(1, (2 if has_download_entries else 0) + len(download_entries) + len(deletion_candidates))
        current_step = 0

        try:
            # 第三步：仅在存在新增或变更文件时，才下载并解压完整资源包。
            if has_download_entries and package_entry is not None:
                package_download_path = self.temp_dir / Path(package_entry.path).name
                # 资源包先下载到 update_temp 根目录，再解压到 update_temp/extracted。
                extract_dir = self.temp_dir / "extracted"

                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
                log.info("正在下载图片资源包")
                self._download_resource_package(check_result.source, package_entry, package_download_path)

                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
                log.info("正在解压图片资源包")
                self._extract_resource_package(package_download_path, extract_dir)
            else:
                extract_dir = None

            # 第四步：按同步计划从解压目录复制新增和变更文件到本地资源目录。
            downloaded_count = 0
            for entry in download_entries:
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
                if extract_dir is None:
                    raise ValueError("存在待下载文件时未准备资源包解压目录")
                extracted_path = extract_dir / entry.path
                if not extracted_path.is_file():
                    raise ValueError(f"资源包中缺少清单要求的文件: {entry.path}")
                if self._calculate_sha256(extracted_path) != entry.sha256:
                    raise ValueError(f"资源包内文件校验失败: {entry.path}")

                target_path = self.assets_dir / entry.path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(extracted_path, target_path)
                downloaded_count += 1

            # 第五步：删除所有已不在远端清单中的本地图片文件。
            deleted_count = 0
            if deletion_candidates:
                log.info("正在清理本地多余图片资源")
            for relative_path in deletion_candidates:
                current_step += 1
                if progress_callback:
                    progress_callback(current_step, total_steps)
                target_path = self.assets_dir / relative_path
                if target_path.exists():
                    target_path.unlink()
                    deleted_count += 1

            # 第六步：刷新本地状态文件与运行时缓存，为下一轮检查提供新基线。
            state = self._build_state_from_check_result(
                check_result,
                local_snapshot=self._build_local_snapshot(),
            )
            self.save_state(state)
            self._refresh_runtime_image_cache()
            log.info("图片资源同步完成：更新 %s，删除 %s", downloaded_count, deleted_count)
            return ResourceApplyResult(
                downloaded_count=downloaded_count,
                deleted_count=deleted_count,
                state=state,
            )
        finally:
            # 第七步：只有实际使用过资源包流程时，才清理临时目录。
            if has_download_entries:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
