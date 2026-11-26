import sys
from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QDialog, QTextEdit
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    FlyoutViewBase,
    PopUpAniStackedWidget,
    PrimaryPushButton,
    PushButton,
    TextEdit,
    ToolTipFilter,
    ToolTipPosition,
    TransparentToolButton,
    qconfig,
    setCustomStyleSheet,
)

from app import mediator
from app.base_combination import *
from app.base_tools import *
from app.common.ui_config import get_log_text_edit_qss, set_border_style
from app.language_manager import LanguageManager
from app.page_card import PageMirror, PageSetWindows
from app.task_queue.queue_list import schedule_title
from app.task_queue.queue_panel import WINDOW_SETTINGS_ID, TaskQueuePanel
from app.task_queue.task_pages import DailyTaskPage, EnkephalinTaskPage, RewardTaskPage
from app.team_setting_card import TeamSettingCard
from module.after_completion_types import (
    ACTION_EXIT_AALC,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_GAME,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_LOCK,
    POWER_ACTION_NONE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_SLEEP,
    normalize_after_completion_config,
)
from module.automation import auto
from module.config import cfg
from module.config.task_queue import AfterCompletion, MirrorTask
from module.game_and_screen import screen
from module.hotkey_listener import ExactGlobalHotKeys
from module.logger import log
from module.logger.my_log import ui_log_dispatcher
from module.system_actions import (
    get_after_completion_config,
    set_after_completion_config,
)
from tasks.base.run_plan import Problem, RunPlan, plan_for_request, plan_problem
from tasks.base.script_task_scheme import my_script_task, refresh_auto_hard_mirror


class AfterCompletionActionEditor(FlyoutViewBase):
    def __init__(
        self,
        actions: list[str],
        power_action: str,
        on_apply: Callable[[list[str], str, bool], None],
        parent=None,
    ):
        super().__init__(parent)
        self._on_apply = on_apply
        self._action_text = {
            ACTION_EXIT_GAME: QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "退出游戏"),
            ACTION_EXIT_EMULATOR: QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "退出模拟器"),
            ACTION_EXIT_AALC: QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "退出AALC"),
        }
        self._power_items = [
            (QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "无"), POWER_ACTION_NONE),
            (QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "睡眠"), POWER_ACTION_SLEEP),
            (QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "休眠"), POWER_ACTION_HIBERNATE),
            (QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "锁屏"), POWER_ACTION_LOCK),
            (QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "关机"), POWER_ACTION_SHUTDOWN),
        ]
        self._title_actions = QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "前置动作（可多选）")
        self._title_power = QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "最终动作（单选）")
        self._button_apply_once = QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "仅本次生效")
        self._button_save_default = QT_TRANSLATE_NOOP("AfterCompletionActionEditor", "保存为默认")

        self.vbox = QVBoxLayout(self)
        self.vbox.setSpacing(10)
        self.vbox.setContentsMargins(18, 14, 18, 14)

        self.label_actions = BodyLabel(self._title_actions)
        self.vbox.addWidget(self.label_actions)

        self.box_exit_game = CheckBox(self._action_text[ACTION_EXIT_GAME], self)
        self.box_exit_emulator = CheckBox(self._action_text[ACTION_EXIT_EMULATOR], self)
        self.box_exit_aalc = CheckBox(self._action_text[ACTION_EXIT_AALC], self)
        self.vbox.addWidget(self.box_exit_game)
        self.vbox.addWidget(self.box_exit_emulator)
        self.vbox.addWidget(self.box_exit_aalc)

        self.label_power = BodyLabel(self._title_power)
        self.vbox.addWidget(self.label_power)

        self.power_combo = ComboBox(self)
        self.power_combo.addItems([self.tr(text) for text, _ in self._power_items])
        self.vbox.addWidget(self.power_combo)

        self.button_row = QHBoxLayout()
        self.button_apply = PushButton(self._button_apply_once, self)
        self.button_save = PrimaryPushButton(self._button_save_default, self)
        self.button_row.addWidget(self.button_apply)
        self.button_row.addWidget(self.button_save)
        self.vbox.addLayout(self.button_row)

        self.set_state(actions, power_action)

        self.button_apply.clicked.connect(lambda: self._apply(False))
        self.button_save.clicked.connect(lambda: self._apply(True))
        self.retranslateUi()

    def set_state(self, actions: list[str], power_action: str) -> None:
        self.box_exit_game.setChecked(ACTION_EXIT_GAME in actions)
        self.box_exit_emulator.setChecked(ACTION_EXIT_EMULATOR in actions)
        self.box_exit_aalc.setChecked(ACTION_EXIT_AALC in actions)
        self._set_power_combo(power_action)

    def _set_power_combo(self, power_action: str) -> None:
        for index, (_, value) in enumerate(self._power_items):
            if value == power_action:
                self.power_combo.setCurrentIndex(index)
                return
        self.power_combo.setCurrentIndex(0)

    def _collect_actions(self) -> list[str]:
        actions: list[str] = []
        if self.box_exit_game.isChecked():
            actions.append(ACTION_EXIT_GAME)
        if self.box_exit_emulator.isChecked():
            actions.append(ACTION_EXIT_EMULATOR)
        if self.box_exit_aalc.isChecked():
            actions.append(ACTION_EXIT_AALC)
        return actions

    def _collect_power_action(self) -> str:
        idx = max(0, self.power_combo.currentIndex())
        return self._power_items[idx][1]

    def _apply(self, permanent: bool) -> None:
        self._on_apply(self._collect_actions(), self._collect_power_action(), permanent)

    def retranslateUi(self):
        self.label_actions.setText(self.tr(self._title_actions))
        self.label_power.setText(self.tr(self._title_power))
        self.box_exit_game.setText(self.tr(self._action_text[ACTION_EXIT_GAME]))
        self.box_exit_emulator.setText(self.tr(self._action_text[ACTION_EXIT_EMULATOR]))
        self.box_exit_aalc.setText(self.tr(self._action_text[ACTION_EXIT_AALC]))
        for index, (text, _) in enumerate(self._power_items):
            self.power_combo.setItemText(index, self.tr(text))
        self.button_apply.setText(self.tr(self._button_apply_once))
        self.button_save.setText(self.tr(self._button_save_default))


class AfterCompletionSelector(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._none_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "无")
        self._action_text = {
            ACTION_EXIT_GAME: QT_TRANSLATE_NOOP("AfterCompletionSelector", "退出游戏"),
            ACTION_EXIT_EMULATOR: QT_TRANSLATE_NOOP("AfterCompletionSelector", "退出模拟器"),
            ACTION_EXIT_AALC: QT_TRANSLATE_NOOP("AfterCompletionSelector", "退出AALC"),
        }
        self._power_text = {
            POWER_ACTION_NONE: QT_TRANSLATE_NOOP("AfterCompletionSelector", "无"),
            POWER_ACTION_SLEEP: QT_TRANSLATE_NOOP("AfterCompletionSelector", "睡眠"),
            POWER_ACTION_HIBERNATE: QT_TRANSLATE_NOOP("AfterCompletionSelector", "休眠"),
            POWER_ACTION_LOCK: QT_TRANSLATE_NOOP("AfterCompletionSelector", "锁屏"),
            POWER_ACTION_SHUTDOWN: QT_TRANSLATE_NOOP("AfterCompletionSelector", "关机"),
        }
        self._edit_button_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "编辑")
        self._saved_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "默认")
        self._once_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "本次")
        self._exit_prefix_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "退出")
        self._joiner_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "与")
        self._after_power_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "后，再{0}")
        self._power_only_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "执行{0}")
        self._do_nothing_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "什么也不干")
        self._tool_tip_text = QT_TRANSLATE_NOOP(
            "AfterCompletionSelector", "支持组合动作：退出目标后再执行电源动作，可选择仅本次或保存默认"
        )
        self._schedule_prefix_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "定时任务「{0}」：{1}")
        self._command_prefix_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "命令行指定：{0}")
        self._queued_text = QT_TRANSLATE_NOOP("AfterCompletionSelector", "存在另一定时任务")
        self._queued_tooltip_text = QT_TRANSLATE_NOOP(
            "AfterCompletionSelector",
            "还有排队中的自动任务，本次任务结束后不会执行收尾动作，待全部任务完成后由最后一个任务执行",
        )

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(10, 5, 10, 5)
        self.hbox.setSpacing(8)

        self.summary = BodyLabel("", self)
        self.summary.setWordWrap(True)
        self.edit_button = PushButton(self._edit_button_text, self)
        self.edit_button.setFixedWidth(72)

        self.hbox.addWidget(self.summary, stretch=1)
        self.hbox.addWidget(self.edit_button)
        self.setMinimumWidth(280)
        self._editor_dialog = None

        # 「仅本次生效」的结束后操作只放在内存里，重启 AALC 后失效，不写入配置文件
        self._once: tuple[list[str], str] | None = None
        # 定时任务 / 命令行运行期间显示它自己的结束后操作（同样不写配置）
        self._run_override: tuple[str | None, list[str], str] | None = None

        self.edit_button.installEventFilter(ToolTipFilter(self))
        self.summary.installEventFilter(ToolTipFilter(self.summary, position=ToolTipPosition.BOTTOM))

        self.edit_button.clicked.connect(self._show_editor)
        self.apply_style()
        # 抑制状态决定摘要口径，必须在首次 refresh_from_config 之前就绪。
        # 此刻队列逻辑尚未运行，抑制开关必为关。
        self._completion_suppressed = False
        mediator.completion_suppressed_changed.connect(self._on_completion_suppressed_changed)
        self.retranslateUi()

        qconfig.themeChangedFinished.connect(self.apply_style)

    def apply_style(self):
        set_border_style(self)

    def _summary_text(self, actions: list[str], power_action: str, once: bool) -> tuple[str, str]:
        exit_names = [self.tr(self._action_text[action]) for action in actions if action in self._action_text]
        exit_targets = [
            name[len(self.tr(self._exit_prefix_text)) :] if name.startswith(self.tr(self._exit_prefix_text)) else name
            for name in exit_names
        ]
        power_text = self.tr(self._power_text.get(power_action, self._none_text))

        if exit_targets:
            exit_text = self.tr(self._joiner_text).join(exit_targets)
            exit_clause = f"{self.tr(self._exit_prefix_text)}{exit_text}"
            if power_action != POWER_ACTION_NONE:
                display_text = f"{exit_clause}{self.tr(self._after_power_text).format(power_text)}"
            else:
                display_text = exit_clause
        else:
            if power_action != POWER_ACTION_NONE:
                display_text = self.tr(self._power_only_text).format(power_text)
            else:
                display_text = self.tr(self._do_nothing_text)

        mode = self.tr(self._once_text if once else self._saved_text)
        full_text = f"{display_text}（{mode}）"

        # 动作较多时用换行压缩宽度，完整内容通过悬浮提示查看
        if len(exit_targets) >= 3 and power_action != POWER_ACTION_NONE:
            exit_text = self.tr(self._joiner_text).join(exit_targets)
            display_text = (
                f"{self.tr(self._exit_prefix_text)}{exit_text}\n{self.tr(self._after_power_text).format(power_text)}"
            )

        return display_text, full_text

    def _show_editor(self):
        if self._editor_dialog is not None and self._editor_dialog.isVisible():
            self._editor_dialog.raise_()
            self._editor_dialog.activateWindow()
            return

        # 先刷新摘要，确保界面展示与配置一致
        self.refresh_from_config()
        actions, power_action = self._effective()
        dialog = QDialog(self.window())
        dialog.setWindowTitle(self.tr("结束后操作"))
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        editor = AfterCompletionActionEditor(
            actions,
            power_action,
            lambda selected_actions, selected_power, permanent: self._apply_from_dialog(
                selected_actions,
                selected_power,
                permanent,
                dialog,
            ),
            dialog,
        )
        dialog_layout.addWidget(editor)
        dialog.resize(360, 280)
        dialog.finished.connect(lambda _: setattr(self, "_editor_dialog", None))
        self._editor_dialog = dialog
        dialog.show()

    def _effective(self) -> tuple[list[str], str]:
        if self._once is not None:
            return self._once
        return get_after_completion_config()

    def apply_selection(self, actions: list[str], power_action: str, permanent: bool):
        normalized = normalize_after_completion_config(actions, power_action)
        if permanent:
            set_after_completion_config(*normalized)
            self._once = None
        else:
            self._once = normalized
        self.refresh_from_config()
        self._close_dialog()

    def once_after_completion(self) -> AfterCompletion | None:
        """「仅本次生效」时返回本次的结束后操作，否则 None（使用默认设置）"""
        if self._once is None:
            return None
        actions, power_action = self._once
        return AfterCompletion(actions=actions, power_action=power_action)

    def show_run(self, schedule_name: str | None, after_completion: AfterCompletion) -> None:
        """定时任务 / 命令行运行期间，摘要显示它自己的结束后操作"""
        actions, power_action = after_completion.normalized()
        self._run_override = (schedule_name, actions, power_action)
        self.refresh_from_config()

    def clear_run(self) -> None:
        if self._run_override is not None:
            self._run_override = None
            self.refresh_from_config()

    def _apply_from_dialog(self, actions: list[str], power_action: str, permanent: bool, dialog: QDialog):
        self.apply_selection(actions, power_action, permanent)
        try:
            dialog.close()
        except Exception:
            pass

    def _close_dialog(self):
        if self._editor_dialog is not None:
            try:
                self._editor_dialog.close()
            except Exception:
                pass
            self._editor_dialog = None

    def _hide_editor(self):
        # 兼容外部调用
        self._close_dialog()

    def _on_completion_suppressed_changed(self, suppressed: bool) -> None:
        """收尾动作被排队任务抑制时，摘要如实提示，而不是把配置清空成无。"""
        self._completion_suppressed = suppressed
        self.refresh_from_config()

    def refresh_from_config(self):
        if self._completion_suppressed:
            # 有排队任务：本次收尾不会执行，如实提示用户，配置本身保持不变。
            self.summary.setText(self.tr(self._queued_text))
            self.summary.setToolTip(self.tr(self._queued_tooltip_text))
            return
        if self._run_override is not None:
            name, actions, power_action = self._run_override
            summary_text, full_text = self._summary_text(actions, power_action, once=True)
            if name is not None:
                summary_text = self.tr(self._schedule_prefix_text).format(name, summary_text)
                full_text = self.tr(self._schedule_prefix_text).format(name, full_text)
            else:
                summary_text = self.tr(self._command_prefix_text).format(summary_text)
                full_text = self.tr(self._command_prefix_text).format(full_text)
        else:
            actions, power_action = self._effective()
            summary_text, full_text = self._summary_text(actions, power_action, once=self._once is not None)
        self.summary.setText(summary_text)
        self.summary.setToolTip(full_text)

    def retranslateUi(self):
        self.edit_button.setText(self.tr(self._edit_button_text))
        self.refresh_from_config()
        if self._tool_tip_text:
            self.setToolTip(self.tr(self._tool_tip_text))


class FarmingInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # objectName 由 addSubInterface 设置，这里不需要设置
        self.hbox_layout = QHBoxLayout(self)
        self.hbox_layout_left = QVBoxLayout()
        self.hbox_layout_center = QVBoxLayout()
        self.hbox_layout_right = QVBoxLayout()
        self.hbox_layout.addLayout(self.hbox_layout_left, stretch=3)
        self.hbox_layout.addLayout(self.hbox_layout_center, stretch=4)
        self.hbox_layout.addLayout(self.hbox_layout_right, stretch=3)

        """
        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)
        self.setViewportMargins(0, 0, 0, 5)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)"""

        self.interface_left = FarmingInterfaceLeft()
        self.interface_center = FarmingInterfaceCenter()
        self.interface_right = FarmingInterfaceRight()
        self.listener = None
        self.hbox_layout_left.addWidget(self.interface_left)
        self.hbox_layout_center.addWidget(self.interface_center)
        self.hbox_layout_right.addWidget(self.interface_right)

        # 左侧选中哪一项，中间就显示哪一项的设置；任何改动都写回配置
        panel = self.interface_left.task_panel
        panel.itemSelected.connect(self.interface_center.show_item)
        panel.changed.connect(self._on_queue_changed)
        self.interface_center.taskChanged.connect(self._on_task_param_changed)
        mediator.task_queue_editable.connect(self.interface_center.refresh_dependencies)
        panel.select(cfg.last_selected_task)
        # self.setStyleSheet("border: 1px solid black;")
        # 启动快捷键监听

        self._listener_start()
        mediator.hotkey_listener_stop_signal.connect(self._listener_stop)
        mediator.hotkey_listener_start_signal.connect(self._listener_start)

    def _on_queue_changed(self):
        cfg.save()

    def _on_task_param_changed(self):
        cfg.save()
        self.interface_left.queue_list.refresh()

    def _listener_stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _listener_start(self):
        self._listener_stop()
        try:
            self.listener = ExactGlobalHotKeys(
                {
                    cfg.shutdown_hotkey: self.my_stop_shortcut,
                    cfg.pause_hotkey: self.my_pause_and_resume,
                    cfg.resume_hotkey: self.my_pause_and_resume,
                }
            )
            self.listener.start()
        except ValueError:
            self.listener = None
            log.error("快捷键监听启动失败，请确认设置的快捷键格式有效")

    def my_stop_shortcut(self):
        mediator.link_start.emit()

    def my_pause_and_resume(self):
        mediator.pause_resume.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)


class FarmingInterfaceLeft(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceLeft")

        self.my_script = None
        self._running_schedule = None

        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        self.connect_mediator()

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.hbox_layout = QVBoxLayout(self)

    def __init_card(self):
        self.task_panel = TaskQueuePanel(lambda: cfg.config.task_queue, self)
        self.queue_list = self.task_panel.queue_list
        # 亚哈共鸣不是任务，放在列表外面
        self.resonate_with_Ahab = BaseCheckBox(
            "resonate_with_Ahab", None, QT_TRANSLATE_NOOP("BaseCheckBox", "亚哈共鸣"), center=False
        )

        self.then = BaseLabel(QT_TRANSLATE_NOOP("BaseLabel", "之后"))

        self.after_completion_selector = AfterCompletionSelector(self)
        self.link_start_button = NormalTextButton("Link Start!", "link_start", 0)
        self.link_start_button.clicked.connect(self.start_and_stop_tasks)
        self.link_start_button.button.setMinimumSize(130, 70)
        self.pause_resume_button = NormalTextButton(QT_TRANSLATE_NOOP("NormalTextButton", "暂停"), "pause_resume", 0)
        self.pause_resume_button.clicked.connect(self.pause_or_resume_tasks)
        self.pause_resume_button.button.setMinimumSize(90, 70)
        self.pause_resume_button.setVisible(False)
        scale_factor = QApplication.primaryScreen().logicalDotsPerInch() / 96  # Windows 标准 DPI 是 96
        font_size = min(14, int(14 / scale_factor))
        # 创建字体对象并设置大小
        font = self.link_start_button.button.font()  # 获取当前字体
        font.setPointSize(font_size)  # 设置字体大小（单位：点）
        self.link_start_button.button.setFont(font)  # 应用新字体
        self.pause_resume_button.button.setFont(font)

    def __init_layout(self):
        self.hbox_layout.addWidget(self.task_panel, stretch=1)
        self.hbox_layout.addWidget(self.resonate_with_Ahab)
        self.hbox_layout.addWidget(self.then)
        self.hbox_layout.addWidget(self.after_completion_selector)
        self.action_button_layout = QHBoxLayout()
        self.action_button_layout.addWidget(self.link_start_button)
        self.action_button_layout.addWidget(self.pause_resume_button)
        self.hbox_layout.addLayout(self.action_button_layout)

    def stop_AALC(self):
        log.debug("即将关闭AALC")
        try:
            self.after_completion_selector._hide_editor()
        except Exception:
            pass
        sys.exit(0)

    def manual_plan(self) -> RunPlan:
        """手动点击 Link Start：主界面任务列表 + 结束后操作（「仅本次生效」优先）"""
        return RunPlan.from_queue(
            cfg.config.task_queue,
            self.after_completion_selector.once_after_completion(),
            source="manual",
        )

    def check_setting(self, plan: RunPlan):
        # 检测是否有未保存的镜牢队伍设置
        if self.parent().parent().findChild(TeamSettingCard):
            list(self.parent().parent().parent().pivot.items.values())[-1].click()
            mediator.save_warning.emit()
            return False

        if any(isinstance(task, MirrorTask) for task in plan.tasks):
            # 判断是否进入新的自动困牢周期，并整理队伍勾选状态
            refresh_auto_hard_mirror()
            if sum(1 for team in cfg.teams_be_select if team) != cfg.teams_be_select_num:
                cfg.normalize_and_sync_team_state()
            cfg.flush()
            if cfg.auto_hard_mirror and cfg.hard_mirror_chance > 0:
                log.debug(f"自动困牢启用中，剩余次数：{cfg.hard_mirror_chance}")

        selected_teams = {
            index + 1: cfg.config.teams[f"{index + 1}"] for index, on in enumerate(cfg.teams_be_select) if on
        }
        problem = plan_problem(
            plan,
            selected_teams,
            auto_hard_mirror=cfg.auto_hard_mirror,
            hard_mirror_chance=cfg.hard_mirror_chance,
        )
        if problem is None:
            return True
        if problem.kind == "no_tasks":
            mediator.tasks_warning.emit()
        else:
            mediator.warning.emit(self._problem_text(problem))
        return False

    def _problem_text(self, problem: Problem) -> str:
        if problem.kind == "no_team":
            return self.tr("没有启用任何队伍，请选择一个队伍进行镜牢任务")
        if problem.kind == "team_without_sinners":
            return self.tr("存在未配置角色选择的队伍：TEAM_{0}").format(problem.team)
        if problem.kind == "no_team_for_hard":
            return self.tr("启用了困牢，但是无可用于困牢的队伍")
        return self.tr("启用了普牢，但是无可用于普牢的队伍")

    def start_and_stop_tasks(self, plan: RunPlan | None = None):
        # 设置按下启动与停止按钮时，其他模块的启用与停用
        current_text = self.link_start_button.get_text()
        if current_text == "Link Start!":
            if not isinstance(plan, RunPlan):
                plan = self.manual_plan()
            # 启动前检查设置，防呆
            if self.check_setting(plan) is False:
                self._clear_running_schedule()
                return
            self.link_start_button.set_text("S t o p !")
            self.sync_pause_resume_button()
            self._disable_setting(self.parent())
            self.task_panel.set_editable(False)
            self.create_and_start_script(plan)
        else:
            if cfg.set_reduce_miscontact and cfg.simulator is False:
                # 手动停止时仍需恢复游戏窗口，但这里不再要求抢前台。
                screen.reset_win(activate=False)
            else:
                if cfg.simulator_type == 0:
                    from module.automation.input_handlers.simulator.mumu_control import (
                        MumuControl,
                    )

                    while True:
                        try:
                            MumuControl.clean_connect()
                            break
                        except Exception:
                            continue
                else:
                    from module.automation.input_handlers.simulator.simulator_control import (
                        SimulatorControl,
                    )

                    while True:
                        try:
                            SimulatorControl.clean_connect()
                            break
                        except Exception:
                            continue
            self.link_start_button.set_text("Link Start!")
            self._enable_setting(self.parent())
            self.reset_pause_resume_button()
            mediator.refresh_teams_order.emit()
            # 检查线程是否仍在运行，如果仍在运行则执行清理，否则跳过（因为脚本已自行清理）
            thread_was_running = self.my_script is not None and self.my_script.isRunning()
            self.stop_script()
            if thread_was_running:
                auto.clear_img_cache()
            mediator.mirror_bar_kill_signal.emit()
            self._after_run_ui_reset()

    def plan_from_request(self, request) -> RunPlan | None:
        """把命令行 / 定时启动请求变成本次要执行的计划；找不到定时任务时返回 None"""
        plan, schedule = plan_for_request(
            request,
            cfg.config.task_queue,
            cfg.config.schedules,
            self.after_completion_selector.once_after_completion(),
        )
        if plan is None:
            log.error(f"找不到定时任务 {request.schedule_id}，本次启动已跳过")
            return None
        if schedule is not None:
            self._running_schedule = schedule
            self.after_completion_selector.show_run(schedule_title(schedule), schedule.after_completion)
        elif request is not None and request.after_completion is not None:
            self.after_completion_selector.show_run(None, request.after_completion)
        return plan

    def start_tasks_from_command(self, request=None):
        """Start a command/scheduled task without toggling a running task to stop."""
        if self.my_script is not None and self.my_script.isRunning():
            log.warning("收到命令行或定时启动请求，但已有脚本正在运行，本次启动请求已安全跳过")
            return
        if self.link_start_button.get_text() != "Link Start!":
            log.warning("启动按钮状态与脚本线程不一致，已恢复为空闲状态后继续定时启动")
            self._on_script_finished()
        plan = self.plan_from_request(request)
        if plan is None:
            return
        self.start_and_stop_tasks(plan)

    def _clear_running_schedule(self):
        self._running_schedule = None
        self.after_completion_selector.clear_run()

    def _after_run_ui_reset(self):
        self.task_panel.set_editable(True)
        self.queue_list.set_running("")
        self._clear_running_schedule()
        mediator.task_queue_editable.emit()

    def _on_script_finished(self):
        # 自然结束只做 UI 收尾；不要复用“手动停止”入口，否则会重复触发窗口清理。
        log.debug("脚本自然结束，执行 UI 收尾，不再重复重置游戏窗口")
        self.link_start_button.set_text("Link Start!")
        self._enable_setting(self.parent())
        self.reset_pause_resume_button()
        mediator.refresh_teams_order.emit()
        mediator.mirror_bar_kill_signal.emit()
        self._after_run_ui_reset()

    def _disable_setting(self, parent):
        for child in parent.children():
            # 跳过非 QWidget 类型的子对象（如信号、槽等）
            if not isinstance(child, QWidget):
                continue
            if child.objectName() in ("link_start", "pause_resume"):
                continue
            # 检查是否为目标控件类型
            if isinstance(
                child,
                (
                    ToSettingButton,
                    CheckBox,
                    PushButton,
                    ComboBox,
                    SpinBox,
                    TransparentToolButton,
                ),
            ):
                child.setEnabled(False)
            else:
                # 递归处理子部件的子部件（如布局中的嵌套控件）
                self._disable_setting(child)

    def _enable_setting(self, parent):
        for child in parent.children():
            # 跳过非 QWidget 类型的子对象（如信号、槽等）
            if not isinstance(child, QWidget):
                continue
            # 检查是否为目标控件类型
            if isinstance(
                child,
                (
                    ToSettingButton,
                    CheckBox,
                    PushButton,
                    ComboBox,
                    SpinBox,
                    TransparentToolButton,
                ),
            ):
                child.setEnabled(True)
            else:
                # 递归处理子部件的子部件（如布局中的嵌套控件）
                self._enable_setting(child)

    def create_and_start_script(self, plan: RunPlan):
        try:
            msg = "开始进行所有任务"
            log.info(msg)
            ui_log_dispatcher.clear()
            # 启动脚本线程
            self.my_script = my_script_task(plan)
            # 设置脚本线程为守护(当程序被关闭，一起停止)
            self.my_script.daemon = True
            self.my_script.finished.connect(mediator.script_finished.emit)
            self.my_script.start()
        except Exception as e:
            log.error(f"启动脚本失败: {e}")
            self.link_start_button.set_text("Link Start!")
            self._enable_setting(self.parent())
            self.reset_pause_resume_button()
            self._after_run_ui_reset()

    def stop_script(self):
        if self.my_script and self.my_script.isRunning():
            log.debug("正在终止脚本线程...")
            self.my_script.terminate()  # 终止线程

    def my_stop_shortcut(self):
        current_text = self.link_start_button.get_text()
        if current_text != "Link Start!":
            self.link_start_button.be_click()

    def pause_or_resume_tasks(self):
        if self.link_start_button.get_text() == "Link Start!":
            self.reset_pause_resume_button()
            return
        auto.set_pause()
        self.sync_pause_resume_button()

    def sync_pause_resume_button(self):
        if self.link_start_button.get_text() == "Link Start!":
            self.reset_pause_resume_button()
            return
        paused = False
        try:
            paused = auto.check_pause()
        except Exception as e:
            log.debug(f"同步暂停状态失败: {e}")
        self.pause_resume_button.set_text(self.tr("继续" if paused else "暂停"))
        self.pause_resume_button.setVisible(True)

    def reset_pause_resume_button(self):
        try:
            if auto.check_pause():
                auto.set_pause()
        except Exception as e:
            log.debug(f"重置暂停状态失败: {e}")
        self.pause_resume_button.setVisible(False)

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.link_start.connect(self.my_stop_shortcut)
        mediator.pause_resume.connect(self.pause_or_resume_tasks)
        mediator.kill_signal.connect(self.stop_AALC)
        # 自动任务只能启动，不能切换为停止当前任务。
        mediator.finished_signal.connect(self.start_tasks_from_command)
        mediator.script_finished.connect(self._on_script_finished)
        mediator.task_item_started.connect(self.queue_list.set_running)

    def retranslateUi(self):
        self.task_panel.retranslateUi()
        self.resonate_with_Ahab.retranslateUi()
        self.then.retranslateUi()
        self.after_completion_selector.retranslateUi()
        self.sync_pause_resume_button()


class FarmingInterfaceCenter(QWidget):
    taskChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceCenter")
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.vbox = QVBoxLayout(self)
        self.setting_page = PopUpAniStackedWidget(self)

    def __init_card(self):
        self.set_windows = PageSetWindows(self)
        self.daily_task = DailyTaskPage(self)
        self.get_reward = RewardTaskPage(self)
        self.buy_enkephalin = EnkephalinTaskPage(self)
        self.mirror = PageMirror(self)
        self.task_pages = {
            "daily": self.daily_task,
            "reward": self.get_reward,
            "enkephalin": self.buy_enkephalin,
            "mirror": self.mirror,
        }
        for page in self.task_pages.values():
            page.taskChanged.connect(lambda _field: self.taskChanged.emit())

    def __init_layout(self):
        self.setting_page.addWidget(self.set_windows)
        for page in self.task_pages.values():
            self.setting_page.addWidget(page)
        self.vbox.addWidget(self.setting_page)

    def show_item(self, item_id: str) -> None:
        """显示窗口设置，或某个任务的设置页（并绑定到该任务）"""
        page = self.set_windows
        if item_id != WINDOW_SETTINGS_ID:
            task = next((t for t in cfg.config.task_queue if t.id == item_id), None)
            if task is not None:
                page = self.task_pages[task.type]
                page.bind(task)
            else:
                item_id = WINDOW_SETTINGS_ID
        if self.setting_page.currentWidget() is not page:
            self.setting_page.setCurrentWidget(page)
        if cfg.last_selected_task != item_id:
            cfg.set_value("last_selected_task", item_id)

    def refresh_dependencies(self) -> None:
        for page in self.task_pages.values():
            page.refresh_dependencies()

    def retranslateUi(self):
        self.set_windows.retranslateUi()
        for page in self.task_pages.values():
            page.retranslateUi()


class FarmingInterfaceRight(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        self._apply_theme_style()
        self._connect_log_stream()
        self._bootstrap_log_history()

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)

    def __init_card(self):
        self.scroll_log_edit = TextEdit()
        self.scroll_log_edit.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.scroll_log_edit.setReadOnly(True)

    def _apply_theme_style(self):
        light, dark = get_log_text_edit_qss()
        setCustomStyleSheet(self.scroll_log_edit, light, dark)
        self.scroll_log_edit.layer.hide()  # 隐藏指示线

    def __init_layout(self):
        self.main_layout.addWidget(self.scroll_log_edit)

    def _connect_log_stream(self):
        ui_log_dispatcher.new_lines.connect(self._handle_new_lines)
        ui_log_dispatcher.cleared.connect(self._handle_log_cleared)

    def _bootstrap_log_history(self):
        history = ui_log_dispatcher.snapshot()
        if history:
            self._append_lines(history, force_scroll=True)

    def _handle_new_lines(self, lines: list[str]):
        self._append_lines(lines)

    def _append_lines(self, lines: list[str], force_scroll: bool = False):
        if not lines:
            return
        scrollbar = self.scroll_log_edit.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        for line in lines:
            self.scroll_log_edit.append(line)
        if force_scroll or at_bottom:
            self.scroll_log_edit.moveCursor(QTextCursor.End)

    def _handle_log_cleared(self):
        self.scroll_log_edit.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FarmingInterface()
    w.show()
    app.exec()
