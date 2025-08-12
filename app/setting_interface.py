from PyQt5.QtCore import QUrl, QT_TRANSLATE_NOOP, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QFileDialog
from qfluentwidgets import FluentIcon as FIF, InfoBarPosition
from qfluentwidgets import ScrollArea, ExpandLayout

from app.base_combination import ComboBoxSettingCard, SwitchSettingCard, PushSettingCardMirrorchyan, \
    BaseSettingCardGroup, BasePushSettingCard, BasePrimaryPushSettingCard
from app.card.messagebox_custom import BaseInfoBar
from app.language_manager import SUPPORTED_LANG_NAME, LanguageManager
from module.config import cfg


class SettingInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.__init_widget()
        self.__init_card()
        self.__initLayout()
        self.set_style_sheet()
        self.__connect_signal()
        self.setWidget(self.scroll_widget)
        self.setObjectName("SettingInterface")

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.setWidgetResizable(True)

    def __init_card(self):
        self.game_setting_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "游戏设置"),
            self.scroll_widget
        )
        self.game_setting_card = ComboBoxSettingCard(
            "select_team_by_order",
            FIF.SEARCH,
            QT_TRANSLATE_NOOP('ComboBoxSettingCard', '选择队伍方式'),
            QT_TRANSLATE_NOOP('ComboBoxSettingCard', '设置选择队伍方式'),
            texts={
                QT_TRANSLATE_NOOP('ComboBoxSettingCard', '使用队伍名'): False,
                QT_TRANSLATE_NOOP('ComboBoxSettingCard', '使用队伍序号'): True
            },
            parent=self.game_setting_group
        )

        self.game_path_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "启动游戏"),
            self.scroll_widget
        )
        self.game_path_card = BasePushSettingCard(
            QT_TRANSLATE_NOOP("BasePushSettingCard", '修改'),
            FIF.FOLDER,
            QT_TRANSLATE_NOOP("BasePushSettingCard", "游戏路径"),
            cfg.game_path,
            parent=self.game_path_group
        )

        self.personal_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "个性化"),
            self.scroll_widget
        )
        self.language_card = ComboBoxSettingCard(
            "language_in_program",
            FIF.LANGUAGE,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '语言'),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '设置程序 UI 使用的语言'),
            texts=SUPPORTED_LANG_NAME,
            parent=self.personal_group
        )
        self.zoom_card = ComboBoxSettingCard(
            "zoom_scale",
            FIF.ZOOM,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '缩放'),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '设置程序 UI 使用的缩放'),
            texts={
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "跟随系统"): 0,
                "100%": 100,
                "125%": 125,
                "150%": 150,
                "175%": 175,
                "200%": 200,
            },
            parent=self.personal_group
        )

        self.update_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "更新设置"),
            self.scroll_widget
        )
        self.check_update_card = SwitchSettingCard(
            FIF.SYNC,
            QT_TRANSLATE_NOOP("SwitchSettingCard", '加入预览版更新渠道'),
            "",
            "update_prerelease_enable",
            parent=self.update_group
        )
        self.update_source_card = ComboBoxSettingCard(
            "update_source",
            FIF.CLOUD_DOWNLOAD,
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '更新源'),
            QT_TRANSLATE_NOOP("ComboBoxSettingCard", '选择更新源'),
            texts={
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "Github源"): "GitHub",
                QT_TRANSLATE_NOOP("ComboBoxSettingCard", "Mirror 酱"): "MirrorChyan"
            },
            parent=self.update_group
        )
        self.mirrorchyan_cdk_card = PushSettingCardMirrorchyan(
            QT_TRANSLATE_NOOP("PushSettingCardMirrorchyan", '修改'),
            FIF.BOOK_SHELF,
            QT_TRANSLATE_NOOP("PushSettingCardMirrorchyan", "Mirror 酱 CDK"),
            self.parent,
            "mirrorchyan_cdk",
            parent=self.update_group,
        )

        self.logs_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "日志设置"),
            self.scroll_widget
        )
        self.logs_clean_card = SwitchSettingCard(
            FIF.BROOM,
            QT_TRANSLATE_NOOP("SwitchSettingCard", '自动清理日志'),
            QT_TRANSLATE_NOOP("SwitchSettingCard", "自动清理一周前的日志"),
            config_name="clean_logs",
            parent=self.logs_group
        )
        self.open_logs_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '日志'),
            FIF.FOLDER_ADD,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '打开日志文件夹'),
            parent=self.logs_group
        )

        self.about_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "关于"),
            self.scroll_widget
        )
        self.github_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '项目主页'),
            FIF.GITHUB,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '项目主页'),
            "https://github.com/KIYI671/AhabAssistantLimbusCompany"
        )
        self.qq_group_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '加入群聊'),
            FIF.EXPRESSIVE_INPUT_ENTRY,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", 'QQ群'),
            "946227774"
        )
        self.feedback_card = BasePrimaryPushSettingCard(
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '提供反馈'),
            FIF.FEEDBACK,
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '提供反馈'),
            QT_TRANSLATE_NOOP("BasePrimaryPushSettingCard", '帮助我们改进 AhabAssistantLimbusCompany')
        )

        self.experimental_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", "实验性内容"),
            self.scroll_widget
        )

        self.auto_lang_card = SwitchSettingCard(
            FIF.DEVELOPER_TOOLS,
            QT_TRANSLATE_NOOP("SwitchSettingCard", '自动检测并切换游戏语言'),
            "",
            config_name="experimental_auto_lang",
            parent=self.experimental_group
        )

    def __initLayout(self):
        self.game_setting_group.addSettingCard(self.game_setting_card)

        self.game_path_group.addSettingCard(self.game_path_card)

        self.personal_group.addSettingCard(self.language_card)
        self.personal_group.addSettingCard(self.zoom_card)

        self.update_group.addSettingCard(self.check_update_card)
        self.update_group.addSettingCard(self.update_source_card)
        self.update_group.addSettingCard(self.mirrorchyan_cdk_card)

        self.logs_group.addSettingCard(self.logs_clean_card)
        self.logs_group.addSettingCard(self.open_logs_card)

        self.about_group.addSettingCard(self.github_card)
        self.about_group.addSettingCard(self.qq_group_card)
        self.about_group.addSettingCard(self.feedback_card)

        self.experimental_group.addSettingCard(self.auto_lang_card)

        self.expand_layout.addWidget(self.game_setting_group)
        self.expand_layout.addWidget(self.game_path_group)
        self.expand_layout.addWidget(self.personal_group)
        self.expand_layout.addWidget(self.update_group)
        self.expand_layout.addWidget(self.logs_group)
        self.expand_layout.addWidget(self.about_group)
        self.expand_layout.addWidget(self.experimental_group)

    def set_style_sheet(self):
        self.setStyleSheet("""
                SettingInterface, #scrollWidget {
                    background-color: #fdfdfd;
                }
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
            """)

    def __connect_signal(self):
        self.game_path_card.clicked.connect(self.__onGamePathCardClicked)
        self.open_logs_card.clicked.connect(self.__onOpenLogsCardClicked)

        self.zoom_card.valueChanged.connect(self.__onZoomCardValueChanged)
        self.auto_lang_card.switchButton.checkedChanged.connect(self.__onAutoLangCardChecked)

        self.github_card.clicked.connect(self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany"))
        self.qq_group_card.clicked.connect(self.__openUrl("https://qm.qq.com/q/SdgSRPrssg"))
        self.feedback_card.clicked.connect(
            self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany/issues"))

    def __onGamePathCardClicked(self):
        game_path, _ = QFileDialog.getOpenFileName(self, "选择游戏路径", "", "All Files (*)")
        if not game_path or cfg.game_path == game_path:
            return
        cfg.set_value("game_path", game_path)
        self.game_path_card.setContent(game_path)

    def __onOpenLogsCardClicked(self):
        import os
        os.startfile(os.path.abspath("./logs"))

    def __onZoomCardValueChanged(self):
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", '更改将在重新启动后生效'),
            content='',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self
        )
        bar.retranslateUi()

    def __onAutoLangCardChecked(self, Checked):
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", '更改将在重新启动后生效'),
            content='',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=self
        )
        bar.retranslateUi()
        if Checked:
            cfg.set_value("language_in_game", "-")
        else:
            cfg.set_value("language_in_game", "en")

    def __openUrl(self, url):
        return lambda: QDesktopServices.openUrl(QUrl(url))

    def retranslateUi(self):
        self.game_setting_group.retranslateUi()
        self.game_setting_card.retranslateUi()
        self.game_path_card.retranslateUi()
        self.game_path_group.retranslateUi()
        self.personal_group.retranslateUi()
        self.language_card.retranslateUi()
        self.zoom_card.retranslateUi()
        self.update_group.retranslateUi()
        self.update_source_card.retranslateUi()
        self.check_update_card.retranslateUi()
        self.mirrorchyan_cdk_card.retranslateUi()
        self.logs_group.retranslateUi()
        self.logs_clean_card.retranslateUi()
        self.about_group.retranslateUi()
        self.open_logs_card.retranslateUi()
        self.github_card.retranslateUi()
        self.qq_group_card.retranslateUi()
        self.feedback_card.retranslateUi()
