"""资源同步界面编排协调类。"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QLabel
from qfluentwidgets import InfoBarPosition, isDarkTheme

from app.card.messagebox_custom import BaseInfoBar, MessageBoxConfirm
from module.config import cfg
from module.logger import log
from module.resource_sync import (
    ResourceApplyResult,
    ResourceCheckPayload,
    ResourceCheckResult,
    ResourceCheckStatus,
    ResourceSyncPlan,
    ResourceSyncService,
    ResourceSyncWorker,
    ResourceWorkerMode,
)
from module.update.check_update import (
    UpdateStatus,
    check_update,
)

# start 自动任务模式下，等待资源更新确认的超时时间。
_RESOURCE_SYNC_CONFIRM_TIMEOUT_MS = 5 * 60 * 1000


class ResourceSyncCoordinator(QObject):
    """负责主窗口资源同步的 UI 编排、线程调度与启动阶段衔接。"""

    def __init__(
        self,
        *,
        window: Any,
        status_label: QLabel,
        startup_argv: list[str],
        continue_startup: Callable[[], None],
        set_progress: Callable[[int], None],
        has_running_script: Callable[[], bool],
        service: ResourceSyncService | None = None,
    ) -> None:
        """初始化资源同步协调类。

        参数:
            window: 主窗口对象。
            status_label: 展示“有可更新图片资源”的标签对象。
            startup_argv: 程序启动时收到的命令行参数列表。
            continue_startup: 资源同步后后续的回调
            set_progress: 更新主窗口进度环的回调，参数为 0 到 100 的进度值。
            has_running_script: 判断主脚本当前是否仍在运行中的回调。
            service: 可选的资源同步服务对象；未传入时内部创建默认实例。
        """
        super().__init__(window)
        # 第一阶段：缓存主窗口接缝对象与外部注入回调。
        self._window = window
        self._status_label = status_label
        self._continue_startup = continue_startup
        self._set_progress = set_progress
        self._has_running_script_callback = has_running_script

        # 第二阶段：初始化资源同步编排过程中需要持续维护的状态。
        self._resource_sync_service = service or ResourceSyncService()
        self._resource_sync_worker: ResourceSyncWorker | None = None
        self._resource_sync_worker_context: str | None = None
        self._pending_resource_sync_apply_request: dict[str, Any] | None = None
        self._startup_argv = list(startup_argv)
        self._startup_sequence_continued = False
        self._resource_sync_status_kind = "hidden"

    def start_startup_check(self) -> None:
        """触发启动阶段的资源同步门禁检查。"""
        # 对外暴露的启动入口
        self._start_resource_sync_gate_check(trigger="startup")

    def start_manual_resource_sync_check(self) -> None:
        """由设置页触发的手动资源同步检查入口。"""
        # 第一步：如果当前已有资源任务在跑，则直接提示用户稍后再试。
        if self._resource_sync_worker is not None and self._resource_sync_worker.isRunning():
            self._show_resource_sync_infobar(
                level="warning",
                title=self._window.tr("图片资源任务进行中"),
                content=self._window.tr("当前已有图片资源检查或同步任务正在运行，请稍后再试"),
            )
            return

        # 第二步：手动入口也先走软件更新门禁，确保与启动入口共用同一套版本规则。
        log.debug("开始手动检查图片资源更新前的软件版本状态")
        self._start_resource_sync_gate_check(trigger="manual")

    def apply_status_style(self, is_dark: bool) -> None:
        """根据主题刷新标题栏资源状态标签样式。

        参数:
            is_dark: 当前是否为深色主题。
        """
        # 对外暴露一个轻量刷新入口，供主窗口在主题切换时调用。
        self._apply_resource_sync_status_style(is_dark)

    def refresh_status_text(self) -> None:
        """根据当前状态重新设置标题栏资源状态文本。"""
        # 语言刷新时重新走一遍状态渲染，确保文案与当前翻译一致。
        self._set_resource_sync_status(self._resource_sync_status_kind)

    def _continue_startup_sequence_once(self) -> None:
        """在资源同步阶段结束后继续执行原有启动链路，且只执行一次。"""
        if self._startup_sequence_continued:
            return

        # 先标记启动链路已恢复，防止多条异步分支重复调用。
        self._startup_sequence_continued = True

        # 再按原顺序恢复公告板、命令行启动参数和系统托盘初始化。
        self._continue_startup()

    def _start_resource_sync_gate_check(self, *, trigger: str) -> None:
        """在资源同步前复用既有软件更新检查，以补充版本门禁。

        参数:
            trigger: 当前触发场景，仅支持 startup 或 manual。
        """
        # 第一步：读取软件更新提示开关，并为当前场景生成对应的门禁提示策略。
        check_update_enabled = cfg.get_value("check_update", True)
        if trigger == "startup":
            show_success = check_update_enabled
            show_failure = check_update_enabled
            show_update_dialog = check_update_enabled
            notify_user_when_blocked = False
        elif trigger == "manual":
            show_success = False
            show_failure = False
            show_update_dialog = check_update_enabled
            notify_user_when_blocked = True
        else:
            raise ValueError(f"不支持的资源同步门禁触发场景: {trigger}")
        trigger_text = self._window.tr("启动阶段") if trigger == "startup" else self._window.tr("手动资源同步")
        log.debug(f"{trigger_text}将先检查软件版本更新状态，再决定是否继续图片资源同步")

        # 第二步：调用既有软件更新检查入口，并把资源同步回调附加进去。
        check_update(
            self._window,
            flag=False,
            on_finished=partial(
                self._on_resource_sync_gate_check_finished,
                trigger=trigger,
                notify_user_when_blocked=notify_user_when_blocked,
            ),
            show_success=show_success,
            show_failure=show_failure,
            show_update_dialog=show_update_dialog,
        )

    def _is_resource_sync_version_ready(
        self,
        status: UpdateStatus,
        update_thread: Any,
        *,
        notify_user: bool,
    ) -> bool:
        """判断当前软件版本是否允许继续执行图片资源同步。

        参数:
            status: 软件更新检查完成后的状态枚举。
            update_thread: 本轮更新检查使用的线程对象。
            notify_user: 版本门禁阻断时是否额外提示用户。

        返回:
            若允许继续执行资源同步则返回 True，否则返回 False。
        """
        # 第一步：若软件更新检查失败，则直接阻断资源同步，避免在版本状态未知时覆盖资源。
        latest_version = update_thread.new_version or self._window.tr("未知版本")
        if status is UpdateStatus.FAILURE:
            log.warning("无法确认当前软件是否为最新版本，已跳过图片资源同步")
            if notify_user:
                self._show_resource_sync_infobar(
                    level="warning",
                    title=self._window.tr("无法同步图片资源"),
                    content=self._window.tr("软件版本检查失败，暂时无法确认当前版本是否为最新版本"),
                )
            return False

        # 第二步：若本地软件版本尚未追平最新版本，则阻断资源同步并给出原因。
        if not getattr(update_thread, "is_current_version_latest", False):
            log.info(f"当前软件版本 {cfg.version} 与最新版本 {latest_version} 不一致，已跳过图片资源同步")
            if notify_user:
                self._show_resource_sync_infobar(
                    level="warning",
                    title=self._window.tr("无法同步图片资源"),
                    content=self._window.tr("当前软件版本与最新版本不一致，请先更新软件后再同步图片资源"),
                )
            return False

        return True

    def _on_resource_sync_gate_check_finished(
        self,
        status: UpdateStatus,
        update_thread: Any,
        *,
        trigger: str,
        notify_user_when_blocked: bool,
    ) -> None:
        """在资源同步前的软件更新检查结束后，决定后续资源同步动作。

        参数:
            status: 软件更新检查完成后的状态枚举。
            update_thread: 本轮更新检查使用的线程对象。
            trigger: 当前资源同步触发场景。
            notify_user_when_blocked: 当前场景下，资源同步被门禁拦截时是否额外提示用户。
        """
        # 第一步：先判断版本门禁是否放行资源同步。
        if not self._is_resource_sync_version_ready(
            status,
            update_thread,
            notify_user=notify_user_when_blocked,
        ):
            if trigger == "startup":
                self._continue_startup_sequence_once()
            return

        # 第二步：启动场景放行后继续自动/仅检查流程；手动场景则进入检查并规划模式。
        if trigger == "startup":
            self._start_resource_sync_on_startup()
            return

        # 第三步：手动入口通过门禁后，直接进入“检查并规划”模式，由后续确认框决定是否应用。
        log.debug("软件版本校验通过，开始手动检查图片资源更新")
        self._start_resource_sync_worker(
            mode=ResourceWorkerMode.CHECK_AND_PLAN,
            context="manual",
        )

    def _start_resource_sync_on_startup(self) -> None:
        """在启动时按配置决定资源同步检查策略。"""
        if cfg.get_value("image_resource_sync", True):
            # 自动同步开启时，启动阶段直接进入“检查并规划”模式。
            log.debug("已启用图片资源自动同步，启动时将先检查远端图片资源清单")
            started = self._start_resource_sync_worker(
                mode=ResourceWorkerMode.CHECK_AND_PLAN,
                context="startup_auto",
            )
            if not started:
                self._continue_startup_sequence_once()
            return

        # 自动同步关闭时，仅检查清单更新状态，不自动触发下载应用。
        log.debug("图片资源自动同步已关闭，启动时仅检查远端图片资源清单是否更新")
        self._start_resource_sync_worker(
            mode=ResourceWorkerMode.CHECK_ONLY,
            context="startup_check_only",
        )
        self._continue_startup_sequence_once()

    def _start_resource_sync_worker(
        self,
        *,
        mode: ResourceWorkerMode,
        context: str,
        check_result: ResourceCheckResult | None = None,
        sync_plan: ResourceSyncPlan | None = None,
    ) -> bool:
        """启动资源同步工作线程，并统一连接信号。

        参数:
            mode: 当前资源同步线程执行模式。
            context: 当前线程对应的业务上下文标记。
            check_result: 应用阶段需要复用的检查结果。
            sync_plan: 应用阶段需要复用的同步计划。

        返回:
            若成功启动新线程则返回 True；若已有线程运行则返回 False。
        """
        # 第一步：避免重复启动资源同步线程，保护后台状态机的一致性。
        if self._resource_sync_worker is not None and self._resource_sync_worker.isRunning():
            return False

        # 第二步：读取当前资源源偏好并构造工作线程对象。
        preferred_source = cfg.get_value("image_resource_source", "Auto") or "Auto"
        worker = ResourceSyncWorker(
            service=self._resource_sync_service,
            mode=mode,
            preferred_source=preferred_source,
            check_result=check_result,
            sync_plan=sync_plan,
            parent=self._window,
        )

        # 第三步：缓存线程与上下文，并统一连接进度、成功和失败信号。
        self._resource_sync_worker = worker
        self._resource_sync_worker_context = context
        worker.progressChanged.connect(self._on_resource_sync_progress_changed)
        worker.checkFinished.connect(self._on_resource_sync_check_finished)
        worker.applyFinished.connect(self._on_resource_sync_apply_finished)
        worker.failed.connect(self._on_resource_sync_failed)
        worker.finished.connect(self._on_resource_sync_worker_finished)
        worker.start()
        return True

    def _start_pending_resource_sync_apply(self) -> tuple[bool, dict[str, Any] | None]:
        """尝试接力启动挂起的资源同步应用阶段。

        返回:
            一个二元组；第一个值表示是否成功启动应用阶段，
            第二个值表示本轮是否实际取到了挂起请求。
        """
        # 第一步：若当前没有挂起的应用请求，则直接返回“无需处理”。
        pending_request = self._pending_resource_sync_apply_request
        if pending_request is None:
            return False, None

        # 第二步：先取出挂起请求，再尝试按原参数启动应用阶段。
        self._pending_resource_sync_apply_request = None
        started = self._start_resource_sync_worker(**pending_request)

        # 第三步：若启动失败，则恢复挂起请求，避免请求被静默吞掉。
        if not started:
            self._pending_resource_sync_apply_request = pending_request
        return started, pending_request

    def _on_resource_sync_progress_changed(self, value: int) -> None:
        """将资源同步进度映射到界面进度环。

        参数:
            value: 后台线程上报的 0 到 100 进度值。
        """
        # 统一复用主窗口现有进度环组件
        # 检测远端清单与本地差异时不显示进度环，只在真正下载、解压和应用资源包时显示。
        if self._resource_sync_worker_context in {"startup_auto", "startup_check_only", "manual"}:
            self._window.progress_ring.hide()
            return
        self._set_progress(value)

    def _on_resource_sync_check_finished(self, payload: ResourceCheckPayload) -> None:
        """处理资源同步检查结果，并决定是否继续提示或应用更新。

        参数:
            payload: 后台检查阶段返回的检查结果与可选同步计划。
        """
        # 第一步：拆出当前上下文、检查结果和同步计划，便于后续分支复用。
        context = self._resource_sync_worker_context or ""
        check_result = payload.check_result
        sync_plan = payload.sync_plan

        # 第二步：先处理未配置、检查失败和已是最新这三类无需应用同步的分支。
        if check_result.status is ResourceCheckStatus.UNCONFIGURED:
            log.debug(check_result.message)
            if context == "manual":
                self._show_resource_sync_infobar(
                    level="warning",
                    title=self._window.tr("图片资源未配置"),
                    content=check_result.message,
                )
            if context.startswith("startup_"):
                self._continue_startup_sequence_once()
            return

        if check_result.status is ResourceCheckStatus.ERROR:
            log.warning(check_result.message)
            self._set_resource_sync_status("hidden")
            if context == "manual":
                self._show_resource_sync_infobar(
                    level="error",
                    title=self._window.tr("图片资源检查失败"),
                    content=check_result.message,
                )
            if context.startswith("startup_"):
                self._continue_startup_sequence_once()
            return

        if check_result.status is ResourceCheckStatus.UP_TO_DATE:
            # 当本轮拿到了远端 manifest 正文时，说明这次已经做过完整对账。
            # 即使最终结果仍是“无需更新”，也要刷新本地轻量快照基线，
            # 避免后续每次启动都因为旧快照未更新而重复下载远端清单。
            if sync_plan is not None and check_result.remote_manifest is not None:
                self._resource_sync_service.accept_remote_state(check_result)
            log.debug("本地图片资源已与远端清单保持一致")
            self._set_resource_sync_status("hidden")
            if context == "manual":
                self._show_resource_sync_infobar(
                    level="success",
                    title=self._window.tr("图片资源已是最新"),
                    content=self._window.tr("本地图片资源与远端清单一致"),
                )
            if context.startswith("startup_"):
                self._continue_startup_sequence_once()
            return

        # 第三步：走到这里时说明检查结果已经进入“可继续同步”的状态，因此同步计划理论上必然存在。
        if sync_plan is None:
            raise ValueError("资源同步检查结果缺少同步计划，无法继续处理")

        if not sync_plan.has_changes:
            log.debug("远端图片资源清单已更新，但本地无需下载或删除图片，正在刷新状态文件")
            self._resource_sync_service.accept_remote_state(check_result)
            self._set_resource_sync_status("synced")
            if context == "manual":
                self._show_resource_sync_infobar(
                    level="success",
                    title=self._window.tr("图片资源状态已刷新"),
                    content=self._window.tr("远端清单已更新，但本地图片无需重新下载"),
                )
            if context == "startup_auto":
                self._continue_startup_sequence_once()
            return

        # 第四步：针对仍有变化的计划，结合上下文决定仅提示、延后还是立即确认应用。
        summary_text = self._format_resource_sync_plan_summary(sync_plan)
        if context == "startup_check_only":
            self._set_resource_sync_status("update_available")
            log.debug(f"检测到图片资源更新，自动同步已关闭：{summary_text}")
            return

        if context == "manual" and self._has_running_script_callback():
            self._set_resource_sync_status("update_available")
            log.debug(f"当前有任务运行，仅完成图片资源检查：{summary_text}")
            self._show_resource_sync_infobar(
                level="warning",
                title=self._window.tr("检测到图片资源更新"),
                content=self._window.tr("当前有任务运行，请稍后更新资源"),
            )
            return

        if not self._confirm_apply_resource_sync(sync_plan, startup_context=context == "startup_auto"):
            self._set_resource_sync_status("update_available")
            log.debug(f"用户跳过了本次图片资源同步：{summary_text}")
            if context == "startup_auto":
                self._continue_startup_sequence_once()
            return

        # 第五步：用户确认后，把应用阶段请求挂起，等待当前检查线程结束后再接力启动。
        self._pending_resource_sync_apply_request = {
            "mode": ResourceWorkerMode.APPLY_PLAN,
            "context": "startup_apply" if context == "startup_auto" else "manual_apply",
            "check_result": check_result,
            "sync_plan": sync_plan,
        }

    def _on_resource_sync_apply_finished(self, apply_result: ResourceApplyResult) -> None:
        """处理资源同步应用完成后的收尾逻辑。

        参数:
            apply_result: 资源同步应用阶段返回的结果对象。
        """
        # 第一步：先刷新标题栏状态并记录本轮下载/删除统计。
        context = self._resource_sync_worker_context or ""
        self._set_resource_sync_status("synced")
        log.debug(
            "图片资源同步已完成：下载 %s，删除 %s",
            apply_result.downloaded_count,
            apply_result.deleted_count,
        )

        # 第二步：再按上下文决定是否弹成功提示，以及是否继续启动链路。
        if context == "manual_apply":
            self._show_resource_sync_infobar(
                level="success",
                title=self._window.tr("图片资源已同步"),
                content=self._window.tr("本地图片资源已经更新完成"),
            )

        if context == "startup_apply":
            self._continue_startup_sequence_once()

    def _on_resource_sync_failed(self, message: str) -> None:
        """处理资源同步线程抛出的异常。

        参数:
            message: 后台线程抛出的中文错误信息。
        """
        # 第一步：先根据当前上下文刷新标题栏状态并记录异常日志。
        context = self._resource_sync_worker_context or ""
        self._set_resource_sync_status("update_available" if context.endswith("apply") else "hidden")
        log.error(f"图片资源同步流程异常结束：{message}")

        # 第二步：手动场景需要直接告知用户失败原因；启动场景则继续放行原启动链路。
        if context in {"manual", "manual_apply"}:
            self._show_resource_sync_infobar(
                level="error",
                title=self._window.tr("图片资源同步失败"),
                content=message,
            )

        if context in {"startup_auto", "startup_apply"}:
            self._continue_startup_sequence_once()

    def _on_resource_sync_worker_finished(self) -> None:
        """在线程退出后清理状态，并在需要时接力启动应用阶段。"""
        # 第一步：暂存当前线程对象和挂起的应用请求，便于清理后继续处理。
        finished_worker = self._resource_sync_worker
        pending_request = self._pending_resource_sync_apply_request

        if finished_worker is not None:
            finished_worker.deleteLater()

        # 第二步：重置协调类上的线程状态引用，避免下一轮启动误判。
        self._resource_sync_worker = None
        self._resource_sync_worker_context = None

        # 第三步：若有挂起的应用请求，则在线程真正结束后接力启动应用阶段。
        if pending_request is not None:
            self._pending_resource_sync_apply_request = pending_request
            started, resumed_request = self._start_pending_resource_sync_apply()
            if not started and resumed_request is not None and resumed_request["context"] == "startup_apply":
                self._continue_startup_sequence_once()
            return

        self._pending_resource_sync_apply_request = None

        # 第四步：没有后续任务时，稍后隐藏进度环，避免界面闪烁。
        QTimer.singleShot(800, self._window.progress_ring.hide)

    def _is_auto_task_start(self, argv: list[str]) -> bool:
        """判断本次启动是否由 start 命令触发。

        参数:
            argv: 启动程序时收到的命令行参数列表。

        返回:
            若包含 start 命令则返回 True，否则返回 False。
        """
        # start 模式下需要给资源确认框附加超时跳过策略。
        return "start" in argv[1:]

    def _format_resource_sync_plan_summary(self, sync_plan: ResourceSyncPlan) -> str:
        """生成人类可读的同步计划摘要，用于日志和提示。

        参数:
            sync_plan: 本轮资源同步计划对象。

        返回:
            用于日志和弹窗展示的中文摘要文本。
        """
        # 将三类变化压缩成一行摘要，方便日志栏和确认框复用。
        return self._window.tr(
            "新增 {add_count} 张，变更 {update_count} 张，删除 {delete_count} 张"
        ).format(
            add_count=len(sync_plan.files_to_add),
            update_count=len(sync_plan.files_to_update),
            delete_count=len(sync_plan.files_to_delete),
        )

    def _confirm_apply_resource_sync(self, sync_plan: ResourceSyncPlan, *, startup_context: bool) -> bool:
        """提示用户是否立即应用检测到的图片资源更新。

        参数:
            sync_plan: 本轮资源同步计划对象。
            startup_context: 当前确认是否发生在启动阶段。

        返回:
            用户确认应用时返回 True，否则返回 False。
        """
        # 第一步：先拼接同步计划摘要，生成确认框正文。
        content = self._window.tr(
            "{summary}\n是否立即同步？"
        ).format(summary=self._format_resource_sync_plan_summary(sync_plan))

        # 第二步：start 自动任务模式下追加超时提示，避免阻塞无人值守启动。
        if startup_context and self._is_auto_task_start(self._startup_argv):
            content += self._window.tr("\n当前为 start 自动任务模式，5 分钟内未选择将默认跳过本次更新。")

        message_box = MessageBoxConfirm(
            self._window.tr("检测到图片资源更新"),
            content,
            self._window.window(),
        )

        # 第三步：仅在 start 自动任务模式下安装超时自动拒绝逻辑。
        timeout_timer = None
        if startup_context and self._is_auto_task_start(self._startup_argv):
            timeout_timer = QTimer(message_box)
            timeout_timer.setSingleShot(True)

            def _reject_on_timeout() -> None:
                # 自动任务模式下不让确认框无限阻塞启动流程，超时后按“跳过同步”处理。
                if message_box.isVisible():
                    log.info("start 自动任务模式下等待图片资源更新确认超时 5 分钟，默认跳过本次同步")
                    message_box.reject()

            timeout_timer.timeout.connect(_reject_on_timeout)
            timeout_timer.start(_RESOURCE_SYNC_CONFIRM_TIMEOUT_MS)

        # 第四步：执行确认框，并在退出前清理可能存在的超时计时器。
        accepted = bool(message_box.exec())
        if timeout_timer is not None:
            timeout_timer.stop()
        return accepted

    def _show_resource_sync_infobar(self, *, level: str, title: str, content: str) -> None:
        """统一弹出资源同步相关提示，保持提示风格一致。

        参数:
            level: 提示等级，可选 info、success、warning、error。
            title: 提示标题文本。
            content: 提示正文文本。
        """
        # 先根据等级选出对应的 InfoBar 工厂，再用统一参数弹出提示。
        infobar_factory = {
            "info": BaseInfoBar.info,
            "success": BaseInfoBar.success,
            "warning": BaseInfoBar.warning,
            "error": BaseInfoBar.error,
        }.get(level, BaseInfoBar.info)
        infobar_factory(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self._window,
        )

    def _resolve_resource_sync_status_presentation(self, is_dark: bool) -> tuple[str | None, str | None]:
        """解析当前标题栏资源状态需要展示的文案与颜色。

        参数:
            is_dark: 当前是否为深色主题。

        返回:
            一个二元组；第一个值为标题栏文案，第二个值为对应文字颜色。
            若当前状态无需展示，则两个值都返回 None。
        """
        # 第一步：仅在“检测到更新”状态下返回标题栏展示内容，其余状态统一视为隐藏。
        if self._resource_sync_status_kind != "update_available":
            return None, None

        # 第二步：根据当前主题为同一状态挑选对应的高亮文字颜色。
        text = self._window.tr("检测到图片资源更新")
        text_color = "#f87171" if is_dark else "#dc2626"
        return text, text_color

    def _set_resource_sync_status(self, status_kind: str) -> None:
        """更新标题栏中的资源同步状态标记。

        参数:
            status_kind: 状态标记类型，可选 hidden、update_available 或 synced。
        """
        # 第一步：若任务已完成，则恢复正常标题栏，仅记录日志而不再显示“资源已同步”标签。
        if status_kind == "synced":
            log.info("图片资源同步任务已完成")
            status_kind = "hidden"

        # 第二步：缓存当前状态类型，便于主题切换和界面翻译时重绘。
        self._resource_sync_status_kind = status_kind
        status_text, _ = self._resolve_resource_sync_status_presentation(isDarkTheme())
        if status_text is None:
            self._status_label.hide()
            return

        # 第三步：根据当前状态解析结果更新标题栏文案。
        self._status_label.setText(status_text)

        # 第四步：刷新样式并显示标记。
        self._apply_resource_sync_status_style(isDarkTheme())
        self._status_label.adjustSize()
        self._status_label.show()

    def _apply_resource_sync_status_style(self, is_dark: bool) -> None:
        """根据当前主题刷新标题栏资源状态标记的配色。

        参数:
            is_dark: 当前是否为深色主题。
        """
        # 第一步：若当前状态无需展示，则直接收起标签，避免残留旧样式。
        _, text_color = self._resolve_resource_sync_status_presentation(is_dark)
        if text_color is None:
            self._status_label.hide()
            return

        # 第二步：统一更新标题栏状态标记的字号和前景色。
        self._status_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: transparent;
                border: none;
                color: {text_color};
                font-size: 12px;
                font-weight: 600;
                padding: 0 2px;
            }}
            """
        )
