import sys
import threading

from PyQt5.QtCore import Qt, QTimer, QFile, QTextStream, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog
from qfluentwidgets import setThemeColor
from pynput import keyboard
from command.use_yaml import get_yaml_information, save_yaml
from main_windows import Ui_MainWindow
from my_log.my_log import my_log
from script.script_task_scheme import my_script_task
from setting_ui import Ui_all_team_basic_setting

set_select_team_options = {"Team1": 1, "Team2": 2, "Team3": 3, "Team4": 4, "Team5": 5,
                           "Team6": 6, "Team7": 7, "Team8": 8, "Team9": 9, "Team10": 10,
                           "Team11": 11, "Team12": 12, "Team13": 13, "Team14": 14, "Team15": 15,
                           "Team16": 16, "Team17": 17, "Team18": 18, "Team19": 19, "Team20": 20,
                           }
all_systems = {"烧伤(burn)": 0, "流血(bleed)": 1, "震颤(tremor)": 2, "破裂(rupture)": 3, "呼吸(poise)": 4,
               "沉沦(sinking)": 5, "充能(charge)": 6, "斩击(slash)": 7, "突刺(clash)": 8, "打击(blunt)": 9}


class MainWindow(QMainWindow, Ui_MainWindow):
    clear_signal = pyqtSignal()  # 用于右边日志栏清理

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.my_script = None
        self.setupUi(self)

        self.init_ui()
        # 启动快捷键监听
        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+q': self.my_stop_shortcut
        })
        self.listener.start()

    def init_ui(self):
        # 设置界面主题为红色
        setThemeColor("#9c080b")

        self.setWindowIcon(QIcon('./pic/icon/my_icon_256X256.ico'))

        # 设置各个按钮的交互
        self.set_windows_button.clicked.connect(self.change_page)
        self.daily_task_button.clicked.connect(self.change_page)
        self.mirror_button.clicked.connect(self.change_page)
        self.buy_enkephalin_button.clicked.connect(self.change_page)
        self.get_reward_button.clicked.connect(self.change_page)
        self.start_with_key_page.clicked.connect(self.change_page)
        self.instructions_page.clicked.connect(self.change_page)
        self.about_page.clicked.connect(self.change_page)
        self.select_all.clicked.connect(self.change_select)
        self.select_none.clicked.connect(self.change_select)

        self.team1_setting.clicked.connect(self.setting_teams)
        self.team2_setting.clicked.connect(self.setting_teams)
        self.team3_setting.clicked.connect(self.setting_teams)
        self.team4_setting.clicked.connect(self.setting_teams)
        self.team5_setting.clicked.connect(self.setting_teams)
        self.team6_setting.clicked.connect(self.setting_teams)
        self.team7_setting.clicked.connect(self.setting_teams)

        # 设置各个选项卡中的下拉框内容
        set_reduce_miscontact_options = {'是': 0, '否': 1}
        self.set_reduce_miscontact.addItems(set_reduce_miscontact_options)

        self.all_teams.addItems(set_select_team_options)

        set_lunacy_to_enkephalin_options = {"不换": 0, "换第一次": 1, "换第二次": 2}
        self.set_lunacy_to_enkephalin.addItems(set_lunacy_to_enkephalin_options)

        set_get_prize_options = {"邮件+日/周常": 0, "日/周常": 1, "邮件": 2}
        self.set_get_prize.addItems(set_get_prize_options)

        set_win_size_options = {"1920*1080": 0, "2560*1440": 1, "1280*720": 2, "1600*900": 3, "3200*1800": 4,
                                "3840*2160": 5}
        self.set_win_size.addItems(set_win_size_options)

        # 设置各个下拉框选择时，改变config.yaml中的参数
        self.set_reduce_miscontact.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(set_reduce_miscontact_options))
        self.set_lunacy_to_enkephalin.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(set_lunacy_to_enkephalin_options))
        self.set_get_prize.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_get_prize_options))
        self.set_win_size.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_win_size_options))
        self.all_teams.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_select_team_options))

        # 设置当复选框选中时，修改配队顺序
        self.team1.stateChanged.connect(
            lambda checked, combo=self.team1_order: self.checkbox_state_changed(checked, combo))
        self.team2.stateChanged.connect(
            lambda checked, combo=self.team2_order: self.checkbox_state_changed(checked, combo))
        self.team3.stateChanged.connect(
            lambda checked, combo=self.team3_order: self.checkbox_state_changed(checked, combo))
        self.team4.stateChanged.connect(
            lambda checked, combo=self.team4_order: self.checkbox_state_changed(checked, combo))
        self.team5.stateChanged.connect(
            lambda checked, combo=self.team5_order: self.checkbox_state_changed(checked, combo))
        self.team6.stateChanged.connect(
            lambda checked, combo=self.team6_order: self.checkbox_state_changed(checked, combo))
        self.team7.stateChanged.connect(
            lambda checked, combo=self.team7_order: self.checkbox_state_changed(checked, combo))

        # 设置保存主页几个任务复选框的启用状态
        self.set_windows.stateChanged.connect(lambda checked: self.menu_checkbox_state_changed())
        self.daily_task.stateChanged.connect(lambda checked: self.menu_checkbox_state_changed())
        self.mirror.stateChanged.connect(lambda checked: self.menu_checkbox_state_changed())
        self.buy_enkephalin.stateChanged.connect(lambda checked: self.menu_checkbox_state_changed())
        self.get_reward.stateChanged.connect(lambda checked: self.menu_checkbox_state_changed())

        # 设置各个数值选择器变化时，改变config.yaml中的参数
        self.set_EXP_count.valueChanged.connect(lambda value: self.spinbox_changed(value))
        self.set_thread_count.valueChanged.connect(lambda value: self.spinbox_changed(value))
        self.set_mirror_count.valueChanged.connect(lambda value: self.spinbox_changed(value))

        # 设置开始按钮按下后的变化
        self.start_tasks.clicked.connect(self.start_and_stop_tasks)

        # 显示主界面，并且允许程序在长时间运行的任务中处理事件队列中的事件
        self.show()
        QApplication.processEvents()

        self.instructions_text.setText('''此项目仅支持使用英语(EN)作为游戏语言进行使用 \n
        坐牢设置中，可能出现编队号码的初始值不为1的情况，此时需要将队伍全部关闭后重新选择\n
        暂时只能使用1920 * 1080的窗口设置，未测试屏幕小于等于1920 * 1080的情况\n
        可能存在各种奇奇怪怪的BUG\n
        随机、斩击、突刺、打击队伍不怎么用，很不完善\n
        镜牢初始自动选择第1、2项EGO饰品\n
        使用CTRL+Q按键暂停脚本进程\n
        其他的所见即所得，懒得写了''')

        self.about_text.setText('''使用CTRL+Q按键暂停脚本进程，其他的直接看github项目主页的README吧，懒得写了''')

    def setting_teams(self):
        button = self.sender()
        button_name = button.objectName()
        self.setting_page = setting_window(which_team=button_name)

    def my_stop_shortcut(self):
        current_text = self.start_tasks.text()
        if current_text != "Link Start!":
            self.start_tasks.click()

    def spinbox_changed(self, value):
        # 微调框改变时，将值传给yaml文件
        config_datas = get_yaml_information()
        sender_spinbox = self.sender()
        name = sender_spinbox.objectName()
        config_datas[name] = value
        save_yaml(config_datas)

    def menu_checkbox_state_changed(self):
        # 将主页几个任务复选框的启用状态保存到yaml文件
        config_datas = get_yaml_information()
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        if sender_checkbox.isChecked() != config_datas[name]:
            if not config_datas[name]:
                config_datas[name] = True
            else:
                config_datas[name] = False
        save_yaml(config_datas)

    def checkbox_state_changed(self, checked, combo):
        # 各个配队的复选框被选中时，修改旁边的启动顺序
        config_datas = get_yaml_information()
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        this_team = name + "_order"
        if sender_checkbox.isChecked():
            config_datas["teams_be_select"] += 1
            config_datas[this_team] = str(config_datas["teams_be_select"])
            combo.setText(str(config_datas["teams_be_select"]))
        else:
            config_datas = self.reset_team_order(config_datas, this_team)
            config_datas["teams_be_select"] -= 1
            config_datas[this_team] = ""
            combo.setText("")
        if sender_checkbox.isChecked() != config_datas[name]:
            if not config_datas[name]:
                config_datas[name] = True
            else:
                config_datas[name] = False
        save_yaml(config_datas)

    # 修改配队顺序的函数
    def reset_team_order(self, config_datas, which):
        all_teams = [self.team1_order, self.team2_order, self.team3_order, self.team4_order, self.team5_order,
                     self.team6_order, self.team7_order]
        all_teams_name = ["team1_order", "team2_order", "team3_order", "team4_order",
                          "team5_order", "team6_order", "team7_order"]
        for i in range(6):
            if config_datas[all_teams_name[i]] != '':
                if int(config_datas[all_teams_name[i]]) > int(config_datas[which]):
                    config_datas[all_teams_name[i]] = str((int(config_datas[all_teams_name[i]])) - 1)
            all_teams[i].setText(config_datas[all_teams_name[i]])
        return config_datas

    def on_combobox_changed(self, data_dict):
        # 各个下拉框改变时，改变config.yaml中的参数
        config_datas = get_yaml_information()
        sender_combo_box = self.sender()
        selected_key = sender_combo_box.currentText()
        selected_value = data_dict[selected_key]
        name = sender_combo_box.objectName()
        config_datas[name] = selected_value
        save_yaml(config_datas)

    def change_page(self):
        # 获取发送信号的按钮对象，改变设置的页面
        button = self.sender()

        config_datas = get_yaml_information()

        if button == self.set_windows_button:
            self.detail_setting.setCurrentIndex(0)
            config_datas["default_page"] = 0
        elif button == self.daily_task_button:
            self.detail_setting.setCurrentIndex(1)
            config_datas["default_page"] = 1
        elif button == self.mirror_button:
            self.detail_setting.setCurrentIndex(2)
            config_datas["default_page"] = 2
        elif button == self.buy_enkephalin_button:
            self.detail_setting.setCurrentIndex(3)
            config_datas["default_page"] = 3
        elif button == self.get_reward_button:
            self.detail_setting.setCurrentIndex(4)
            config_datas["default_page"] = 4
        elif button == self.start_with_key_page:
            self.all_pages.setCurrentIndex(0)
        elif button == self.instructions_page:
            self.all_pages.setCurrentIndex(1)
        elif button == self.about_page:
            self.all_pages.setCurrentIndex(2)

        save_yaml(config_datas)

    def change_select(self):
        # 设置“全选”与“清空”按钮的选中与取消选中功能
        button = self.sender()
        if button == self.select_all:
            self.set_windows.setChecked(True)
            self.daily_task.setChecked(True)
            self.mirror.setChecked(True)
            self.buy_enkephalin.setChecked(True)
            self.get_reward.setChecked(True)
        if button == self.select_none:
            self.set_windows.setChecked(False)
            self.daily_task.setChecked(False)
            self.mirror.setChecked(False)
            self.buy_enkephalin.setChecked(False)
            self.get_reward.setChecked(False)

    def setting_unavailable(self):
        # 使所有设置项不可用
        self.daily_task.setEnabled(False)
        self.mirror.setEnabled(False)
        self.buy_enkephalin.setEnabled(False)
        self.get_reward.setEnabled(False)
        self.set_win_size.setEnabled(False)
        self.set_win_position.setEnabled(False)
        self.set_reduce_miscontact.setEnabled(False)
        self.set_EXP_count.setEnabled(False)
        self.set_thread_count.setEnabled(False)
        self.all_teams.setEnabled(False)
        self.team1.setEnabled(False)
        self.team2.setEnabled(False)
        self.team3.setEnabled(False)
        self.team4.setEnabled(False)
        self.team5.setEnabled(False)
        self.team6.setEnabled(False)
        self.team7.setEnabled(False)
        self.set_mirror_counts.setEnabled(False)
        self.set_lunacy_to_enkephalin.setEnabled(False)
        self.set_get_prize.setEnabled(False)
        self.select_all.setEnabled(False)
        self.select_none.setEnabled(False)

    def setting_available(self):
        # 使所有设置项可用
        self.daily_task.setEnabled(True)
        self.mirror.setEnabled(True)
        self.buy_enkephalin.setEnabled(True)
        self.get_reward.setEnabled(True)
        self.set_win_size.setEnabled(True)
        self.set_win_position.setEnabled(True)
        self.set_reduce_miscontact.setEnabled(True)
        self.set_EXP_count.setEnabled(True)
        self.set_thread_count.setEnabled(True)
        self.all_teams.setEnabled(True)
        self.team1.setEnabled(True)
        self.team2.setEnabled(True)
        self.team3.setEnabled(True)
        self.team4.setEnabled(True)
        self.team5.setEnabled(True)
        self.team6.setEnabled(True)
        self.team7.setEnabled(True)
        self.set_mirror_counts.setEnabled(True)
        self.set_lunacy_to_enkephalin.setEnabled(True)
        self.set_get_prize.setEnabled(True)
        self.select_all.setEnabled(True)
        self.select_none.setEnabled(True)

    def refresh_team_order(self):
        config_datas = get_yaml_information()
        self.team1_order.setText(config_datas["team1_order"])
        self.team2_order.setText(config_datas["team2_order"])
        self.team3_order.setText(config_datas["team3_order"])
        self.team4_order.setText(config_datas["team4_order"])
        self.team5_order.setText(config_datas["team5_order"])
        self.team6_order.setText(config_datas["team6_order"])
        self.team7_order.setText(config_datas["team7_order"])

    def start_and_stop_tasks(self):
        # 设置按下启动与停止按钮时，其他模块的启用与停用
        current_text = self.start_tasks.text()
        if current_text == "Link Start!":
            self.start_tasks.setText("S t o p !")
            self.setting_unavailable()
            self.create_and_start_script()
        else:
            self.start_tasks.setText("Link Start!")
            self.setting_available()
            self.refresh_team_order()
            if self.my_script and self.my_script.isRunning():
                self.stop_script()

    def create_and_start_script(self):
        msg = f"开始进行所有任务"
        my_log("info", msg)
        self.set_log(option=1)
        # 启动脚本线程
        self.my_script = my_script_task()
        # 设置脚本线程为守护(当程序被关闭，一起停止)
        self.my_script.daemon = True
        self.my_script.finished_signal.connect(self.start_and_stop_tasks)
        self.my_script.start()

    def stop_script(self):
        if self.my_script and self.my_script.isRunning():
            self.my_script.terminate()  # 终止线程

    def load_log_text(self):

        self.scoll_log_edit.clear()
        # 打开 log 文件，使用 UTF-8 编码
        file = QFile('./logs/myLog.log')
        if not file.open(QFile.ReadOnly | QFile.Text):
            return

        # 使用 QTextStream 读取文件内容，并指定 UTF-8 编码
        stream = QTextStream(file)
        stream.setCodec('UTF-8')  # 设置编码为 UTF-8
        while not stream.atEnd():
            line = stream.readLine()
            self.scoll_log_edit.append(line)

        # 关闭文件
        file.close()

    def clear_all_log(self):
        file = QFile('./logs/myLog.log')
        if not file.open(QFile.WriteOnly | QFile.Text):
            self.text_edit.append('无法打开文件')
            return

        # 清空文件内容
        file.write('')

        # 关闭文件
        file.close()
        # 重新加载文件内容到 QTextEdit
        self.load_log()

    def set_log(self, option=0):
        if option == 0:
            try:
                self.load_log_text()
            except:
                pass

        else:
            try:
                self.clear_all_log()
            except:
                pass


# 镜牢队伍设置窗口界面
class setting_window(QDialog, Ui_all_team_basic_setting):
    def __init__(self, which_team, parent=None):
        super(setting_window, self).__init__(parent)
        self.my_script = None
        self.setupUi(self)

        self.init_ui(which_team)

    def init_ui(self, which_team):
        # 设置界面主题为红色
        setThemeColor("#9c080b")
        # 去除标题栏，并使窗口无法改变大小
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 为下拉框提供选项
        self.all_teams.addItems(set_select_team_options)
        self.all_system.addItems(all_systems)

        # 读取已有设置项
        self.read_my_setting(which_team)

        # 设置当复选框选中时，修改配队顺序
        self.YiSang.stateChanged.connect(
            lambda checked, combo=self.YiSang_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Faust.stateChanged.connect(
            lambda checked, combo=self.Faust_order: self.checkbox_state_changed(checked, combo, which_team))
        self.DonQuixote.stateChanged.connect(
            lambda checked, combo=self.DonQuixote_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Ryoshu.stateChanged.connect(
            lambda checked, combo=self.Ryoshu_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Meursault.stateChanged.connect(
            lambda checked, combo=self.Meursault_order: self.checkbox_state_changed(checked, combo, which_team))
        self.HongLu.stateChanged.connect(
            lambda checked, combo=self.HongLu_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Heathcliff.stateChanged.connect(
            lambda checked, combo=self.Heathcliff_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Ishmael.stateChanged.connect(
            lambda checked, combo=self.Ishmael_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Rodion.stateChanged.connect(
            lambda checked, combo=self.Rodion_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Sinclair.stateChanged.connect(
            lambda checked, combo=self.Sinclair_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Outis.stateChanged.connect(
            lambda checked, combo=self.Outis_order: self.checkbox_state_changed(checked, combo, which_team))
        self.Gregor.stateChanged.connect(
            lambda checked, combo=self.Gregor_order: self.checkbox_state_changed(checked, combo, which_team))

        # 设置各个下拉框选择时，改变config.yaml中的参数
        self.all_system.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(all_systems, which_team))
        self.all_teams.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(set_select_team_options, which_team))

        # 设置当复选框选中时，修改配队顺序
        self.burn.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.bleed.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.tremor.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.rupture.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.poise.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.sinking.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.charge.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.slash.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.clash.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.blunt.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))

        # 设置完成按钮
        self.confirm_button.clicked.connect(self.close)

        self.exec_()

    def shop_checkbox_state_changed(self, checked, which_team):
        # 各个配队的复选框被选中时，修改旁边的启动顺序
        config_datas = get_yaml_information()
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        if sender_checkbox.isChecked() != config_datas[which_team][name]:
            if not config_datas[which_team][name]:
                config_datas[which_team][name] = True
            else:
                config_datas[which_team][name] = False
        save_yaml(config_datas)

    def on_combobox_changed(self, data_dict, which_team):
        # 各个下拉框改变时，改变config.yaml中的参数
        config_datas = get_yaml_information()
        sender_combo_box = self.sender()
        selected_key = sender_combo_box.currentText()
        selected_value = data_dict[selected_key]
        name = sender_combo_box.objectName()
        config_datas[which_team][name] = selected_value
        save_yaml(config_datas)

    def checkbox_state_changed(self, checked, combo, which_team):
        # 各个配队的复选框被选中时，修改旁边的启动顺序
        config_datas = get_yaml_information()
        check_teams_select_num(config_datas)

        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        this_sinner = name + "_order"
        if sender_checkbox.isChecked():
            config_datas[which_team]["sinners_be_select"] += 1
            config_datas[which_team][this_sinner] = str(config_datas[which_team]["sinners_be_select"])
            combo.setText(str(config_datas[which_team]["sinners_be_select"]))
        else:
            config_datas = self.reset_sinner_order(config_datas, this_sinner, which_team)
            config_datas[which_team]["sinners_be_select"] -= 1
            config_datas[which_team][this_sinner] = ""
            combo.setText("")
        if sender_checkbox.isChecked() != config_datas[which_team][name]:
            if not config_datas[which_team][name]:
                config_datas[which_team][name] = True
            else:
                config_datas[which_team][name] = False
        save_yaml(config_datas)

    # 修改配队顺序的函数
    def reset_sinner_order(self, config_datas, sinner, which_team):
        all_sinners = [self.YiSang_order, self.Faust_order, self.DonQuixote_order, self.Ryoshu_order,
                       self.Meursault_order, self.HongLu_order, self.Heathcliff_order, self.Ishmael_order,
                       self.Rodion_order, self.Sinclair_order, self.Outis_order, self.Gregor_order]
        all_sinners_name = ["YiSang_order", "Faust_order", "DonQuixote_order", "Ryoshu_order", "Meursault_order",
                            "HongLu_order", "Heathcliff_order", "Ishmael_order",
                            "Rodion_order", "Sinclair_order", "Outis_order", "Gregor_order"]
        for i in range(12):
            if config_datas[which_team][all_sinners_name[i]] != '':
                if int(config_datas[which_team][all_sinners_name[i]]) > int(config_datas[which_team][sinner]):
                    config_datas[which_team][all_sinners_name[i]] = str(
                        (int(config_datas[which_team][all_sinners_name[i]])) - 1)
            all_sinners[i].setText(config_datas[which_team][all_sinners_name[i]])
        return config_datas

    # 读取配置文件中的设置
    def read_my_setting(self, which_team):
        # 读取设置
        config_datas = get_yaml_information()
        # 读取之前最后下拉框设置
        self.all_teams.setCurrentIndex(config_datas[which_team]["all_teams"] - 1)
        self.all_system.setCurrentIndex(config_datas[which_team]["all_system"])

        # 读取之前罪人复选框设置
        self.YiSang.setChecked(config_datas[which_team]["YiSang"])
        self.Faust.setChecked(config_datas[which_team]["Faust"])
        self.DonQuixote.setChecked(config_datas[which_team]["DonQuixote"])
        self.Ryoshu.setChecked(config_datas[which_team]["Ryoshu"])
        self.Meursault.setChecked(config_datas[which_team]["Meursault"])
        self.HongLu.setChecked(config_datas[which_team]["HongLu"])
        self.Heathcliff.setChecked(config_datas[which_team]["Heathcliff"])
        self.Ishmael.setChecked(config_datas[which_team]["Ishmael"])
        self.Rodion.setChecked(config_datas[which_team]["Rodion"])
        self.Sinclair.setChecked(config_datas[which_team]["Sinclair"])
        self.Outis.setChecked(config_datas[which_team]["Outis"])
        self.Gregor.setChecked(config_datas[which_team]["Gregor"])

        # 读取之前排序文本框的数据
        self.YiSang_order.setText(config_datas[which_team]["YiSang_order"])
        self.Faust_order.setText(config_datas[which_team]["Faust_order"])
        self.DonQuixote_order.setText(config_datas[which_team]["DonQuixote_order"])
        self.Ryoshu_order.setText(config_datas[which_team]["Ryoshu_order"])
        self.Meursault_order.setText(config_datas[which_team]["Meursault_order"])
        self.HongLu_order.setText(config_datas[which_team]["HongLu_order"])
        self.Heathcliff_order.setText(config_datas[which_team]["Heathcliff_order"])
        self.Ishmael_order.setText(config_datas[which_team]["Ishmael_order"])
        self.Rodion_order.setText(config_datas[which_team]["Rodion_order"])
        self.Sinclair_order.setText(config_datas[which_team]["Sinclair_order"])
        self.Outis_order.setText(config_datas[which_team]["Outis_order"])
        self.Gregor_order.setText(config_datas[which_team]["Gregor_order"])

        # 读取之前商店复选框设置
        self.burn.setChecked(config_datas[which_team]["burn"])
        self.bleed.setChecked(config_datas[which_team]["bleed"])
        self.tremor.setChecked(config_datas[which_team]["tremor"])
        self.rupture.setChecked(config_datas[which_team]["rupture"])
        self.poise.setChecked(config_datas[which_team]["poise"])
        self.sinking.setChecked(config_datas[which_team]["sinking"])
        self.charge.setChecked(config_datas[which_team]["charge"])
        self.slash.setChecked(config_datas[which_team]["slash"])
        self.clash.setChecked(config_datas[which_team]["clash"])
        self.blunt.setChecked(config_datas[which_team]["blunt"])


def read_last_setting(mygui):
    # 读取设置
    config_datas = get_yaml_information()

    # 读取之前最后页面
    mygui.detail_setting.setCurrentIndex(config_datas["default_page"])

    # 读取之前最后下拉框设置
    mygui.all_teams.setCurrentIndex(config_datas["all_teams"] - 1)

    mygui.set_reduce_miscontact.setCurrentIndex(config_datas["set_reduce_miscontact"])

    mygui.set_lunacy_to_enkephalin.setCurrentIndex(config_datas["set_lunacy_to_enkephalin"])

    mygui.set_get_prize.setCurrentIndex(config_datas["set_get_prize"])

    mygui.set_win_size.setCurrentIndex(config_datas["set_win_size"])

    # 读取之前最后复选框设置
    mygui.team1.setChecked(config_datas["team1"])
    mygui.team2.setChecked(config_datas["team2"])
    mygui.team3.setChecked(config_datas["team3"])
    mygui.team4.setChecked(config_datas["team4"])
    mygui.team5.setChecked(config_datas["team5"])
    mygui.team6.setChecked(config_datas["team6"])
    mygui.team7.setChecked(config_datas["team7"])

    mygui.set_windows.setChecked(config_datas["set_windows"])
    mygui.daily_task.setChecked(config_datas["daily_task"])
    mygui.mirror.setChecked(config_datas["mirror"])
    mygui.buy_enkephalin.setChecked(config_datas["buy_enkephalin"])
    mygui.get_reward.setChecked(config_datas["get_reward"])

    # 读取之前最后数字调节框设置
    mygui.set_mirror_count.setValue(config_datas["set_mirror_count"])
    mygui.set_EXP_count.setValue(config_datas["set_EXP_count"])
    mygui.set_thread_count.setValue(config_datas["set_thread_count"])

    # 读取之前排序文本框的数据
    mygui.team1_order.setText(config_datas["team1_order"])
    mygui.team2_order.setText(config_datas["team2_order"])
    mygui.team3_order.setText(config_datas["team3_order"])
    mygui.team4_order.setText(config_datas["team4_order"])
    mygui.team5_order.setText(config_datas["team5_order"])
    mygui.team6_order.setText(config_datas["team6_order"])
    mygui.team7_order.setText(config_datas["team7_order"])

    print(config_datas["team4_order"])
    # 重计算选中几支队伍，防未知错误
    check_teams_select_num(config_datas)


# 重计算选中几支队伍，防未知错误
def check_teams_select_num(config_datas):
    seven_teams = ["team1", "team2", "team3", "team4", "team5", "team6", "team7"]
    team_be_select = 0
    for team in seven_teams:
        if config_datas[team]:
            team_be_select += 1
    if config_datas["teams_be_select"] != team_be_select:
        config_datas["teams_be_select"] = team_be_select
    save_yaml(config_datas)


def mygui():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    ui = MainWindow()
    read_last_setting(ui)
    timer = QTimer()
    timer.timeout.connect(lambda option=0: ui.set_log(option))
    timer.start(1000)  # 每秒更新一次
    sys.exit(app.exec_())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    ui = MainWindow()
    read_last_setting(ui)
    sys.exit(app.exec_())
