import datetime

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QSizePolicy
from qfluentwidgets import MessageBox, BodyLabel, FluentStyleSheet, \
    PrimaryPushButton, LineEdit, ScrollArea, InfoBar, DateTimeEdit, SpinBox
from qfluentwidgets.common.icon import FluentIconBase
from qfluentwidgets.components.widgets.info_bar import InfoBarIcon, InfoBarPosition

from module.config import cfg


class MessageBoxHtml(MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.buttonLayout.removeWidget(self.yesButton)
        self.buttonLayout.removeWidget(self.cancelButton)
        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.contentLabel = BodyLabel(content, parent)
        self.contentLabel.setObjectName('contentLabel')
        self.contentLabel.setOpenExternalLinks(True)
        self.contentLabel.linkActivated.connect(self.open_url)
        self.contentLabel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        FluentStyleSheet.DIALOG.apply(self.contentLabel)
        self.contentLabel.setWordWrap(True)  # 启用自动换行

        # 创建滚动区域并配置
        self.scrollArea = ScrollArea(self.widget)
        self.scrollArea.setWidgetResizable(True)  # 允许内容扩展
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.scrollArea.setWidget(self.contentLabel)  # 将内容标签放入滚动区域
        # 设置 ScrollArea 的最小高度
        self.scrollArea.setMinimumHeight(300)

        # 添加新的跳转按钮

        self.jumpButton = PrimaryPushButton('跳转', self.buttonGroup)
        self.jumpButton.adjustSize()
        self.jumpButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.jumpButton.setFocus()
        # self.jumpButton = QPushButton('跳转', parent)
        self.jumpButton.clicked.connect(
            lambda: self.open_url('https://github.com/KIYI671/AhabAssistantLimbusCompany/releases'))

        # 调整按钮组的大小策略（关键！）
        button_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.buttonGroup.setSizePolicy(button_policy)
        self.buttonGroup.setMinimumWidth(750)  # 保留最小宽度，但移除固定高度
        # self.buttonGroup.setMinimumHeight(500)  # 移除这行！避免固定高度挤压上方空间

        # 重新添加控件到布局（调整顺序和拉伸因子）
        # textLayout中滚动区域占满空间（拉伸因子1）
        self.textLayout.addWidget(self.scrollArea, 0, Qt.AlignTop)
        self.textLayout.setContentsMargins(24, 24, 24, 24)  # 保持边距合理
        self.textLayout.setSpacing(12)  # 保持内边距合理

        # buttonLayout中按钮均匀分布（拉伸因子1）
        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.jumpButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)
        self.buttonLayout.setSpacing(12)
        self.buttonLayout.setContentsMargins(24, 24, 24, 24)

        # 调整主布局的空间分配（textLayout占剩余空间）
        main_layout = self.layout()  # 获取主垂直布局（vBoxLayout）
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除主布局边距（可选）
        main_layout.setSpacing(0)  # 移除主布局内边距（可选）

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))


class MessageBoxUpdate(MessageBoxHtml):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.yesButton.setText(self.tr('下载'))
        self.cancelButton.setText(self.tr('好的'))
        self.jumpButton.setText(self.tr('跳转'))


class MessageBoxConfirm(MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.buttonLayout.removeWidget(self.yesButton)
        self.buttonLayout.removeWidget(self.cancelButton)
        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.contentLabel = BodyLabel(content, parent)
        self.contentLabel.setObjectName("contentLabel")
        self.contentLabel.setOpenExternalLinks(True)
        self.contentLabel.linkActivated.connect(self.open_url)
        self.contentLabel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        FluentStyleSheet.DIALOG.apply(self.contentLabel)

        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)
        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignTop)

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))


class MessageBoxEdit(MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.text = title

        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.yesButton.setText(self.tr("确认"))
        self.cancelButton.setText(self.tr("取消"))

        self.lineEdit = LineEdit(self)
        self.lineEdit.setText(self.content)
        self.lineEdit.returnPressed.connect(self.yesButton.click)

        self.textLayout.addWidget(self.lineEdit, 0, Qt.AlignTop)

        self.buttonGroup.setMinimumWidth(400)

        self.lineEdit.setFocus()

    def getText(self):
        return self.lineEdit.text()

    def retranslateUi(self):
        text = self.tr(self.text)
        self.titleLabel.setText(text)


class MessageBoxWarning(MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.yesButton.setText(self.tr('我已了解以上信息'))
        self.cancelButton.setHidden(True)


class BaseInfoBar(InfoBar):
    def __init__(self, icon: InfoBarIcon | FluentIconBase | QIcon | str, title: str, content: str, orient=Qt.Horizontal,
                 isClosable=True, duration=1000, position=InfoBarPosition.TOP_RIGHT, parent=None):
        super().__init__(icon, title, content, orient, isClosable, duration, position, parent)

    def retranslateUi(self):
        self.titleLabel.setText(self.tr(self.title))
        self.contentLabel.setText(self.tr(self.content))

    @classmethod
    def new(cls, icon, title, content, orient=Qt.Horizontal, isClosable=True, duration=1000,
            position=InfoBarPosition.TOP_RIGHT, parent=None):
        w = BaseInfoBar(icon, title, content, orient,
                        isClosable, duration, position, parent)
        w.show()
        return w

    @classmethod
    def info(cls, title, content, orient=Qt.Horizontal, isClosable=True, duration=1000,
             position=InfoBarPosition.TOP_RIGHT, parent=None):
        return cls.new(InfoBarIcon.INFORMATION, title, content, orient, isClosable, duration, position, parent)

    @classmethod
    def success(cls, title, content, orient=Qt.Horizontal, isClosable=True, duration=1000,
                position=InfoBarPosition.TOP_RIGHT, parent=None):
        return cls.new(InfoBarIcon.SUCCESS, title, content, orient, isClosable, duration, position, parent)

    @classmethod
    def warning(cls, title, content, orient=Qt.Horizontal, isClosable=True, duration=1000,
                position=InfoBarPosition.TOP_RIGHT, parent=None):
        return cls.new(InfoBarIcon.WARNING, title, content, orient, isClosable, duration, position, parent)

    @classmethod
    def error(cls, title, content, orient=Qt.Horizontal, isClosable=True, duration=1000,
              position=InfoBarPosition.TOP_RIGHT, parent=None):
        return cls.new(InfoBarIcon.ERROR, title, content, orient, isClosable, duration, position, parent)


class MessageBoxDate(MessageBox):
    def __init__(self, title: str, content: datetime, parent=None):
        super().__init__(title, "", parent)

        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.yesButton.setText('确认')
        self.cancelButton.setText('取消')

        self.datePicker = DateTimeEdit(self)
        self.datePicker.setDateTime(content)

        self.textLayout.addWidget(self.datePicker, 0, Qt.AlignTop)

        self.buttonGroup.setMinimumWidth(480)

    def getDateTime(self):
        return self.datePicker.dateTime().toPyDateTime()


class MessageBoxSpinbox(MessageBox):
    def __init__(self, title: str, parent=None):
        super().__init__(title, '', parent)

        self.text = title

        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.yesButton.setText(self.tr("确认"))
        self.cancelButton.setText(self.tr("取消"))

        self.box = SpinBox(self)
        self.box.setValue(int(cfg.hard_mirror_chance))
        self.box.setMinimum(0)
        self.box.setMaximum(3)

        self.textLayout.addWidget(self.box, 0, Qt.AlignTop)

        self.buttonGroup.setMinimumWidth(250)

    def getValue(self):
        return self.box.value()

    def retranslateUi(self):
        text = self.tr(self.text)
        self.titleLabel.setText(text)
