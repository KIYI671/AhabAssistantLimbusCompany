import os

import pyperclip
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ExpandSettingCard,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    ScrollArea,
    SmoothMode,
    ToolButton,
    ToolTipFilter,
    ToolTipPosition,
)
from qfluentwidgets import FluentIcon as FIF

from app import *
from app.base_combination import (
    CheckBoxWithComboBox,
    LabelWithComboBox,
    ObserveGiftSelectionRow,
    SinnerSelect,
)
from app.base_tools import BaseCheckBox, BaseComboBox, BaseLabel, BaseLineEdit, BaseSettingLayout
from app.card.messagebox_custom import BaseInfoBar
from app.common.ui_config import (
    STARLIGHT_BONUS_COSTS,
    get_starlight_action_label,
    get_starlight_bonus_name,
    get_starlight_total_cost_qss,
)
from app.language_manager import LanguageManager
from app.starlight_bonus import StarlightCard, StarlightLevelSelector
from app.team_setting_column import TeamSettingBlankColumn
from app.theme_pack_setting_interface import ThemePackSettingDialog
from module.config import cfg, theme_list
from module.logger import log
from app.observe_ego_gift_selection import (
    MAX_OBSERVE_GIFT_SELECTIONS,
    ObserveGiftSelection,
    ensure_placeholder_row,
    parse_observe_ego_gift_values,
    serialize_observe_ego_gift_values,
)


class TeamSettingCard(QFrame):
    def __init__(self, team_num=0, parent=None):
        super().__init__(parent)
        self.team_num = team_num
        self.setObjectName("TeamSettingCard")
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        # 编队设置数据切换到当前编队team_num
        self.team_setting = cfg.get_team(team_num)
        self.team_setting.team_number = team_num
        self.blank_column.set_current_team(team_num)

        self.read_settings()
        self.refresh_starlight_select()

        self.connect_mediator()
        LanguageManager().register_component(self)
        self.select_system.retranslateUi()
        self.select_shop_strategy.retranslateUi()


    def set_team_num(self, team_num: int):
        """切换常驻队伍设置页当前编辑的编队。"""
        self.team_num = team_num
        self.team_setting = cfg.get_team(team_num)
        self.customize_settings_module.team_num = team_num
        self.observe_ego_gift_module.team_num = team_num
        self.customize_info_module.set_team_num(team_num)
        self.blank_column.set_current_team(team_num)
        self.read_settings()
        self.refresh_starlight_select()

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0) # 移除页面边距
        self.content_layout = QHBoxLayout()
        self.blank_column = TeamSettingBlankColumn(self)
        self.blank_column.team_selected.connect(self.set_team_num)
        self.scroll_general = ScrollArea()
        self.scroll_general.setObjectName("teamSettingContentScroll")
        self.scroll_general.setSmoothMode(SmoothMode.LINEAR, Qt.Orientation.Vertical)
        self.scroll_general.scrollDelagate.verticalSmoothScroll.duration = 100
        self.scroll_general.setWidgetResizable(True)
        self.scroll_general.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.page_widget = QWidget()
        self.page_widget.setObjectName("teamSettingPageWidget")
        self.scroll_general.setWidget(self.page_widget)

        self.layout_ = QVBoxLayout(self.page_widget)

        self.content_layout.addWidget(self.blank_column)
        self.content_layout.addWidget(self.scroll_general, 1)
        self.main_layout.addLayout(self.content_layout, 1)

        self.combobox_layout = BaseSettingLayout(box_type=1)
        self.combobox_layout.setMaximumHeight(75)
        self.combobox_layout.BoxLayout.setSpacing(40)
        self.sinner_layout = QGridLayout()

        self.gift_system_layout = BaseSettingLayout(box_type=2)
        self.gift_system_layout.setMaximumHeight(150)
        self.gift_system_list_1 = QHBoxLayout()
        self.gift_system_list_2 = QHBoxLayout()

        self.custom_layout = ExpandSettingCard(
            icon=FIF.EDIT,
            title=self.tr("自定义设置（设置存在冲突时，将根据优先级覆盖生效）"),
        )

        self.observe_ego_gift_layout = ExpandSettingCard(
            icon=FIF.SEARCH,
            title=self.tr("观测EGO饰品"),
        )

        self.custom_layout2 = ExpandSettingCard(icon=FIF.INFO, title=self.tr("编队统计数据"))

        self.setting_layout = QHBoxLayout()

        self.scroll_general.enableTransparentBackground()

    def __init_card(self):
        self.copy_team_button = PushButton(self)
        self.copy_team_button.setText(self.tr("复制"))
        self.copy_team_button.clicked.connect(self.copy_team_settings)
        self.reset_team_button = PushButton(self)
        self.reset_team_button.setText(self.tr("重置"))
        self.reset_team_button.clicked.connect(self.reset_team_settings)
        self.paste_team_button = PushButton(self)
        self.paste_team_button.setText(self.tr("粘贴"))
        self.paste_team_button.clicked.connect(self.paste_team_settings)
        self.team_clipboard_layout = QHBoxLayout()
        self.team_clipboard_layout.setSpacing(8)
        self.team_clipboard_layout.addWidget(self.copy_team_button)
        self.team_clipboard_layout.addWidget(self.paste_team_button)
        self.team_clipboard_layout.addWidget(self.reset_team_button)

        self.select_system = LabelWithComboBox(self.tr("体系"), "team_system", all_systems, vbox=False)
        self.select_shop_strategy = LabelWithComboBox(
            self.tr("商店策略"), "shop_strategy", shop_strategy, vbox=False
        )
        self.alias_layout = QHBoxLayout()
        self.alias_layout.setSpacing(10)
        self.alias_label = BaseLabel(self.tr("备注"))
        self.alias_input = BaseLineEdit("alias", self)
        self.alias_input.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alias_input.line_edit.setPlaceholderText(f"{self.tr('编队')}{self.team_num}")
        self.alias_layout.addWidget(self.alias_label)
        self.alias_layout.addWidget(self.alias_input)

        self.sinner_YiSang = SinnerSelect(
            "YiSang",
            self.tr("李箱"),
            None,
        )
        self.sinner_Faust = SinnerSelect(
            "Faust",
            self.tr("浮士德"),
            None,
        )
        self.sinner_DonQuixote = SinnerSelect(
            "DonQuixote",
            self.tr("堂吉诃德"),
            None,
        )
        self.sinner_Ryoshu = SinnerSelect(
            "Ryoshu",
            self.tr("良秀"),
            None,
        )
        self.sinner_Meursault = SinnerSelect(
            "Meursault",
            self.tr("默尔索"),
            None,
        )
        self.sinner_HongLu = SinnerSelect(
            "HongLu",
            self.tr("鸿璐"),
            None,
        )

        self.sinner_Heathcliff = SinnerSelect(
            "Heathcliff",
            self.tr("希斯克利夫"),
            None,
        )
        self.sinner_Ishmael = SinnerSelect(
            "Ishmael",
            self.tr("以实玛利"),
            None,
        )
        self.sinner_Rodion = SinnerSelect(
            "Rodion",
            self.tr("罗佳"),
            None,
        )
        self.sinner_Sinclair = SinnerSelect(
            "Sinclair",
            self.tr("辛克莱"),
            None,
        )
        self.sinner_Outis = SinnerSelect(
            "Outis",
            self.tr("奥提斯"),
            None,
        )
        self.sinner_Gregor = SinnerSelect(
            "Gregor",
            self.tr("格里高尔"),
            None,
        )

        self.shop_setting = BaseLabel(self.tr("舍弃的体系"))
        self.shop_setting.add_icon(FIF.DELETE)

        self.burn = BaseCheckBox(
            "system_burn",
            "./assets/app/status_effects/burn.png",
            self.tr("烧伤"),
            icon_size=30,
        )
        self.bleed = BaseCheckBox(
            "system_bleed",
            "./assets/app/status_effects/bleed.png",
            self.tr("流血"),
            icon_size=30,
        )
        self.tremor = BaseCheckBox(
            "system_tremor",
            "./assets/app/status_effects/tremor.png",
            self.tr("震颤"),
            icon_size=30,
        )
        self.rupture = BaseCheckBox(
            "system_rupture",
            "./assets/app/status_effects/rupture.png",
            self.tr("破裂"),
            icon_size=30,
        )
        self.sinking = BaseCheckBox(
            "system_sinking",
            "./assets/app/status_effects/sinking.png",
            self.tr("沉沦"),
            icon_size=30,
        )

        self.poise = BaseCheckBox(
            "system_poise",
            "./assets/app/status_effects/poise.png",
            self.tr("呼吸"),
            icon_size=30,
        )
        self.charge = BaseCheckBox(
            "system_charge",
            "./assets/app/status_effects/charge.png",
            self.tr("充能"),
            icon_size=30,
        )
        self.slash = BaseCheckBox(
            "system_slash",
            "./assets/app/status_effects/slash.png",
            self.tr("斩击"),
            icon_size=30,
        )
        self.pierce = BaseCheckBox(
            "system_pierce",
            "./assets/app/status_effects/pierce.png",
            self.tr("突刺"),
            icon_size=30,
        )
        self.blunt = BaseCheckBox(
            "system_blunt",
            "./assets/app/status_effects/blunt.png",
            self.tr("打击"),
            icon_size=30,
        )

        self.customize_settings_module = CustomizeSettingsModule(self.team_num)
        self.observe_ego_gift_module = ObserveEgoGiftModule(self.team_num)
        self.customize_info_module = CustomizeInfoModule(self.team_num)
        self.customize_settings_module.select_theme_pack_weight_button.clicked.connect(
            self.open_theme_pack_weight_dialog
        )

    def __init_layout(self):
        self.combobox_layout.add(self.team_clipboard_layout)
        self.combobox_layout.add(self.alias_layout)
        self.combobox_layout.add(self.select_system)
        self.combobox_layout.add(self.select_shop_strategy)

        self.sinner_layout.setContentsMargins(15, 10, 15, 20)
        self.sinner_layout.addWidget(self.sinner_YiSang, 0, 0)
        self.sinner_layout.addWidget(self.sinner_Faust, 0, 1)
        self.sinner_layout.addWidget(self.sinner_DonQuixote, 0, 2)
        self.sinner_layout.addWidget(self.sinner_Ryoshu, 0, 3)
        self.sinner_layout.addWidget(self.sinner_Meursault, 0, 4)
        self.sinner_layout.addWidget(self.sinner_HongLu, 0, 5)
        self.sinner_layout.setVerticalSpacing(13) # 罪人卡片之间的垂直间距 （向下取整
        self.sinner_layout.setHorizontalSpacing(6) # 罪人卡片之间的水平间距（向下取整
        self.sinner_layout.addWidget(self.sinner_Heathcliff, 1, 0)
        self.sinner_layout.addWidget(self.sinner_Ishmael, 1, 1)
        self.sinner_layout.addWidget(self.sinner_Rodion, 1, 2)
        self.sinner_layout.addWidget(self.sinner_Sinclair, 1, 3)
        self.sinner_layout.addWidget(self.sinner_Outis, 1, 4)
        self.sinner_layout.addWidget(self.sinner_Gregor, 1, 5)

        self.gift_system_list_1.addWidget(self.burn)
        self.gift_system_list_1.addWidget(self.bleed)
        self.gift_system_list_1.addWidget(self.tremor)
        self.gift_system_list_1.addWidget(self.rupture)
        self.gift_system_list_1.addWidget(self.sinking)
        self.gift_system_list_2.addWidget(self.poise)
        self.gift_system_list_2.addWidget(self.charge)
        self.gift_system_list_2.addWidget(self.slash)
        self.gift_system_list_2.addWidget(self.pierce)
        self.gift_system_list_2.addWidget(self.blunt)
        self.gift_system_layout.add(self.shop_setting)
        self.gift_system_layout.add(self.gift_system_list_1)
        self.gift_system_layout.add(self.gift_system_list_2)

        self.layout_.addWidget(self.combobox_layout)
        self.layout_.addLayout(self.sinner_layout)
        self.layout_.addWidget(self.gift_system_layout)
        self.layout_.addWidget(self.custom_layout)
        self.layout_.addWidget(self.observe_ego_gift_layout)
        self.layout_.addWidget(self.custom_layout2)

        self.main_layout.addLayout(self.setting_layout)
        self.main_layout.addSpacing(15)
        self.setting_layout.setContentsMargins(10, 0, 10, 0)  # 手动对齐其他组件

        self.custom_layout.viewLayout.addWidget(self.customize_settings_module)
        self.observe_ego_gift_layout.viewLayout.addWidget(self.observe_ego_gift_module)
        self.custom_layout2.viewLayout.addWidget(self.customize_info_module)
        self.custom_layout.setExpand(True)
        self.observe_ego_gift_layout.setExpand(True)
        self.custom_layout2.setExpand(True)

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.team_setting.connect(self.setting_team)
        mediator.team_alias_changed.connect(self.refresh_alias_input)
        mediator.sinner_be_selected.connect(self.refresh_sinner_order)

    def disconnect_mediator(self):
        """断开所有 mediator 信号连接"""
        mediator.team_setting.disconnect(self.setting_team)
        mediator.team_alias_changed.disconnect(self.refresh_alias_input)
        mediator.sinner_be_selected.disconnect(self.refresh_sinner_order)


    def setting_team(self, data_dict: dict):
        """接收UI信号，更新编队配置信息"""
        keys = list(data_dict.keys())[0]
        values = list(data_dict.values())[0]
        if keys == "alias":
            self.team_setting.alias = values
            mediator.team_alias_changed.emit(self.team_num)
        elif hasattr(self.team_setting, f"{keys}"):
            setattr(self.team_setting, keys, values)
            if keys == "team_system":
                self.foolproof(values)
        elif keys == "observe_ego_gift_selected":
            self.team_setting.observe_ego_gift_selected = values
        elif keys in all_sinners_name:
            sinner_index = all_sinners_name.index(keys)
            if values:
                self.team_setting.sinners_be_select += 1
                self.team_setting.chosen_sinners[sinner_index] = 1
                self.team_setting.sinner_order[sinner_index] = self.team_setting.sinners_be_select
            else:
                order = self.team_setting.sinner_order[sinner_index]
                self.team_setting.sinners_be_select -= 1
                self.team_setting.chosen_sinners[sinner_index] = 0
                for i in range(12):
                    if self.team_setting.sinner_order[i] > order:
                        self.team_setting.sinner_order[i] -= 1
                self.team_setting.sinner_order[sinner_index] = 0
            self.refresh_sinner_order()
        elif keys == "starlight_all_state":
            bonus_value = max(0, min(int(values), 3))
            self.team_setting.opening_bonus = [bonus_value] * 10
            self.refresh_starlight_select()
        elif "starlight_state_" in keys:
            starlight_index = int(keys.split("_")[-1]) - 1
            self.team_setting.opening_bonus[starlight_index] = max(0, min(int(values), 3))
            self.refresh_starlight_select()
        elif keys in second_system_mode:
            mode_index = second_system_mode.index(keys)
            self.team_setting.second_system_action[mode_index] = values
        elif "ignore_shop_" in keys:
            shop_index = int(keys.split("_")[-1]) - 1
            self.team_setting.ignore_shop[shop_index] = values
        cfg.save_team(self.team_num)


    def open_theme_pack_weight_dialog(self):
        team_index = int(self.team_num)

        dialog = ThemePackSettingDialog(
            self,
            config_data=theme_list.get_team_theme_pack_weight(team_index),
            save_callback=lambda data: theme_list.save_team_theme_pack_weight(team_index, data),
            is_team_specific=True,
            team_num=team_index,
        )
        dialog.exec()

    def refresh_starlight_select(self):
        opening_bonus = self.team_setting.opening_bonus
        for i in range(1, 11):
            starlight = self.findChild(StarlightLevelSelector, f"starlight_{i}")
            if starlight is not None:
                bonus_value = opening_bonus[i - 1] if i <= len(opening_bonus) else 0
                starlight.set_state(bonus_value)
        # 单个星光按钮刷新完成后，同步“全选”按钮状态。
        self.refresh_starlight_select_all()
        # 更新总星光消耗
        self.customize_settings_module.update_total_starlight_cost(opening_bonus)

    def refresh_starlight_select_all(self):
        select_all = self.findChild(StarlightLevelSelector, "starlight_all")
        if select_all is None:
            return

        opening_bonus = self.team_setting.opening_bonus
        if len(opening_bonus) < 10:
            select_all.set_state(0)
            return

        if all(opening_bonus[index] >= 3 for index in range(10)):
            select_all.set_state(3)
        elif all(opening_bonus[index] >= 2 for index in range(10)):
            select_all.set_state(2)
        elif all(opening_bonus[index] >= 1 for index in range(10)):
            select_all.set_state(1)
        else:
            select_all.set_state(0)

    def refresh_sinner_order(self):
        sinner_order = self.team_setting.sinner_order
        for i in range(12):
            sinner = self.findChild(SinnerSelect, all_sinners_name[i])
            if sinner is not None:
                if sinner_order[i] != 0:
                    sinner.set_text(str(sinner_order[i]))
                else:
                    sinner.set_text("")

    def read_settings(self):
        chosen_sinners = self.team_setting.chosen_sinners
        for i in range(12):
            sinner = self.findChild(SinnerSelect, all_sinners_name[i])
            if sinner is not None:
                if chosen_sinners[i]:
                    sinner.set_checkbox(True)
                else:
                    sinner.set_checkbox(False)

        self.refresh_sinner_order()

        second_system_action = self.team_setting.second_system_action
        ignore_shop = self.team_setting.ignore_shop
        # 显示第二体系的各个选项
        for i in range(4):
            self.findChild(BaseCheckBox, second_system_mode[i]).set_checked(bool(second_system_action[i]))

        # 显示需要忽略商店的楼层
        for i in range(1, 6):
            self.findChild(BaseCheckBox, f"ignore_shop_{i}").set_checked(bool(ignore_shop[i - 1]))

        for checkbox in all_checkbox_config_name:
            if self.findChild(BaseCheckBox, checkbox):
                self.findChild(BaseCheckBox, checkbox).set_checked(getattr(self.team_setting, checkbox))

        for combobox in all_combobox_config_name:
            if self.findChild(BaseComboBox, combobox):
                self.findChild(BaseComboBox, combobox).set_options(getattr(self.team_setting, combobox))
                if combobox == "team_system":
                    self.foolproof(getattr(self.team_setting, combobox))

        # 读取编队码设置
        if team_code_input := self.findChild(BaseLineEdit, "team_code"):
            team_code_input.setText(self.team_setting.team_code)

        self.refresh_alias_input(self.team_num)

        # 回显观测EGO饰品选中状态
        observe_module = self.findChild(ObserveEgoGiftModule, "ObserveEgoGiftModule")
        if observe_module:
            observe_module.load_selected(self.team_setting.observe_ego_gift_selected)

    def copy_team_settings(self):
        """复制当前队伍设置（含主题包权重）到剪贴板。"""
        yaml_str = cfg.team_config.copy_team_as_yaml(self.team_num)
        pyperclip.copy(yaml_str)
        BaseInfoBar.success(
            title=self.tr("已复制到剪切板"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.window(),
        )

    def paste_team_settings(self):
        """从剪贴板粘贴队伍设置（含主题包权重）到当前队伍。"""
        setting = pyperclip.paste().strip()
        try:
            cfg.team_config.paste_team_from_yaml(self.team_num, setting)
        except ValueError:
            BaseInfoBar.error(
                title=self.tr("剪贴板为空") if not setting else self.tr("不是合法的格式"),
                content="",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=500,
                parent=self.window(),
            )
            return

        mediator.team_alias_changed.emit(self.team_num)
        BaseInfoBar.success(
            title=self.tr("已粘贴设置"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.window(),
        )
        self.team_setting = cfg.get_team(self.team_num)
        self.team_setting.team_number = self.team_num
        self.read_settings()
        self.refresh_starlight_select()

    def reset_team_settings(self):
        """将队伍设置重置为默认值。"""
        cfg.team_config.reset_team(self.team_num)
        mediator.team_alias_changed.emit(self.team_num)
        BaseInfoBar.success(
            title=self.tr("已重置设置"),
            content="",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=500,
            parent=self.window(),
        )
        self.team_setting = cfg.get_team(self.team_num)
        self.team_setting.team_number = self.team_num
        self.read_settings()
        self.refresh_starlight_select()

    def refresh_alias_input(self, team_num: int):
        if team_num != self.team_num:
            return
        self.team_setting = cfg.get_team(team_num)
        if alias_input := self.findChild(BaseLineEdit, "alias"):
            alias_input.line_edit.setPlaceholderText(f"{self.tr('编队')}{self.team_num}")
            alias_input.setText(self.team_setting.alias or "")

    def foolproof(self, team_system):
        for checkbox in all_checkbox_config_name:
            if check_box := self.findChild(BaseCheckBox, checkbox):
                if checkbox.startswith("system_"):
                    check_box.set_box_enabled(True)
        check_box = self.findChild(BaseCheckBox, f"system_{all_systems_name[team_system]}")
        if check_box:
            check_box.set_checked(False)
            check_box.set_box_enabled(False)
            setattr(self.team_setting, f"system_{all_systems_name[team_system]}", False)

    def retranslateUi(self):
        self.select_system.retranslateUi()
        self.select_shop_strategy.retranslateUi()
        self.copy_team_button.setText(self.tr("复制"))
        self.reset_team_button.setText(self.tr("重置"))
        self.paste_team_button.setText(self.tr("粘贴"))
        self.select_system.label.label.setText(self.tr("体系"))
        self.alias_label.label.setText(self.tr("备注"))
        self.alias_input.line_edit.setPlaceholderText(f"{self.tr('编队')}{self.team_num}")
        self.select_shop_strategy.label.label.setText(self.tr("商店策略"))
        self.sinner_YiSang.name_label.setText(self.tr("李箱"))
        self.sinner_Faust.name_label.setText(self.tr("浮士德"))
        self.sinner_DonQuixote.name_label.setText(self.tr("堂吉诃德"))
        self.sinner_Ryoshu.name_label.setText(self.tr("良秀"))
        self.sinner_Meursault.name_label.setText(self.tr("默尔索"))
        self.sinner_HongLu.name_label.setText(self.tr("鸿璐"))
        self.sinner_Heathcliff.name_label.setText(self.tr("希斯克利夫"))
        self.sinner_Ishmael.name_label.setText(self.tr("以实玛利"))
        self.sinner_Rodion.name_label.setText(self.tr("罗佳"))
        self.sinner_Sinclair.name_label.setText(self.tr("辛克莱"))
        self.sinner_Outis.name_label.setText(self.tr("奥提斯"))
        self.sinner_Gregor.name_label.setText(self.tr("格里高尔"))
        self.shop_setting.label.setText(self.tr("舍弃的体系"))

        self.burn.check_box.setText(self.tr("烧伤"))
        self.bleed.check_box.setText(self.tr("流血"))
        self.tremor.check_box.setText(self.tr("震颤"))
        self.rupture.check_box.setText(self.tr("破裂"))
        self.sinking.check_box.setText(self.tr("沉沦"))
        self.poise.check_box.setText(self.tr("呼吸"))
        self.charge.check_box.setText(self.tr("充能"))
        self.slash.check_box.setText(self.tr("斩击"))
        self.pierce.check_box.setText(self.tr("突刺"))
        self.blunt.check_box.setText(self.tr("打击"))


class CustomizeSettingsModule(QFrame):
    def __init__(self, team_num: int, parent=None):
        super().__init__(parent)
        self.team_num = team_num
        self.setObjectName("CustomizeSettingsModule")
        self.main_layout = QVBoxLayout(self)
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        LanguageManager().register_component(self)
        self.retranslateUi()

    def __init_widget(self):
        self.first_line_widget = QWidget()
        self.first_line_widget.setFixedWidth(900)
        self.first_line = QHBoxLayout(self.first_line_widget)
        self.second_line_widget = QWidget()
        self.second_line_widget.setFixedWidth(900)
        self.second_line = QHBoxLayout(self.second_line_widget)
        self.third_line_widget = QWidget()
        self.third_line_widget.setFixedWidth(900)
        self.third_line = QHBoxLayout(self.third_line_widget)

        self.features_patch_widget_1 = QWidget()
        self.features_patch_widget_1.setFixedWidth(900)
        self.features_patch_line_1 = QHBoxLayout(self.features_patch_widget_1)

        self.star_layout = BaseSettingLayout(box_type=2)
        self.star_layout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # 星光加成外框的最大高度。
        self.star_layout.setMaximumHeight(240)
        # 星光加成外框的最大宽度，影响一行 5 个星光选择框可分到的总空间。
        self.star_layout.setMaximumWidth(850)
        self.star_list = QGridLayout()
        # 两行星光选择框之间的上下间距。
        self.star_list.setVerticalSpacing(10)
        # 同一行内相邻星光选择框之间的左右间距。
        self.star_list.setHorizontalSpacing(10)

        self.fourth_line_widget = QWidget()
        self.fourth_line = QHBoxLayout(self.fourth_line_widget)
        self.features_patch_widget_2 = QWidget()
        self.features_patch_line_2 = QVBoxLayout(self.features_patch_widget_2)
        self.fifth_line_widget = QWidget()
        self.fifth_line = QHBoxLayout(self.fifth_line_widget)
        self.second_system_widget = QWidget()
        self.second_system_layout = QVBoxLayout(self.second_system_widget)
        self.second_system_line1 = QHBoxLayout()
        self.second_system_line2 = QHBoxLayout()
        self.seventh_line_widget = QWidget()
        self.seventh_line = QHBoxLayout(self.seventh_line_widget)
        self.eighth_line_widget = QWidget()
        self.eighth_line = QHBoxLayout(self.eighth_line_widget)
        self.ninth_line_widget = QWidget()
        self.ninth_line = QHBoxLayout(self.ninth_line_widget)
        self.tenth_line_widget = QWidget()
        self.tenth_line = QHBoxLayout(self.tenth_line_widget)
        self.eleventh_line_widget = QWidget()
        self.eleventh_line = QHBoxLayout(self.eleventh_line_widget)
        self.floor_shop = QHBoxLayout()

    def __init_card(self):
        self.do_not_heal = BaseCheckBox("do_not_heal", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不治疗罪人"))
        self.do_not_buy = BaseCheckBox("do_not_buy", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不购买饰品"))
        self.do_not_fuse = BaseCheckBox("do_not_fuse", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不合成饰品"))
        self.do_not_sell = BaseCheckBox("do_not_sell", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不出售饰品"))
        self.do_not_enhance = BaseCheckBox("do_not_enhance", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不升级饰品"))

        self.only_aggressive_fuse = BaseCheckBox(
            "only_aggressive_fuse",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "只激进合成"),
        )
        self.do_not_system_fuse = BaseCheckBox(
            "do_not_system_fuse",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "不使用公式合成"),
        )
        self.only_system_fuse = BaseCheckBox(
            "only_system_fuse",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "只使用公式合成"),
        )

        self.avoid_skill_3 = BaseCheckBox(
            "avoid_skill_3",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "链接战避免使用三技能"),
        )
        self.re_formation_each_floor = BaseCheckBox(
            "re_formation_each_floor",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "每楼层重新编队"),
        )
        self.use_starlight = BaseCheckBox("use_starlight", None, QT_TRANSLATE_NOOP("BaseCheckBox", "开局星光换钱"))

        self.aggressive_also_enhance = BaseCheckBox(
            "aggressive_also_enhance",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "激进合成期间也升级饰品"),
        )
        self.aggressive_save_systems = BaseCheckBox(
            "aggressive_save_systems",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "激进合成保留体系饰品"),
        )
        self.defense_first_round = BaseCheckBox(
            "defense_first_round",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "链接战第一回合全员防御"),
        )

        self.fixed_team_use = CheckBoxWithComboBox(
            "fixed_team_use",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "固定队伍用途"),
            None,
            "fixed_team_use_select",
        )
        self.fixed_team_use.add_items(fixed_team_use)
        self.reward_cards = CheckBoxWithComboBox(
            "reward_cards",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "奖励卡优先度"),
            None,
            "reward_cards_select",
        )
        self.reward_cards.add_items(reward_cards)

        QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星光")
        self.starlight_1 = StarlightCard(
            "starlight_1", get_starlight_bonus_name(0, cfg.language_in_program), self.team_num
        )
        self.starlight_2 = StarlightCard(
            "starlight_2", get_starlight_bonus_name(1, cfg.language_in_program), self.team_num
        )
        self.starlight_3 = StarlightCard(
            "starlight_3", get_starlight_bonus_name(2, cfg.language_in_program), self.team_num
        )
        self.starlight_4 = StarlightCard(
            "starlight_4", get_starlight_bonus_name(3, cfg.language_in_program), self.team_num
        )
        self.starlight_5 = StarlightCard(
            "starlight_5", get_starlight_bonus_name(4, cfg.language_in_program), self.team_num
        )

        self.starlight_6 = StarlightCard(
            "starlight_6", get_starlight_bonus_name(5, cfg.language_in_program), self.team_num
        )
        self.starlight_7 = StarlightCard(
            "starlight_7", get_starlight_bonus_name(6, cfg.language_in_program), self.team_num
        )
        self.starlight_8 = StarlightCard(
            "starlight_8", get_starlight_bonus_name(7, cfg.language_in_program), self.team_num
        )
        self.starlight_9 = StarlightCard(
            "starlight_9", get_starlight_bonus_name(8, cfg.language_in_program), self.team_num
        )
        self.starlight_10 = StarlightCard(
            "starlight_10", get_starlight_bonus_name(9, cfg.language_in_program), self.team_num
        )
        self.starlight_select_all = StarlightLevelSelector(
            "starlight_all",
            QT_TRANSLATE_NOOP("CustomizeSettingsModule", "全选"),
            self,
            starlight_index=0,
            base_cost=sum(STARLIGHT_BONUS_COSTS),
            emit_team_setting=False,
        )

        self.starlight_select_all_wrapper = QWidget(self)
        select_all_layout = QVBoxLayout(self.starlight_select_all_wrapper)
        # 全选选择框在自己网格单元内的左、上、右、下留白。
        select_all_layout.setContentsMargins(0, 0, 0, 0)
        select_all_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        select_all_layout.addWidget(self.starlight_select_all)

        self.starlight_clear_button = PushButton(QT_TRANSLATE_NOOP("CustomizeSettingsModule", "清空"))

        self.starlight_clear_button_wrapper = QWidget(self)
        clear_btn_layout = QVBoxLayout(self.starlight_clear_button_wrapper)
        # 清空按钮在自己网格单元内的左、上、右、下留白。
        clear_btn_layout.setContentsMargins(10, 0, 0, 0)
        clear_btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        clear_btn_layout.addWidget(self.starlight_clear_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.starlight_total_cost_label = QLabel(self)
        self.starlight_total_cost_label.setObjectName("starlightTotalCostLabel")
        self.starlight_total_cost_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._apply_total_cost_style()

        self.starlight_clear_button.clicked.connect(lambda: self.__set_all_starlight(0))
        self.starlight_select_all.stateChangedByClick.connect(self.__set_all_starlight)

        self.after_level_IV = CheckBoxWithComboBox(
            "after_level_IV",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "合成四级以后"),
            None,
            "after_level_IV_select",
        )
        self.after_level_IV.add_items(after_fuse_level_IV)
        self.after_level_IV.hBoxLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.after_level_IV.combo_box.setFixedWidth(220)
        self.after_level_IV.combo_box.combo_box.setFixedWidth(220)
        self.shopping_strategy = CheckBoxWithComboBox(
            "shopping_strategy",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "购物策略"),
            None,
            "shopping_strategy_select",
        )
        self.shopping_strategy.add_items(shopping_strategy)
        self.shopping_strategy.hBoxLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.shopping_strategy.combo_box.setFixedWidth(190)
        self.shopping_strategy.combo_box.combo_box.setFixedWidth(190)

        self.opening_items = CheckBoxWithComboBox(
            "opening_items",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "自选开局饰品"),
            None,
            "opening_items_system",
        )
        self.opening_items.add_items(all_systems)
        self.opening_items.add_combobox("opening_items_select")
        self.opening_items.add_times_for_additional(start_gift)
        self.opening_items.hBoxLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.opening_items.combo_box.setFixedWidth(90)
        self.opening_items.combo_box.combo_box.setFixedWidth(90)
        self.opening_items.additional_combo_box.setFixedWidth(110)
        self.opening_items.additional_combo_box.combo_box.setFixedWidth(110)

        self.second_system = CheckBoxWithComboBox(
            "second_system",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "第二体系"),
            None,
            "second_system_select",
        )
        self.second_system.add_items(all_systems)
        self.second_system.add_combobox("second_system_setting")
        self.second_system.add_times_for_additional(second_systems)
        self.second_system.hBoxLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.second_system.combo_box.setFixedWidth(90)
        self.second_system.combo_box.combo_box.setFixedWidth(90)
        self.second_system.additional_combo_box.setFixedWidth(220)
        self.second_system.additional_combo_box.combo_box.setFixedWidth(220)

        self.second_system_fuse_IV = BaseCheckBox(
            "second_system_fuse_IV", None, QT_TRANSLATE_NOOP("BaseCheckBox", "合成四级")
        )
        self.second_system_buy = BaseCheckBox("second_system_buy", None, QT_TRANSLATE_NOOP("BaseCheckBox", "购买"))
        self.second_system_select = BaseCheckBox(
            "second_system_choose",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "选取胜利奖励"),
        )
        self.second_system_power_up = BaseCheckBox(
            "second_system_power_up",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "升级四级"),
        )

        self.skill_replacement = CheckBoxWithComboBox(
            "skill_replacement",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "技能替换"),
            None,
            "skill_replacement_select",
        )
        self.skill_replacement.add_items(skill_replacement_sinner)
        self.skill_replacement.add_combobox("skill_replacement_mode")
        self.skill_replacement.add_times_for_additional(skill_replacement_mode)
        self.skill_replacement.hBoxLayout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.skill_replacement.combo_box.setFixedWidth(140)
        self.skill_replacement.combo_box.combo_box.setFixedWidth(140)
        self.skill_replacement.additional_combo_box.setFixedWidth(90)
        self.skill_replacement.additional_combo_box.combo_box.setFixedWidth(90)

        QT_TRANSLATE_NOOP("BaseLabel", "忽略商店")
        self.ignore_shop = BaseLabel("忽略商店")
        self.ignore_shop.add_icon(FIF.CUT)
        self.floor_shop_1 = BaseCheckBox("ignore_shop_1", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第一层"))
        self.floor_shop_2 = BaseCheckBox("ignore_shop_2", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第二层"))
        self.floor_shop_3 = BaseCheckBox("ignore_shop_3", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第三层"))
        self.floor_shop_4 = BaseCheckBox("ignore_shop_4", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第四层"))
        self.floor_shop_5 = BaseCheckBox("ignore_shop_5", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第五层"))

        self.max_keyword_refresh = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "定向刷新上限"),
            "max_keyword_refresh",
            refresh_count_options,
        )
        self.max_normal_refresh = LabelWithComboBox(
            QT_TRANSLATE_NOOP("LabelWithComboBox", "普通刷新上限"),
            "max_normal_refresh",
            refresh_count_options,
        )

        self.use_custom_theme_pack_weight = BaseCheckBox(
            "use_custom_theme_pack_weight",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "使用自定义主题包权重"),
        )
        self.select_theme_pack_weight_button = PushButton(self.tr("权重选择"))

        self.use_team_code = BaseCheckBox(
            "use_team_code",
            None,
            QT_TRANSLATE_NOOP("BaseCheckBox", "使用编队码"),
        )
        self.team_code_warning = BaseLabel("")
        self.team_code_warning.add_icon(FIF.INFO)
        self.team_code_warning.setMaximumWidth(40)
        self.team_code_warning.iconLabel.setToolTip(
            self.tr("后台模式下输入编队码可能不稳定\n输入编队码会覆盖原有的队伍配置")
        )
        self.team_code_warning.iconLabel.setToolTipDuration(-1)
        self.team_code_input = BaseLineEdit("team_code", self)
        self.team_code_input.line_edit.setPlaceholderText(self.tr("输入编队码"))
        self.team_code_input.line_edit.setMaximumWidth(400)

    def __init_layout(self):
        self.first_line.addWidget(self.do_not_heal)
        self.first_line.addWidget(self.do_not_buy)
        self.first_line.addWidget(self.do_not_fuse)
        self.first_line.addWidget(self.do_not_sell)
        self.first_line.addWidget(self.do_not_enhance)

        self.second_line.addWidget(self.only_aggressive_fuse)
        self.second_line.addWidget(self.do_not_system_fuse)
        self.second_line.addWidget(self.only_system_fuse)

        self.third_line.addWidget(self.avoid_skill_3)
        self.third_line.addWidget(self.re_formation_each_floor)
        self.third_line.addWidget(self.use_starlight)

        self.features_patch_line_1.addWidget(self.aggressive_also_enhance)
        self.features_patch_line_1.addWidget(self.aggressive_save_systems)
        self.features_patch_line_1.addWidget(self.defense_first_round)

        # 第 0 行是全选、清空和总费用；第 1、2 行是 10 个星光选择框。
        self.star_list.addWidget(self.starlight_select_all_wrapper, 0, 0)
        self.star_list.addWidget(self.starlight_clear_button_wrapper, 0, 1)
        self.star_list.addWidget(self.starlight_total_cost_label, 0, 4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.star_list.addWidget(self.starlight_1, 1, 0)
        self.star_list.addWidget(self.starlight_2, 1, 1)
        self.star_list.addWidget(self.starlight_3, 1, 2)
        self.star_list.addWidget(self.starlight_4, 1, 3)
        self.star_list.addWidget(self.starlight_5, 1, 4)
        self.star_list.addWidget(self.starlight_6, 2, 0)
        self.star_list.addWidget(self.starlight_7, 2, 1)
        self.star_list.addWidget(self.starlight_8, 2, 2)
        self.star_list.addWidget(self.starlight_9, 2, 3)
        self.star_list.addWidget(self.starlight_10, 2, 4)
        self.star_layout.add(self.star_list)

        self.fourth_line.addWidget(self.after_level_IV)
        self.fourth_line.addWidget(self.shopping_strategy)

        self.features_patch_line_2.addWidget(self.fixed_team_use)
        self.features_patch_line_2.addWidget(self.reward_cards)

        self.fifth_line.addWidget(self.opening_items, Qt.AlignLeft)

        self.second_system_line1.addWidget(self.second_system)
        self.second_system_line2.addSpacing(115)
        self.second_system_line2.addWidget(self.second_system_fuse_IV)
        self.second_system_line2.addWidget(self.second_system_buy)
        self.second_system_line2.addWidget(self.second_system_select)
        self.second_system_line2.addWidget(self.second_system_power_up)
        self.second_system_layout.addLayout(self.second_system_line1)
        self.second_system_layout.addLayout(self.second_system_line2)

        self.seventh_line.addWidget(self.skill_replacement)

        self.eighth_line.addWidget(self.ignore_shop)
        self.eighth_line.addSpacing(20)
        self.floor_shop.addWidget(self.floor_shop_1)
        self.floor_shop.addWidget(self.floor_shop_2)
        self.floor_shop.addWidget(self.floor_shop_3)
        self.floor_shop.addWidget(self.floor_shop_4)
        self.floor_shop.addWidget(self.floor_shop_5)
        self.eighth_line.addLayout(self.floor_shop, Qt.AlignLeft)

        self.ninth_line.addWidget(self.max_keyword_refresh)
        self.ninth_line.addWidget(self.max_normal_refresh)
        self.ninth_line.addStretch()

        self.tenth_line.addWidget(self.use_custom_theme_pack_weight)
        self.tenth_line.addWidget(self.select_theme_pack_weight_button)
        self.tenth_line.addStretch()

        self.eleventh_line.addWidget(self.use_team_code)
        self.eleventh_line.addWidget(self.team_code_warning)
        self.eleventh_line.addWidget(self.team_code_input)
        self.eleventh_line.addStretch()

        self.main_layout.addWidget(self.first_line_widget)
        self.main_layout.addWidget(self.second_line_widget)
        self.main_layout.addWidget(self.third_line_widget)
        self.main_layout.addWidget(self.features_patch_widget_1)
        self.main_layout.addWidget(self.star_layout)
        self.main_layout.addWidget(self.features_patch_widget_2, Qt.AlignLeft)
        self.main_layout.addWidget(self.fourth_line_widget)
        self.main_layout.addWidget(self.fifth_line_widget)
        self.main_layout.addWidget(self.second_system_widget)
        self.main_layout.addWidget(self.seventh_line_widget)
        self.main_layout.addWidget(self.eighth_line_widget)
        self.main_layout.addWidget(self.ninth_line_widget)
        self.main_layout.addWidget(self.tenth_line_widget)
        self.main_layout.addWidget(self.eleventh_line_widget)

    def __set_all_starlight(self, bonus_value: int):
        mediator.team_setting.emit({"starlight_all_state": max(0, min(int(bonus_value), 3))})

    def _apply_total_cost_style(self):
        from qfluentwidgets import setCustomStyleSheet
        from app.starlight_bonus import _register_custom_style_widget
        _register_custom_style_widget(self.starlight_total_cost_label)
        light_qss, dark_qss = get_starlight_total_cost_qss()
        setCustomStyleSheet(self.starlight_total_cost_label, light_qss, dark_qss)

    def update_total_starlight_cost(self, opening_bonus: list[int]):
        total = sum(
            STARLIGHT_BONUS_COSTS[i] * opening_bonus[i]
            for i in range(min(len(opening_bonus), len(STARLIGHT_BONUS_COSTS)))
        )
        self.starlight_total_cost_label.setText(str(total))

    def retranslateUi(self):
        self.do_not_heal.retranslateUi()
        self.do_not_buy.retranslateUi()
        self.do_not_fuse.retranslateUi()
        self.do_not_enhance.retranslateUi()
        self.do_not_sell.retranslateUi()
        self.do_not_system_fuse.retranslateUi()
        self.only_aggressive_fuse.retranslateUi()
        self.only_system_fuse.retranslateUi()
        self.avoid_skill_3.retranslateUi()
        self.use_starlight.retranslateUi()
        self.aggressive_also_enhance.retranslateUi()
        self.aggressive_save_systems.retranslateUi()
        self.defense_first_round.retranslateUi()
        self.fixed_team_use.retranslateUi()
        self.reward_cards.retranslateUi()
        self.re_formation_each_floor.retranslateUi()
        self.starlight_select_all.set_label_text(get_starlight_action_label(self.tr("全选"), cfg.language_in_program))
        self.starlight_clear_button.setText(get_starlight_action_label(self.tr("清空"), cfg.language_in_program))

        for index in range(1, 11):
            starlight = self.findChild(StarlightLevelSelector, f"starlight_{index}")
            starlight.set_label_text(get_starlight_bonus_name(index - 1, cfg.language_in_program))
            if index <= 5:
                floor_shop = self.findChild(BaseCheckBox, f"ignore_shop_{index}")
                floor_shop.retranslateUi()

        self.after_level_IV.retranslateUi()
        self.shopping_strategy.retranslateUi()
        self.opening_items.retranslateUi()
        self.second_system.retranslateUi()
        self.second_system_fuse_IV.retranslateUi()
        self.second_system_buy.retranslateUi()
        self.second_system_select.retranslateUi()
        self.second_system_power_up.retranslateUi()
        self.skill_replacement.retranslateUi()
        self.ignore_shop.retranslateUi()
        self.max_keyword_refresh.retranslateUi()
        self.max_normal_refresh.retranslateUi()
        self.use_custom_theme_pack_weight.retranslateUi()
        self.select_theme_pack_weight_button.setText(self.tr("权重选择"))
        self.use_team_code.retranslateUi()

        self.max_keyword_refresh.setToolTip(self.tr("每次商店访问时定向刷新商品的次数上限"))
        self.max_normal_refresh.setToolTip(self.tr("每次商店访问时普通刷新商品的次数上限"))


class SystemIconButton(QLabel):
    """体系图标按钮"""

    def __init__(self, system: str, icon_path: str, tooltip: str, parent=None, force_text: bool = False):
        super().__init__(parent)
        self.system = system
        self._active = False
        self._force_text = force_text
        self._normal_pixmap = QPixmap(icon_path)
        if not self._force_text and not self._normal_pixmap.isNull():
            self.setPixmap(self._normal_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText(tooltip)
        self.setFixedSize(54, 54)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self._refresh_style()

    def _refresh_style(self):
        is_text_mode = self._force_text or self._normal_pixmap.isNull()
        text_style = "font-size: 12px; color: palette(text);" if is_text_mode else ""
        if self._active:
            self.setStyleSheet(
                f"border: 2px solid rgba(128,128,128,0.45); border-radius: 6px; background-color: transparent;{text_style}"
            )
        else:
            self.setStyleSheet(
                f"border: 1px solid rgba(128,128,128,0.25); border-radius: 6px; background-color: transparent;{text_style}"
            )

    def set_active(self, active: bool):
        self._active = active
        self._refresh_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            module = self._find_module()
            if module:
                module.on_system_clicked(self)
        super().mousePressEvent(event)

    def _find_module(self):
        w = self.parent()
        while w:
            if isinstance(w, ObserveEgoGiftModule):
                return w
            w = w.parent()
        return None


class PreviewGiftLabel(QLabel):
    """预览区体系图标，点击后定位到对应控件组"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_index: int | None = None
        self.setFixedSize(36, 36)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.row_index is not None:
            module = self._find_module()
            if module:
                module.on_preview_clicked(self.row_index)
        super().mousePressEvent(event)

    def _find_module(self):
        w = self.parent()
        while w:
            if isinstance(w, ObserveEgoGiftModule):
                return w
            w = w.parent()
        return None


class ObserveEgoGiftModule(QFrame):
    """观测饰品"""

    def __init__(self, team_num: int, parent=None):
        super().__init__(parent)
        self.team_num = team_num
        self.setObjectName("ObserveEgoGiftModule")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        self._row_selections = ensure_placeholder_row([])
        self._row_widgets: list[ObserveGiftSelectionRow] = []

        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        self._rebuild_rows()
        self._refresh_preview()

        LanguageManager().register_component(self)
        self.retranslateUi()

    def __init_widget(self):
        self.top_row_widget = QWidget()
        self.top_row_layout = QHBoxLayout(self.top_row_widget)
        self.top_row_layout.setContentsMargins(0, 0, 0, 0)
        self.top_row_layout.setSpacing(8)
        self.top_row_layout.setAlignment(Qt.AlignLeft)

        self.observe_ego_gift_checkbox = BaseCheckBox(
            "observe_ego_gift",
            None,
            self.tr("启用观测"),
            icon_size=30,
        )

        self.selected_preview_widget = QWidget()
        self.selected_preview_layout = QHBoxLayout(self.selected_preview_widget)
        self.selected_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.selected_preview_layout.setSpacing(4)
        self.selected_preview_layout.setAlignment(Qt.AlignLeft)
        self._preview_labels: list[PreviewGiftLabel] = []
        for _ in range(MAX_OBSERVE_GIFT_SELECTIONS):
            lbl = PreviewGiftLabel()
            lbl.setStyleSheet(
                "border: 1px solid rgba(128,128,128,0.4); border-radius: 4px; background-color: rgba(0,0,0,0.1);"
            )
            self._preview_labels.append(lbl)
            self.selected_preview_layout.addWidget(lbl)
        self.selected_preview_layout.addSpacing(4)

        self.preview_hint_button = ToolButton(FIF.INFO, self.selected_preview_widget)
        self.preview_hint_button.setFixedSize(32, 32)
        self.preview_hint_button.setCursor(Qt.ArrowCursor)
        self.preview_hint_button.setToolTip(self._preview_hint_tooltip())
        self.preview_hint_button.installEventFilter(
            ToolTipFilter(self.preview_hint_button, showDelay=0, position=ToolTipPosition.BOTTOM_LEFT)
        )
        self.selected_preview_layout.addWidget(self.preview_hint_button)

        self.system_select_widget = QWidget()
        self.system_select_layout = QHBoxLayout(self.system_select_widget)
        self.system_select_layout.setContentsMargins(0, 0, 0, 0)
        self.system_select_layout.setSpacing(5)
        self.system_select_layout.setAlignment(Qt.AlignLeft)

        self.selection_rows_widget = QWidget()
        self.selection_rows_layout = QVBoxLayout(self.selection_rows_widget)
        self.selection_rows_layout.setContentsMargins(0, 4, 0, 4)
        self.selection_rows_layout.setSpacing(6)
        self.selection_rows_layout.setAlignment(Qt.AlignTop)

    def __init_card(self):
        self.observe_systems = [
            ("burn", self.tr("烧伤")),
            ("bleed", self.tr("流血")),
            ("tremor", self.tr("震颤")),
            ("rupture", self.tr("破裂")),
            ("sinking", self.tr("沉沦")),
            ("poise", self.tr("呼吸")),
            ("charge", self.tr("充能")),
            ("slash", self.tr("斩击")),
            ("pierce", self.tr("突刺")),
            ("blunt", self.tr("打击")),
            ("general", self.tr("泛用")),
        ]

        self._system_buttons: dict[str, SystemIconButton] = {}
        for system, label in self.observe_systems:
            icon_path = f"./assets/app/status_effects/{system}.png"
            btn = SystemIconButton(system, icon_path, label, self.system_select_widget, force_text=system == "general")
            self._system_buttons[system] = btn
            self.system_select_layout.addWidget(btn)

    def __init_layout(self):
        self.top_row_layout.addWidget(self.observe_ego_gift_checkbox)
        self.top_row_layout.addWidget(self.selected_preview_widget)
        self.top_row_layout.addStretch()

        self.main_layout.addWidget(self.top_row_widget)
        self.main_layout.addWidget(self.system_select_widget)
        self.main_layout.addWidget(self.selection_rows_widget)

    def _row_labels(self) -> dict[str, str]:
        return {
            "system": self.tr("体系"),
            "level": self.tr("等级"),
            "row": self.tr("所在行"),
            "col": self.tr("所在列"),
        }

    def _preview_hint_tooltip(self) -> str:
        return self.tr(
            '<div style="font-size: 15px; line-height: 1.6;">'
            "知道你们想要什么<br>"
            "2026-06 蜘蛛巢良秀专武在泛用-3级-4行-8列"
            "</div>"
        )

    def _find_scroll_area(self):
        w = self.parent()
        while w:
            if isinstance(w, ScrollArea):
                return w
            w = w.parent()
        return None

    def _scroll_to_row(self, row_index: int):
        if not (0 <= row_index < len(self._row_widgets)):
            return

        target_widget = self._row_widgets[row_index]
        if scroll_area := self._find_scroll_area():
            scroll_area.ensureWidgetVisible(target_widget, 0, 40)

    def _completed_rows(self) -> list[tuple[int, ObserveGiftSelection]]:
        return [(index, row) for index, row in enumerate(self._row_selections) if row.is_complete()]

    def _first_row_with_system(self, system: str) -> int | None:
        for index, row in enumerate(self._row_selections):
            if row.system == system:
                return index
        return None

    def _first_fillable_row(self) -> int | None:
        for index, row in enumerate(self._row_selections):
            if row.system is None and not row.is_complete():
                return index
        return None

    def _normalize_row_selections(self, rows: list[ObserveGiftSelection]) -> list[ObserveGiftSelection]:
        return ensure_placeholder_row(rows, max_completed=MAX_OBSERVE_GIFT_SELECTIONS)

    def _emit_selected_rows(self):
        mediator.team_setting.emit({"observe_ego_gift_selected": serialize_observe_ego_gift_values(self._row_selections)})

    def _rebuild_rows(self, target_row_index: int | None = None, emit: bool = False):
        while self.selection_rows_layout.count():
            item = self.selection_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._row_widgets.clear()
        labels = self._row_labels()
        for index, selection in enumerate(self._row_selections):
            row_widget = ObserveGiftSelectionRow(index, self.observe_systems, labels, self.selection_rows_widget)
            row_widget.set_selection(selection)
            row_widget.selectionChanged.connect(self._on_row_selection_changed)
            row_widget.removeRequested.connect(self._on_row_remove_requested)
            self._row_widgets.append(row_widget)
            self.selection_rows_layout.addWidget(row_widget)

        self._refresh_preview()
        QTimer.singleShot(0, self._notify_expand_card)

        if target_row_index is not None:
            QTimer.singleShot(0, lambda index=target_row_index: self._scroll_to_row(index))

        if emit:
            self._emit_selected_rows()

    def on_system_clicked(self, btn: SystemIconButton):
        for system_button in self._system_buttons.values():
            system_button.set_active(system_button is btn)

        row_index = self._first_row_with_system(btn.system)
        if row_index is not None:
            self._scroll_to_row(row_index)
            return

        fillable_index = self._first_fillable_row()
        if fillable_index is not None:
            new_rows = [ObserveGiftSelection(row.system, row.level, row.row, row.col) for row in self._row_selections]
            row = new_rows[fillable_index]
            new_rows[fillable_index] = ObserveGiftSelection(btn.system, row.level, row.row, row.col)
            self._row_selections = self._normalize_row_selections(new_rows)
            self._rebuild_rows(target_row_index=fillable_index, emit=True)
            return

        if len(self._completed_rows()) < MAX_OBSERVE_GIFT_SELECTIONS:
            new_rows = [ObserveGiftSelection(row.system, row.level, row.row, row.col) for row in self._row_selections]
            new_rows.append(ObserveGiftSelection(system=btn.system))
            self._row_selections = self._normalize_row_selections(new_rows)
            self._rebuild_rows(target_row_index=len(self._row_selections) - 1, emit=True)

    def _notify_expand_card(self):
        from qfluentwidgets import ExpandSettingCard

        w = self.parent()
        while w:
            if isinstance(w, ExpandSettingCard):
                w._adjustViewSize()
                return
            w = w.parent()

    def _on_row_selection_changed(self, row_index: int, selection: ObserveGiftSelection):
        if not (0 <= row_index < len(self._row_selections)):
            return

        new_rows = [ObserveGiftSelection(row.system, row.level, row.row, row.col) for row in self._row_selections]
        new_rows[row_index] = selection
        self._row_selections = self._normalize_row_selections(new_rows)
        self._rebuild_rows(target_row_index=row_index, emit=True)

    def _on_row_remove_requested(self, row_index: int):
        if not (0 <= row_index < len(self._row_selections)):
            return

        new_rows = [ObserveGiftSelection(row.system, row.level, row.row, row.col) for row in self._row_selections]
        if new_rows[row_index].is_complete():
            new_rows.pop(row_index)
            target_row_index = min(row_index, len(new_rows) - 1) if new_rows else 0
        else:
            new_rows[row_index] = ObserveGiftSelection()
            target_row_index = row_index

        self._row_selections = self._normalize_row_selections(new_rows)
        self._rebuild_rows(target_row_index=target_row_index, emit=True)

    def on_preview_clicked(self, row_index: int):
        self._scroll_to_row(row_index)

    def _refresh_preview(self):
        completed_rows = self._completed_rows()
        for index, label in enumerate(self._preview_labels):
            if index < len(completed_rows):
                row_index, selection = completed_rows[index]
                label.row_index = row_index
                pixmap = QPixmap(f"./assets/app/status_effects/{selection.system}.png")
                if not pixmap.isNull():
                    label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setStyleSheet(
                        "border: 1px solid rgba(128,128,128,0.4); border-radius: 4px; background-color: rgba(0,0,0,0.1);"
                    )
                    continue

            label.row_index = None
            label.clear()
            label.setStyleSheet(
                "border: 1px solid rgba(128,128,128,0.4); border-radius: 4px; background-color: rgba(0,0,0,0.1);"
            )

    def load_selected(self, selected: list[str]):
        for system_button in self._system_buttons.values():
            system_button.set_active(False)
        self._row_selections = parse_observe_ego_gift_values(selected)
        self._rebuild_rows()

    def retranslateUi(self):
        self.observe_ego_gift_checkbox.check_box.setText(self.tr("启用观测"))
        self.preview_hint_button.setToolTip(self._preview_hint_tooltip())
        self.observe_systems = [
            ("burn", self.tr("烧伤")),
            ("bleed", self.tr("流血")),
            ("tremor", self.tr("震颤")),
            ("rupture", self.tr("破裂")),
            ("sinking", self.tr("沉沦")),
            ("poise", self.tr("呼吸")),
            ("charge", self.tr("充能")),
            ("slash", self.tr("斩击")),
            ("pierce", self.tr("突刺")),
            ("blunt", self.tr("打击")),
            ("general", self.tr("泛用")),
        ]
        for system, label in self.observe_systems:
            if system in self._system_buttons:
                if self._system_buttons[system]._force_text or self._system_buttons[system]._normal_pixmap.isNull():
                    self._system_buttons[system].setText(label)
        self._rebuild_rows()


class CustomizeInfoModule(QFrame):
    def __init__(self, team_num=0, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomizeInfoModule")
        self.main_layout = QVBoxLayout(self)
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        self.team_num = team_num
        self.info = self.get_info(team_num)
        self.update_data()

        LanguageManager().register_component(self)
        self.retranslateUi()

    def __init_widget(self):
        self.first_line_widget = QWidget()
        self.first_line = QHBoxLayout(self.first_line_widget)
        self.second_line_widget = QWidget()
        self.second_line = QHBoxLayout(self.second_line_widget)
        self.third_line_widget = QWidget()
        self.third_line = QHBoxLayout(self.third_line_widget)
        self.fresh_data_button_layout = QHBoxLayout()
        self.clear_data_button_layout = QHBoxLayout()

    def __init_card(self):
        self.total_count = BaseLabel(self.tr("总镜牢次数: 统计数据不足"), parent=self)
        self.hard_count = BaseLabel(self.tr("困难镜牢次数: 统计数据不足"), parent=self)
        self.normal_count = BaseLabel(self.tr("普通镜牢次数: 统计数据不足"), parent=self)
        self.average_time_hard = BaseLabel(self.tr("困难平均用时: 统计数据不足"), parent=self)
        self.average_time_hard_last5 = BaseLabel(self.tr("困难最近5次平均用时: 统计数据不足"), parent=self)
        self.average_time_hard_last10 = BaseLabel(self.tr("困难最近10次平均用时: 统计数据不足"), parent=self)
        self.average_time_normal = BaseLabel(self.tr("普通平均用时: 统计数据不足"), parent=self)
        self.average_time_normal_last5 = BaseLabel(self.tr("普通最近5次平均用时: 统计数据不足"), parent=self)
        self.average_time_normal_last10 = BaseLabel(self.tr("普通最近10次平均用时: 统计数据不足"), parent=self)

        self.refesh_button = PushButton(self.tr("刷新数据"))
        self.refesh_button.clicked.connect(self.fresh_data)
        self.clear_data_button = PrimaryPushButton(self.tr("清除历史统计数据"))
        self.clear_data_button.clicked.connect(self.clear_data)

    def __init_layout(self):
        self.first_line.addWidget(self.total_count)
        self.first_line.addWidget(self.hard_count)
        self.first_line.addWidget(self.normal_count)
        self.second_line.addWidget(self.average_time_hard)
        self.second_line.addWidget(self.average_time_hard_last5)
        self.second_line.addWidget(self.average_time_hard_last10)
        self.third_line.addWidget(self.average_time_normal)
        self.third_line.addWidget(self.average_time_normal_last5)
        self.third_line.addWidget(self.average_time_normal_last10)
        self.fresh_data_button_layout.addWidget(self.refesh_button)
        self.clear_data_button_layout.addWidget(self.clear_data_button)

        self.main_layout.addWidget(self.first_line_widget)
        self.main_layout.addWidget(self.second_line_widget)
        self.main_layout.addWidget(self.third_line_widget)
        self.main_layout.addLayout(self.fresh_data_button_layout)
        self.main_layout.addLayout(self.clear_data_button_layout)

    def retranslateUi(self):
        pass

    def get_info(self, team_num: int):
        return_dict = {}
        team = cfg.get_team(team_num)
        team_total_mirror_time_hard = team.total_mirror_time_hard
        team_total_mirror_hard_count = team.mirror_hard_count
        team_total_mirror_time_normal = team.total_mirror_time_normal
        team_total_mirror_normal_count = team.mirror_normal_count

        return_dict["total_count"] = team_total_mirror_hard_count + team_total_mirror_normal_count
        return_dict["hard_count"] = team_total_mirror_hard_count
        return_dict["normal_count"] = team_total_mirror_normal_count
        return_dict["average_time_hard"] = (
            team_total_mirror_time_hard[0] if len(team_total_mirror_time_hard) > 0 else 0
        )
        return_dict["average_time_hard_last5"] = (
            team_total_mirror_time_hard[1] if len(team_total_mirror_time_hard) > 1 else 0
        )
        return_dict["average_time_hard_last10"] = (
            team_total_mirror_time_hard[2] if len(team_total_mirror_time_hard) > 2 else 0
        )
        return_dict["average_time_normal"] = (
            team_total_mirror_time_normal[0] if len(team_total_mirror_time_normal) > 0 else 0
        )
        return_dict["average_time_normal_last5"] = (
            team_total_mirror_time_normal[1] if len(team_total_mirror_time_normal) > 1 else 0
        )
        return_dict["average_time_normal_last10"] = (
            team_total_mirror_time_normal[2] if len(team_total_mirror_time_normal) > 2 else 0
        )
        return return_dict

    def clear_data(self):
        team = cfg.get_team(self.team_num)
        team.total_mirror_time_hard = [0.0, 0.0, 0.0]
        team.mirror_hard_count = 0
        team.total_mirror_time_normal = [0.0, 0.0, 0.0]
        team.mirror_normal_count = 0
        cfg.save_team(self.team_num)
        self.fresh_data()

    def update_data(self):
        self.total_count.setText(self.tr("总镜牢次数: ") + str(self.info.get("total_count", 0)))
        self.hard_count.setText(self.tr("困难镜牢次数: ") + str(self.info.get("hard_count", 0)))
        self.normal_count.setText(self.tr("普通镜牢次数: ") + str(self.info.get("normal_count", 0)))
        average_time_hard = self.info.get("average_time_hard", 0.0)
        if average_time_hard >= 0.005:
            self.average_time_hard.setText(
                self.tr("困难平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_hard // 60, sec=average_time_hard % 60
                )
            )
        else:
            self.average_time_hard.setText(self.tr("困难平均用时: 统计数据不足"))
        average_time_hard_last5 = self.info.get("average_time_hard_last5", 0.0)
        if average_time_hard_last5 >= 0.005:
            self.average_time_hard_last5.setText(
                self.tr("困难最近5次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_hard_last5 // 60, sec=average_time_hard_last5 % 60
                )
            )
        else:
            self.average_time_hard_last5.setText(self.tr("困难最近5次平均用时: 统计数据不足"))
        average_time_hard_last10 = self.info.get("average_time_hard_last10", 0.0)
        if average_time_hard_last10 >= 0.005:
            self.average_time_hard_last10.setText(
                self.tr("困难最近10次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_hard_last10 // 60,
                    sec=average_time_hard_last10 % 60,
                )
            )
        else:
            self.average_time_hard_last10.setText(self.tr("困难最近10次平均用时: 统计数据不足"))
        average_time_normal = self.info.get("average_time_normal", 0.0)
        if average_time_normal >= 0.005:
            self.average_time_normal.setText(
                self.tr("普通平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_normal // 60, sec=average_time_normal % 60
                )
            )
        else:
            self.average_time_normal.setText(self.tr("普通平均用时: 统计数据不足"))
        average_time_normal_last5 = self.info.get("average_time_normal_last5", 0.0)
        if average_time_normal_last5 >= 0.005:
            self.average_time_normal_last5.setText(
                self.tr("普通最近5次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_normal_last5 // 60,
                    sec=average_time_normal_last5 % 60,
                )
            )
        else:
            self.average_time_normal_last5.setText(self.tr("普通最近5次平均用时: 统计数据不足"))
        average_time_normal_last10 = self.info.get("average_time_normal_last10", 0.0)
        if average_time_normal_last10 >= 0.005:
            self.average_time_normal_last10.setText(
                self.tr("普通最近10次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_normal_last10 // 60,
                    sec=average_time_normal_last10 % 60,
                )
            )
        else:
            self.average_time_normal_last10.setText(self.tr("普通最近10次平均用时: 统计数据不足"))

    def fresh_data(self):
        self.info = self.get_info(self.team_num)
        self.update_data()

    def set_team_num(self, team_num: int):
        self.team_num = team_num
        self.fresh_data()
