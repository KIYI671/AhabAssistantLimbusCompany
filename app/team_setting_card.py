from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget, QHBoxLayout, QSizePolicy, QGridLayout
from qfluentwidgets import FluentIcon as FIF, ExpandSettingCard
from qfluentwidgets import ScrollArea, PrimaryPushButton, PushButton

from app import *
from app.base_combination import LabelWithComboBox, SinnerSelect, CheckBoxWithComboBox, CheckBoxWithLineEdit
from app.base_tools import BaseCheckBox, BaseSettingLayout, BaseLabel, BaseComboBox
from module.config import cfg


class TeamSettingCard(QFrame):
    def __init__(self, team_num=0, parent=None):
        super().__init__(parent)
        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        #self.setStyleSheet("border: 1px solid black;")

        self.team_num=team_num
        if cfg.get_value(f"team{team_num}_setting"):
            self.team_setting = cfg.get_value(f"team{team_num}_setting")
        else:
            self.team_setting = dict(team_setting_template)
        self.dict_keys = list(team_setting_template.keys())

        self.read_settings()
        self.refresh_starlight_select()

        self.connect_mediator()

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        self.scroll_general = ScrollArea(self)
        self.scroll_general.setWidgetResizable(True)
        self.scroll_general.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.page_widget = QWidget()
        self.scroll_general.setWidget(self.page_widget)

        self.layout = QVBoxLayout(self.page_widget)

        self.main_layout.addWidget(self.scroll_general)

        self.combobox_layout = BaseSettingLayout(box_type=1)
        self.combobox_layout.setMaximumHeight(75)
        self.combobox_layout.BoxLayout.setSpacing(40)
        self.select_sinner_layout_1 = QHBoxLayout()
        self.select_sinner_layout_2 = QHBoxLayout()

        self.gift_system_layout = BaseSettingLayout(box_type=2)
        self.gift_system_layout.setMaximumHeight(150)
        self.gift_system_list_1 = QHBoxLayout()
        self.gift_system_list_2 = QHBoxLayout()

        self.custom_layout = ExpandSettingCard(icon=FIF.EDIT, title="自定义设置", parent=self)

        self.setting_layout = QHBoxLayout()

        self.scroll_general.enableTransparentBackground()

    def __init_card(self):
        self.select_team = LabelWithComboBox("选择队伍名称", "team_number", all_teams, vbox=False)
        self.select_system = LabelWithComboBox("选择队伍体系", "team_system", all_systems, vbox=False)
        self.select_shop_strategy = LabelWithComboBox("选择商店策略", "shop_strategy", shop_strategy, vbox=False)

        self.sinner_YiSang = SinnerSelect("YiSang", "李箱", None, "./assets/app/sinner/YiSang.png")
        self.sinner_Faust = SinnerSelect("Faust", "浮士德", None, "./assets/app/sinner/Faust.png")
        self.sinner_DonQuixote = SinnerSelect("DonQuixote", "堂吉诃德", None, "./assets/app/sinner/DonQuixote.png")
        self.sinner_Ryoshu = SinnerSelect("Ryoshu", "良秀", None, "./assets/app/sinner/Ryoshu.png")
        self.sinner_Meursault = SinnerSelect("Meursault", "默尔索", None, "./assets/app/sinner/Meursault.png")
        self.sinner_HongLu = SinnerSelect("HongLu", "鸿潞", None, "./assets/app/sinner/HongLu.png")

        self.sinner_Heathcliff = SinnerSelect("Heathcliff", "希斯克利夫", None, "./assets/app/sinner/Heathcliff.png")
        self.sinner_Ishmael = SinnerSelect("Ishmael", "以实玛利", None, "./assets/app/sinner/Ishmael.png")
        self.sinner_Rodion = SinnerSelect("Rodion", "罗佳", None, "./assets/app/sinner/Rodion.png")
        self.sinner_Sinclair = SinnerSelect("Sinclair", "辛克莱", None, "./assets/app/sinner/Sinclair.png")
        self.sinner_Outis = SinnerSelect("Outis", "奥提斯", None, "./assets/app/sinner/Outis.png")
        self.sinner_Gregor = SinnerSelect("Gregor", "格里高尔", None, "./assets/app/sinner/Gregor.png")

        self.shop_setting = BaseLabel("舍弃的体系")
        self.shop_setting.add_icon(FIF.DELETE)

        self.burn = BaseCheckBox("system_burn", "./assets/app/status_effects/burn.png", "烧伤", icon_size=30)
        self.bleed = BaseCheckBox("system_bleed", "./assets/app/status_effects/bleed.png", "流血", icon_size=30)
        self.tremor = BaseCheckBox("system_tremor", "./assets/app/status_effects/tremor.png", "震颤", icon_size=30)
        self.rupture = BaseCheckBox("system_rupture", "./assets/app/status_effects/rupture.png", "破裂", icon_size=30)
        self.sinking = BaseCheckBox("system_sinking", "./assets/app/status_effects/sinking.png", "沉沦", icon_size=30)

        self.poise = BaseCheckBox("system_poise", "./assets/app/status_effects/poise.png", "呼吸", icon_size=30)
        self.charge = BaseCheckBox("system_charge", "./assets/app/status_effects/charge.png", "充能", icon_size=30)
        self.slash = BaseCheckBox("system_slash", "./assets/app/status_effects/slash.png", "斩击", icon_size=30)
        self.pierce = BaseCheckBox("system_pierce", "./assets/app/status_effects/pierce.png", "突刺", icon_size=30)
        self.blunt = BaseCheckBox("system_blunt", "./assets/app/status_effects/blunt.png", "打击", icon_size=30)

        self.customize_settings_module = CustomizeSettingsModule()

        self.cancel_button = PushButton("取消", self)
        self.cancel_button.clicked.connect(self.cancel_team_setting)
        self.confirm_button = PrimaryPushButton("保存", self)
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

        self.layout.addWidget(self.combobox_layout)
        self.layout.addLayout(self.select_sinner_layout_1)
        self.layout.addLayout(self.select_sinner_layout_2)
        self.layout.addWidget(self.gift_system_layout)
        self.layout.addWidget(self.custom_layout)
        self.layout.addLayout(self.setting_layout)

        self.custom_layout.viewLayout.addWidget(self.customize_settings_module)

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.team_setting.connect(self.setting_team)
        mediator.sinner_be_selected.connect(self.refresh_sinner_order)

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
                self.team_setting["sinner_order"][sinner_index] = self.team_setting["sinners_be_select"]
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
            starlight_index = int(keys.split("_")[-1]) -1
            if values:
                self.team_setting["opening_bonus_select"] += 1
                self.team_setting["opening_bonus"][starlight_index] = 1
                self.team_setting["opening_bonus_order"][starlight_index] = self.team_setting["opening_bonus_select"]
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
            self.team_setting["second_system_action"][mode_index]= values
        elif "ignore_shop_" in keys:
            shop_index = int(keys.split("_")[-1]) -1
            self.team_setting["ignore_shop"][shop_index] = values

    def save_team_setting(self):
        cfg.set_value(f"team{self.team_num}_setting",self.team_setting)
        self.cancel_team_setting()

    def refresh_starlight_order(self):
        opening_bonus_order = self.team_setting["opening_bonus_order"]
        for i in range(1,11):
            starlight = self.findChild(CheckBoxWithLineEdit, f'starlight_{i}')
            if starlight is not None:
                if opening_bonus_order[i-1] != 0:
                    starlight.set_text(str(opening_bonus_order[i-1]))
                else:
                    starlight.set_text("")

    def refresh_starlight_select(self):
        opening_bonus = self.team_setting["opening_bonus"]
        for i in range(1, 11):
            starlight = self.findChild(CheckBoxWithLineEdit, f'starlight_{i}')
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

        for i in range(1,6):
            if ignore_shop[i-1]:
                self.findChild(BaseCheckBox, f"ignore_shop_{i}").set_checked(True)

        for checkbox in all_checkbox_config_name:
            if self.findChild(BaseCheckBox, checkbox):
                self.findChild(BaseCheckBox, checkbox).set_checked(self.team_setting[checkbox])

        for combobox in all_combobox_config_name:
            if self.findChild(BaseComboBox, combobox):
                if combobox == "team_number":
                    self.findChild(BaseComboBox, combobox).set_options(self.team_setting[combobox]-1)
                else:
                    self.findChild(BaseComboBox, combobox).set_options(self.team_setting[combobox])
                    if combobox == "team_system":
                        self.foolproof(self.team_setting[combobox])

    def foolproof(self,team_system):
        for checkbox in all_checkbox_config_name:
            if check_box := self.findChild(BaseCheckBox, checkbox):
                if checkbox.startswith("system_"):
                    check_box.set_box_enabled(True)
        check_box = self.findChild(BaseCheckBox, f"system_{all_systems_name[team_system]}")
        if check_box:
            check_box.set_checked(False)
            check_box.set_box_enabled(False)


    def cancel_team_setting(self):
        mediator.close_setting.emit()




class CustomizeSettingsModule(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

    def __init_widget(self):
        self.first_line_widget = QWidget(self)
        self.first_line = QHBoxLayout(self.first_line_widget)
        self.second_line_widget = QWidget(self)
        self.second_line = QHBoxLayout(self.second_line_widget)
        self.third_line_widget = QWidget(self)
        self.third_line = QHBoxLayout(self.third_line_widget)

        self.star_layout = BaseSettingLayout(box_type=2, parent=self)
        self.star_layout.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.star_layout.setMaximumHeight(150)
        self.star_layout.setMaximumWidth(950)
        self.star_list = QGridLayout()

        self.fourth_line_widget = QWidget(self)
        self.fourth_line = QHBoxLayout(self.fourth_line_widget)
        self.reward_cards_widget = QWidget(self)
        self.reward_cards_line = QVBoxLayout(self.reward_cards_widget)
        self.fifth_line_widget = QWidget(self)
        self.fifth_line = QHBoxLayout(self.fifth_line_widget)
        self.second_system_widget = QWidget(self)
        self.second_system_layout = QVBoxLayout(self.second_system_widget)
        self.second_system_line1 = QHBoxLayout()
        self.second_system_line2 = QHBoxLayout()
        self.seventh_line_widget = QWidget(self)
        self.seventh_line = QHBoxLayout(self.seventh_line_widget)
        self.eighth_line_widget = QWidget(self)
        self.eighth_line = QHBoxLayout(self.eighth_line_widget)
        self.flood_shop = QHBoxLayout()

    def __init_card(self):
        self.do_not_heal = BaseCheckBox("do_not_heal", None, "不治疗罪人")
        self.do_not_buy = BaseCheckBox("do_not_buy", None, "不购买饰品")
        self.do_not_fuse = BaseCheckBox("do_not_fuse", None, "不合成饰品")
        self.do_not_sell = BaseCheckBox("do_not_sell", None, "不出售饰品")
        self.do_not_enhance = BaseCheckBox("do_not_enhance", None, "不升级饰品")

        self.only_aggressive_fuse = BaseCheckBox("only_aggressive_fuse", None, "只激进合成")
        self.do_not_system_fuse = BaseCheckBox("do_not_system_fuse", None, "不合成体系饰品")
        self.only_system_fuse = BaseCheckBox("only_system_fuse", None, "只合成体系饰品")

        self.avoid_skill_3 = BaseCheckBox("avoid_skill_3", None, "链接战避免使用三技能")
        self.re_formation_each_floor = BaseCheckBox("re_formation_each_floor", None, "每楼层重新编队")
        self.use_starlight = BaseCheckBox("use_starlight", None, "开局星光换钱")

        self.reward_cards = CheckBoxWithComboBox("reward_cards", "奖励卡优先度", None, "reward_cards_select",
                                                 parent=self)
        self.reward_cards.add_items(reward_cards)

        self.choose_opening_bonus = BaseCheckBox("choose_opening_bonus", FIF.BUS, "自选开局加成", center=False)

        self.starlight_1 = CheckBoxWithLineEdit("starlight_1", "星光1")
        self.starlight_2 = CheckBoxWithLineEdit("starlight_2","星光2")
        self.starlight_3 = CheckBoxWithLineEdit("starlight_3","星光3")
        self.starlight_4 = CheckBoxWithLineEdit("starlight_4","星光4")
        self.starlight_5 = CheckBoxWithLineEdit("starlight_5","星光5")

        self.starlight_6 = CheckBoxWithLineEdit("starlight_6","星光6")
        self.starlight_7 = CheckBoxWithLineEdit("starlight_7","星光7")
        self.starlight_8 = CheckBoxWithLineEdit("starlight_8","星光8")
        self.starlight_9 = CheckBoxWithLineEdit("starlight_9","星光9")
        self.starlight_10 = CheckBoxWithLineEdit("starlight_10","星光10")

        self.after_level_IV = CheckBoxWithComboBox("after_level_IV", "合成四级以后", None, "after_level_IV_select",
                                                   parent=self)
        self.after_level_IV.add_items(after_fuse_level_IV)
        self.shopping_strategy = CheckBoxWithComboBox("shopping_strategy", "购物策略", None, "shopping_strategy_select",
                                                      parent=self)
        self.shopping_strategy.add_items(shopping_strategy)

        self.opening_items = CheckBoxWithComboBox("opening_items", "自选开局饰品", None, "opening_items_system",
                                                  parent=self)
        self.opening_items.add_items(all_systems)
        self.opening_items.add_combobox("opening_items_select")
        self.opening_items.add_times_for_additional(start_gift)

        self.second_system = CheckBoxWithComboBox("second_system", "第二体系", None, "second_system_select",
                                                  parent=self)
        self.second_system.add_items(all_systems)
        self.second_system.add_combobox("second_system_setting")
        self.second_system.add_times_for_additional(second_systems)
        self.second_system_fuse_IV = BaseCheckBox("second_system_fuse_IV", None, "合成四级")
        self.second_system_buy = BaseCheckBox("second_system_buy", None, "购买")
        self.second_system_select = BaseCheckBox("second_system_choose", None, "选取胜利奖励")
        self.second_system_power_up = BaseCheckBox("second_system_power_up", None, "升级四级")

        self.skill_replacement = CheckBoxWithComboBox("skill_replacement", "技能替换", None, "skill_replacement_select",
                                                      parent=self)
        self.skill_replacement.add_items(skill_replacement_sinner)
        self.skill_replacement.add_combobox("skill_replacement_mode")
        self.skill_replacement.add_times_for_additional(skill_replacement_mode)

        self.ignore_shop = BaseLabel("忽略商店")
        self.ignore_shop.add_icon(FIF.CUT)
        self.flood_shop_1 = BaseCheckBox("ignore_shop_1", None, "第一层")
        self.flood_shop_2 = BaseCheckBox("ignore_shop_2", None, "第二层")
        self.flood_shop_3 = BaseCheckBox("ignore_shop_3", None, "第三层")
        self.flood_shop_4 = BaseCheckBox("ignore_shop_4", None, "第四层")
        self.flood_shop_5 = BaseCheckBox("ignore_shop_5", None, "第五层")

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

        self.reward_cards_line.addWidget(self.reward_cards)

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
        self.flood_shop.addWidget(self.flood_shop_1)
        self.flood_shop.addWidget(self.flood_shop_2)
        self.flood_shop.addWidget(self.flood_shop_3)
        self.flood_shop.addWidget(self.flood_shop_4)
        self.flood_shop.addWidget(self.flood_shop_5)
        self.eighth_line.addLayout(self.flood_shop, Qt.AlignLeft)

        self.main_layout.addWidget(self.first_line_widget)
        self.main_layout.addWidget(self.second_line_widget)
        self.main_layout.addWidget(self.third_line_widget)
        self.main_layout.addWidget(self.star_layout)
        self.main_layout.addWidget(self.reward_cards_widget, Qt.AlignLeft)
        self.main_layout.addWidget(self.fourth_line_widget)
        self.main_layout.addWidget(self.fifth_line_widget)
        self.main_layout.addWidget(self.second_system_widget)
        self.main_layout.addWidget(self.seventh_line_widget)
        self.main_layout.addWidget(self.eighth_line_widget)
