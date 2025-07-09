from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import MessageBox, BodyLabel, FluentStyleSheet, PrimaryPushButton, LineEdit


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

        # 添加新的跳转按钮
        self.jumpButton = PrimaryPushButton(self.tr('跳转 / JUMP'), self.buttonGroup)
        self.jumpButton.adjustSize()
        self.jumpButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.jumpButton.setFocus()
        # self.jumpButton = QPushButton('跳转', parent)
        self.jumpButton.clicked.connect(
            lambda: self.open_url('https://github.com/KIYI671/AhabAssistantLimbusCompany/releases'))

        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.jumpButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)
        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignTop)

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

class MessageBoxUpdate(MessageBoxHtml):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.yesButton.setText('下载 / DOWNLOAD')
        self.cancelButton.setText('好的 / OK')


class MessageBoxEdit(MessageBox):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(title, content, parent)

        self.textLayout.removeWidget(self.contentLabel)
        self.contentLabel.clear()

        self.yesButton.setText('确认')
        self.cancelButton.setText('取消')

        self.lineEdit = LineEdit(self)
        self.lineEdit.setText(self.content)
        self.textLayout.addWidget(self.lineEdit, 0, Qt.AlignTop)

        self.buttonGroup.setMinimumWidth(400)

    def getText(self):
        return self.lineEdit.text()