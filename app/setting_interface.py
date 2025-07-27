from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QFileDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import ScrollArea, ExpandLayout, SettingCardGroup, PushSettingCard, \
    PrimaryPushSettingCard

from app.base_combination import ComboBoxSettingCard, SwitchSettingCard, PushSettingCardMirrorchyan
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

    def __init_widget(self):
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.setWidgetResizable(True)

    def __init_card(self):
        self.game_setting_group = SettingCardGroup("游戏设置", self.scroll_widget)
        self.game_setting_card = ComboBoxSettingCard(
            "select_team_by_order",
            FIF.SEARCH,
            self.tr('选择队伍方式'),
            self.tr('设置选择队伍方式'),
            texts={'使用队伍名':False, '使用队伍序号':"en"},
            parent=self.game_setting_group
        )

        self.game_path_group = SettingCardGroup("游戏路径", self.scroll_widget)
        self.game_path_card = PushSettingCard(
            self.tr('修改'),
            FIF.FOLDER,
            self.tr("游戏路径"),
            cfg.game_path,
            parent=self.game_path_group
        )

        self.personal_group = SettingCardGroup("个性化", self.scroll_widget)
        self.language_card = ComboBoxSettingCard(
            "language_in_program",
            FIF.LANGUAGE,
            self.tr('语言'),
            self.tr('设置程序 UI 使用的语言'),
            texts={'简体中文':"zh_cn", 'English':"en"},
            parent=self.personal_group
        )

        self.update_group = SettingCardGroup("更新设置", self.scroll_widget)
        self.check_update_card = SwitchSettingCard(
            FIF.SYNC,
            self.tr('检查更新'),
            "启用检查更新功能",
            "check_update",
            parent=self.update_group
        )
        self.update_source_card = ComboBoxSettingCard(
            "update_source",
            FIF.CLOUD_DOWNLOAD,
            self.tr('更新源'),
            self.tr('选择更新源'),
            texts={"Github源": "GitHub", "Mirror 酱": "MirrorChyan"},
            parent=self.update_group
        )
        self.mirrorchyan_cdk_card = PushSettingCardMirrorchyan(
            self.tr('修改'),
            FIF.BOOK_SHELF,
            self.tr("Mirror 酱 CDK"),
            self.update_group,
            "mirrorchyan_cdk"
        )

        self.logs_group = SettingCardGroup("日志设置", self.scroll_widget)
        self.logs_clean_card = SwitchSettingCard(
            FIF.BROOM,
            self.tr('自动清理日志'),
            "自动清理一周前的日志",
            config_name="clean_logs",
            parent=self.logs_group
        )
        self.open_logs_card = PrimaryPushSettingCard(
            self.tr('日志'),
            FIF.FOLDER_ADD,
            self.tr('打开日志文件夹'),
            parent=self.logs_group
        )

        self.about_group = SettingCardGroup("关于", self.scroll_widget)
        self.github_card = PrimaryPushSettingCard(
            self.tr('项目主页'),
            FIF.GITHUB,
            self.tr('项目主页'),
            "https://github.com/KIYI671/AhabAssistantLimbusCompany"
        )
        self.qq_group_card = PrimaryPushSettingCard(
            self.tr('加入群聊'),
            FIF.EXPRESSIVE_INPUT_ENTRY,
            self.tr('QQ群'),
            "946227774"
        )
        self.feedback_card = PrimaryPushSettingCard(
            self.tr('提供反馈'),
            FIF.FEEDBACK,
            self.tr('提供反馈'),
            self.tr('帮助我们改进 AhabAssistantLimbusCompany')
        )

    def __initLayout(self):
        self.game_setting_group.addSettingCard(self.game_setting_card)

        self.game_path_group.addSettingCard(self.game_path_card)

        self.personal_group.addSettingCard(self.language_card)

        self.update_group.addSettingCard(self.check_update_card)
        self.update_group.addSettingCard(self.update_source_card)
        self.update_group.addSettingCard(self.mirrorchyan_cdk_card)

        self.logs_group.addSettingCard(self.logs_clean_card)
        self.logs_group.addSettingCard(self.open_logs_card)

        self.about_group.addSettingCard(self.github_card)
        self.about_group.addSettingCard(self.qq_group_card)
        self.about_group.addSettingCard(self.feedback_card)

        self.expand_layout.addWidget(self.game_setting_group)
        self.expand_layout.addWidget(self.game_path_group)
        self.expand_layout.addWidget(self.personal_group)
        self.expand_layout.addWidget(self.update_group)
        self.expand_layout.addWidget(self.logs_group)
        self.expand_layout.addWidget(self.about_group)

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

        self.github_card.clicked.connect(self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany"))
        self.qq_group_card.clicked.connect(self.__openUrl("https://qm.qq.com/q/SdgSRPrssg"))
        self.feedback_card.clicked.connect(self.__openUrl("https://github.com/KIYI671/AhabAssistantLimbusCompany/issues"))

    def __onGamePathCardClicked(self):
        game_path, _ = QFileDialog.getOpenFileName(self, "选择游戏路径", "", "All Files (*)")
        if not game_path or cfg.game_path == game_path:
            return
        cfg.set_value("game_path", game_path)
        self.game_path_card.setContent(game_path)

    def __onOpenLogsCardClicked(self):
        import os
        os.startfile(os.path.abspath("./logs"))

    def __openUrl(self, url):
        return lambda: QDesktopServices.openUrl(QUrl(url))