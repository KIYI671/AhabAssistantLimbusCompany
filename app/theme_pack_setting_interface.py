from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from qfluentwidgets import (
    BodyLabel,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SubtitleLabel,
    TitleLabel,
)
from qfluentwidgets import FluentIcon as FIF

from app.base_tools import BaseSpinBox
from app.language_manager import LanguageManager
from module.config import theme_list
from module.logger import log


# 主题包 key 到图片文件名的映射表（普通模式）
THEME_PACK_IMAGE_MAP = {
    # 普通模式主题包
    "forgot": "The Forgotten.png",
    "gambl": "Flat-broke Gamblers.png",
    "und": "Nagel and Hammer.png",
    "faith": "Faith & Erosion.png",
    "unconf": "The Unconfronting.png",
    "workshop": "Nest, Workshop, and Technology.png",
    "tearful": "Tearful Things.png",
    "lake": "Lake World.png",
    "dregs": "Dregs of the Manor.png",
    "certain": "A Certain World.png",
    "chick": "Hell's Chicken.png",
    "s.e.a": "ASEA.png",
    "miracle": "Miracle in District 20.png",
    "bullet": "Full-Stopped by a Bullet.png",
    "cleaved": "To be Cleaved.png",
    "penetra": "Piercers & Penetrators.png",
    "pierced": "To be Pierced.png",
    "crushers": "Crushers & Breakers.png",
    "repression": "Emotional Repression.png",
    "addict": "Addicting Lust.png",
    "seduct": "Emotional Seduction.png",
    "dolen": "Emotional Indolence.png",
    "glutton": "Devoured Gluttony.png",
    "cravi": "Emotional Craving.png",
    "gloom": "Degraded Gloom.png",
    "subserv": "Emotional Subservience.png",
    "nsignif": "Insignificant Envy.png",
    "judgment": "Emotional Judgment.png",
    "outcast": "The Outcast.png",
    "curshed": "To be Crushed.png",
    "crushed": "To be Crushed.png",
    "automated": "Automated Factory.png",
    "spring": "Spring Cultivation.png",
    "unloving": "The Unloving.png",
    "flowers": "Falling Flowers.png",
    "abyss": "Crawling Abyss.png",
    "bones": "Yield My Flesh to Claim Their Bones.png",
    "time": "Timekilling Time.png",
    "warp": "Murder on the WARP Express.png",
    "violet": "The Moon of Violet.png",
    "dicers": "Slicers & Dicers.png",
    "wrath": "Unbound Wrath.png",
    "sloth": "Treadwheel Sloth.png",
    "flood": "Emotional Flood.png",
    "vain": "Vain Pride.png",
    "check": "LCB Reguar Checkup.png",
    "sweep": "Nocturnal Sweeping.png",
    "Hatred": "Hatred and Despair.png",
    # 以下主题包暂无对应图片文件
    # "Wander": "The Wander.png",  # 灯客蚣檀/彷徨
    # "compassion": "The Compassion.png",  # 明日方舟联动/巡礼
}

# 英文key到中文名称的映射表（普通模式）
THEME_PACK_NAME_MAP = {
    "forgot": "遗忘",
    "gambl": "赌徒",
    "und": "钉与锤",
    "faith": "信仰",
    "unconf": "无作为",
    "workshop": "工坊",
    "tearful": "落泪",
    "lake": "湖的",
    "dregs": "宅邸",
    "certain": "某个世界",
    "chick": "地狱鸡",
    "s.e.a": "海·边",
    "miracle": "20区的奇迹",
    "bullet": "句点",
    "cleaved": "当斩",
    "penetra": "穿刺者",
    "pierced": "当贯",
    "crushers": "粉碎者",
    "repression": "情感压迫",
    "addict": "沉迷的色欲",
    "seduct": "感情困惑",
    "dolen": "情感懒惰",
    "glutton": "吞噬的暴食",
    "cravi": "情感饥渴",
    "gloom": "没落的忧郁",
    "subserv": "情感屈从",
    "nsignif": "寒微的嫉妒",
    "judgment": "情感评判",
    "outcast": "无归属",
    "curshed": "当碎",
    "crushed": "当碎",
    "automated": "自动化工厂",
    "spring": "琢春",
    "unloving": "无慈悲",
    "flowers": "落花",
    "abyss": "伏行深渊",
    "bones": "骨断",
    "time": "时间杀人",
    "warp": "谋杀",
    "violet": "紫罗兰",
    "dicers": "斩切",
    "wrath": "压抑的暴怒",
    "sloth": "沉溺者",
    "flood": "空转",
    "vain": "虚张声势",
    "check": "体检",
    "sweep": "清扫",
    "Hatred": "绝望",
    "Wander": "彷徨",
    "compassion": "巡礼",
}

# 英文key到中文名称的映射表（困难模式）
THEME_PACK_HARD_NAME_MAP = {
    "20": "20区的奇迹",
    "seismic": "异常震区",
    "extrenal": "破坏性外力",
    "thunder": "电闪雷鸣",
    "sanguine": "渗出的鲜血丝",
    "dizzying": "缭乱之舞",
    "pang": "沉于光芒之海",
    "sigh": "深邃的叹息",
    "supply": "冉冉升起的能量供给",
    "four": "四大家族",
    "opening": "拉曼查兰开园",
    "procession": "无限游行",
    "unchanging": "未改变的",
    "unchang": "未改变的",
    "evil": "定义为恶",
    "heartb": "心意相悖",
    "line": "号线",
    "repressed": "压抑的暴怒",
    "unbound": "解放的暴怒",
    "tangling": "束缚的色欲",
    "inert": "停滞的懒惰",
    "excessive": "漫溢的暴食",
    "sunk": "沉溺的忧郁",
    "pride": "自以为是的傲慢",
    "pitiful": "凄惨的嫉妒",
    "haze": "雾霭氤氲",
    "season": "盛火之季",
    "corpses": "血山",
    "might": "破竹之势",
    "deluge": "沉沦泛滥",
    "poised": "循环呼吸",
    "ending": "梦之终焉",
    "witnessing": "观望",
    "Text": "教材",
    "Blade": "刀与作",
    "Unsever": "割舍",
}

# 主题包 key 到图片文件名的映射表（困难模式）
THEME_PACK_HARD_IMAGE_MAP = {
    "20": "Miracle in District 20.png",
    "seismic": "Abnormal Seismi Zone.png",
    "extrenal": "Crushing External Force.png",
    "thunder": "Thunder and Lightning.png",
    "sanguine": "Trickled Sanguin Blood.png",
    "dizzying": "Dizzying Waves.png",
    "pang": "Sinking Pang.png",
    "sigh": "Deep Sigh.png",
    "supply": "Rising Power Supply.png",
    "four": "Four Houses and Greed.png",
    "opening": "La Manchaland Reopening.png",
    "procession": "The Infinite Procession.png",
    "unchanging": "The Unchanging.png",
    "unchang": "The Unchanging.png",
    "evil": "The Evil Defining.png",
    "heartb": "The Heartbreaking.png",
    "line": "Line 1.png",
    "repressed": "Repressed Wrath.png",
    "unbound": "Unbound Wrath.png",
    "tangling": "Tangling Lust.png",
    "inert": "Inert Sloth.png",
    "excessive": "Excessive Gluttong.png",
    "sunk": "Sunk Gloom.png",
    "pride": "Tyrannical Pride.png",
    "pitiful": "Pitiful Envy.png",
    "haze": "Burning Haze.png",
    "season": "Season of the Flame.png",
    "corpses": "Mountain of Corpses, Sea of Blood.png",
    "might": "Unrelenting Might.png",
    "deluge": "Sinking Deluge.png",
    "poised": "Poised Breathing.png",
    "ending": "The Dream Ending.png",
    "witnessing": "The Surrendered Witnessing.png",
    # 以下主题包暂无对应图片文件
    # "Text": "The Text.png",  # 教材/卢西奥、火蛾
    # "Blade": "The Blade.png",  # 刀与作/黑檀、莲、阿尔比娜
    # "Unsever": "The Unsever.png",  # 割舍/空
    # 轨道线系列（如需支持多条线路，可添加以下映射）
    # "line2": "Line 2.png",
    # "line3": "Line 3.png",
    # "line4_3": "Line 4 Section#3.png",
    # "line4_4": "Line 4 Section#4.png",
    # "line5": "Line 5.png",
}


def get_image_path(pack_key, is_hard=False):
    """获取主题包图片路径"""
    image_map = THEME_PACK_HARD_IMAGE_MAP if is_hard else THEME_PACK_IMAGE_MAP
    # 将key转换为字符串进行比较
    pack_key_str = str(pack_key)
    image_name = image_map.get(pack_key_str, "")
    if image_name:
        return f"./assets/images/share/mirror/theme_pack/theme_packs/{image_name}"
    return ""


class ThemePackCard(QFrame):
    """单个主题包卡片组件"""

    weight_changed = Signal(str, int, bool)  # pack_key, weight, is_hard

    def __init__(self, pack_key, weight, is_hard=False, parent=None):
        super().__init__(parent)
        self.pack_key = str(pack_key)  # 确保是字符串，与 Signal 声明一致
        self.is_hard = is_hard
        self.weight = int(weight)  # 确保是整数
        self.setObjectName(f"ThemePackCard_{pack_key}")
        self.setFixedSize(200, 380)  # 设置卡片尺寸

        self.__init_widget()
        self.__init_layout()
        self.set_style_sheet()

        # 设置初始权重值
        self.weight_spinbox.spin_box.setValue(self.weight)

        # 注册到语言管理器
        LanguageManager().register_component(self)

    def get_display_name(self):
        """根据当前语言获取显示名称"""
        from module.config import cfg

        # 获取当前语言，优先使用 current_lang，否则从配置读取
        lang = LanguageManager().current_lang
        if lang is None:
            lang = cfg.get_value("language_in_program", "zh_CN")

        # 确保 pack_key 是字符串
        pack_key_str = str(self.pack_key)

        # 判断是否为中文环境
        is_chinese = lang and ("zh" in lang.lower() or "cn" in lang.lower() or lang == "简体中文")

        if is_chinese:
            # 中文环境，尝试获取中文名称
            name_map = THEME_PACK_HARD_NAME_MAP if self.is_hard else THEME_PACK_NAME_MAP
            return name_map.get(pack_key_str, pack_key_str)
        else:
            # 英文环境，直接返回英文key
            return pack_key_str

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # 图片标签 - 根据原始图片分辨率 170x330 按比例缩放
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(140, 270)  # 放大图片尺寸
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)

        # 加载图片
        image_path = get_image_path(self.pack_key, self.is_hard)
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText(self.tr("无图片"))
                self.image_label.setStyleSheet("background-color: rgba(128, 128, 128, 0.3); border-radius: 5px;")
        else:
            self.image_label.setText(self.tr("无图片"))
            self.image_label.setStyleSheet("background-color: rgba(128, 128, 128, 0.3); border-radius: 5px;")

        # 主题包名称标签
        self.name_label = BodyLabel()
        self.name_label.setText(self.get_display_name())
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedHeight(24)  # 增加高度以显示完整名称
        font = QFont()
        font.setPointSize(13)  # 增大字体
        font.setBold(True)
        self.name_label.setFont(font)

        # 权重输入框 - 使用 BaseSpinBox
        self.weight_spinbox = BaseSpinBox(None, parent=self, min_value=-10, min_step=1)
        self.weight_spinbox.spin_box.setRange(-10, 10)
        self.weight_spinbox.spin_box.setAlignment(Qt.AlignCenter)
        self.weight_spinbox.spin_box.valueChanged.connect(self._on_weight_changed)

        # 权重标签
        self.weight_label = BodyLabel()
        self.weight_label.setText(self.tr("权重:"))
        self.weight_label.setAlignment(Qt.AlignCenter)

    def __init_layout(self):
        self.main_layout.addWidget(self.image_label, 0, Qt.AlignCenter)
        self.main_layout.addWidget(self.name_label, 0, Qt.AlignCenter)

        # 权重输入区域
        self.weight_layout = QHBoxLayout()
        self.weight_layout.addStretch()
        self.weight_layout.addWidget(self.weight_label)
        self.weight_layout.addWidget(self.weight_spinbox)
        self.weight_layout.addStretch()

        self.main_layout.addLayout(self.weight_layout)
        self.main_layout.addStretch()

    def set_style_sheet(self):
        self.setStyleSheet("""
            ThemePackCard {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 8px;
            }
            ThemePackCard:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(128, 128, 128, 0.5);
            }
        """)

    def _on_weight_changed(self, value):
        """权重值改变时触发"""
        self.weight_changed.emit(self.pack_key, value, self.is_hard)

    def update_weight(self, weight):
        """更新权重显示值"""
        self.weight_spinbox.spin_box.setValue(int(weight))

    def retranslateUi(self, lang_code=None):
        """更新界面翻译"""
        self.name_label.setText(self.get_display_name())
        self.weight_label.setText(self.tr("权重:"))

    def __del__(self):
        """析构时注销组件（静默处理，因为closeEvent已负责主要清理）"""
        try:
            # 使用丢弃模式注销，避免重复注销时的警告
            if self in LanguageManager().translatable_components:
                LanguageManager().translatable_components.remove(self)
        except:
            pass


class ThemePackSettingDialog(QDialog):
    """主题包权重设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemePackSettingDialog")
        self.setWindowTitle(self.tr("主题包权重配置"))
        self.setMinimumSize(1100, 600)
        self.resize(1200, 700)

        self.normal_cards = {}
        self.hard_cards = {}

        self.__init_widget()
        self.__init_layout()
        self.load_theme_packs()
        self.set_style_sheet()

        LanguageManager().register_component(self)

    def __init_widget(self):
        # 主滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 滚动内容容器
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(20)
        self.scroll_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area.setWidget(self.scroll_widget)

        # 标题
        self.title_label = TitleLabel(self.tr("主题包权重配置"), self)
        self.title_label.setAlignment(Qt.AlignCenter)

        # 说明标签
        self.info_label = BodyLabel(
            self.tr("权重说明: 正数=优先选择(值越大优先级越高), 负数=避免选择, 0=无特殊偏好"),
            self
        )
        self.info_label.setAlignment(Qt.AlignCenter)

        # 普通模式分组
        self.normal_group_label = SubtitleLabel(self.tr("普通模式主题包"), self)
        self.normal_grid_widget = QWidget()
        self.normal_grid_layout = QGridLayout(self.normal_grid_widget)
        self.normal_grid_layout.setSpacing(16)
        self.normal_grid_layout.setContentsMargins(0, 0, 0, 0)

        # 困难模式分组
        self.hard_group_label = SubtitleLabel(self.tr("困难模式主题包"), self)
        self.hard_grid_widget = QWidget()
        self.hard_grid_layout = QGridLayout(self.hard_grid_widget)
        self.hard_grid_layout.setSpacing(16)
        self.hard_grid_layout.setContentsMargins(0, 0, 0, 0)

        # 按钮区域
        self.button_widget = QWidget()
        self.button_widget.setObjectName("button_widget")
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 10, 0, 10)

        self.reset_button = PushButton(self.tr("重置为默认"), self)
        self.reset_button.clicked.connect(self.reset_to_default)

        self.save_button = PrimaryPushButton(self.tr("保存并关闭"), self)
        self.save_button.clicked.connect(self.save_and_close)

        self.close_button = PushButton(self.tr("关闭"), self)
        self.close_button.clicked.connect(self.close)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.reset_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.close_button)
        self.button_layout.addStretch()

    def __init_layout(self):
        # 将组件添加到滚动布局
        self.scroll_layout.addWidget(self.title_label)
        self.scroll_layout.addWidget(self.info_label)
        self.scroll_layout.addSpacing(10)
        self.scroll_layout.addWidget(self.normal_group_label)
        self.scroll_layout.addWidget(self.normal_grid_widget)
        self.scroll_layout.addWidget(self.hard_group_label)
        self.scroll_layout.addWidget(self.hard_grid_widget)
        self.scroll_layout.addStretch()
        # 注意：按钮区域不再添加到滚动布局中

        # 主布局 - 上方是滚动区域，下方是固定按钮区域
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.scroll_area, 1)  # 滚动区域占据剩余空间
        self.main_layout.addWidget(self.button_widget)  # 按钮区域固定在底部

    def set_style_sheet(self):
        # 获取对话框实际背景色
        bg_color = self.palette().window().color().name()

        self.setStyleSheet(f"""
            ThemePackSettingDialog {{
                background-color: {bg_color};
            }}
            QScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea > QWidget {{
                background-color: {bg_color};
            }}
            #button_widget {{
                background-color: {bg_color};
            }}
        """)

    def load_theme_packs(self):
        """加载主题包配置并创建卡片"""
        # 加载普通模式主题包
        normal_packs = theme_list.get_value("theme_pack_list", {})

        col_count = 5  # 每行5个卡片
        row = 0
        col = 0

        for pack_key, weight in normal_packs.items():
            card = ThemePackCard(pack_key, weight, is_hard=False)
            card.weight_changed.connect(self._on_weight_changed)
            self.normal_cards[pack_key] = card

            self.normal_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

        # 加载困难模式主题包
        hard_packs = theme_list.get_value("theme_pack_list_hard", {})

        col_count = 5  # 每行5个卡片
        row = 0
        col = 0

        for pack_key, weight in hard_packs.items():
            card = ThemePackCard(pack_key, weight, is_hard=True)
            card.weight_changed.connect(self._on_weight_changed)
            self.hard_cards[pack_key] = card

            self.hard_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _on_weight_changed(self, pack_key, weight, is_hard):
        """处理权重改变事件，实时保存到配置"""
        import copy

        if is_hard:
            config_key = "theme_pack_list_hard"
        else:
            config_key = "theme_pack_list"

        # 直接修改配置并保存（避免重新加载配置）
        config = theme_list.get_value(config_key, {})
        # 确保所有键都是字符串类型（YAML可能将数字键解析为整数）
        config = {str(k): v for k, v in config.items()}
        config[pack_key] = weight
        # 直接修改内部配置并保存
        theme_list.config[config_key] = copy.deepcopy(config)
        theme_list.save_config()

    def reset_to_default(self):
        """重置为默认配置"""
        import copy

        # 获取示例配置路径
        from module import THEME_PACK_LIST_EXAMPLE_PATH

        # 加载示例配置
        with open(THEME_PACK_LIST_EXAMPLE_PATH, "r", encoding="utf-8") as f:
            from ruamel.yaml import YAML
            yaml = YAML()
            example_config = yaml.load(f) or {}

        # 重置普通模式
        normal_default = example_config.get("theme_pack_list", {})
        for pack_key, weight in normal_default.items():
            if pack_key in self.normal_cards:
                self.normal_cards[pack_key].update_weight(weight)

        # 重置困难模式
        hard_default = example_config.get("theme_pack_list_hard", {})
        for pack_key, weight in hard_default.items():
            if pack_key in self.hard_cards:
                self.hard_cards[pack_key].update_weight(weight)

        # 保存重置后的配置
        theme_list.config["theme_pack_list"] = copy.deepcopy(normal_default)
        theme_list.config["theme_pack_list_hard"] = copy.deepcopy(hard_default)
        theme_list.save_config()

    def save_and_close(self):
        """保存并关闭对话框"""
        self.close()

    def closeEvent(self, event):
        """对话框关闭时注销所有组件，防止内存泄漏"""
        # 注销所有普通模式卡片
        for card in self.normal_cards.values():
            try:
                LanguageManager().unregister_component(card)
            except:
                pass

        # 注销所有困难模式卡片
        for card in self.hard_cards.values():
            try:
                LanguageManager().unregister_component(card)
            except:
                pass

        # 注销对话框自身
        try:
            LanguageManager().unregister_component(self)
        except:
            pass

        # 清空卡片字典，帮助垃圾回收
        self.normal_cards.clear()
        self.hard_cards.clear()

        # 调用父类的 closeEvent
        super().closeEvent(event)

    def retranslateUi(self, lang_code=None):
        """更新界面翻译"""
        self.setWindowTitle(self.tr("主题包权重配置"))
        self.title_label.setText(self.tr("主题包权重配置"))
        self.info_label.setText(self.tr("权重说明: 正数=优先选择(值越大优先级越高), 负数=避免选择, 0=无特殊偏好"))
        self.normal_group_label.setText(self.tr("普通模式主题包"))
        self.hard_group_label.setText(self.tr("困难模式主题包"))
        self.reset_button.setText(self.tr("重置为默认"))
        self.save_button.setText(self.tr("保存并关闭"))
        self.close_button.setText(self.tr("关闭"))

        # 卡片会通过 LanguageManager 自动更新翻译
