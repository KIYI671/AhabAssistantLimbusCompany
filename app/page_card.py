import os

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from PySide6.QtCore import QCoreApplication, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QImage,
    QPainter,
    QTextDocument,
)
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    PopUpAniStackedWidget,
    RoundMenu,
    ScrollArea,
    SmoothMode,
    TextBrowser,
    TransparentToolButton,
    isDarkTheme,
    qconfig,
    setCustomStyleSheet,
)
from qfluentwidgets import FluentIcon as FIF

from app import *
from app.base_combination import (
    LabelWithComboBox,
    LabelWithSpinBox,
    MirrorTeamCombination,
    TextProgressBar,
)
from app.base_tools import BaseCheckBox
from app.common.ui_config import get_theme_aware_text_browser_qss
from app.language_manager import LanguageManager
from app.task_queue.task_fields import GLOBAL_HINT, GlobalHint, TaskWidgets, mirror_widgets
from app.task_queue.task_store import TaskStore
from app.widget.custom_segmented_widget import CustomSegmentedWidget
from module.config import TeamSetting, cfg, theme_list
from module.config.team_import_export import apply_team_settings, import_team_settings
from module.logger import log

from .markdown_it_imgdiv import imgdiv_plugin, render_div_close, render_div_open


class PageCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.card_layout = QVBoxLayout(self)
        self.all_page = PopUpAniStackedWidget(self)

        self.page_general = QWidget()
        self.page_advanced = QWidget()
        self.vbox_general = QVBoxLayout(self.page_general)
        self.vbox_advanced = QVBoxLayout(self.page_advanced)

        self.scroll_general = ScrollArea(self)
        self.scroll_general.setWidgetResizable(True)
        self.scroll_advanced = ScrollArea(self)
        self.scroll_advanced.setWidgetResizable(True)

        self.set_pivot()

        self.scroll_general.setWidget(self.page_general)
        self.scroll_general.setObjectName("general")
        self.scroll_advanced.setWidget(self.page_advanced)
        self.scroll_advanced.setObjectName("advanced")

        self.all_page.addWidget(self.scroll_general, deltaX=-76, deltaY=0)
        self.all_page.addWidget(self.scroll_advanced, deltaX=76, deltaY=0)

        self.card_layout.addWidget(self.all_page)
        self.card_layout.addWidget(self.pivot)

        self.scroll_general.enableTransparentBackground()
        self.scroll_advanced.enableTransparentBackground()

        self.__init_widget()

    def set_pivot(self):
        self.pivot = CustomSegmentedWidget(self)
        self.pivot.setFixedHeight(36)

        self.pivot.addItem("general", "常规设置")
        self.pivot.addItem("advanced", "高级设置")
        self.pivot.setCurrentItem("general")
        self.pivot.currentItemChanged.connect(lambda k: self.all_page.setCurrentWidget(self.findChild(QWidget, k)))

    def __init_widget(self):
        self.card_layout.setAlignment(Qt.AlignTop)
        self.vbox_general.setAlignment(Qt.AlignTop)
        self.vbox_advanced.setAlignment(Qt.AlignTop)

    def retranslateUi(self):
        self.pivot.setItemText("general", QCoreApplication.translate("PageCard", "常规设置"))
        self.pivot.setItemText("advanced", QCoreApplication.translate("PageCard", "高级设置"))

    @classmethod
    def tr(cls, text):
        return QCoreApplication.translate(cls.__name__, text)


class PageSetWindows(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_set_windows")

    def __init_card(self):
        self.win_size = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "窗口分辨率"),
            "set_win_size",
            set_win_size_options,
        )
        self.win_position = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "窗口位置"),
            "set_win_position",
            set_win_position_options,
        )
        self.recovery_window = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "结束后恢复窗口"),
            "set_reduce_miscontact",
            set_reduce_miscontact_options,
        )
        self.screenshot_interval = LabelWithSpinBox(
            QT_TRANSLATE_NOOP("LabelWithSpinBox", "截图间隔"),
            "screenshot_interval",
            double=True,
        )
        self.mouse_action_interval = LabelWithSpinBox(
            QT_TRANSLATE_NOOP("LabelWithSpinBox", "鼠标活动间隔"),
            "mouse_action_interval",
            double=True,
        )
        self.mouse_down_duration = LabelWithSpinBox(
            QT_TRANSLATE_NOOP("LabelWithSpinBox", "鼠标按下持续时间"),
            "mouse_down_duration",
            double=True,
            tips=QT_TRANSLATE_NOOP(
                "LabelWithSpinBox", "仅在使用异步方法进行鼠标输入时生效，单位为秒，每次鼠标按下都会增加对应的延迟"
            ),
        )
        self.use_post_message = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "使用异步方法进行键鼠输入"),
            "use_post_message",
            {QT_TRANSLATE_NOOP("BaseComboBox", "否 (默认)"): False, QT_TRANSLATE_NOOP("BaseComboBox", "是"): True},
            tips=QT_TRANSLATE_NOOP("LabelWithComboBox", "提高点击速度，但是对硬件与网络有一定需求，否则可能出现漏点"),
        )

    def __init_layout(self):
        self.vbox_general.addWidget(self.win_size)
        self.vbox_general.addWidget(self.win_position)
        self.vbox_general.addWidget(self.recovery_window)

        self.vbox_advanced.addWidget(self.screenshot_interval)
        self.vbox_advanced.addWidget(self.mouse_action_interval)
        self.vbox_advanced.addWidget(self.mouse_down_duration)
        self.vbox_advanced.addWidget(self.use_post_message)

    def retranslateUi(self):
        self.win_size.retranslateUi()
        self.win_position.retranslateUi()
        self.recovery_window.retranslateUi()
        self.screenshot_interval.retranslateUi()
        self.mouse_action_interval.retranslateUi()
        self.mouse_down_duration.retranslateUi()
        self.use_post_message.retranslateUi()

        super().retranslateUi()


class PageMirror(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("page_mirror")
        self.__init_card()
        self.__init_layout()

        self.get_setting()
        self.refresh()
        self.bar = None
        self.bar_layout = None
        self.connect_mediator()
        self.retranslateUi()

    def __init_card(self):
        self.team = MirrorTeamCombination(
            1,
            "the_team_1",
            QT_TRANSLATE_NOOP("MirrorTeamCombination", "编队1"),
            None,
            "team1_setting",
        )

        # 镜牢次数和选项绑定当前选中的镜牢任务；队伍列表和键盘寻路是全局设置
        self.store = TaskStore(self)
        self.taskChanged = self.store.changed
        self.fields = TaskWidgets(self.store)
        self.mirror_count, common, rest = mirror_widgets(self.fields, scheduled=False)
        self.option_fields = common + rest
        self.global_hint = GlobalHint(GLOBAL_HINT, self)

        self.add_team = QHBoxLayout()
        self.add_team_button = TransparentToolButton(FIF.ADD, None)
        self.add_team_button.setMinimumWidth(200)
        self.add_team_button.clicked.connect(self.show_team_creation_menu)

        self.mirror_keyboard_navigation = BaseCheckBox(
            "mirror_keyboard_navigation",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "使用键盘进行镜牢寻路"),
            center=False,
        )
        self.mirror_keyboard_simple_pathfinding = BaseCheckBox(
            "mirror_keyboard_simple_pathfinding",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "简单键盘寻路（始终按↑键，避免鼠标拖动）"),
            center=False,
        )

        self.mirror_keyboard_navigation.check_box.toggled.connect(
            self._on_keyboard_navigation_toggled
        )
        self._on_keyboard_navigation_toggled(cfg.mirror_keyboard_navigation)

    def _on_keyboard_navigation_toggled(self, checked: bool):
        if not checked and cfg.mirror_keyboard_simple_pathfinding:
            self.mirror_keyboard_simple_pathfinding.set_check_false()
        self.mirror_keyboard_simple_pathfinding.set_box_enabled(checked)

    def __init_layout(self):
        self.vbox_general.addWidget(self.team)

        self.add_team.addWidget(self.add_team_button)
        self.vbox_general.addLayout(self.add_team)

        for field in self.option_fields:
            self.vbox_advanced.addWidget(field)
        self.vbox_advanced.addWidget(self.global_hint)
        self.vbox_advanced.addWidget(self.mirror_keyboard_navigation)
        self.vbox_advanced.addWidget(self.mirror_keyboard_simple_pathfinding)

        self.card_layout.insertWidget(self.card_layout.count() - 1, self.mirror_count)

    @property
    def task(self):
        return self.store.task

    def bind(self, task) -> None:
        self.store.task = task
        if task is not None:
            self.fields.load()

    def refresh_dependencies(self) -> None:
        self.fields.refresh_dependencies()

    def _create_mirror_bar(self, current: int, total: int, hard: bool) -> TextProgressBar:
        """创建进度条"""
        bar = TextProgressBar(self)
        self.bar_layout = QVBoxLayout()
        self.bar_layout.addWidget(bar)

        bar_width = int(200)
        bar_height = int(bar_width / 10)
        bar.setFixedHeight(bar_height)
        bar.setFixedWidth(bar_width)
        self.bar_layout.setAlignment(Qt.AlignRight)
        self.bar_layout.setContentsMargins(0, 0, 32, 0)
        self.card_layout.insertLayout(1, self.bar_layout)

        QT_TRANSLATE_NOOP("PageCard", "镜 牢 进 度 ")
        if hard:
            text = self.tr("镜 牢 进 度 ( 困 难 ) ")
        else:
            text = self.tr("镜 牢 进 度 ( 普 通 ) ")

        if total >= 9000:
            bar.setFormat(f"{text}: %v / ∞")
        else:
            bar.setFormat(f"{text}: %v / %m")

        bar.show()
        bar.setRange(0, total)
        bar.setValue(current)

        return bar

    def update_mirror_bar(self, current: int, total: int, hard: bool = False):
        """更新进度条 若不存在则新建"""
        self.bar_hard = hard
        if self.bar is not None:
            if hard:
                text = self.tr("镜 牢 进 度 ( 困 难 ) ")
            else:
                text = self.tr("镜 牢 进 度 ( 普 通 ) ")
            if total > self.bar.maximum() and total > 0:
                self.bar.setRange(0, total)
            self.bar.setValue(current)
            if total >= 9000:
                self.bar.specialValue = current
                self.bar.setFormat(f"{text}: %raw / ∞")
                self.bar.setValue(total)
                self.bar.setUseAni(False)
            elif total <= 0:
                self.bar.hide()
                self.bar.setFormat(f"{text}: %v / %m")
            else:
                if self.bar.isHidden():
                    self.bar.show()
                self.bar.setUseAni(True)
                self.bar.setFormat(f"{text}: %v / %m")
        else:
            self.bar = self._create_mirror_bar(current, total, hard)

    def destroy_mirror_bar(self):
        """销毁进度条"""
        if self.bar is not None:
            log.info(
                f"已完成{'困难镜牢' if getattr(self, 'bar_hard', False) else '普通镜牢'}进度 {self.bar.value() if self.bar.maximum() < 9000 else self.bar.specialValue} / {self.bar.maximum()}"
            )
            self.bar.deleteLater()
            self.bar = None
        if self.bar_layout is not None:
            self.bar_layout.deleteLater()
            self.bar_layout = None

    def get_setting(self):
        team_toggle_button_group.clear()
        cfg.normalize_and_sync_team_state(persist=False)
        self.page_general.setUpdatesEnabled(False)
        try:
            for i in range(1, 21):
                if self.findChild(MirrorTeamCombination, f"team_{i}") is not None:
                    self.remove_team_card(f"team_{i}")
                if cfg.config.teams.get(f"{i}", None) is not None:
                    self.vbox_general.insertWidget(
                        self.vbox_general.count() - 1,
                        MirrorTeamCombination(i, f"the_team_{i}", f"编队{i}", None, f"team{i}_setting"),
                    )
        finally:
            self.page_general.setUpdatesEnabled(True)
        QT_TRANSLATE_NOOP("MirrorTeamCombination", "编队")
        self.refresh()

    def new_team(self):
        number = len(team_toggle_button_group) + 1
        if number < 20:
            self.page_general.setUpdatesEnabled(False)
            try:
                newTeamComb = MirrorTeamCombination(
                    number,
                    f"the_team_{number}",
                    f"编队{number}",
                    None,
                    f"team{number}_setting",
                )

                newTeamComb.retranslateUi()
                self.vbox_general.insertWidget(self.vbox_general.count() - 1, newTeamComb)
            finally:
                self.page_general.setUpdatesEnabled(True)

            if cfg.config.teams.get(f"{number}", None) is None:
                cfg.config.teams[f"{number}"] = TeamSetting()
                cfg.normalize_and_sync_team_state()
                theme_list.create_team_weight_config(number)

    def show_team_creation_menu(self):
        """显示菜单，提供从头创建队伍或从文件创建的选项"""
        menu = RoundMenu(parent=self)

        create_new_action = Action(FIF.ADD, self.tr("创建空白队伍"))
        create_new_action.triggered.connect(self.new_team)
        menu.addAction(create_new_action)

        create_from_file_action = Action(FIF.FOLDER_ADD, self.tr("从现有配置创建"))
        create_from_file_action.triggered.connect(self.create_team_from_file)
        menu.addAction(create_from_file_action)

        # 在按钮位置显示菜单
        menu.exec(self.add_team_button.mapToGlobal(self.add_team_button.rect().bottomLeft()))

    def create_team_from_file(self):
        """从导入的配置文件创建新队伍"""
        # 打开文件对话框选择 YAML 文件
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("选择队伍配置文件"), "", "YAML Files (*.yaml *.yml)")

        if not file_path:
            return

        # 从文件导入队伍设置
        team_setting, theme_pack_weight, missing_fields = import_team_settings(file_path, 1)

        if team_setting is None:
            MessageBox(self.tr("导入失败"), self.tr("无法读取配置文件，请检查文件格式是否正确。"), self).exec()
            return

        # 如果字段缺失则显示警告
        if missing_fields:
            missing_text = "\n- ".join(missing_fields)
            w = MessageBox(
                self.tr("缺少字段"),
                self.tr(f"配置文件中缺少以下字段：\n- {missing_text}\n\n将使用默认值填充这些字段。是否继续？"),
                self,
            )
            w.yesButton.setText(self.tr("继续"))
            w.cancelButton.setText(self.tr("取消"))
            if not w.exec():
                return

        # 自动递增到下一个可用的队伍槽位
        existing_teams = sorted([int(k) for k in cfg.config.teams.keys()])

        # 查找下一个可用槽位
        team_num = None
        for i in range(1, 21):
            if i not in existing_teams:
                team_num = i
                break

        if team_num is None:
            MessageBox(self.tr("无可用队伍槽位"), self.tr("已达到最大队伍数量（20个），无法创建新队伍。"), self).exec()
            return

        # 应用导入的设置
        try:
            apply_team_settings(team_num, team_setting, theme_pack_weight)

            # 添加到 teams_be_select 和 teams_order
            while len(cfg.config.teams_be_select) < team_num:
                cfg.config.teams_be_select.append(False)
            while len(cfg.config.teams_order) < team_num:
                cfg.config.teams_order.append(0)

            # 刷新界面
            self.get_setting()

            InfoBar.success(
                title=self.tr("导入成功"),
                content=self.tr(f"已成功从文件创建队伍 {team_num}"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            log.error(f"Failed to create team from file: {e}")
            MessageBox(self.tr("创建失败"), self.tr(f"创建队伍时出错：{str(e)}"), self).exec()

    def remove_team_card(self, target: str):
        try:
            team = self.findChild(MirrorTeamCombination, target)
            if team is None:
                return
            self.vbox_general.removeWidget(team)
            team.setParent(None)
            team.deleteLater()
            team = None
        except Exception as e:
            log.error(f"delete_team 出错：{e}")

    def delete_team(self, target: str):
        try:
            team = self.findChild(MirrorTeamCombination, target)
            if team is not None:
                team_order_box = team.findChild(BaseCheckBox, f"the_team_{team.team_number}")
                if team_order_box is not None:
                    team_order_box.set_check_false()
            number = int(target.split("_")[-1])
            self.remove_team_card(target)

            cfg.remove_team_from_queue(number)
            cfg.config.teams.pop(f"{number}", None)
            theme_list.delete_team_weight_config(number)

            self.refresh_team_setting_card()
        except Exception as e:
            log.error(f"delete_team 出错：{e}")

    def refresh_team_setting_card(self):
        old_to_new = {}
        compact_teams = {}
        for new_index, old_index in enumerate(sorted(cfg.config.teams, key=lambda k: int(k)), start=1):
            old_number = int(old_index)
            old_to_new[old_number] = new_index
            team_setting = cfg.config.teams[old_index]
            compact_teams[f"{new_index}"] = team_setting
            if new_index != old_number:
                theme_list.set_team_weight_config_from_team(new_index, old_number)
                theme_list.delete_team_weight_config(old_number)

        cfg.config.teams = compact_teams
        cfg.reindex_team_queue(old_to_new)

        cfg.save()
        self.get_setting()

    def refresh(self):
        mirror_teams = self.findChildren(MirrorTeamCombination)
        teams_order = cfg.config.teams_order
        for team in mirror_teams:
            number = team.team_number
            idx = number - 1
            if idx < len(teams_order) and teams_order[idx] != 0:
                team.order.setText(str(teams_order[idx]))
            else:
                team.order.setText("")

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.delete_team_setting.connect(self.delete_team)
        mediator.refresh_teams_order.connect(self.refresh)
        mediator.mirror_signal.connect(self.update_mirror_bar)
        mediator.mirror_bar_kill_signal.connect(self.destroy_mirror_bar)

    def retranslateUi(self):
        self.fields.retranslateUi()
        self.global_hint.retranslateUi()
        self.mirror_keyboard_navigation.retranslateUi()
        self.mirror_keyboard_simple_pathfinding.retranslateUi()
        self.add_team_button.setToolTip(self.tr("添加队伍"))
        for child in self.findChildren(MirrorTeamCombination):
            child.retranslateUi()

        super().retranslateUi()


def transform_image_url(self, tokens, idx, options, env):
    """将本地图片路径转换为 'dimmed:' scheme 以触发 loadResource 处理"""
    token = tokens[idx]
    src = token.attrs.get("src", "")

    if isinstance(src, str) and not src.startswith(("http://", "https://", "dimmed:")):
        url = QUrl(src)
        new_src = ("." + url.path()) if url.path().startswith("/") else src
        tokens[idx].attrSet("src", "dimmed:" + new_src)

    return self.image(tokens, idx, options, env)


class ThemeAwareTextBrowser(TextBrowser):
    """
    支持主题感知图片渲染的自定义 TextBrowser。

    重写 loadResource 处理 'dimmed:' URI scheme，
    在深色模式下对图片应用半透明黑色叠加层以降低亮度。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_theme_style()

    def _apply_theme_style(self):
        """设置 HTML body 一致的背景色"""
        self.layer.hide()  # 隐藏指示线
        light, dark = get_theme_aware_text_browser_qss()
        setCustomStyleSheet(self, light, dark)

    def _dimImage(self, image: QImage, opacity: int = 128) -> QImage:
        """对图片应用暗化效果"""
        dimmed = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        dimmed.fill(Qt.transparent)

        painter = QPainter(dimmed)
        painter.drawImage(0, 0, image)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.fillRect(dimmed.rect(), QColor(0, 0, 0, opacity))
        painter.end()
        return dimmed

    def loadResource(self, type, name):
        """加载资源，支持 dimmed: scheme 的图片暗化处理"""
        if type == QTextDocument.ImageResource and name.scheme() == "dimmed":
            # 提取实际路径
            path = name.path() or name.toString().split(":", 1)[1]

            image = QImage(path)
            if not image.isNull():
                return self._dimImage(image) if isDarkTheme() else image

        return super().loadResource(type, name)


class MarkdownViewer(QWidget):
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除布局边距
        layout.setSpacing(0)  # 移除布局间距
        self.setLayout(layout)

        LanguageManager().register_component(self)

        self.text_browser = ThemeAwareTextBrowser()
        self.text_browser.scrollDelegate.verticalSmoothScroll.setSmoothMode(SmoothMode.LINEAR)
        self.text_browser.scrollDelegate.verticalSmoothScroll.duration = 100
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        self.text_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单

        self.md = (
            MarkdownIt("commonmark", {"html": True})
            .enable("linkify")
            .enable("table")
            .enable("strikethrough")
            .use(
                anchors_plugin,
                max_level=4,
                slug_func=lambda s: s.lower().replace(" ", "-"),
            )
        )
        self.md.add_render_rule("image", transform_image_url)
        self.md.use(imgdiv_plugin, class_name="figure", focusable=False, align="center")

        self.md.add_render_rule("div_open", render_div_open)
        self.md.add_render_rule("div_close", render_div_close)

        self.html = """
        <html>
            <body>
                <h1>帮助页面加载失败！</h1>
            </body>
        </html>
        """

        layout.addWidget(self.text_browser)
        self.help_path = file_path

        # 在设置 help_path 后连接主题变化信号
        qconfig.themeChanged.connect(self.updateStyle)
        self.reset_viewer()

    def reset_viewer(self):
        if os.path.exists(self.help_path):
            self.load_markdown(self.help_path)
            self.text_browser.setHtml(self.html)
        else:
            self.text_browser.setPlainText(f"错误: 无法加载文件 {self.help_path}，请检查文件路径是否正确。")

    def handle_link_clicked(self, url: QUrl):
        """
        处理 QTextBrowser 中点击链接的逻辑
        """
        if url.scheme() in ["http", "https"]:
            # 用系统默认浏览器打开外部链接
            QDesktopServices.openUrl(url)
        elif url.scheme() != "":
            # 其他链接，不处理
            pass
        else:
            # 本地文件
            file_path = url.path()
            if file_path.startswith("/"):
                # 处理以项目根目录为base的路径
                file_path = file_path[1:]

            if os.path.exists(file_path) and file_path.endswith(".md"):
                # 如果是本地文件链接，尝试加载 Markdown 文件
                self.load_markdown(file_path)
                self.text_browser.setHtml(self.html)

                if url.hasFragment():
                    # 如果链接有锚点，滚动到对应的锚点
                    self.text_browser.scrollToAnchor(url.fragment())
                return

        self.text_browser.setHtml(self.html)

    def load_markdown(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

                html_body = self.md.render(markdown_text)
                css_content = self._get_css_content()

                # 添加 HTML 头部
                self.html = f"""
                <html>
                <head>
                    <style>
                    {css_content}
                    </style>
                </head>
                <body class="markdown-body">
                    {html_body}
                </body>
                </html>
                """
        except Exception as e:
            self.text_browser.setPlainText(f"错误: 无法加载文件\n{str(e)}")

    def _get_css_content(self) -> str:
        """获取当前主题的 CSS 内容"""
        if isDarkTheme():
            css_path = "assets/styles/github-markdown-dark.css"
        else:
            css_path = "assets/styles/github-markdown-light.css"

        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as css_file:
                return css_file.read()
        return ""

    def retranslateUi(self, lang_code):
        if lang_code == "zh_CN":
            self.help_path = "./assets/doc/zh/How_to_use.md"
        else:
            self.help_path = "./assets/doc/en/How_to_use_EN.md"
        self.reset_viewer()

    def updateStyle(self):
        """主题变化时重新加载 HTML 以应用新的 CSS"""
        self.reset_viewer()
