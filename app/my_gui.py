import sys

from PyQt5.QtCore import Qt, QTimer, QFile, QTextStream, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog
from pynput import keyboard
from qfluentwidgets import setThemeColor

from app.main_windows import Ui_MainWindow
from app.setting_ui import Ui_all_team_basic_setting
from module.automation import auto
from module.config import cfg
from module.logger import log
from module.screen import screen
from module.update.check_update import check_update
from tasks.base.script_task_scheme import my_script_task

set_select_team_options = {f"Team{i}": i for i in range(1, 21)}
all_systems = {"烧伤(burn)": 0, "流血(bleed)": 1, "震颤(tremor)": 2, "破裂(rupture)": 3, "呼吸(poise)": 4,
               "沉沦(sinking)": 5, "充能(charge)": 6, "斩击(slash)": 7, "突刺(pierce)": 8, "打击(blunt)": 9}


class MainWindow(QMainWindow, Ui_MainWindow):
    clear_signal = pyqtSignal()  # 用于右边日志栏清理

    def __init__(self):
        super().__init__()
        self.my_script = None
        self.last_position = 0
        self.setupUi(self)

        self.init_ui()
        # 启动快捷键监听
        self.listener = keyboard.GlobalHotKeys(
            {
                "<ctrl>+q": self.my_stop_shortcut,
                "<alt>+p": self.my_pause_and_resume,
                "<alt>+r": self.my_pause_and_resume,
            }
        )
        self.listener.start()

        self.read_last_setting()
        self.timer = QTimer()
        self.timer.timeout.connect(lambda option=0: self.set_log(option))
        self.timer.start(1000)  # 每秒更新一次

        try:
            check_update(self, flag=True)
            pass
        except Exception as e:
            log.ERROR(f"检查更新失败，原因：{e}")

    def init_ui(self):
        # 设置界面主题为红色
        setThemeColor("#9c080b")

        # 设置窗口标志以禁用最大化按钮
        #self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

        self.setWindowIcon(QIcon('./assets/logo/my_icon_256X256.ico'))
        self.setWindowTitle(f"Ahab Assistant Limbus Company -  {cfg.version}")

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
        set_reduce_miscontact_options = {'是': True}
        self.set_reduce_miscontact.addItems(set_reduce_miscontact_options)

        self.daily_teams.addItems(set_select_team_options)

        set_language_options = {'English': 'en','简体中文': 'zh_cn'}
        self.language.addItems(set_language_options)

        set_lunacy_to_enkephalin_options = {"不换": 0, "换第一次": 1, "换第二次": 2}
        self.set_lunacy_to_enkephalin.addItems(set_lunacy_to_enkephalin_options)

        set_get_prize_options = {"邮件+日/周常": 0, "日/周常": 1, "邮件": 2}
        self.set_get_prize.addItems(set_get_prize_options)

        set_win_size_options = {"1920*1080": 1080, "2560*1440": 1440, "1280*720": 720, "1600*900": 900,
                                "3200*1800": 1800,
                                "3840*2160": 2160}
        self.set_win_size.addItems(set_win_size_options)

        # 设置各个下拉框选择时，改变config.yaml中的参数
        self.set_reduce_miscontact.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(set_reduce_miscontact_options))
        self.set_lunacy_to_enkephalin.currentIndexChanged.connect(
            lambda: self.on_combobox_changed(set_lunacy_to_enkephalin_options))
        self.set_get_prize.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_get_prize_options))
        self.set_win_size.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_win_size_options))
        self.daily_teams.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_select_team_options))
        self.language.currentIndexChanged.connect(lambda: self.on_combobox_changed(set_language_options))

        # 设置当复选框选中时，修改配队顺序
        self.team1.stateChanged.connect(
            lambda checked, combo=self.team1_order: self.team_checkbox_state_changed(checked, combo))
        self.team2.stateChanged.connect(
            lambda checked, combo=self.team2_order: self.team_checkbox_state_changed(checked, combo))
        self.team3.stateChanged.connect(
            lambda checked, combo=self.team3_order: self.team_checkbox_state_changed(checked, combo))
        self.team4.stateChanged.connect(
            lambda checked, combo=self.team4_order: self.team_checkbox_state_changed(checked, combo))
        self.team5.stateChanged.connect(
            lambda checked, combo=self.team5_order: self.team_checkbox_state_changed(checked, combo))
        self.team6.stateChanged.connect(
            lambda checked, combo=self.team6_order: self.team_checkbox_state_changed(checked, combo))
        self.team7.stateChanged.connect(
            lambda checked, combo=self.team7_order: self.team_checkbox_state_changed(checked, combo))

        self.hard_mirror.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        self.no_weekly_bonuses.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        cfg.set_value("hard_mirror", False)
        cfg.set_value("no_weekly_bonuses", False)

        # 设置保存主页几个任务复选框的启用状态
        self.set_windows.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        self.daily_task.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        self.mirror.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        self.buy_enkephalin.stateChanged.connect(lambda checked: self.checkbox_state_changed())
        self.get_reward.stateChanged.connect(lambda checked: self.checkbox_state_changed())

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
        使用CTRL+Q按键结束脚本操作\n
        使用ALT+P按键暂停脚本操作，ALT+R恢复脚本操作\n
        其他的所见即所得，懒得写了''')

        self.about_text.setText(f'''本项目为非科班出身、非计算机从业人员心血来潮的作品。\n
        是一个掺杂了第三方项目、初学者乱七八糟风格代码、可能存在各种BUG的手游LimbusCompany的PC端小助手。\n
        此项目基于图像识别与文字识别，一键护肝。\n
        本软件开源、免费，仅供学习交流使用。\n
        若您遇到商家使用本软件进行代练并收费，可能是设备与时间等费用，产生的问题及后果与本软件无关。\n
        获取管理员权限是为了确保运行顺利。\n
        该项目除自动更新功能外纯离线。\n
        软件图标素材来源网图，不属于GPL协议开源的内容，如有侵权，请及时联系作者删除。\n
        用户在使用过程中需自行遵守相关平台的使用规则与服务条款。因使用本软件可能导致的游戏账号封禁、违规行为等一切后果，作者概不负责。用户需对自身行为负责，并承担使用本软件可能带来的所有风险。\n                                                                                                                        
        \n
        向感谢以下项目提供的帮助：\n
        LixAssistantLimbusCompany：https://github.com/HSLix/LixAssistantLimbusCompany\n
        OCR文字识别：https://github.com/hiroi-sora/PaddleOCR-json\n
        图形界面组件库：https://github.com/zhiyiYo/PyQt-Fluent-Widgets\n
        三月七小助手：https://github.com/moesnow/March7thAssistant\n
        \n
        同时向直接或间接参与到本软件开发的所有人员，包括在网络上分享各种教程的大佬们，还有开源自己代码的巨佬们致谢！\n
        \n
        项目地址:https://github.com/KIYI671/AhabAssistantLimbusCompany\n
        \n
        本项目使用 AGPL-3.0 开源协议。\n
        \n
        当前版本号:  {cfg.version}\n            
        ''')
        # 向日志打印当前版本号
        msg = f"当前版本号:  {cfg.version}"
        log.DEBUG(msg)

    def my_pause_and_resume(self):
        auto.set_pause()

    def setting_teams(self):
        button = self.sender()
        button_name = button.objectName()
        self.setting_page = setting_window(which_team=button_name)

    def my_stop_shortcut(self):
        screen.reset_win()
        current_text = self.start_tasks.text()
        if current_text != "Link Start!":
            self.start_tasks.click()

    def spinbox_changed(self, value):
        # 微调框改变时，将值传给yaml文件
        sender_spinbox = self.sender()
        name = sender_spinbox.objectName()
        cfg.set_value(name, value)

    def checkbox_state_changed(self):
        # 将主页几个任务复选框的启用状态保存到yaml文件
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        status = cfg.get_value(name)
        cfg.set_value(name, not status)

    def team_checkbox_state_changed(self, checked, combo):
        # 各个配队的复选框被选中时，修改旁边的启动顺序
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        this_team = name + "_order"
        if sender_checkbox.isChecked():
            cfg.set_value("teams_be_select", cfg.get_value("teams_be_select") + 1)
            cfg.set_value(this_team, cfg.get_value("teams_be_select"))
            cfg.set_value(name, True)
            combo.setText(str(cfg.get_value("teams_be_select")))
        else:
            self.reset_team_order(this_team)
            cfg.set_value(name, False)
            cfg.set_value("teams_be_select", cfg.get_value("teams_be_select") - 1)

    # 修改配队顺序的函数
    def reset_team_order(self, which):
        all_teams = [getattr(self, f"team{i}_order") for i in range(1, 8)]
        all_teams_name = [f"team{i}_order" for i in range(1, 8)]
        for i in range(7):
            if cfg.get_value(all_teams_name[i]) != 0:
                if cfg.get_value(all_teams_name[i]) > cfg.get_value(which):
                    cfg.set_value(all_teams_name[i], cfg.get_value(all_teams_name[i]) - 1)
        cfg.set_value(which, 0)
        for i in range(7):
            team_order = cfg.get_value(all_teams_name[i])
            if team_order != 0:
                all_teams[i].setText(str(team_order))
            else:
                all_teams[i].setText("")

    def on_combobox_changed(self, data_dict):
        # 各个下拉框改变时，改变config.yaml中的参数
        sender_combo_box = self.sender()
        selected_key = sender_combo_box.currentText()
        selected_value = data_dict[selected_key]
        name = sender_combo_box.objectName()
        cfg.set_value(name, selected_value)

    def change_page(self):
        # 获取发送信号的按钮对象，改变设置的页面
        button = self.sender()

        if button == self.set_windows_button:
            self.detail_setting.setCurrentIndex(0)
            cfg.set_value("default_page", 0)
        elif button == self.daily_task_button:
            self.detail_setting.setCurrentIndex(1)
            cfg.set_value("default_page", 1)
        elif button == self.mirror_button:
            self.detail_setting.setCurrentIndex(2)
            cfg.set_value("default_page", 2)
        elif button == self.buy_enkephalin_button:
            self.detail_setting.setCurrentIndex(3)
            cfg.set_value("default_page", 3)
        elif button == self.get_reward_button:
            self.detail_setting.setCurrentIndex(4)
            cfg.set_value("default_page", 4)
        elif button == self.start_with_key_page:
            self.all_pages.setCurrentIndex(0)
        elif button == self.instructions_page:
            self.all_pages.setCurrentIndex(1)
        elif button == self.about_page:
            self.all_pages.setCurrentIndex(2)

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
        self.language.setEnabled(False)
        self.set_EXP_count.setEnabled(False)
        self.set_thread_count.setEnabled(False)
        self.daily_teams.setEnabled(False)
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
        self.set_reduce_miscontact.setEnabled(True)
        self.set_EXP_count.setEnabled(True)
        self.set_thread_count.setEnabled(True)
        self.daily_teams.setEnabled(True)
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
        all_teams = [getattr(self, f"team{i}_order") for i in range(1, 8)]
        for i, team in enumerate(all_teams, start=1):
            try:
                team.setText(str(cfg.get_value(f"team{i}_order")) if cfg.get_value(f"team{i}_order") != 0 else "")
            except Exception as e:
                log.ERROR(f"更新队伍顺序失败: {e}")

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
        try:
            msg = f"开始进行所有任务"
            log.INFO(msg)
            self.scoll_log_edit.clear()
            self.last_position = 0
            self.set_log(option=1)
            # 启动脚本线程
            self.my_script = my_script_task()
            # 设置脚本线程为守护(当程序被关闭，一起停止)
            self.my_script.daemon = True
            self.my_script.finished_signal.connect(self.start_and_stop_tasks)
            self.my_script.start()
        except Exception as e:
            log.ERROR(f"启动脚本失败: {e}")

    def stop_script(self):
        if self.my_script and self.my_script.isRunning():
            self.my_script.terminate()  # 终止线程

    def load_log_text(self):

        # 打开 log 文件，使用 UTF-8 编码
        file = QFile('./logs/myLog.log')
        if not file.open(QFile.ReadOnly | QFile.Text):
            return

        # 使用 QTextStream 读取文件内容，并指定 UTF-8 编码
        stream = QTextStream(file)
        stream.setCodec('UTF-8')  # 设置编码为 UTF-8

        # 如果是首次读取，初始化 last_position
        if not hasattr(self, 'last_position'):
            self.last_position = 0

        # 从上次读取的位置继续读取
        file.seek(self.last_position)

        new_content = ""
        while not stream.atEnd():
            line = stream.readLine()
            new_content += line
            if not stream.atEnd():
                new_content += '\n'

        # 更新文件读取位置
        self.last_position = file.pos()

        # 如果有新内容，追加到 QTextEdit 控件
        if new_content:
            self.scoll_log_edit.append(new_content)

        # 如果用户滚动到底部，则自动滚动
        if self.scoll_log_edit.verticalScrollBar().value() == self.scoll_log_edit.verticalScrollBar().maximum():
            self.scoll_log_edit.moveCursor(self.scoll_log_edit.textCursor().End)

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

    # 读取复选框时阻止信号触发
    def set_checkbox_state(self, checkbox, value):
        checkbox.blockSignals(True)
        checkbox.setChecked(value)
        checkbox.blockSignals(False)

    def read_last_setting(self):
        """读取设置"""
        # 读取之前最后页面
        self.detail_setting.setCurrentIndex(cfg.default_page)

        # 读取之前最后下拉框设置
        self.daily_teams.setCurrentIndex(cfg.daily_teams - 1)

        self.set_reduce_miscontact.setCurrentIndex(cfg.set_reduce_miscontact)

        self.set_lunacy_to_enkephalin.setCurrentIndex(cfg.set_lunacy_to_enkephalin)

        self.set_get_prize.setCurrentIndex(cfg.set_get_prize)

        win_size = {"1080": 0, "1440": 1, "2160": 3, "720": 4, "900": 5, "1800": 6}
        self.set_win_size.setCurrentIndex(win_size[str(cfg.set_win_size)])

        language_Index = {'en': 0,'zh_cn': 1}
        self.language.setCurrentIndex(language_Index[str(cfg.language)])

        # 读取之前最后复选框设置
        self.set_checkbox_state(self.team1, cfg.team1)
        self.set_checkbox_state(self.team2, cfg.team2)
        self.set_checkbox_state(self.team3, cfg.team3)
        self.set_checkbox_state(self.team4, cfg.team4)
        self.set_checkbox_state(self.team5, cfg.team5)
        self.set_checkbox_state(self.team6, cfg.team6)
        self.set_checkbox_state(self.team7, cfg.team7)

        # 读取复选框设置，不执行选中时的行为
        self.set_checkbox_state(self.set_windows, cfg.set_windows)
        self.set_checkbox_state(self.daily_task, cfg.daily_task)
        self.set_checkbox_state(self.mirror, cfg.mirror)
        self.set_checkbox_state(self.buy_enkephalin, cfg.buy_enkephalin)
        self.set_checkbox_state(self.get_reward, cfg.get_reward)

        # 读取之前最后数字调节框设置
        self.set_mirror_count.setValue(cfg.set_mirror_count)
        self.set_EXP_count.setValue(cfg.set_EXP_count)
        self.set_thread_count.setValue(cfg.set_thread_count)

        # 重计算选中几支队伍，防未知错误
        self.check_teams_select_num()

        # 读取之前排序文本框的数据
        self.team1_order.setText(str(cfg.team1_order) if cfg.team1_order != 0 else "")
        self.team2_order.setText(str(cfg.team2_order) if cfg.team2_order != 0 else "")
        self.team3_order.setText(str(cfg.team3_order) if cfg.team3_order != 0 else "")
        self.team4_order.setText(str(cfg.team4_order) if cfg.team4_order != 0 else "")
        self.team5_order.setText(str(cfg.team5_order) if cfg.team5_order != 0 else "")
        self.team6_order.setText(str(cfg.team6_order) if cfg.team6_order != 0 else "")
        self.team7_order.setText(str(cfg.team7_order) if cfg.team7_order != 0 else "")

    # 重计算选中几支队伍，防未知错误
    def check_teams_select_num(self):
        seven_teams = [f"team{i}" for i in range(1, 8)]
        seven_teams_order = [f"team{i}_order" for i in range(1, 8)]
        team_be_select = 0
        for team in seven_teams:
            if cfg.get_value(team):
                team_be_select += 1
        if cfg.get_value("teams_be_select") != team_be_select:
            cfg.set_value("teams_be_select", team_be_select)
        for team in seven_teams_order:
            if cfg.get_value(team) > team_be_select:
                cfg.set_value(team, cfg.get_value(team) - team_be_select)


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

        # 设置当复选框选中时，修改是否启用对应关键词的售卖/合成
        self.burn.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.bleed.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.tremor.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.rupture.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.poise.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.sinking.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.charge.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.slash.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.pierce.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))
        self.blunt.stateChanged.connect(lambda checked: self.shop_checkbox_state_changed(checked, which_team))

        # 设置当按钮点击时改变商店逻辑
        self.switch_button.checkedChanged.connect(
            lambda checked: self.shop_switch_button_state_changed(checked, which_team, name="fuse"))
        self.switch_button_2.checkedChanged.connect(
            lambda checked: self.shop_switch_button_state_changed(checked, which_team, name="fuse_aggressive"))
        config_datas = cfg.get_value(f"{which_team}")
        if config_datas['fuse']:
            self.switch_button_2.show()
        else:
            self.switch_button_2.hide()

        # 设置完成按钮
        self.confirm_button.clicked.connect(self.close)

        self.exec_()

    def shop_switch_button_state_changed(self, check, which_team, name='fuse'):
        sender_check = self.sender()
        config_datas = cfg.get_value(f"{which_team}")
        config_datas[name] = not config_datas[name]
        if name == 'fuse':
            if config_datas[name]:
                self.switch_button_2.show()
            else:
                self.switch_button_2.hide()
        cfg.set_value(f"{which_team}", config_datas)

    def shop_checkbox_state_changed(self, checked, which_team):
        # 设置当复选框选中时，修改是否启用对应关键词的售卖/合成
        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        config_datas = cfg.get_value(f"{which_team}")
        config_datas[name] = not config_datas[name]
        cfg.set_value(f"{which_team}", config_datas)

    def on_combobox_changed(self, data_dict, which_team):
        # 各个下拉框改变时，改变config.yaml中的参数
        sender_combo_box = self.sender()
        selected_key = sender_combo_box.currentText()
        selected_value = data_dict[selected_key]
        name = sender_combo_box.objectName()
        config_datas = cfg.get_value(f"{which_team}")
        config_datas[name] = selected_value
        cfg.set_value(f"{which_team}", config_datas)

    def checkbox_state_changed(self, checked, combo, which_team):
        # 各个配队的复选框被选中时，修改旁边的启动顺序
        self.check_teams_select_num()

        sender_checkbox = self.sender()
        name = sender_checkbox.objectName()
        this_sinner = name + "_order"
        if sender_checkbox.isChecked():
            config_datas = cfg.get_value(f"{which_team}")
            config_datas[name] = True
            config_datas["sinners_be_select"] += 1
            config_datas[this_sinner] = config_datas["sinners_be_select"]
            combo.setText(str(config_datas["sinners_be_select"]))
            cfg.set_value(f"{which_team}", config_datas)
        else:
            self.reset_sinner_order(this_sinner, which_team)
            config_datas = cfg.get_value(f"{which_team}")
            config_datas[name] = False
            config_datas["sinners_be_select"] -= 1
            config_datas[this_sinner] = 0
            combo.setText("")
            cfg.set_value(f"{which_team}", config_datas)

    # 修改配队顺序的函数
    def reset_sinner_order(self, sinner, which_team):
        try:
            all_sinners = [self.YiSang_order, self.Faust_order, self.DonQuixote_order, self.Ryoshu_order,
                           self.Meursault_order, self.HongLu_order, self.Heathcliff_order, self.Ishmael_order,
                           self.Rodion_order, self.Sinclair_order, self.Outis_order, self.Gregor_order]
            all_sinners_name = ["YiSang_order", "Faust_order", "DonQuixote_order", "Ryoshu_order", "Meursault_order",
                                "HongLu_order", "Heathcliff_order", "Ishmael_order",
                                "Rodion_order", "Sinclair_order", "Outis_order", "Gregor_order"]
            config_datas = cfg.get_value(which_team)
            for i in range(12):
                if config_datas[all_sinners_name[i]] != 0:
                    if config_datas[all_sinners_name[i]] > config_datas[sinner]:
                        config_datas[all_sinners_name[i]] = config_datas[all_sinners_name[i]] - 1
                if config_datas[all_sinners_name[i]] != 0:
                    all_sinners[i].setText(str(config_datas[all_sinners_name[i]]))
                else:
                    all_sinners[i].setText("")
            cfg.set_value(which_team, config_datas)
        except Exception as e:
            raise log.ERROR(f"读取配置出错{e}")

    def set_checkbox_state(self, checkbox, value):
        checkbox.blockSignals(True)
        checkbox.setChecked(value)
        checkbox.blockSignals(False)

    # 读取配置文件中的设置
    def read_my_setting(self, which_team):
        try:
            # 读取设置
            config_datas = cfg.get_value(which_team)
            # 读取之前最后下拉框设置
            self.all_teams.setCurrentIndex(config_datas["all_teams"] - 1)
            self.all_system.setCurrentIndex(config_datas["all_system"])

            # 读取之前罪人复选框设置
            self.set_checkbox_state(self.YiSang, config_datas["YiSang"])
            self.set_checkbox_state(self.Faust, config_datas["Faust"])
            self.set_checkbox_state(self.DonQuixote, config_datas["DonQuixote"])
            self.set_checkbox_state(self.Ryoshu, config_datas["Ryoshu"])
            self.set_checkbox_state(self.Meursault, config_datas["Meursault"])
            self.set_checkbox_state(self.HongLu, config_datas["HongLu"])
            self.set_checkbox_state(self.Heathcliff, config_datas["Heathcliff"])
            self.set_checkbox_state(self.Ishmael, config_datas["Ishmael"])
            self.set_checkbox_state(self.Rodion, config_datas["Rodion"])
            self.set_checkbox_state(self.Sinclair, config_datas["Sinclair"])
            self.set_checkbox_state(self.Outis, config_datas["Outis"])
            self.set_checkbox_state(self.Gregor, config_datas["Gregor"])

            # 读取之前排序文本框的数据
            self.YiSang_order.setText(str(config_datas["YiSang_order"]) if config_datas["YiSang_order"] != 0 else "")
            self.Faust_order.setText(str(config_datas["Faust_order"]) if config_datas["Faust_order"] != 0 else "")
            self.DonQuixote_order.setText(
                str(config_datas["DonQuixote_order"]) if config_datas["DonQuixote_order"] != 0 else "")
            self.Ryoshu_order.setText(str(config_datas["Ryoshu_order"]) if config_datas["Ryoshu_order"] != 0 else "")
            self.Meursault_order.setText(
                str(config_datas["Meursault_order"]) if config_datas["Meursault_order"] != 0 else "")
            self.HongLu_order.setText(str(config_datas["HongLu_order"]) if config_datas["HongLu_order"] != 0 else "")
            self.Heathcliff_order.setText(
                str(config_datas["Heathcliff_order"]) if config_datas["Heathcliff_order"] != 0 else "")
            self.Ishmael_order.setText(str(config_datas["Ishmael_order"]) if config_datas["Ishmael_order"] != 0 else "")
            self.Rodion_order.setText(str(config_datas["Rodion_order"]) if config_datas["Rodion_order"] != 0 else "")
            self.Sinclair_order.setText(
                str(config_datas["Sinclair_order"]) if config_datas["Sinclair_order"] != 0 else "")
            self.Outis_order.setText(str(config_datas["Outis_order"]) if config_datas["Outis_order"] != 0 else "")
            self.Gregor_order.setText(str(config_datas["Gregor_order"]) if config_datas["Gregor_order"] != 0 else "")

            # 读取是否启用合成饰品
            self.switch_button.setChecked(config_datas["fuse"])
            self.switch_button_2.setChecked(config_datas["fuse_aggressive"])

            # 读取之前商店复选框设置
            self.burn.setChecked(config_datas["burn"])
            self.bleed.setChecked(config_datas["bleed"])
            self.tremor.setChecked(config_datas["tremor"])
            self.rupture.setChecked(config_datas["rupture"])
            self.poise.setChecked(config_datas["poise"])
            self.sinking.setChecked(config_datas["sinking"])
            self.charge.setChecked(config_datas["charge"])
            self.slash.setChecked(config_datas["slash"])
            self.pierce.setChecked(config_datas["pierce"])
            self.blunt.setChecked(config_datas["blunt"])
        except Exception as e:
            raise log.ERROR(f"读取配置出错：{e}")

    def check_teams_select_num(self):
        seven_teams = [f"team{i}" for i in range(1, 8)]
        seven_teams_order = [f"team{i}_order" for i in range(1, 8)]
        team_be_select = 0
        for team in seven_teams:
            if cfg.get_value(team):
                team_be_select += 1
        if cfg.get_value("teams_be_select") != team_be_select:
            cfg.set_value("teams_be_select", team_be_select)
        for team in seven_teams_order:
            if cfg.get_value(team) > team_be_select:
                cfg.set_value(team, cfg.get_value(team) - team_be_select)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    ui = MainWindow()
    sys.exit(app.exec_())
