import sys
from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
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
    TransparentToolButton,
    setCustomStyleSheet,
)

from app.base_combination import *
from app.base_tools import *
from app.common.ui_config import get_log_text_edit_qss
from app.language_manager import LanguageManager
from app.page_card import (
    PageDailyTask,
    PageGetPrize,
    PageLunacyToEnkephalin,
    PageMirror,
    PageSetWindows,
)
from app.team_setting_card import TeamSettingCard
from module.automation import auto
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
from module.game_and_screen import screen
from module.hotkey_listener import ExactGlobalHotKeys
from module.logger import log, ui_log_dispatcher
from module.system_actions import (
    get_after_completion_config,
    set_after_completion_config,
)
from tasks.base.script_task_scheme import my_script_task
from utils.utils import check_hard_mirror_time


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

        self.box_exit_game.setChecked(ACTION_EXIT_GAME in actions)
        self.box_exit_emulator.setChecked(ACTION_EXIT_EMULATOR in actions)
        self.box_exit_aalc.setChecked(ACTION_EXIT_AALC in actions)
        self._set_power_combo(power_action)

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

        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(0, 0, 0, 0)
        self.hbox.setSpacing(8)

        self.summary = BodyLabel("", self)
        self.summary.setWordWrap(True)
        self.edit_button = PushButton(self._edit_button_text, self)
        self.edit_button.setFixedWidth(72)

        self.hbox.addWidget(self.summary, stretch=1)
        self.hbox.addWidget(self.edit_button)
        self.setMinimumWidth(280)
        self._editor_dialog = None
        self.setToolTip(self.tr(self._tool_tip_text))

        if cfg.get_value("keep_after_completion", False) is False:
            self._set_after_completion_config([], POWER_ACTION_NONE, persist=False)

        self.edit_button.clicked.connect(self._show_editor)
        self.refresh_from_config()
        self.retranslateUi()

    def _summary_text(self, actions: list[str], power_action: str) -> tuple[str, str]:
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

        mode = self.tr(self._saved_text if cfg.get_value("keep_after_completion", False) else self._once_text)
        full_text = f"{display_text}（{mode}）"

        # 动作较多时用换行压缩宽度，完整内容通过悬浮提示查看
        if len(exit_targets) >= 3 and power_action != POWER_ACTION_NONE:
            exit_text = self.tr(self._joiner_text).join(exit_targets)
            display_text = (
                f"{self.tr(self._exit_prefix_text)}{exit_text}\n"
                f"{self.tr(self._after_power_text).format(power_text)}"
            )

        return display_text, full_text

    def _show_editor(self):
        if self._editor_dialog is not None and self._editor_dialog.isVisible():
            self._editor_dialog.raise_()
            self._editor_dialog.activateWindow()
            return

        # 先刷新摘要，确保界面展示与配置一致
        self.refresh_from_config()
        actions, power_action = get_after_completion_config()
        dialog = QDialog(self.window())
        dialog.setWindowTitle(self.tr("结束后操作"))
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(12, 12, 12, 12)
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

    def _set_after_completion_config(self, actions: list[str], power_action: str, persist: bool):
        # UI 层统一先规范化一次，避免一次性设置把脏值写入配置。
        normalized_actions, normalized_power = normalize_after_completion_config(actions, power_action)
        if persist:
            set_after_completion_config(normalized_actions, normalized_power)
        else:
            cfg.unsaved_set_value("after_completion_actions", normalized_actions)
            cfg.unsaved_set_value("after_completion_power_action", normalized_power)

    def apply_selection(self, actions: list[str], power_action: str, permanent: bool):
        cfg.unsaved_set_value("keep_after_completion", permanent)
        self._set_after_completion_config(actions, power_action, persist=permanent)
        self.refresh_from_config()
        self._close_dialog()

    def set_from_external(self, actions: list[str], power_action: str):
        # 命令行/定时注入视为一次性设置，不覆盖用户默认偏好
        cfg.unsaved_set_value("keep_after_completion", False)
        self._set_after_completion_config(actions, power_action, persist=False)
        self.refresh_from_config()
        self._close_dialog()

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

    def refresh_from_config(self):
        actions, power_action = get_after_completion_config()
        summary_text, full_text = self._summary_text(actions, power_action)
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
        # self.setStyleSheet("border: 1px solid black;")
        # 启动快捷键监听

        self._listener_start()
        mediator.hotkey_listener_stop_signal.connect(self._listener_stop)
        mediator.hotkey_listener_start_signal.connect(self._listener_start)

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
        auto.set_pause()

    def resizeEvent(self, event):
        super().resizeEvent(event)


class FarmingInterfaceLeft(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceLeft")

        self.my_script = None

        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        self.connect_mediator()

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.hbox_layout = QVBoxLayout(self)
        self.setting_layout = QVBoxLayout()
        self.setting_options = QVBoxLayout()
        self.setting_options.setSpacing(10)

        self.setting_box = BaseSettingLayout()
        self.setting_box.setLayout(self.setting_layout)

    def __init_card(self):
        self.set_windows = CheckBoxWithButton(
            "set_windows",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "窗口设置"),
            None,
            "set_windows",
        )
        self.set_windows.set_box_enabled(False)

        self.daily_task = CheckBoxWithButton(
            "daily_task",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "日常任务"),
            None,
            "daily_task",
        )

        self.get_reward = CheckBoxWithButton(
            "get_reward",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "领取奖励"),
            None,
            "get_reward",
        )
        self.buy_enkephalin = CheckBoxWithButton(
            "buy_enkephalin",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "狂气换体"),
            None,
            "buy_enkephalin",
        )
        self.mirror = CheckBoxWithButton(
            "mirror",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "坐牢设置"),
            None,
            "mirror",
        )
        self.resonate_with_Ahab = CheckBoxWithButton(
            "resonate_with_Ahab",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "亚哈共鸣"),
            None,
            "resonate_with_Ahab",
        )

        self.resonate_with_Ahab.button.setEnabled(False)

        self.select_all = NormalTextButton(QT_TRANSLATE_NOOP("NormalTextButton", "全选"), "select_all")
        self.select_all.clicked.connect(self.select_all_function)

        self.clear_all = NormalTextButton(QT_TRANSLATE_NOOP("NormalTextButton", "清空"), "clear_all")
        self.clear_all.clicked.connect(self.clear_all_function)

        self.then = BaseLabel(QT_TRANSLATE_NOOP("BaseLabel", "之后"))

        self.after_completion_selector = AfterCompletionSelector(self)
        self.link_start_button = NormalTextButton("Link Start!", "link_start", 0)
        self.link_start_button.clicked.connect(self.start_and_stop_tasks)
        self.link_start_button.button.setMinimumSize(130, 70)
        scale_factor = QApplication.primaryScreen().logicalDotsPerInch() / 96  # Windows 标准 DPI 是 96
        font_size = min(14, int(14 / scale_factor))
        # 创建字体对象并设置大小
        font = self.link_start_button.button.font()  # 获取当前字体
        font.setPointSize(font_size)  # 设置字体大小（单位：点）
        self.link_start_button.button.setFont(font)  # 应用新字体

    def __init_layout(self):
        self.setting_options.addWidget(self.set_windows)
        self.setting_options.addWidget(self.daily_task)
        self.setting_options.addWidget(self.get_reward)
        self.setting_options.addWidget(self.buy_enkephalin)
        self.setting_options.addWidget(self.mirror)
        self.setting_options.addWidget(self.resonate_with_Ahab)
        self.setting_layout.addLayout(self.setting_options)

        self.hbox_button = QHBoxLayout()
        self.hbox_button.addWidget(self.select_all)
        self.hbox_button.addWidget(self.clear_all)

        self.setting_layout.addLayout(self.hbox_button)

        self.hbox_layout.addWidget(self.setting_box)
        self.hbox_layout.addWidget(self.then)
        self.hbox_layout.addWidget(self.after_completion_selector)
        self.hbox_layout.addWidget(self.link_start_button)

    @staticmethod
    def select_all_function():
        for check_box in task_check_box[:5]:
            check_box.setChecked(True)

    @staticmethod
    def clear_all_function():
        for check_box in task_check_box[1:5]:
            check_box.setChecked(False)

    def stop_AALC(self):
        log.debug("即将关闭AALC")
        try:
            self.after_completion_selector._hide_editor()
        except Exception:
            pass
        sys.exit(0)

    def check_setting(self):
        # 检测是否有未保存的镜牢队伍设置
        if self.parent().parent().findChild(TeamSettingCard):
            list(self.parent().parent().parent().pivot.items.values())[-1].click()
            mediator.save_warning.emit()
            return False

        if cfg.mirror:
            # 判断是否启用了自动切换困牢
            if cfg.auto_hard_mirror:
                from datetime import datetime

                get_timezone()
                if cfg.last_auto_change == 1715990400:
                    cfg.set_value("last_auto_change", datetime.now().timestamp())
                    cfg.flush()
                if check_hard_mirror_time():
                    log.info("识别到新的困牢周期，自动切换困难镜牢，设置困牢次数为3")
                    cfg.set_value("last_auto_change", datetime.now().timestamp())
                    cfg.set_value("hard_mirror", True)
                    cfg.set_value("hard_mirror_chance", 3)
                if cfg.hard_mirror_chance > 0:
                    cfg.set_value("hard_mirror", True)

            # 检查队伍配置状况
            teams_be_select = sum(1 for team in cfg.teams_be_select if team)
            if teams_be_select != cfg.teams_be_select_num:
                cfg.set_value("teams_be_select_num", teams_be_select)
                from utils.utils import check_teams_order

                teams_order = check_teams_order(cfg.teams_order)
                cfg.set_value("teams_order", teams_order)
                cfg.flush()

            if cfg.teams_be_select_num == 0:
                message = self.tr("没有启用任何队伍，请选择一个队伍进行镜牢任务")
                mediator.warning.emit(message)
                return False

            # 检测是否有未配置角色选择的队伍
            teams_be_select = cfg.get_value("teams_be_select")
            for index in (i for i, t in enumerate(teams_be_select) if t is True):
                team_setting = cfg.get_value(f"team{index + 1}_setting")
                if team_setting["sinners_be_select"] == 0:
                    message = self.tr("存在未配置角色选择的队伍：TEAM_{0}")
                    mediator.warning.emit(message.format(index + 1))
                    return False

            # 检测配置的队伍能否顺利执行
            useful = False
            hard = bool(cfg.hard_mirror)
            teams_be_select = cfg.get_value("teams_be_select")
            for index in (i for i, t in enumerate(teams_be_select) if t is True):
                team_setting = cfg.get_value(f"team{index + 1}_setting")
                if team_setting["fixed_team_use"] is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 1 and hard is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 0 and hard is True:
                    useful = True
                    break
            if useful is False:
                if hard:
                    message = self.tr("启用了困牢，但是无可用于困牢的队伍")
                else:
                    message = self.tr("启用了普牢，但是无可用于普牢的队伍")
                mediator.warning.emit(message)
                return False

        if cfg.daily_task is False and cfg.get_reward is False and cfg.buy_enkephalin is False and cfg.mirror is False:
            mediator.tasks_warning.emit()
            return False

    def start_and_stop_tasks(self):
        # 设置按下启动与停止按钮时，其他模块的启用与停用
        current_text = self.link_start_button.get_text()
        if current_text == "Link Start!":
            # 启动前检查设置，防呆
            if self.check_setting() is False:
                return
            self.link_start_button.set_text("S t o p !")
            self._disable_setting(self.parent())
            self.create_and_start_script()
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
            mediator.refresh_teams_order.emit()
            # 检查线程是否仍在运行，如果仍在运行则执行清理，否则跳过（因为脚本已自行清理）
            thread_was_running = self.my_script is not None and self.my_script.isRunning()
            self.stop_script()
            if thread_was_running:
                auto.clear_img_cache()
            mediator.mirror_bar_kill_signal.emit()

    def _on_script_finished(self):
        # 自然结束只做 UI 收尾；不要复用“手动停止”入口，否则会重复触发窗口清理。
        log.debug("脚本自然结束，执行 UI 收尾，不再重复重置游戏窗口")
        self.link_start_button.set_text("Link Start!")
        self._enable_setting(self.parent())
        mediator.refresh_teams_order.emit()
        mediator.mirror_bar_kill_signal.emit()

    def _disable_setting(self, parent):
        for child in parent.children():
            # 跳过非 QWidget 类型的子对象（如信号、槽等）
            if not isinstance(child, QWidget):
                continue
            if child.objectName() == "link_start":
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
            if child.objectName() == "set_windows":
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

    def create_and_start_script(self):
        try:
            msg = "开始进行所有任务"
            log.info(msg)
            ui_log_dispatcher.clear()
            # 启动脚本线程
            self.my_script = my_script_task()
            # 设置脚本线程为守护(当程序被关闭，一起停止)
            self.my_script.daemon = True
            self.my_script.start()
        except Exception as e:
            log.error(f"启动脚本失败: {e}")
            self.link_start_button.set_text("Link Start!")
            self._enable_setting(self.parent())

    def stop_script(self):
        if self.my_script and self.my_script.isRunning():
            log.debug("正在终止脚本线程...")
            self.my_script.terminate()  # 终止线程

    def my_stop_shortcut(self):
        current_text = self.link_start_button.get_text()
        if current_text != "Link Start!":
            self.link_start_button.be_click()

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.link_start.connect(self.my_stop_shortcut)
        mediator.kill_signal.connect(self.stop_AALC)
        # finished_signal 表示线程自然结束，不应再走开始/停止按钮的副作用逻辑。
        mediator.finished_signal.connect(self._on_script_finished)

    def retranslateUi(self):
        self.set_windows.retranslateUi()
        self.daily_task.retranslateUi()
        self.get_reward.retranslateUi()
        self.buy_enkephalin.retranslateUi()
        self.mirror.retranslateUi()
        self.resonate_with_Ahab.retranslateUi()

        self.then.retranslateUi()
        self.after_completion_selector.retranslateUi()
        self.select_all.retranslateUi()
        self.clear_all.retranslateUi()


class FarmingInterfaceCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceCenter")
        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        self.__init_setting()

        self.connect_mediator()

        LanguageManager().register_component(self)

    def __init_widget(self):
        # self.setting_box = CardWidget()
        self.vbox = QVBoxLayout(self)

        self.setting_page = PopUpAniStackedWidget(self)

    def __init_card(self):
        self.set_windows = PageSetWindows(self)
        self.daily_task = PageDailyTask(self)
        self.get_reward = PageGetPrize(self)
        self.buy_enkephalin = PageLunacyToEnkephalin(self)
        self.mirror = PageMirror(self)

    def __init_layout(self):
        self.setting_page.addWidget(self.set_windows)
        self.setting_page.addWidget(self.daily_task)
        self.setting_page.addWidget(self.get_reward)
        self.setting_page.addWidget(self.buy_enkephalin)
        self.setting_page.addWidget(self.mirror)
        self.vbox.addWidget(self.setting_page)
        # self.setting_box.setLayout(self.vbox)

    def __init_setting(self):
        self.setting_page.setCurrentIndex(cfg.get_value("default_page"))
        list(toggle_button_group.items())[cfg.get_value("default_page")][1].setChecked(True)

    def switch_to_page(self, target: str):
        try:
            """切换页面（带越界保护）"""
            page_index = page_name_and_index[target]
            self.setting_page.setCurrentIndex(page_index)  # 当调用 setCurrentIndex 时，StackedWidget 会自动播放过渡动画
            cfg.set_value("default_page", page_index)
        except Exception as e:
            log.error(f"【异常】switch_to_page 出错：{type(e).__name__}:{e}")

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.switch_page.connect(self.switch_to_page)

    def retranslateUi(self):
        self.set_windows.retranslateUi()
        self.daily_task.retranslateUi()
        self.get_reward.retranslateUi()
        self.buy_enkephalin.retranslateUi()
        self.mirror.retranslateUi()


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
