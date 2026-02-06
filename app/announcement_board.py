import time

import requests
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QListWidgetItem,
    QSizePolicy,
    QSpacerItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ListWidget, PrimaryPushButton
from qfluentwidgets import PopUpAniStackedWidget

from app import AnnouncementStatus
from module.config import cfg
from module.logger import log


class AnnouncementThread(QThread):
    """
    公告线程类，用于在后台检查和处理公告更新。
    该类继承自 QThread，使用 Qt 的信号机制来通知 GUI 线程更新状态。
    """

    AnnouncementSignal = Signal(AnnouncementStatus)

    def __init__(self):
        """
        初始化公告线程。
        """
        super().__init__()

    def run(self) -> None:
        """
        公告线程的主逻辑。
        检查是否有新公告，如果有，则发送公告可用信号；否则发送成功信号。
        """
        try:
            url = "https://gitee.com/KIYI/aalcresource/raw/main/AALC/announcements.json"

            response = requests.get(url)
            response.raise_for_status()  # 如果状态码非200则抛出异常

            # 解析 JSON 数据
            announcements = response.json()
            time_str = announcements["Time"]
            time_struct = time.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            target_timestamp = time.mktime(time_struct)
            current_timestamp = cfg.announcement
            if current_timestamp > target_timestamp:
                self.AnnouncementSignal.emit(AnnouncementStatus.SUCCESS)
                return
            self.announcement_time = target_timestamp
            self.announcement = announcements["Announcement"]
            self.AnnouncementSignal.emit(AnnouncementStatus.ANNO_AVAILABLE)
        except Exception as e:
            log.error(f"获取公告失败:{e}")
            self.AnnouncementSignal.emit(AnnouncementStatus.FAILURE)


class Announcement(QWidget):
    def __init__(self, parent=None, title="title", content="text", content_type="text"):
        super().__init__(parent)
        self.title = title
        # 保存原始内容（raw_content）以便合并到 ALL 页面时使用
        self.raw_content = content
        self.content_type = content_type

        self.setLayout(QVBoxLayout())
        self.content = QTextBrowser(self)
        self.content.setOpenExternalLinks(True)
        self.content.setAutoFillBackground(True)

        # 根据 content_type 渲染内容
        if content_type == "html":
            self.content.setHtml(content)
        elif content_type == "markdown":
            try:
                self.content.setMarkdown(content)
            except Exception:
                # 兼容性回退：若不支持 setMarkdown 则设置为纯文本
                self.content.setText(content)
        else:
            # 默认为纯文本
            self.content.setText(content)

        self.layout().addWidget(self.content)

    def get_markdown(self) -> str:
        """返回可用于合并到 ALL 页的 markdown 文本。
        若原始为 HTML 或纯文本，会直接返回原始内容（调用方可根据需要转换）。
        """
        return self.raw_content


class AnnouncementBoard(QDialog):
    def __init__(self, anno, time, parent=None):
        super().__init__(parent=parent)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.resize(750, 550)
        self.setFont(QFont("MicroSoft YaHei", 13))
        self.setWindowIcon(QIcon("./assets/logo/my_icon_256X256.ico"))
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowTitle(self.tr("公告"))

        # 左侧标题栏
        self.title_list = ListWidget()
        self.title_list.setSpacing(10)
        self.title_list.setFixedWidth(150)  # 固定宽度
        self.title_list.currentRowChanged.connect(self.on_title_clicked)
        self.title_list.addItem(QListWidgetItem("ALL"))

        # 右侧内容栏
        self.right_content_bar = QGridLayout()
        self.content_stack = PopUpAniStackedWidget()
        self.right_content_bar.addWidget(self.content_stack, 0, 0, 1, 3)
        horizontal_spacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.right_content_bar.addItem(horizontal_spacer, 1, 0, 1, 1)

        self.buttonGroup = QFrame(parent)
        self.yesButton = PrimaryPushButton(
            self.tr("新公告前不再显示"), self.buttonGroup
        )
        self.cancelButton = PrimaryPushButton(self.tr("关闭"), self.buttonGroup)
        self.yesButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.cancelButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.yesButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.button_widget = QWidget(self.buttonGroup)
        self.buttonLayout = QHBoxLayout(self.button_widget)
        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)

        self.right_content_bar.addWidget(self.button_widget, 1, 1, 1, 1)

        # 创建ALL公告页面
        msg = self.tr("滚动至底部可关闭公告")
        self.all = Announcement(
            None,
            "ALL",
            f"<h4>{msg}</h4>"
            "<h3>Ahab Assistant Limbus Company</h3>"
            f"<h3>{cfg.version}</h3>",
            content_type="markdown",
        )
        self.content_stack.addWidget(self.all)

        # 存储标题和内容的映射
        self.title_content_map = {"ALL": self.all}
        # 存储 ALL 页的合并 markdown 文本
        self.all_markdown = str(self.all.content.toMarkdown())

        # 添加到主布局
        self.main_layout.addWidget(self.title_list)
        self.main_layout.addLayout(self.right_content_bar)

        # 跟踪当前活动的滚动区域
        self.current_scroll_area = None

        # 连接滚动事件
        self.setup_scroll_handlers()

        self.set_announcement(anno)

        self.announcement_time = time

    def set_announcement(self, announcements):
        """设置公告"""
        for anno in announcements:
            self.add(
                Announcement(
                    None,
                    anno["title"],
                    anno["content"],
                    anno.get("contentType", "markdown"),
                )
            )

        title_name = self.tr("长期公告")
        if cfg.language_in_program == "zh_cn":
            msg = (
                f"<h4>{title_name}</h4>"
                "<h2>Ahab Assistant Limbus Company</h2>"
                f"<h2>{cfg.version}</h2>"
                "<h3>声明：</h3>"
                "<p>本程序<font color='green'>开源、免费</font>，仅供学习交流使用。本程序依靠计算机图像识别和模拟操作运行，"
                "不会做出任何修改游戏文件、读写游戏内存等任何危害游戏本体的行为。"
                "您在使用此程序中产生的任何问题（除程序错误导致外）与此程序无关，<b>相应的后果由您自行承担</b>。</p>"
                "请不要在边狱巴士及月亮计划在各平台的官方动态下讨论任何关于 AALC 的内容。<br>"
                "人话：不要跳脸官方～(∠・ω&lt; )⌒☆</html>"
            )
        else:
            msg = (
                f"<h4>{title_name}</h4>"
                "<h2>Ahab Assistant Limbus Company</h2>"
                f"<h2>{cfg.version}</h2>"
                "<h3>Disclaimer:</h3>"
                "<p>This program is <font color='green'>open-source and free</font>, intended solely for learning and exchange purposes. It operates using computer image recognition and simulated operations,"
                "Will not engage in any actions that harm the game itself—such as modifying game files, reading/writing game memory, or other similar activities"
                "Any issues arising from your use of this program (excluding those caused by program errors) are unrelated to it, and <b>you bear full responsibility for the corresponding consequences</b>.</p>"
                "Please do not discuss anything related to AALC under the official posts of Limbus Company or the Project Moon across various platforms.<br>"
                "In plain terms: Let’s not poke the official bear with AALC talk～(∠・ω&lt; )⌒☆</html>"
            )
        self.add(Announcement(None, title_name, msg))

    def setup_scroll_handlers(self):
        """设置滚动事件处理"""
        # 为ALL页面设置滚动监听
        if hasattr(self.all.content, "verticalScrollBar"):
            scroll_bar = self.all.content.verticalScrollBar()
            scroll_bar.valueChanged.connect(lambda: self.check_scroll_position("ALL"))

        # 监听内容栈切换事件，以便为新显示的页面设置滚动监听
        self.content_stack.currentChanged.connect(self.on_stack_changed)

    def on_stack_changed(self, index):
        """当切换到新的内容页面时，设置滚动监听"""
        # 移除之前页面的滚动监听
        if self.current_scroll_area and hasattr(
            self.current_scroll_area, "verticalScrollBar"
        ):
            scroll_bar = self.current_scroll_area.verticalScrollBar()
            try:
                scroll_bar.valueChanged.disconnect(self.check_current_scroll_position)
            except TypeError:
                pass  # 如果没有连接过，忽略错误

        # 获取当前页面并设置新的滚动监听
        current_widget = self.content_stack.widget(index)
        if (
            current_widget
            and hasattr(current_widget, "content")
            and hasattr(current_widget.content, "verticalScrollBar")
        ):
            self.current_scroll_area = current_widget.content
            scroll_bar = self.current_scroll_area.verticalScrollBar()
            scroll_bar.valueChanged.connect(self.check_current_scroll_position)
            # 检查当前滚动位置
            self.check_current_scroll_position(scroll_bar.value())

    def check_current_scroll_position(self, value):
        """检查当前活动页面的滚动位置"""
        if not self.current_scroll_area:
            return

        current_title = self.title_list.currentItem().text()
        self.check_scroll_position(current_title)

    def check_scroll_position(self, title):
        """检查指定页面是否滚动到底部"""
        # 已经有一次确认，就不需要重复检查
        if self.yesButton.isEnabled():
            return
        # 获取对应页面的内容部件
        if title in self.title_content_map:
            widget = self.title_content_map[title]
            if hasattr(widget.content, "verticalScrollBar"):
                scroll_bar = widget.content.verticalScrollBar()
                # 检查是否滚动到底部（考虑一定的容差，例如10像素）
                is_at_bottom = scroll_bar.value() + 10 >= scroll_bar.maximum()
                # 更新按钮状态
                self.yesButton.setEnabled(is_at_bottom)
                self.cancelButton.setEnabled(is_at_bottom)

    def add(self, dialog: Announcement):
        """添加一个公告条目"""
        # 将标题添加到左侧标题栏
        title = dialog.title
        dialog.setParent(self)
        self.title_list.addItem(title)

        # 将内容添加到右侧内容栏
        self.content_stack.addWidget(dialog)

        # 保存标题和内容的映射关系
        self.title_content_map[title] = dialog
        # 使用 Announcement.raw_content（通过 get_markdown）合并到 ALL 页面
        # 为避免 QTextBrowser.append 在 markdown 渲染上产生问题，使用 setMarkdown
        new_md = dialog.get_markdown()
        if new_md:
            # 用分隔符分隔不同公告，保留原始 markdown
            if self.all_markdown:
                self.all_markdown += "\n\n---\n\n" + new_md
            else:
                self.all_markdown = new_md
            try:
                # 尝试直接以 markdown 设置 ALL 页内容
                self.all.content.setMarkdown(self.all_markdown)
            except Exception:
                # 兼容性回退：若 setMarkdown 不可用，则设置为纯文本
                self.all.content.setText(self.all_markdown)

        # 为新添加的公告设置滚动监听
        if hasattr(dialog.content, "verticalScrollBar"):
            scroll_bar = dialog.content.verticalScrollBar()

            def _on_value_changed(val, t=title):
                self.check_scroll_position(t)

            scroll_bar.valueChanged.connect(_on_value_changed)

        # 重新检查ALL页面的滚动状态，因为内容已更新
        self.check_scroll_position("ALL")

    @Slot(int)
    def on_title_clicked(self, index):
        """当用户点击左侧标题栏时，切换右侧内容栏"""
        self.content_stack.setCurrentIndex(index)

    def setDefault(self, index: int):
        self.title_list.setCurrentRow(index)
        self.all.content.verticalScrollBar().setValue(0)
        # 确保按钮初始为禁用状态
        self.yesButton.setEnabled(False)
        self.cancelButton.setEnabled(False)

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        cfg.set_value("announcement", self.announcement_time + 1)
        super().accept()
