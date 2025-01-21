import sys

from PyQt5.QtWidgets import QMainWindow, QApplication
from qfluentwidgets import setThemeColor

from app.main_windows import Ui_MainWindow


class MyDesiger(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyDesiger, self).__init__(parent)
        self.setupUi(self)

        # 设置界面主题为红色
        setThemeColor("#9c080b")

        #
        self.set_windows_button.clicked.connect(self.changePage)
        self.daily_task_button.clicked.connect(self.changePage)
        self.mirror_button.clicked.connect(self.changePage)
        self.buy_enkephalin_button.clicked.connect(self.changePage)
        self.get_reward_button.clicked.connect(self.changePage)
        self.start_with_key_page.clicked.connect(self.changePage)
        self.instructions_page.clicked.connect(self.changePage)
        self.about_page.clicked.connect(self.changePage)

    def changePage(self):
        # 获取发送信号的按钮对象
        button = self.sender()

        if button == self.set_windows_button:
            self.detail_setting.setCurrentIndex(0)
        elif button == self.daily_task_button:
            self.detail_setting.setCurrentIndex(1)
        elif button == self.mirror_button:
            self.detail_setting.setCurrentIndex(2)
        elif button == self.buy_enkephalin_button:
            self.detail_setting.setCurrentIndex(3)
        elif button == self.get_reward_button:
            self.detail_setting.setCurrentIndex(4)
        elif button == self.start_with_key_page:
            self.all_pages.setCurrentIndex(0)
        elif button == self.instructions_page:
            self.all_pages.setCurrentIndex(1)
        elif button == self.about_page:
            self.all_pages.setCurrentIndex(2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MyDesiger()
    ui.show()
    sys.exit(app.exec_())
