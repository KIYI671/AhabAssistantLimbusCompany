import sys
from PyQt5.QtWidgets import QApplication, QMessageBox


def show_error_message(message):
    app = QApplication(sys.argv)
    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Critical)
    error_box.setWindowTitle("Error！")
    error_box.setText("发生错误")
    error_box.setInformativeText(message)
    error_box.setStandardButtons(QMessageBox.Ok)
    error_box.exec_()


def show_error_box(message):
    show_error_message(message)
