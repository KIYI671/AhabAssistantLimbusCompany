"""资源同步后台工作线程。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QThread, Signal

from module.resource_sync.service import (
    ResourceCheckResult,
    ResourceCheckStatus,
    ResourceSyncPlan,
    ResourceSyncService,
)


class ResourceWorkerMode(Enum):
    """声明资源同步工作线程的执行模式。"""

    CHECK_ONLY = "check_only"
    CHECK_AND_PLAN = "check_and_plan"
    APPLY_PLAN = "apply_plan"


@dataclass(slots=True)
class ResourceCheckPayload:
    """承载检查阶段返回给 UI 的完整结果。"""

    # 远端检查结果，包含资源源、清单版本与状态说明。
    check_result: ResourceCheckResult
    # 同步计划，仅在检查并规划模式下、且远端存在清单时生成。
    sync_plan: ResourceSyncPlan | None = None


class ResourceSyncWorker(QThread):
    """在后台线程中执行图片资源检查与同步，避免阻塞主界面。"""

    # 检查阶段完成后回传检查结果与可选同步计划。
    checkFinished = Signal(object)
    # 应用阶段完成后回传同步结果。
    applyFinished = Signal(object)
    # 任一步骤失败时回传可直接展示的中文错误信息。
    failed = Signal(str)
    # 统一向外回传 0 到 100 的进度值。
    progressChanged = Signal(int)

    def __init__(
        self,
        *,
        service: ResourceSyncService,
        mode: ResourceWorkerMode,
        preferred_source: str,
        check_result: ResourceCheckResult | None = None,
        sync_plan: ResourceSyncPlan | None = None,
        parent=None,
    ):
        """初始化资源同步后台线程，并缓存本次执行所需的上下文参数。

        参数:
            service: 资源同步服务对象，负责具体的网络和文件操作。
            mode: 当前线程的执行模式。
            preferred_source: 用户配置的优先资源源。
            check_result: 应用阶段需要复用的远端检查结果。
            sync_plan: 应用阶段需要复用的同步计划。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        # 持有服务对象，所有网络与文件操作都交给服务层完成。
        self.service = service
        # 当前线程执行模式。
        self.mode = mode
        # 优先资源源配置，通常来自用户设置。
        self.preferred_source = preferred_source
        # 应用阶段需要使用的检查结果。
        self.check_result = check_result
        # 应用阶段需要使用的同步计划。
        self.sync_plan = sync_plan
        # 记录最近一次已发出的进度，避免重复发射相同值。
        self._last_progress: int | None = None

    def _emit_progress(self, value: int) -> None:
        """仅在进度值发生变化时发射信号，减少 UI 刷新噪声。

        参数:
            value: 待发射的原始进度值。
        """
        # 先把外部传入值钳制到 0 到 100，保证 UI 侧收到的进度合法。
        normalized_value = max(0, min(100, int(value)))
        if normalized_value == self._last_progress:
            return
        # 仅在值变化时发射，避免标题栏和日志栏重复刷新。
        self._last_progress = normalized_value
        self.progressChanged.emit(normalized_value)

    @staticmethod
    def _map_apply_progress(current_step: int, total_steps: int) -> int:
        """将服务层的下载进度映射到 30 到 100 的应用阶段区间。

        参数:
            current_step: 当前已完成步骤数。
            total_steps: 本轮应用阶段的总步骤数。

        返回:
            映射后的 UI 进度值。
        """
        if total_steps <= 0:
            return 100
        ratio = current_step / total_steps
        return 30 + round(ratio * 70)

    def _run_check(self, *, emit_mid_progress: bool) -> None:
        """执行资源检查阶段，并按需要补充中段进度更新。

        参数:
            emit_mid_progress: 是否在远端清单检查完成后立即上报一次中段进度。
        """
        # 第一步：读取本地状态并完成远端清单检查。
        local_state = self.service.load_state()
        self._emit_progress(5)
        check_result = self.service.check_for_updates(self.preferred_source, state=local_state)
        if emit_mid_progress:
            self._emit_progress(15)

        # 第二步：若已拿到远端清单，则继续构建同步计划，并复用该计划识别本地漂移。
        sync_plan = self._build_sync_plan_from_check_result(check_result)

        # 第三步：将检查结果和可选计划一起回传给 UI 层做后续决策。
        self._emit_progress(30)
        self.checkFinished.emit(
            ResourceCheckPayload(
                check_result=check_result,
                sync_plan=sync_plan,
            )
        )

    def _build_sync_plan_from_check_result(self, check_result: ResourceCheckResult) -> ResourceSyncPlan | None:
        """根据检查结果决定是否继续生成本地同步计划。

        参数:
            check_result: 远端检查阶段返回的结果对象。

        返回:
            若当前结果携带远端清单则返回同步计划，否则返回 None。
        """
        # 第一步：只有在检查结果里拿到了远端 manifest，才有条件继续比对本地文件。
        if check_result.remote_manifest is None:
            return None

        # 第二步：对照远端清单扫描本地图片状态，识别新增、变更与删除项。
        sync_plan = self.service.build_sync_plan(check_result.remote_manifest)

        # 第三步：若远端清单未变化但本地文件已漂移，则提升为“可更新”状态。
        if check_result.status is ResourceCheckStatus.UP_TO_DATE and sync_plan.has_changes:
            check_result.status = ResourceCheckStatus.UPDATE_AVAILABLE
            check_result.message = "本地图片资源与远端清单不一致"
        return sync_plan

    def _run_apply_plan(self) -> None:
        """执行同步计划应用模式。"""
        if self.check_result is None or self.sync_plan is None:
            raise ValueError("应用图片资源同步前缺少检查结果或同步计划")

        # 第一步：切换到应用阶段进度区间，并调用服务层执行真正的同步。
        self._emit_progress(30)
        apply_result = self.service.apply_sync_plan(
            check_result=self.check_result,
            sync_plan=self.sync_plan,
            progress_callback=lambda current, total: self._emit_progress(self._map_apply_progress(current, total)),
        )
        # 第二步：应用成功后发出 100% 进度和最终结果。
        self._emit_progress(100)
        self.applyFinished.emit(apply_result)

    def run(self) -> None:
        """根据模式分派后台任务，并将异常转换为统一错误信号。"""
        try:
            # 根据构造时指定的模式进入对应分支，保证线程职责单一明确。
            if self.mode is ResourceWorkerMode.CHECK_ONLY:
                self._run_check(emit_mid_progress=False)
            elif self.mode is ResourceWorkerMode.CHECK_AND_PLAN:
                self._run_check(emit_mid_progress=True)
            elif self.mode is ResourceWorkerMode.APPLY_PLAN:
                self._run_apply_plan()
            else:
                raise ValueError(f"不支持的资源同步工作模式: {self.mode}")
        except Exception as exc:
            # 统一把异常转成失败信号，交由界面层决定如何提示用户。
            self.failed.emit(str(exc))
