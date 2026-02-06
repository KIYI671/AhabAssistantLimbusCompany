from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import ExpandSettingCard, PrimaryPushButton, PushButton, ScrollArea
from qfluentwidgets import FluentIcon as FIF

from app import *
from app.base_combination import (
    CheckBoxWithComboBox,
    CheckBoxWithLineEdit,
    LabelWithComboBox,
    SinnerSelect,
)
from app.base_tools import BaseCheckBox, BaseComboBox, BaseLabel, BaseSettingLayout
from app.language_manager import LanguageManager
from module.config import cfg


class TeamSettingCard(QFrame):
    def __init__(self, team_num=0, parent=None):
        super().__init__(parent)
        self.team_num = team_num
        self.setObjectName("TeamSettingCard")
        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        # self.setStyleSheet("border: 1px solid black;")

        if cfg.get_value(f"team{team_num}_setting"):
            config_team_setting = cfg.get_value(f"team{team_num}_setting")
            import copy

            self.team_setting = copy.deepcopy(team_setting_template)
            # 用配置中的值覆盖模板的同名key（仅处理模板中存在的key）
            for key, value in config_team_setting.items():
                if key in self.team_setting:  # 忽略模板中已删除的key
                    self.team_setting[key] = value
        else:
            self.team_setting = dict(team_setting_template)
        self.dict_keys = list(team_setting_template.keys())

        self.read_settings()
        self.refresh_starlight_select()

        self.connect_mediator()
        LanguageManager().register_component(self)
        self.select_system.retranslateUi()
        self.select_shop_strategy.retranslateUi()

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        self.scroll_general = ScrollArea()
        self.scroll_general.setWidgetResizable(True)
        self.scroll_general.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.page_widget = QWidget()
        self.scroll_general.setWidget(self.page_widget)

        self.layout_ = QVBoxLayout(self.page_widget)

        self.main_layout.addWidget(self.scroll_general)

        self.combobox_layout = BaseSettingLayout(box_type=1)
        self.combobox_layout.setMaximumHeight(75)
        self.combobox_layout.BoxLayout.setSpacing(40)
        self.select_sinner_container_1 = QWidget()
        self.select_sinner_layout_1 = QHBoxLayout(self.select_sinner_container_1)
        self.select_sinner_layout_1.setContentsMargins(
            0, 10, 0, 10
        )  # Add vertical margin for banner overflow
        self.select_sinner_container_2 = QWidget()
        self.select_sinner_layout_2 = QHBoxLayout(self.select_sinner_container_2)
        self.select_sinner_layout_2.setContentsMargins(
            0, 10, 0, 20
        )  # Extra bottom margin for banner

        self.gift_system_layout = BaseSettingLayout(box_type=2)
        self.gift_system_layout.setMaximumHeight(150)
        self.gift_system_list_1 = QHBoxLayout()
        self.gift_system_list_2 = QHBoxLayout()

        self.custom_layout = ExpandSettingCard(
            icon=FIF.EDIT,
            title=self.tr("自定义设置（设置存在冲突时，将根据优先级覆盖生效）"),
        )

        self.custom_layout2 = ExpandSettingCard(
            icon=FIF.INFO, title=self.tr("编队统计数据")
        )

        self.setting_layout = QHBoxLayout()

        self.scroll_general.enableTransparentBackground()

    def __init_card(self):
        self.select_team = LabelWithComboBox(
            self.tr("选择队伍名称"), "team_number", all_teams, vbox=False
        )
        self.select_system = LabelWithComboBox(
            self.tr("选择队伍体系"), "team_system", all_systems, vbox=False
        )
        self.select_shop_strategy = LabelWithComboBox(
            self.tr("选择商店策略"), "shop_strategy", shop_strategy, vbox=False
        )

        self.sinner_YiSang = SinnerSelect(
            "YiSang",
            self.tr("李箱"),
            None,
            "./assets/app/sinner/YiSang/LCB_Sinner_Yi_Sang.png",
        )
        self.sinner_Faust = SinnerSelect(
            "Faust",
            self.tr("浮士德"),
            None,
            "./assets/app/sinner/Faust/LCB_Sinner_Faust.png",
        )
        self.sinner_DonQuixote = SinnerSelect(
            "DonQuixote",
            self.tr("堂吉诃德"),
            None,
            "./assets/app/sinner/DonQuixote/LCB_Sinner_Don_Quixote.png",
        )
        self.sinner_Ryoshu = SinnerSelect(
            "Ryoshu",
            self.tr("良秀"),
            None,
            "./assets/app/sinner/Ryoshu/LCB_Sinner_Ryōshū.png",
        )
        self.sinner_Meursault = SinnerSelect(
            "Meursault",
            self.tr("默尔索"),
            None,
            "./assets/app/sinner/Meursault/LCB_Sinner_Meursault.webp",
        )
        self.sinner_HongLu = SinnerSelect(
            "HongLu",
            self.tr("鸿璐"),
            None,
            "./assets/app/sinner/HongLu/LCB_Sinner_Hong_Lu.png",
        )

        self.sinner_Heathcliff = SinnerSelect(
            "Heathcliff",
            self.tr("希斯克利夫"),
            None,
            "./assets/app/sinner/Heathcliff/LCB_Sinner_Heathcliff.png",
        )
        self.sinner_Ishmael = SinnerSelect(
            "Ishmael",
            self.tr("以实玛利"),
            None,
            "./assets/app/sinner/Ishmael/LCB_Sinner_Ishmael.png",
        )
        self.sinner_Rodion = SinnerSelect(
            "Rodion",
            self.tr("罗佳"),
            None,
            "./assets/app/sinner/Rodion/LCB_Sinner_Rodion.png",
        )
        self.sinner_Sinclair = SinnerSelect(
            "Sinclair",
            self.tr("辛克莱"),
            None,
            "./assets/app/sinner/Sinclair/LCB_Sinner_Sinclair.png",
        )
        self.sinner_Outis = SinnerSelect(
            "Outis",
            self.tr("奥提斯"),
            None,
            "./assets/app/sinner/Outis/LCB_Sinner_Outis.png",
        )
        self.sinner_Gregor = SinnerSelect(
            "Gregor",
            self.tr("格里高尔"),
            None,
            "./assets/app/sinner/Gregor/LCB_Sinner_Gregor.png",
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

        self.customize_settings_module = CustomizeSettingsModule()
        self.customize_info_module = CustomizeInfoModule(self.team_num)

        self.cancel_button = PushButton(self.tr("取消"))
        self.cancel_button.clicked.connect(self.cancel_team_setting)
        self.confirm_button = PrimaryPushButton(self.tr("保存"))
        self.confirm_button.clicked.connect(self.save_team_setting)

    def __init_layout(self):
        self.combobox_layout.add(self.select_team)
        self.combobox_layout.add(self.select_system)
        self.combobox_layout.add(self.select_shop_strategy)

        self.select_sinner_layout_1.addWidget(self.sinner_YiSang)
        self.select_sinner_layout_1.addWidget(self.sinner_Faust)
        self.select_sinner_layout_1.addWidget(self.sinner_DonQuixote)
        self.select_sinner_layout_1.addWidget(self.sinner_Ryoshu)
        self.select_sinner_layout_1.addWidget(self.sinner_Meursault)
        self.select_sinner_layout_1.addWidget(self.sinner_HongLu)
        self.select_sinner_layout_2.addWidget(self.sinner_Heathcliff)
        self.select_sinner_layout_2.addWidget(self.sinner_Ishmael)
        self.select_sinner_layout_2.addWidget(self.sinner_Rodion)
        self.select_sinner_layout_2.addWidget(self.sinner_Sinclair)
        self.select_sinner_layout_2.addWidget(self.sinner_Outis)
        self.select_sinner_layout_2.addWidget(self.sinner_Gregor)

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

        self.setting_layout.addWidget(self.cancel_button)
        self.setting_layout.addWidget(self.confirm_button)

        self.layout_.addWidget(self.combobox_layout)
        self.layout_.addWidget(
            self.select_sinner_container_1
        )  # Use container for banner overflow
        self.layout_.addWidget(
            self.select_sinner_container_2
        )  # Use container for banner overflow
        self.layout_.addWidget(self.gift_system_layout)
        self.layout_.addWidget(self.custom_layout)
        self.layout_.addWidget(self.custom_layout2)

        self.main_layout.addLayout(self.setting_layout)
        self.main_layout.addSpacing(15)
        self.setting_layout.setContentsMargins(10, 0, 10, 0)  # 手动对齐其他组件

        self.custom_layout.viewLayout.addWidget(self.customize_settings_module)
        self.custom_layout2.viewLayout.addWidget(self.customize_info_module)

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.team_setting.connect(self.setting_team)
        mediator.sinner_be_selected.connect(self.refresh_sinner_order)

    def disconnect_mediator(self):
        """断开所有 mediator 信号连接"""
        mediator.team_setting.disconnect(self.setting_team)
        mediator.sinner_be_selected.disconnect(self.refresh_sinner_order)

    def setting_team(self, data_dict: dict):
        keys = list(data_dict.keys())[0]
        values = list(data_dict.values())[0]
        if keys in self.dict_keys:
            self.team_setting[keys] = values
            if keys == "team_system":
                self.foolproof(values)
        elif keys in all_sinners_name:
            sinner_index = all_sinners_name.index(keys)
            if values:
                self.team_setting["sinners_be_select"] += 1
                self.team_setting["chosen_sinners"][sinner_index] = 1
                self.team_setting["sinner_order"][sinner_index] = self.team_setting[
                    "sinners_be_select"
                ]
            else:
                order = self.team_setting["sinner_order"][sinner_index]
                self.team_setting["sinners_be_select"] -= 1
                self.team_setting["chosen_sinners"][sinner_index] = 0
                for i in range(12):
                    if self.team_setting["sinner_order"][i] > order:
                        self.team_setting["sinner_order"][i] -= 1
                self.team_setting["sinner_order"][sinner_index] = 0
            self.refresh_sinner_order()
        elif "starlight_" in keys:
            starlight_index = int(keys.split("_")[-1]) - 1
            if values:
                self.team_setting["opening_bonus_select"] += 1
                self.team_setting["opening_bonus"][starlight_index] = 1
                self.team_setting["opening_bonus_order"][starlight_index] = (
                    self.team_setting["opening_bonus_select"]
                )
            else:
                order = self.team_setting["opening_bonus_order"][starlight_index]
                self.team_setting["opening_bonus_select"] -= 1
                self.team_setting["opening_bonus"][starlight_index] = 0
                for i in range(10):
                    if self.team_setting["opening_bonus_order"][i] > order:
                        self.team_setting["opening_bonus_order"][i] -= 1
                self.team_setting["opening_bonus_order"][starlight_index] = 0
            self.refresh_starlight_order()
        elif keys in second_system_mode:
            mode_index = second_system_mode.index(keys)
            self.team_setting["second_system_action"][mode_index] = values
        elif "ignore_shop_" in keys:
            shop_index = int(keys.split("_")[-1]) - 1
            self.team_setting["ignore_shop"][shop_index] = values

    def save_team_setting(self):
        cfg.set_value(f"team{self.team_num}_setting", self.team_setting)
        self.cancel_team_setting()

    def refresh_starlight_order(self):
        opening_bonus_order = self.team_setting["opening_bonus_order"]
        for i in range(1, 11):
            starlight = self.findChild(CheckBoxWithLineEdit, f"starlight_{i}")
            if starlight is not None:
                if opening_bonus_order[i - 1] != 0:
                    starlight.set_text(str(opening_bonus_order[i - 1]))
                else:
                    starlight.set_text("")

    def refresh_starlight_select(self):
        opening_bonus = self.team_setting["opening_bonus"]
        for i in range(1, 11):
            starlight = self.findChild(CheckBoxWithLineEdit, f"starlight_{i}")
            if starlight is not None:
                if opening_bonus[i - 1]:
                    starlight.set_checked(True)
                else:
                    starlight.set_checked(False)

        self.refresh_starlight_order()

    def refresh_sinner_order(self):
        sinner_order = self.team_setting["sinner_order"]
        for i in range(12):
            sinner = self.findChild(SinnerSelect, all_sinners_name[i])
            if sinner is not None:
                if sinner_order[i] != 0:
                    sinner.set_text(str(sinner_order[i]))
                else:
                    sinner.set_text("")

    def read_settings(self):
        chosen_sinners = self.team_setting["chosen_sinners"]
        for i in range(12):
            sinner = self.findChild(SinnerSelect, all_sinners_name[i])
            if sinner is not None:
                if chosen_sinners[i]:
                    sinner.set_checkbox(True)
                else:
                    sinner.set_checkbox(False)

        self.refresh_sinner_order()

        second_system_action = self.team_setting["second_system_action"]
        ignore_shop = self.team_setting["ignore_shop"]
        for i in range(4):
            if second_system_action[i]:
                self.findChild(BaseCheckBox, second_system_mode[i]).set_checked(True)

        for i in range(1, 6):
            if ignore_shop[i - 1]:
                self.findChild(BaseCheckBox, f"ignore_shop_{i}").set_checked(True)

        for checkbox in all_checkbox_config_name:
            if self.findChild(BaseCheckBox, checkbox):
                self.findChild(BaseCheckBox, checkbox).set_checked(
                    self.team_setting[checkbox]
                )

        for combobox in all_combobox_config_name:
            if self.findChild(BaseComboBox, combobox):
                if combobox == "team_number":
                    self.findChild(BaseComboBox, combobox).set_options(
                        self.team_setting[combobox] - 1
                    )
                else:
                    self.findChild(BaseComboBox, combobox).set_options(
                        self.team_setting[combobox]
                    )
                    if combobox == "team_system":
                        self.foolproof(self.team_setting[combobox])

    def foolproof(self, team_system):
        for checkbox in all_checkbox_config_name:
            if check_box := self.findChild(BaseCheckBox, checkbox):
                if checkbox.startswith("system_"):
                    check_box.set_box_enabled(True)
        check_box = self.findChild(
            BaseCheckBox, f"system_{all_systems_name[team_system]}"
        )
        if check_box:
            check_box.set_checked(False)
            check_box.set_box_enabled(False)
            self.team_setting[f"system_{all_systems_name[team_system]}"] = False

    def cancel_team_setting(self):
        mediator.close_setting.emit()

    def retranslateUi(self):
        self.select_system.retranslateUi()
        self.select_shop_strategy.retranslateUi()
        self.select_team.label.label.setText(self.tr("选择队伍名称"))
        self.select_system.label.label.setText(self.tr("选择队伍体系"))
        self.select_shop_strategy.label.label.setText(self.tr("选择商店策略"))
        self.sinner_YiSang.label_str.setText(self.tr("李箱"))
        self.sinner_Faust.label_str.setText(self.tr("浮士德"))
        self.sinner_DonQuixote.label_str.setText(self.tr("堂吉诃德"))
        self.sinner_Ryoshu.label_str.setText(self.tr("良秀"))
        self.sinner_Meursault.label_str.setText(self.tr("默尔索"))
        self.sinner_HongLu.label_str.setText(self.tr("鸿璐"))
        self.sinner_Heathcliff.label_str.setText(self.tr("希斯克利夫"))
        self.sinner_Ishmael.label_str.setText(self.tr("以实玛利"))
        self.sinner_Rodion.label_str.setText(self.tr("罗佳"))
        self.sinner_Sinclair.label_str.setText(self.tr("辛克莱"))
        self.sinner_Outis.label_str.setText(self.tr("奥提斯"))
        self.sinner_Gregor.label_str.setText(self.tr("格里高尔"))
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

        self.cancel_button.setText(self.tr("取消"))
        self.confirm_button.setText(self.tr("保存"))


class CustomizeSettingsModule(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomizeSettingsModule")
        self.main_layout = QVBoxLayout(self)
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        LanguageManager().register_component(self)
        self.retranslateUi()

    def __init_widget(self):
        self.first_line_widget = QWidget()
        self.first_line = QHBoxLayout(self.first_line_widget)
        self.second_line_widget = QWidget()
        self.second_line = QHBoxLayout(self.second_line_widget)
        self.third_line_widget = QWidget()
        self.third_line = QHBoxLayout(self.third_line_widget)

        self.features_patch_widget_1 = QWidget()
        self.features_patch_line_1 = QHBoxLayout(self.features_patch_widget_1)

        self.star_layout = BaseSettingLayout(box_type=2)
        self.star_layout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.star_layout.setMaximumHeight(150)
        self.star_layout.setMaximumWidth(950)
        self.star_list = QGridLayout()

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
        self.floor_shop = QHBoxLayout()

    def __init_card(self):
        self.do_not_heal = BaseCheckBox(
            "do_not_heal", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不治疗罪人")
        )
        self.do_not_buy = BaseCheckBox(
            "do_not_buy", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不购买饰品")
        )
        self.do_not_fuse = BaseCheckBox(
            "do_not_fuse", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不合成饰品")
        )
        self.do_not_sell = BaseCheckBox(
            "do_not_sell", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不出售饰品")
        )
        self.do_not_enhance = BaseCheckBox(
            "do_not_enhance", None, QT_TRANSLATE_NOOP("BaseCheckBox", "不升级饰品")
        )

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
        self.use_starlight = BaseCheckBox(
            "use_starlight", None, QT_TRANSLATE_NOOP("BaseCheckBox", "开局星光换钱")
        )

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

        self.choose_opening_bonus = BaseCheckBox(
            "choose_opening_bonus",
            FIF.BUS,
            QT_TRANSLATE_NOOP("BaseCheckBox", "自选开局加成"),
            center=False,
        )

        QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星光")
        self.starlight_1 = CheckBoxWithLineEdit("starlight_1", "星光1")
        self.starlight_2 = CheckBoxWithLineEdit("starlight_2", "星光2")
        self.starlight_3 = CheckBoxWithLineEdit("starlight_3", "星光3")
        self.starlight_4 = CheckBoxWithLineEdit("starlight_4", "星光4")
        self.starlight_5 = CheckBoxWithLineEdit("starlight_5", "星光5")

        self.starlight_6 = CheckBoxWithLineEdit("starlight_6", "星光6")
        self.starlight_7 = CheckBoxWithLineEdit("starlight_7", "星光7")
        self.starlight_8 = CheckBoxWithLineEdit("starlight_8", "星光8")
        self.starlight_9 = CheckBoxWithLineEdit("starlight_9", "星光9")
        self.starlight_10 = CheckBoxWithLineEdit("starlight_10", "星光10")

        self.after_level_IV = CheckBoxWithComboBox(
            "after_level_IV",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "合成四级以后"),
            None,
            "after_level_IV_select",
        )
        self.after_level_IV.add_items(after_fuse_level_IV)
        self.shopping_strategy = CheckBoxWithComboBox(
            "shopping_strategy",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "购物策略"),
            None,
            "shopping_strategy_select",
        )
        self.shopping_strategy.add_items(shopping_strategy)

        self.opening_items = CheckBoxWithComboBox(
            "opening_items",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "自选开局饰品"),
            None,
            "opening_items_system",
        )
        self.opening_items.add_items(all_systems)
        self.opening_items.add_combobox("opening_items_select")
        self.opening_items.add_times_for_additional(start_gift)

        self.second_system = CheckBoxWithComboBox(
            "second_system",
            QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "第二体系"),
            None,
            "second_system_select",
        )
        self.second_system.add_items(all_systems)
        self.second_system.add_combobox("second_system_setting")
        self.second_system.add_times_for_additional(second_systems)

        self.second_system_fuse_IV = BaseCheckBox(
            "second_system_fuse_IV", None, QT_TRANSLATE_NOOP("BaseCheckBox", "合成四级")
        )
        self.second_system_buy = BaseCheckBox(
            "second_system_buy", None, QT_TRANSLATE_NOOP("BaseCheckBox", "购买")
        )
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

        QT_TRANSLATE_NOOP("BaseLabel", "忽略商店")
        self.ignore_shop = BaseLabel("忽略商店")
        self.ignore_shop.add_icon(FIF.CUT)
        self.floor_shop_1 = BaseCheckBox(
            "ignore_shop_1", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第一层")
        )
        self.floor_shop_2 = BaseCheckBox(
            "ignore_shop_2", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第二层")
        )
        self.floor_shop_3 = BaseCheckBox(
            "ignore_shop_3", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第三层")
        )
        self.floor_shop_4 = BaseCheckBox(
            "ignore_shop_4", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第四层")
        )
        self.floor_shop_5 = BaseCheckBox(
            "ignore_shop_5", None, QT_TRANSLATE_NOOP("BaseCheckBox", "第五层")
        )

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

        self.star_list.addWidget(self.starlight_1, 0, 0)
        self.star_list.addWidget(self.starlight_2, 0, 1)
        self.star_list.addWidget(self.starlight_3, 0, 2)
        self.star_list.addWidget(self.starlight_4, 0, 3)
        self.star_list.addWidget(self.starlight_5, 0, 4)
        self.star_list.addWidget(self.starlight_6, 1, 0)
        self.star_list.addWidget(self.starlight_7, 1, 1)
        self.star_list.addWidget(self.starlight_8, 1, 2)
        self.star_list.addWidget(self.starlight_9, 1, 3)
        self.star_list.addWidget(self.starlight_10, 1, 4)
        self.star_layout.add(self.choose_opening_bonus)
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
        self.choose_opening_bonus.retranslateUi()
        self.re_formation_each_floor.retranslateUi()

        starlight_text = self.tr("星光")
        for index in range(1, 11):
            starlight = self.findChild(CheckBoxWithLineEdit, f"starlight_{index}")
            starlight.box.setText(f"{starlight_text}{index}")
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
        self.normal_count = BaseLabel(
            self.tr("普通镜牢次数: 统计数据不足"), parent=self
        )
        self.average_time_hard = BaseLabel(
            self.tr("困难平均用时: 统计数据不足"), parent=self
        )
        self.average_time_hard_last5 = BaseLabel(
            self.tr("困难最近5次平均用时: 统计数据不足"), parent=self
        )
        self.average_time_hard_last10 = BaseLabel(
            self.tr("困难最近10次平均用时: 统计数据不足"), parent=self
        )
        self.average_time_normal = BaseLabel(
            self.tr("普通平均用时: 统计数据不足"), parent=self
        )
        self.average_time_normal_last5 = BaseLabel(
            self.tr("普通最近5次平均用时: 统计数据不足"), parent=self
        )
        self.average_time_normal_last10 = BaseLabel(
            self.tr("普通最近10次平均用时: 统计数据不足"), parent=self
        )

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

    def get_info(self, team_num):
        return_dict = {}
        if config_team_history := cfg.get_value(f"team{team_num}_history"):
            team_total_mirror_time_hard = config_team_history.get(
                "total_mirror_time_hard", [0.0, 0.0, 0.0]
            )
            team_total_mirror_hard_count = config_team_history.get(
                "mirror_hard_count", 0
            )
            team_total_mirror_time_normal = config_team_history.get(
                "total_mirror_time_normal", [0.0, 0.0, 0.0]
            )
            team_total_mirror_normal_count = config_team_history.get(
                "mirror_normal_count", 0
            )

            return_dict["total_count"] = (
                team_total_mirror_hard_count + team_total_mirror_normal_count
            )
            return_dict["hard_count"] = team_total_mirror_hard_count
            return_dict["normal_count"] = team_total_mirror_normal_count
            return_dict["average_time_hard"] = (
                team_total_mirror_time_hard[0]
                if len(team_total_mirror_time_hard) > 0
                else 0
            )
            return_dict["average_time_hard_last5"] = (
                team_total_mirror_time_hard[1]
                if len(team_total_mirror_time_hard) > 1
                else 0
            )
            return_dict["average_time_hard_last10"] = (
                team_total_mirror_time_hard[2]
                if len(team_total_mirror_time_hard) > 2
                else 0
            )
            return_dict["average_time_normal"] = (
                team_total_mirror_time_normal[0]
                if len(team_total_mirror_time_normal) > 0
                else 0
            )
            return_dict["average_time_normal_last5"] = (
                team_total_mirror_time_normal[1]
                if len(team_total_mirror_time_normal) > 1
                else 0
            )
            return_dict["average_time_normal_last10"] = (
                team_total_mirror_time_normal[2]
                if len(team_total_mirror_time_normal) > 2
                else 0
            )
        return return_dict

    def clear_data(self):
        if cfg.get_value(f"team{self.team_num}_history"):
            config_team_history = cfg.get_value(f"team{self.team_num}_history")
            config_team_history["total_mirror_time_hard"] = [0.0, 0.0, 0.0]
            config_team_history["mirror_hard_count"] = 0
            config_team_history["total_mirror_time_normal"] = [0.0, 0.0, 0.0]
            config_team_history["mirror_normal_count"] = 0
            cfg.set_value(f"team{self.team_num}_history", config_team_history)
        self.fresh_data()

    def update_data(self):
        self.total_count.setText(
            self.tr("总镜牢次数: ") + str(self.info.get("total_count", 0))
        )
        self.hard_count.setText(
            self.tr("困难镜牢次数: ") + str(self.info.get("hard_count", 0))
        )
        self.normal_count.setText(
            self.tr("普通镜牢次数: ") + str(self.info.get("normal_count", 0))
        )
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
            self.average_time_hard_last5.setText(
                self.tr("困难最近5次平均用时: 统计数据不足")
            )
        average_time_hard_last10 = self.info.get("average_time_hard_last10", 0.0)
        if average_time_hard_last10 >= 0.005:
            self.average_time_hard_last10.setText(
                self.tr("困难最近10次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_hard_last10 // 60,
                    sec=average_time_hard_last10 % 60,
                )
            )
        else:
            self.average_time_hard_last10.setText(
                self.tr("困难最近10次平均用时: 统计数据不足")
            )
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
            self.average_time_normal_last5.setText(
                self.tr("普通最近5次平均用时: 统计数据不足")
            )
        average_time_normal_last10 = self.info.get("average_time_normal_last10", 0.0)
        if average_time_normal_last10 >= 0.005:
            self.average_time_normal_last10.setText(
                self.tr("普通最近10次平均用时: {min:.0f} : {sec:.2f} ").format(
                    min=average_time_normal_last10 // 60,
                    sec=average_time_normal_last10 % 60,
                )
            )
        else:
            self.average_time_normal_last10.setText(
                self.tr("普通最近10次平均用时: 统计数据不足")
            )

    def fresh_data(self):
        self.info = self.get_info(self.team_num)
        self.update_data()
