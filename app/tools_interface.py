from PySide6.QtCore import QT_TRANSLATE_NOOP
from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import ScrollArea, ExpandLayout

from app.base_combination import BaseSettingCardGroup, BasePushSettingCard
from app.language_manager import LanguageManager
from tasks import tools


class ToolsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.__init_widget()
        self.__init_card()
        self.__initLayout()
        self.set_style_sheet()
        self.__connect_signal()
        self.setWidget(self.scroll_widget)

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.expand_layout = ExpandLayout(self.scroll_widget)
        self.setWidgetResizable(True)

    def __init_card(self):
        self.tools_group = BaseSettingCardGroup(
            QT_TRANSLATE_NOOP("BaseSettingCardGroup", '工具箱'),
            self.scroll_widget
        )
        self.auto_battle_card = BasePushSettingCard(
            QT_TRANSLATE_NOOP("BasePushSettingCard", '运行'),
            FIF.CAFE,
            QT_TRANSLATE_NOOP("BasePushSettingCard", "自动战斗"),
            QT_TRANSLATE_NOOP("BasePushSettingCard", "这只是一个为你自动按下P键和Enter键的小工具，不要怀抱太多期待"),
            parent=self.tools_group
        )
        self.auto_production_card = BasePushSettingCard(
            QT_TRANSLATE_NOOP("BasePushSettingCard", '运行'),
            FIF.CAFE,
            QT_TRANSLATE_NOOP("BasePushSettingCard", "自动体力换饼"),
            QT_TRANSLATE_NOOP("BasePushSettingCard", "辅助自动换饼小工具，防止体力溢出"),
            parent=self.tools_group
        )
        self.get_screenshot_card = BasePushSettingCard(
            QT_TRANSLATE_NOOP("BasePushSettingCard", '运行'),
            FIF.CAFE,
            QT_TRANSLATE_NOOP("BasePushSettingCard", "截图小工具"),
            QT_TRANSLATE_NOOP("BasePushSettingCard", "辅助截图小工具"),
            parent=self.tools_group
        )

    def __initLayout(self):
        self.tools_group.addSettingCard(self.auto_battle_card)
        self.tools_group.addSettingCard(self.auto_production_card)
        self.tools_group.addSettingCard(self.get_screenshot_card)

        self.expand_layout.addWidget(self.tools_group)

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
        self.auto_battle_card.clicked.connect(lambda: tools.start("battle"))
        self.auto_production_card.clicked.connect(lambda: tools.start("production"))
        self.get_screenshot_card.clicked.connect(lambda: tools.start("screenshot"))

    def retranslateUi(self):
        self.tools_group.retranslateUi()
        self.auto_battle_card.retranslateUi()
        self.auto_production_card.retranslateUi()
        self.get_screenshot_card.retranslateUi()
