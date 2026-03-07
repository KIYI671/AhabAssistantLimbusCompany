from PySide6.QtCore import QPoint, QCoreApplication, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QWidget


class SettingNav(QFrame):
    """侧边导航栏组件"""

    # 当导航栏按钮被点击时发出信号，传递目标 widget 供右侧滚动区域定位
    navClicked = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("navFrame")
        self.setFixedWidth(200)

        self.nav_layout = QVBoxLayout(self)
        self.nav_layout.setContentsMargins(10, 10, 10, 10)
        self.nav_layout.setSpacing(4)

        self.nav_items = []
        self.nav_buttons: dict[str, QPushButton] = {}
        self._current_nav: str | None = None

    def add_nav_items(self, items: list[tuple[str, str, object]]):
        """初始化导航栏组件
        :param items: ordered navigation items: (key, title, widget)
        """
        self.nav_items = items
        for key, title, _widget in self.nav_items:
            btn = QPushButton(title)
            btn.setObjectName(f"navButton_{key}")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setMinimumHeight(32)
            btn.clicked.connect(self.__make_nav_click_handler(key))
            self.nav_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        self.nav_layout.addStretch(1)
        if self.nav_items:
            self.set_active_nav(self.nav_items[0][0], emit_signal=False)

    def __make_nav_click_handler(self, key: str):
        """生成导航栏按钮的点击事件处理函数
        Factory to create click handlers with proper key capture (avoids late binding issues)
        """

        def handler():
            self.set_active_nav(key, emit_signal=True)

        return handler

    def set_active_nav(self, key: str, emit_signal: bool = True):
        """设置当前激活的导航栏项目
        :param key: 导航栏项目的标识符
        :param emit_signal: 是否发出 navClicked 通知以便外部滚动
        """
        if key not in self.nav_buttons:
            return
        self._current_nav = key
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

        if emit_signal:
            for k, _title, widget in self.nav_items:
                if k == key:
                    self.navClicked.emit(k, widget)
                    break

    def process_content_scrolled(self, value: int, scroll_widget: QWidget):
        """处理右侧内容区域的滚动事件
        根据当前滚动条的位置，计算哪个卡片组最靠近顶部，并自动高亮左侧导航栏的对应项目
        """
        if not self.nav_items:
            return
        closest_key = None
        closest_delta = None
        for key, _title, widget in self.nav_items:
            y = widget.mapTo(scroll_widget, QPoint(0, 0)).y()
            delta = abs(y - value)
            if closest_delta is None or delta < closest_delta:
                closest_delta = delta
                closest_key = key
        if closest_key and closest_key != self._current_nav:
            self.set_active_nav(closest_key, emit_signal=False)

    def retranslateUi(self):
        """更新导航栏项目的多语言翻译"""
        for key, title_key, _widget in self.nav_items:
            if key in self.nav_buttons:
                translated_title = QCoreApplication.translate("Nav", title_key)
                self.nav_buttons[key].setText(translated_title)
