import time

import requests
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CheckBox,
    ListWidget,
    PopUpAniStackedWidget,
    PrimaryPushButton,
    isDarkTheme,
)
from qframelesswindow import FramelessDialog, StandardTitleBar

from app import AnnouncementStatus
from app.common.ui_config import (
    get_announcement_content_qss,
    get_announcement_footer_qss,
    get_announcement_list_qss,
    get_announcement_sidebar_qss,
)
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
    def __init__(
        self,
        parent=None,
        title="title",
        content="text",
        content_type="text",
        show_title=True,
    ):
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
        if show_title:
            if content_type == "html":
                # 在内容前添加标题
                styled_content = (
                    f"<h1 style='margin-bottom: 20px;'>{title}</h1>" + content
                )
                self.content.setHtml(styled_content)
            elif content_type == "markdown":
                try:
                    # 在内容前添加标题
                    styled_content = f"# {title}\n\n" + content
                    self.content.setMarkdown(styled_content)
                except Exception:
                    # 兼容性回退
                    styled_content = f"{title}\n\n" + content
                    self.content.setText(styled_content)
            else:
                # 默认为纯文本
                styled_content = f"{title}\n\n" + content
                self.content.setText(styled_content)
        else:
            if content_type == "html":
                self.content.setHtml(content)
            elif content_type == "markdown":
                try:
                    self.content.setMarkdown(content)
                except Exception:
                    self.content.setText(content)
            else:
                self.content.setText(content)

        self.layout().addWidget(self.content)

    def get_markdown(self) -> str:
        """返回可用于合并到 ALL 页的 markdown 文本。
        若原始为 HTML 或纯文本，会直接返回原始内容（调用方可根据需要转换）。
        """
        return self.raw_content


class AnnouncementBoard(FramelessDialog):
    def __init__(self, anno, time, parent=None):
        super().__init__(parent=parent)

        # 设置标题栏
        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.raise_()
        # 隐藏标题栏按钮
        self.titleBar.minBtn.hide()
        self.titleBar.maxBtn.hide()
        self.titleBar.closeBtn.hide()

        # 设置模态
        self.setWindowModality(Qt.WindowModal)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 32, 0, 0)  # 留出标题栏高度
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        self.resize(800, 580)
        self.setMinimumSize(700, 500)
        self.setFont(QFont("Microsoft YaHei", 13))
        self.setWindowIcon(QIcon("./assets/logo/my_icon_256X256.ico"))
        self.setWindowTitle(self.tr("公告"))

        # ========== 左侧侧边栏 ==========
        self.sidebar = QFrame()
        self.sidebar.setObjectName("announcementSidebar")
        self.sidebar.setFixedWidth(180)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        # 侧边栏头部（带图标和标题） - 已移除
        # self.header_widget = QWidget()
        # ...

        # 标题列表
        self.title_list = ListWidget()
        self.title_list.setSpacing(5)
        self.title_list.setContentsMargins(0, 10, 0, 0)  # 增加顶部间距代替头部
        self.title_list.currentRowChanged.connect(self.on_title_clicked)
        self.title_list.addItem(QListWidgetItem(self.tr("ALL~ 全部公告")))

        self.sidebar_layout.addWidget(self.title_list)

        # ========== 右侧内容区 ==========
        self.right_panel = QVBoxLayout()
        self.right_panel.setContentsMargins(0, 0, 0, 0)
        self.right_panel.setSpacing(0)

        # 内容栈
        self.content_stack = PopUpAniStackedWidget()
        self.right_panel.addWidget(self.content_stack, 1)

        # ========== 底部按钮区 ==========
        self.footer = QFrame()
        self.footer.setObjectName("announcementFooter")
        self.footer.setFixedHeight(60)
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(20, 10, 20, 10)
        self.footer_layout.setSpacing(15)

        # 复选框
        self.dontShowCheckbox = CheckBox(self.tr("下次公告更新前不再显示"))
        self.dontShowCheckbox.setChecked(False)
        self.dontShowCheckbox.setEnabled(False)  # 初始禁用，滚动到底部后启用

        # 确认按钮
        self.yesButton = PrimaryPushButton(self.tr("确认"))
        self.yesButton.setFixedWidth(100)
        self.yesButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.yesButton.clicked.connect(self.accept)
        self.yesButton.setEnabled(False)  # 初始禁用，滚动到底部后启用

        self.footer_layout.addWidget(self.dontShowCheckbox, 0, Qt.AlignVCenter)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.yesButton, 0, Qt.AlignVCenter)

        self.right_panel.addWidget(self.footer)

        # ========== 组装主布局 ==========
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.right_panel, 1)

        # 创建ALL公告页面
        # 创建ALL公告页面
        msg = self.tr("滚动至底部可关闭公告")
        content = (
            f"<h4>{msg}</h4>"
            "<h3>Ahab Assistant Limbus Company</h3>"
            f"<h3>{cfg.version}</h3>"
        )
        self.all = Announcement(
            None,
            self.tr("ALL~ 全部公告"),
            content,
            content_type="markdown",
            show_title=False,
        )
        self.content_stack.addWidget(self.all)

        # 存储标题和内容的映射
        self.title_content_map = {self.tr("ALL~ 全部公告"): self.all}
        # 存储 ALL 页的合并 markdown 文本
        self.all_markdown = str(self.all.content.toMarkdown())

        # 跟踪当前活动的滚动区域
        self.current_scroll_area = None

        # 连接滚动事件
        self.setup_scroll_handlers()

        self.set_announcement(anno)

        self.announcement_time = time

        # 应用主题样式
        self._apply_styles()

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
                f"<h4>   </h4>"
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
                f"<h4>   </h4>"
                "<h2>Ahab Assistant Limbus Company</h2>"
                f"<h2>{cfg.version}</h2>"
                "<h3>Disclaimer:</h3>"
                "<p>This program is <font color='green'>open-source and free</font>, intended solely for learning and exchange purposes. It operates using computer image recognition and simulated operations,"
                "Will not engage in any actions that harm the game itself—such as modifying game files, reading/writing game memory, or other similar activities"
                "Any issues arising from your use of this program (excluding those caused by program errors) are unrelated to it, and <b>you bear full responsibility for the corresponding consequences</b>.</p>"
                "Please do not discuss anything related to AALC under the official posts of Limbus Company or the Project Moon across various platforms.<br>"
                "In plain terms: Let’s not poke the official bear with AALC talk～(∠・ω&lt; )⌒☆</html>"
            )
        self.add(Announcement(None, title_name, msg, content_type="html"))

    def setup_scroll_handlers(self):
        """设置滚动事件处理"""
        # 为ALL页面设置滚动监听
        if hasattr(self.all.content, "verticalScrollBar"):
            scroll_bar = self.all.content.verticalScrollBar()
            scroll_bar.valueChanged.connect(
                lambda: self.check_scroll_position(self.tr("ALL~ 全部公告"))
            )

        # 监听内容栈切换事件，以便为新显示的页面设置滚动监听
        self.content_stack.currentChanged.connect(self.on_stack_changed)

    def on_stack_changed(self, index):
        """当切换到新的内容页面时，设置滚动监听"""
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
                # 复选框在滚动到底部后启用
                self.dontShowCheckbox.setEnabled(is_at_bottom)

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
                self.all_markdown += f"\n\n---\n\n# {title}\n\n" + new_md
            else:
                self.all_markdown = f"# {title}\n\n" + new_md
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
        self.check_scroll_position(self.tr("ALL~ 全部公告"))

    @Slot(int)
    def on_title_clicked(self, index):
        """当用户点击左侧标题栏时，切换右侧内容栏"""
        self.content_stack.setCurrentIndex(index)

    def setDefault(self, index: int):
        self.title_list.setCurrentRow(index)
        self.all.content.verticalScrollBar().setValue(0)
        # 确保按钮和复选框初始为禁用状态
        self.yesButton.setEnabled(False)
        self.dontShowCheckbox.setEnabled(False)

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        # 如果选中了复选框，则记录公告时间戳
        if self.dontShowCheckbox.isChecked():
            cfg.set_value("announcement", self.announcement_time + 1)
        super().accept()

    def _apply_styles(self):
        """应用主题样式到各个组件"""
        # 获取样式
        light_sidebar, dark_sidebar = get_announcement_sidebar_qss()
        light_list, dark_list = get_announcement_list_qss()
        light_content, dark_content = get_announcement_content_qss()
        light_footer, dark_footer = get_announcement_footer_qss()

        if isDarkTheme():
            self.sidebar.setStyleSheet(dark_sidebar)
            self.title_list.setStyleSheet(dark_list)
            self.footer.setStyleSheet(dark_footer)
            # 应用内容区样式
            self._apply_content_style(dark_content)
            # 设置标题栏样式
            self.titleBar.setStyleSheet(
                """
                TitleBar {
                    background-color: rgba(45, 45, 45, 1);
                    color: white;
                }
                TitleBar > QLabel#titleLabel {
                    color: white;
                }
                """
            )
            self.setStyleSheet(
                "AnnouncementBoard { background-color: rgba(28, 28, 28, 1); }"
            )
        else:
            self.sidebar.setStyleSheet(light_sidebar)
            self.title_list.setStyleSheet(light_list)
            self.footer.setStyleSheet(light_footer)
            self._apply_content_style(light_content)
            # 设置标题栏样式
            self.titleBar.setStyleSheet(
                """
                TitleBar {
                    background-color: rgba(245, 245, 245, 1);
                    color: black;
                }
                TitleBar > QLabel#titleLabel {
                    color: black;
                }
                """
            )
            self.setStyleSheet("AnnouncementBoard { background-color: white; }")

    def _apply_content_style(self, qss: str):
        """应用内容区域样式并加载 Markdown CSS"""
        # 应用 QSS 样式
        for title, widget in self.title_content_map.items():
            if hasattr(widget, "content"):
                widget.content.setStyleSheet(qss)

        # 加载 GitHub Markdown 样式
        css_path = (
            "./assets/styles/github-markdown-dark.css"
            if isDarkTheme()
            else "./assets/styles/github-markdown-light.css"
        )
        try:
            with open(css_path, encoding="utf-8") as f:
                css_content = f.read()
                for title, widget in self.title_content_map.items():
                    if hasattr(widget, "content") and hasattr(
                        widget.content, "document"
                    ):
                        widget.content.document().setDefaultStyleSheet(css_content)
        except Exception:
            pass  # 样式加载失败时使用默认样式
