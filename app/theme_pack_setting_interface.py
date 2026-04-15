import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SubtitleLabel,
    TitleLabel,
    isDarkTheme,
)
from qframelesswindow import FramelessDialog, StandardTitleBar
from ruamel.yaml import YAML

from app.base_tools import BaseSpinBox
from app.card.messagebox_custom import MessageBoxConfirm
from module import THEME_PACK_LIST_EXAMPLE_PATH
from module.config import cfg, theme_list

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
    "miracle": "区的奇",
    "bullet": "句点",
    "cleaved": "当斩",
    "penetra": "穿刺者",
    "pierced": "当贯",
    "crushers": "粉碎者",
    "repression": "情感压迫",
    "addict": "沉迷的",
    "seduct": "感情困惑",
    "dolen": "情感懒",
    "glutton": "吞噬的",
    "cravi": "情感饥渴",
    "gloom": "落的忧",
    "subserv": "情感屈从",
    "nsignif": "寒微",
    "judgment": "情感评判",
    "outcast": "无归属",
    "curshed": "当碎",
    "crushed": "当碎",
    "automated": "自动",
    "spring": "琢春",
    "unloving": "无慈悲",
    "flowers": "落花",
    "abyss": "伏行",
    "bones": "骨断",
    "time": "时间杀人",
    "warp": "谋杀",
    "violet": "紫罗兰",
    "dicers": "斩切",
    "wrath": "压抑的",
    "sloth": "沉溺者",
    "flood": "空转",
    "vain": "虚张声势",
    "check": "体检",
    "sweep": "清扫",
    "Hatred": "绝望",
    "Wander": "彷徨",
    "dusk": "黄昏",
    "compassion": "巡礼",
}

# 英文key到中文名称的映射表（困难模式）
THEME_PACK_HARD_NAME_MAP = {
    "20": "奇迹复刻",
    "seismic": "地震",
    "extrenal": "破坏性",
    "thunder": "电闪雷鸣",
    "sanguine": "渗出的",
    "dizzying": "缭乱的",
    "pang": "沉于",
    "sigh": "叹息",
    "supply": "动力",
    "four": "家族",
    "opening": "开园",
    "procession": "无尽的",
    "unchanging": "无改变",
    "unchang": "无改变",
    "evil": "定义为",
    "heartb": "心意相",
    "line": "号线",
    "repressed": "压抑的",
    "unbound": "解放的",
    "tangling": "束缚的",
    "inert": "停滞的",
    "excessive": "漫溢的",
    "sunk": "沉溺的",
    "pride": "自以为",
    "pitiful": "凄惨的",
    "haze": "摇曳",
    "season": "盛火",
    "corpses": "血海",
    "might": "破竹",
    "deluge": "沉沦泛",
    "poised": "循环呼",
    "ending": "终焉",
    "witnessing": "观望",
    "Text": "教材",
    "Blade": "刀与作",
    "Unsever": "割舍",
}

# 中文名称到英文key的反向映射表（普通模式）
CN_TO_EN_NAME_MAP = {v: k for k, v in THEME_PACK_NAME_MAP.items()}

# 中文名称到英文key的反向映射表（困难模式）
CN_TO_EN_HARD_NAME_MAP = {v: k for k, v in THEME_PACK_HARD_NAME_MAP.items()}

# OCR 备用名称映射表（备用名称 -> 主名称）
# 用于处理 OCR 识别误差，备用名称在 GUI 中不显示，但权重会同步更新
CN_OCR_ALTERNATIVES = {
    "海边": "海·边",  # s.e.a 主题包的 OCR 备用
    "切琢": "琢春",  # spring 主题包的 OCR 备用
    "体险": "体检",  # check 主题包的 OCR 备用
}

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
    "Wander": "Charm,Wander,Doubt.png",
    "dusk": "The Dusk of Amber.png",
    # 以下主题包暂无对应图片文件
    # "compassion": "The Compassion.png",  # 明日方舟联动/巡礼
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
    "Text": "Textbook.png",
    "Blade": "Blade and Artwork.png",
    "Unsever": "The Unsevering.png",
    # 以下主题包暂无对应图片文件
    # 轨道线系列（如需支持多条线路，可添加以下映射）
    # "line2": "Line 2.png",
    # "line3": "Line 3.png",
    # "line4_3": "Line 4 Section#3.png",
    # "line4_4": "Line 4 Section#4.png",
    # "line5": "Line 5.png",
}

# 中文主题包名称到图片文件名的映射表（普通模式）
# 通过复用英文映射表和反向映射表来生成
THEME_PACK_CN_IMAGE_MAP = {
    cn_name: THEME_PACK_IMAGE_MAP.get(en_key, "")
    for cn_name, en_key in CN_TO_EN_NAME_MAP.items()
    if en_key in THEME_PACK_IMAGE_MAP
}

# 中文主题包名称到图片文件名的映射表（困难模式）
THEME_PACK_CN_HARD_IMAGE_MAP = {
    cn_name: THEME_PACK_HARD_IMAGE_MAP.get(en_key, "")
    for cn_name, en_key in CN_TO_EN_HARD_NAME_MAP.items()
    if en_key in THEME_PACK_HARD_IMAGE_MAP
}


def get_image_path(pack_key, is_hard=False, is_cn=False):
    """获取主题包图片路径"""
    # 根据是否为中文配置选择对应的映射表
    if is_cn:
        image_map = THEME_PACK_CN_HARD_IMAGE_MAP if is_hard else THEME_PACK_CN_IMAGE_MAP
    else:
        image_map = THEME_PACK_HARD_IMAGE_MAP if is_hard else THEME_PACK_IMAGE_MAP

    # 将key转换为字符串进行比较
    pack_key_str = str(pack_key)
    image_name = image_map.get(pack_key_str, "")
    if image_name:
        return f"./assets/app/theme_packs/{image_name}"
    return ""


class ThemePackCard(QFrame):
    """单个主题包卡片组件"""

    weight_changed = Signal(str, int, bool, bool)  # pack_key, weight, is_hard, is_cn

    def __init__(self, pack_key: str, weight: int, is_hard=False, is_cn=False, parent=None):
        super().__init__(parent)
        self.pack_key = str(pack_key)  # 确保是字符串，与 Signal 声明一致
        self.is_hard = is_hard
        self.is_cn = is_cn  # 是否为中文配置
        self.weight = int(weight)  # 确保是整数
        self.setObjectName(f"ThemePackCard_{pack_key}_{'cn' if is_cn else 'en'}")
        self.setFixedSize(200, 395)  # 按设置卡片尺寸

        self.__init_widget()
        self.__init_layout()
        self._apply_styles()

        # 设置初始权重值
        self.weight_spinbox.spin_box.setValue(self.weight)

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)

        # 图片标签 - 根据原始图片分辨率 170x330 按比例缩放
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(140, 272)  # 保持 170:330 原始比例 (140*330/170≈272)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)

        # 加载图片
        image_path = get_image_path(self.pack_key, self.is_hard, self.is_cn)
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
        self.name_label = TitleLabel()
        # 初始化时从配置获取语言
        # init_lang = cfg.get_value("language_in_program", "zh_cn")
        self.name_label.setText(str(self.pack_key))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)

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

    def _apply_styles(self):
        """根据当前主题设置样式表"""
        if isDarkTheme():
            self.setStyleSheet("""
                ThemePackCard {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                }
                ThemePackCard:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                TitleLabel {
                    color: white;
                    background-color: transparent;
                }
                BodyLabel {
                    color: rgba(255, 255, 255, 0.85);
                    background-color: transparent;
                    border: none;
                }
                BaseSpinBox {
                    background-color: transparent;
                    border: none;
                }
                SpinBox {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 4px;
                    color: white;
                }
                SpinBox:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
            """)
        else:
            self.setStyleSheet("""
                ThemePackCard {
                    background-color: rgba(0, 0, 0, 0.03);
                    border: 1px solid rgba(0, 0, 0, 0.1);
                    border-radius: 8px;
                }
                ThemePackCard:hover {
                    background-color: rgba(0, 0, 0, 0.06);
                    border: 1px solid rgba(0, 0, 0, 0.2);
                }
                TitleLabel {
                    color: black;
                    background-color: transparent;
                }
                BodyLabel {
                    color: rgba(0, 0, 0, 0.85);
                    background-color: transparent;
                    border: none;
                }
                BaseSpinBox {
                    background-color: transparent;
                    border: none;
                }
                SpinBox {
                    background-color: rgba(255, 255, 255, 0.8);
                    border: 1px solid rgba(0, 0, 0, 0.15);
                    border-radius: 4px;
                    color: black;
                }
                SpinBox:hover {
                    background-color: rgba(255, 255, 255, 1);
                    border: 1px solid rgba(0, 0, 0, 0.25);
                }
            """)

    def _on_weight_changed(self, value):
        """权重值改变时触发"""
        self.weight_changed.emit(self.pack_key, value, self.is_hard, self.is_cn)

    def update_weight(self, weight):
        """更新权重显示值"""
        self.weight_spinbox.spin_box.setValue(int(weight))

    def cleanup(self):
        """清理资源，断开信号连接"""
        try:
            self.weight_spinbox.spin_box.valueChanged.disconnect(self._on_weight_changed)
        except (RuntimeError, TypeError):
            pass  # 信号可能已经被断开或对象已被销毁


class ThemePackSettingDialog(FramelessDialog):
    """主题包权重设置对话框"""

    def __init__(self, parent, config_data, save_path):
        super().__init__(parent)
        self.setObjectName("ThemePackSettingDialog")
        self.setWindowTitle(self.tr("主题包权重配置"))
        self.setMinimumSize(1100, 600)
        self.resize(1200, 700)

        # 设置自定义标题栏
        self.setTitleBar(StandardTitleBar(self))
        self.titleBar.raise_()
        # 隐藏最小化和最大化按钮
        self.titleBar.minBtn.hide()
        self.titleBar.maxBtn.hide()

        # 获取当前界面语言，决定加载哪种语言的配置
        self.lang_code = cfg.get_value("language_in_program", "zh_cn")
        self.is_cn = self.lang_code == "zh_cn"  # 是否加载中文配置

        self.normal_cards: dict[str, ThemePackCard] = {}
        self.hard_cards: dict[str, ThemePackCard] = {}

        # 标记是否有未保存的修改
        self._has_unsaved_changes = False

        # 标记是否是保存并关闭
        self._is_save_and_close = False

        # 配置数据和保存路径
        self.config_data = config_data
        self.save_path = save_path
        self.is_team_specific = self.save_path != theme_list.theme_pack_list_path

        # 保存原始配置的副本，用于关闭时不保存恢复
        self._original_config = copy.deepcopy(self.config_data)

        self.__init_widget()
        self.__init_layout()
        self.load_theme_packs()
        self._apply_styles()

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
            self.tr(
                "权重说明: 正数=优先选择(值越大优先级越高), 负数=避免选择, 0=无特殊偏好\n"
                "优选阈值说明: 当主题包权重大于或等于优选阈值时，会被优先选中\n"
                "保存时会自动同步其他语言配置权重 (如有)"
            ),
            self,
        )
        self.info_label.setAlignment(Qt.AlignCenter)

        # 优选阈值设置
        self.threshold_widget = QWidget(self)
        self.threshold_layout = QHBoxLayout(self.threshold_widget)
        self.threshold_layout.setContentsMargins(0, 0, 0, 0)
        self.threshold_layout.setSpacing(8)

        self.threshold_label = BodyLabel(self.tr("优选阈值"), self.threshold_widget)
        self.preferred_threshold_spinbox = BaseSpinBox(None, parent=self.threshold_widget, min_value=-10, min_step=1)
        self.preferred_threshold_spinbox.spin_box.setRange(-10, 10)
        self.preferred_threshold_spinbox.spin_box.setAlignment(Qt.AlignCenter)
        self.preferred_threshold_spinbox.spin_box.setValue(int(self.config_data.get("preferred_thresholds", 0)))
        self.preferred_threshold_spinbox.spin_box.valueChanged.connect(self._on_preferred_threshold_changed)

        self.threshold_layout.addStretch()
        self.threshold_layout.addWidget(self.threshold_label)
        self.threshold_layout.addWidget(self.preferred_threshold_spinbox)
        self.threshold_layout.addStretch()

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
        self.reset_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reset_button.clicked.connect(self.reset_to_default)

        self.set_to_global_button = PushButton(self.tr("拉取全局配置"), self)
        self.set_to_global_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_to_global_button.clicked.connect(self.set_to_global)
        self.set_to_global_button.setVisible(self.is_team_specific)

        self.set_all_negative_button = PushButton(self.tr("全部设为 -5"), self)
        self.set_all_negative_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_all_negative_button.clicked.connect(self.set_all_weights_negative)

        self.save_button = PrimaryPushButton(self.tr("保存并关闭"), self)
        self.save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_button.clicked.connect(self.save_and_close)

        self.close_button = PushButton(self.tr("关闭"), self)
        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.clicked.connect(self.close)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.reset_button)
        self.button_layout.addWidget(self.set_to_global_button)
        self.button_layout.addWidget(self.set_all_negative_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.close_button)
        self.button_layout.addStretch()

    def __init_layout(self):
        # 将组件添加到滚动布局
        self.scroll_layout.addWidget(self.title_label)
        self.scroll_layout.addWidget(self.info_label)
        self.scroll_layout.addWidget(self.threshold_widget)
        self.scroll_layout.addSpacing(10)
        self.scroll_layout.addWidget(self.normal_group_label)
        self.scroll_layout.addWidget(self.normal_grid_widget)
        self.scroll_layout.addWidget(self.hard_group_label)
        self.scroll_layout.addWidget(self.hard_grid_widget)
        self.scroll_layout.addStretch()
        # 注意：按钮区域不再添加到滚动布局中

        # 主布局 - 上方是滚动区域，下方是固定按钮区域
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 32, 0, 0)  # 顶部留出 32px 标题栏高度
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.scroll_area, 1)  # 滚动区域占据剩余空间
        self.main_layout.addWidget(self.button_widget)  # 按钮区域固定在底部

    def _apply_styles(self):
        """应用主题样式到各个组件"""
        # 设置对话框自身样式
        if isDarkTheme():
            bg_color = "rgba(28, 28, 28, 1)"
            text_color = "white"
        else:
            bg_color = "white"
            text_color = "black"

        # 设置对话框自身背景色
        self.setStyleSheet(f"""
            ThemePackSettingDialog {{
                background-color: {bg_color};
            }}
            QScrollArea > QWidget {{
                background-color: {bg_color};
            }}
            #button_widget {{
                background-color: {"#2B2B2B" if isDarkTheme() else "#f3f3f3"};
            }}
            TitleLabel {{
                color: {text_color};
                background-color: transparent;
            }}
            SubtitleLabel {{
                color: {text_color};
                background-color: transparent;
                border-bottom: 2px solid {text_color}; padding-bottom: 4px;
            }}
            BodyLabel {{
                color: {text_color};
                background-color: transparent;
            }}
        """)

        # 设置标题栏样式
        self.titleBar.titleLabel.setStyleSheet(
            f"QLabel {{ background: transparent; font-size: 13px; padding: 0 4px; color: {text_color}; }}"
        )
        for btn in [self.titleBar.minBtn, self.titleBar.maxBtn, self.titleBar.closeBtn]:
            btn.setNormalColor(Qt.GlobalColor.white if isDarkTheme() else Qt.GlobalColor.black)
            btn.setHoverColor(Qt.GlobalColor.white if isDarkTheme() else Qt.GlobalColor.black)
            btn.setPressedColor(Qt.GlobalColor.white if isDarkTheme() else Qt.GlobalColor.black)
        self.titleBar.closeBtn.setHoverColor(Qt.GlobalColor.white)

        # 直接设置各内容区域的背景色
        self.scroll_widget.setStyleSheet(f"background-color: {bg_color};")
        self.normal_grid_widget.setStyleSheet(f"background-color: {bg_color};")
        self.hard_grid_widget.setStyleSheet(f"background-color: {bg_color};")

    def load_theme_packs(self):
        """加载主题包配置并创建卡片，根据语言参数加载对应配置"""
        # 根据语言参数决定加载哪种配置
        if self.is_cn:
            # 中文界面，加载中文配置
            normal_packs = self.config_data.get("theme_pack_list_cn", {})
            hard_packs = self.config_data.get("theme_pack_list_hard_cn", {})
        else:
            # 英文界面，加载英文配置
            normal_packs = self.config_data.get("theme_pack_list", {})
            hard_packs = self.config_data.get("theme_pack_list_hard", {})

        col_count = 5  # 每行5个卡片

        # 加载普通模式主题包（过滤掉 OCR 备用名称）
        row = 0
        col = 0
        for pack_key, weight in normal_packs.items():
            # 如果是 OCR 备用名称，跳过不显示（但配置中保留）
            if self.is_cn and pack_key in CN_OCR_ALTERNATIVES:
                continue
            card = ThemePackCard(pack_key, weight, is_hard=False, is_cn=self.is_cn)
            card.weight_changed.connect(self._on_weight_changed)
            self.normal_cards[pack_key] = card

            self.normal_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

        # 加载困难模式主题包（过滤掉 OCR 备用名称）
        row = 0
        col = 0
        for pack_key, weight in hard_packs.items():
            # 如果是 OCR 备用名称，跳过不显示（但配置中保留）
            if self.is_cn and pack_key in CN_OCR_ALTERNATIVES:
                continue
            card = ThemePackCard(pack_key, weight, is_hard=True, is_cn=self.is_cn)
            card.weight_changed.connect(self._on_weight_changed)
            self.hard_cards[pack_key] = card

            self.hard_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def _on_weight_changed(self, pack_key, weight, is_hard, is_cn):
        """处理权重改变事件，只更新内存中的配置，不保存到文件"""
        pack_key_str = str(pack_key)

        # 确定当前模式的配置键和映射表
        if is_hard:
            en_config_key = "theme_pack_list_hard"
            cn_config_key = "theme_pack_list_hard_cn"
            name_map = THEME_PACK_HARD_NAME_MAP
            reverse_map = CN_TO_EN_HARD_NAME_MAP
        else:
            en_config_key = "theme_pack_list"
            cn_config_key = "theme_pack_list_cn"
            name_map = THEME_PACK_NAME_MAP
            reverse_map = CN_TO_EN_NAME_MAP

        # 同时更新两套配置
        # 1. 更新英文配置
        en_config = copy.deepcopy(self.config_data.get(en_config_key, {}))
        en_config = {str(k): v for k, v in en_config.items()}

        # 2. 更新中文配置
        cn_config = copy.deepcopy(self.config_data.get(cn_config_key, {}))
        cn_config = {str(k): v for k, v in cn_config.items()}

        if self.is_cn:
            # 当前是中文界面，pack_key 是中文名称
            cn_config[pack_key_str] = weight

            # 检查是否有 OCR 备用名称，如果有则同步更新
            if pack_key_str in CN_OCR_ALTERNATIVES:
                # pack_key 是备用名称，找到主名称并更新
                main_name = CN_OCR_ALTERNATIVES[pack_key_str]
                if main_name in cn_config:
                    cn_config[main_name] = weight
            else:
                # pack_key 是主名称，检查是否有备用名称需要同步更新
                for alt_name, main_name in CN_OCR_ALTERNATIVES.items():
                    if main_name == pack_key_str and alt_name in cn_config:
                        cn_config[alt_name] = weight

            # 找到对应的中文名称并更新英文配置
            en_key = reverse_map.get(pack_key_str)
            if en_key and en_key in en_config:
                en_config[en_key] = weight
        else:
            # 当前是英文界面，pack_key 是英文 key
            en_config[pack_key_str] = weight
            # 找到对应的英文 key 并更新中文配置
            cn_key = name_map.get(pack_key_str)
            if cn_key and cn_key in cn_config:
                cn_config[cn_key] = weight
                # 同时检查该中文名称是否有 OCR 备用名称，一并更新
                for alt_name, main_name in CN_OCR_ALTERNATIVES.items():
                    if main_name == cn_key and alt_name in cn_config:
                        cn_config[alt_name] = weight

        # 只更新内存中的配置，不保存到文件
        self.config_data[en_config_key] = copy.deepcopy(en_config)
        self.config_data[cn_config_key] = copy.deepcopy(cn_config)

        # 标记有未保存的修改
        self._has_unsaved_changes = True

    def _on_preferred_threshold_changed(self, value: int):
        """处理优选阈值变化，只更新内存中的配置，不保存到文件"""
        self.config_data["preferred_thresholds"] = int(value)
        self._has_unsaved_changes = True

    def reset_to_default(self):
        """重置为默认配置，只更新内存中的配置和界面，不保存到文件"""
        # 加载示例配置
        with open(THEME_PACK_LIST_EXAMPLE_PATH, "r", encoding="utf-8") as f:
            yaml = YAML()
            example_config = yaml.load(f) or {}

        # 用示例配置替换内存中的配置，但不保存到文件
        self.config_data.clear()
        self.config_data.update(copy.deepcopy(example_config))

        # 根据当前语言更新界面显示
        if self.is_cn:
            normal_default = example_config.get("theme_pack_list_cn", {})
            hard_default = example_config.get("theme_pack_list_hard_cn", {})
        else:
            normal_default = example_config.get("theme_pack_list", {})
            hard_default = example_config.get("theme_pack_list_hard", {})

        self.preferred_threshold_spinbox.spin_box.setValue(int(example_config.get("preferred_thresholds", 0)))

        # 重置普通模式显示
        for pack_key, weight in normal_default.items():
            if pack_key in self.normal_cards:
                self.normal_cards[pack_key].update_weight(weight)

        # 重置困难模式显示
        for pack_key, weight in hard_default.items():
            if pack_key in self.hard_cards:
                self.hard_cards[pack_key].update_weight(weight)

        # 标记有未保存的修改
        self._has_unsaved_changes = True

    def set_to_global(self):
        """将当前配置设置为全局主题包配置（仅内存，不立即保存）。"""
        if not self.is_team_specific:
            return

        global_config = theme_list.load_config(theme_list.theme_pack_list_path)
        if not global_config:
            return

        self.config_data.clear()
        self.config_data.update(copy.deepcopy(global_config))

        if self.is_cn:
            normal_global = global_config.get("theme_pack_list_cn", {})
            hard_global = global_config.get("theme_pack_list_hard_cn", {})
        else:
            normal_global = global_config.get("theme_pack_list", {})
            hard_global = global_config.get("theme_pack_list_hard", {})

        self.preferred_threshold_spinbox.spin_box.setValue(int(global_config.get("preferred_thresholds", 0)))

        for pack_key, weight in normal_global.items():
            if pack_key in self.normal_cards:
                self.normal_cards[pack_key].update_weight(weight)

        for pack_key, weight in hard_global.items():
            if pack_key in self.hard_cards:
                self.hard_cards[pack_key].update_weight(weight)

        self._has_unsaved_changes = True

    def set_all_weights_negative(self):
        """将当前显示的所有主题包权重批量设置为 -5"""
        for card in list(self.normal_cards.values()) + list(self.hard_cards.values()):
            card.update_weight(-5)
        self._has_unsaved_changes = True

    def save_and_close(self):
        """保存配置到文件并关闭对话框"""
        # save_path 必须提供
        if not self.save_path:
            return
        theme_list.save_config(path=self.save_path, config_data=self.config_data)
        self._has_unsaved_changes = False
        self._is_save_and_close = True  # 标记是保存并关闭
        self.close()

    def closeEvent(self, event):
        """对话框关闭时注销所有组件，防止内存泄漏

        如果不是保存并关闭且有未保存的修改，
        则恢复到原始配置，不保存到文件。
        """
        if not self._is_save_and_close and self._has_unsaved_changes:
            confirm = MessageBoxConfirm(
                self.tr("存在未保存修改"),
                self.tr("关闭后将丢失未保存的修改，是否继续？"),
                self.window(),
            )
            if not confirm.exec():
                event.ignore()
                return

        # 如果不是保存并关闭，且有未保存的修改，恢复到原始配置
        if not self._is_save_and_close and self._has_unsaved_changes:
            self.config_data.clear()
            self.config_data.update(copy.deepcopy(self._original_config))

        # 先断开所有信号连接，防止在清理过程中触发信号
        for card in self.normal_cards.values():
            try:
                card.weight_changed.disconnect(self._on_weight_changed)
            except RuntimeError:
                pass  # 信号可能已经被断开
            # 清理卡片内部资源
            card.cleanup()

        for card in self.hard_cards.values():
            try:
                card.weight_changed.disconnect(self._on_weight_changed)
            except RuntimeError:
                pass
            # 清理卡片内部资源
            card.cleanup()

        # 清空卡片字典，帮助垃圾回收
        self.normal_cards.clear()
        self.hard_cards.clear()

        # 使用 deleteLater 延迟销毁，避免 C++ 对象已删除的问题
        self.deleteLater()

        # 调用父类的 closeEvent
        super().closeEvent(event)
