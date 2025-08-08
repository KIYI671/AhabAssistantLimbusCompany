import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QFrame, QHBoxLayout, QTextBrowser, QVBoxLayout
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import SegmentedWidget, ScrollArea, TransparentToolButton
from qfluentwidgets.window.stacked_widget import StackedWidget

from app import *
from app.base_combination import LabelWithComboBox, LabelWithSpinBox, MirrorTeamCombination, \
    MirrorSpinBox
from app.base_tools import BaseCheckBox
from module.config import cfg
from .markdown_it_imgdiv import imgdiv_plugin, render_div_open, render_div_close


class PageCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent

        self.card_layout = QVBoxLayout(self)
        self.all_page = StackedWidget(self)

        self.page_general = QWidget()
        self.page_advanced = QWidget()
        self.vbox_general = QVBoxLayout(self.page_general)
        self.vbox_advanced = QVBoxLayout(self.page_advanced)

        self.scroll_general = ScrollArea(self)
        self.scroll_general.setWidgetResizable(True)
        self.scroll_advanced = ScrollArea(self)
        self.scroll_advanced.setWidgetResizable(True)

        self.set_pivot()

        self.scroll_general.setWidget(self.page_general)
        self.scroll_general.setObjectName("general")
        self.scroll_advanced.setWidget(self.page_advanced)
        self.scroll_advanced.setObjectName("advanced")

        self.all_page.addWidget(self.scroll_general)
        self.all_page.addWidget(self.scroll_advanced)

        self.card_layout.addWidget(self.all_page)
        self.card_layout.addWidget(self.pivot)

        self.scroll_general.enableTransparentBackground()
        self.scroll_advanced.enableTransparentBackground()

        self.__init_widget()

    def set_pivot(self):
        self.pivot = SegmentedWidget(self)
        self.pivot.setFixedHeight(50)
        self.pivot.addItem("general", "常规设置")
        self.pivot.addItem("advanced", "高级设置")
        self.pivot.setCurrentItem("general")
        self.pivot.currentItemChanged.connect(
            lambda k: self.all_page.setCurrentWidget(self.findChild(QWidget, k)))

    def __init_widget(self):
        self.card_layout.setAlignment(Qt.AlignTop)
        self.vbox_general.setAlignment(Qt.AlignTop)
        self.vbox_advanced.setAlignment(Qt.AlignTop)

class PageSetWindows(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_set_windows")

    def __init_card(self):
        self.win_size = LabelWithComboBox("窗口分辨率", "set_win_size",set_win_size_options)
        self.win_position = LabelWithComboBox("窗口位置", "set_win_position",set_win_position_options)
        self.recovery_window = LabelWithComboBox("结束后恢复窗口", "set_recovery_window",set_reduce_miscontact_options)
        self.language_in_game = LabelWithComboBox("游戏使用语言", "language_in_game",set_language_options)

        self.screenshot_interval = LabelWithSpinBox("截图间隔", "screenshot_interval",double=True)
        self.mouse_action_interval = LabelWithSpinBox("鼠标活动间隔", "mouse_action_interval",double=True)

    def __init_layout(self):
        self.vbox_general.addWidget(self.win_size)
        self.vbox_general.addWidget(self.win_position)
        self.vbox_general.addWidget(self.recovery_window)
        self.vbox_general.addWidget(self.language_in_game)

        self.vbox_advanced.addWidget(self.screenshot_interval)
        self.vbox_advanced.addWidget(self.mouse_action_interval)

class PageDailyTask(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_daily_task")

    def __init_card(self):
        self.EXP_count = LabelWithSpinBox("经验本次数", "set_EXP_count", min_value=0, min_step=1)
        self.thread_count = LabelWithSpinBox("纽本次数", "set_thread_count", min_value=0, min_step=1)
        self.team_select = LabelWithComboBox("使用编队", "daily_teams",all_teams)

        self.targeted_teaming_EXP = BaseCheckBox("targeted_teaming_EXP",None, "经验本针对性配队",center=False)
        self.EXP_day_1_2 = LabelWithComboBox("周一、周二（斩击）", "EXP_day_1_2",all_teams)
        self.EXP_day_3_4 = LabelWithComboBox("周三、周四（突刺）", "EXP_day_3_4",all_teams)
        self.EXP_day_5_6 = LabelWithComboBox("周五、周六（打击）", "EXP_day_5_6",all_teams)
        self.EXP_day_7 = LabelWithComboBox("周日", "EXP_day_7",all_teams)
        self.targeted_teaming_thread = BaseCheckBox("targeted_teaming_thread", None, "纽本针对性配队", center=False)
        self.thread_day_1 = LabelWithComboBox("纽本周一（色欲）", "thread_day_1",all_teams)
        self.thread_day_2 = LabelWithComboBox("纽本周二（怠惰）", "thread_day_2",all_teams)
        self.thread_day_3 = LabelWithComboBox("纽本周三（暴食）", "thread_day_3",all_teams)
        self.thread_day_4 = LabelWithComboBox("纽本周四（忧郁）", "thread_day_4",all_teams)
        self.thread_day_5 = LabelWithComboBox("纽本周五（傲慢）", "thread_day_5",all_teams)
        self.thread_day_6 = LabelWithComboBox("纽本周六（嫉妒）", "thread_day_6",all_teams)
        self.thread_day_7 = LabelWithComboBox("纽本周日（暴怒）", "thread_day_7",all_teams)

    def __init_layout(self):
        self.vbox_general.addWidget(self.EXP_count)
        self.vbox_general.addWidget(self.thread_count)
        self.vbox_general.addWidget(self.team_select)

        self.vbox_advanced.addWidget(self.targeted_teaming_EXP)
        self.vbox_advanced.addWidget(self.EXP_day_1_2)
        self.vbox_advanced.addWidget(self.EXP_day_3_4)
        self.vbox_advanced.addWidget(self.EXP_day_5_6)
        self.vbox_advanced.addWidget(self.EXP_day_7)
        self.vbox_advanced.addSpacing(30)
        self.vbox_advanced.addWidget(self.targeted_teaming_thread)
        self.vbox_advanced.addWidget(self.thread_day_1)
        self.vbox_advanced.addWidget(self.thread_day_2)
        self.vbox_advanced.addWidget(self.thread_day_3)
        self.vbox_advanced.addWidget(self.thread_day_4)
        self.vbox_advanced.addWidget(self.thread_day_5)
        self.vbox_advanced.addWidget(self.thread_day_6)
        self.vbox_advanced.addWidget(self.thread_day_7)

class PageGetPrize(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_get_prize")

    def __init_card(self):
        self.set_get_prize = LabelWithComboBox("领取奖励", "set_get_prize",set_get_prize_options)

    def __init_layout(self):
        self.vbox_general.addWidget(self.set_get_prize)

class PageLunacyToEnkephalin(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_lunacy_to_enkephalin")

    def __init_card(self):
        self.set_lunacy_to_enkephalin = LabelWithComboBox("狂气换体", "set_lunacy_to_enkephalin",set_lunacy_to_enkephalin_options)

        self.Dr_Grandet_mode = BaseCheckBox("Dr_Grandet_mode", None, "葛朗台模式",center=False)


    def __init_layout(self):
        self.vbox_general.addWidget(self.set_lunacy_to_enkephalin)

        self.vbox_advanced.addWidget(self.Dr_Grandet_mode)

class PageMirror(PageCard):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_card()
        self.__init_layout()
        self.setObjectName("page_mirror")

        self.get_setting()
        self.refresh()

        self.connect_mediator()

    def __init_card(self):
        self.team = MirrorTeamCombination(1,"team1", "编队1",None,"team1_setting")

        self.mirror_count=MirrorSpinBox("坐牢次数","set_mirror_count")

        self.add_team = QHBoxLayout(self)
        self.add_team_button = TransparentToolButton(FIF.ADD,None)
        self.add_team_button.setMinimumWidth(200)
        self.add_team_button.clicked.connect(self.new_team)
        self.hard_mirror = BaseCheckBox("hard_mirror", None, "使用困难镜牢*",center=False)
        self.no_weekly_bonuses = BaseCheckBox("no_weekly_bonuses", None, "不使用每周加成*", center=False)
        self.flood_3_exit = BaseCheckBox("flood_3_exit", None, "只打三层", center=False)
        self.infinite_dungeons = BaseCheckBox("infinite_dungeons", None, "无限坐牢",center=False)
        self.save_rewards = BaseCheckBox("save_rewards", None, "保存困牢奖励",center=False)
        self.hard_mirror_single_bonuses = BaseCheckBox("hard_mirror_single_bonuses", None, "困牢单次加成",center=False)

    def __init_layout(self):
        self.vbox_general.addWidget(self.team)

        self.add_team.addWidget(self.add_team_button)
        self.vbox_general.addLayout(self.add_team)

        self.vbox_advanced.addWidget(self.hard_mirror)
        self.vbox_advanced.addWidget(self.no_weekly_bonuses)
        self.vbox_advanced.addWidget(self.flood_3_exit)
        self.vbox_advanced.addWidget(self.infinite_dungeons)
        self.vbox_advanced.addWidget(self.save_rewards)
        self.vbox_advanced.addWidget(self.hard_mirror_single_bonuses)

        self.card_layout.insertWidget(self.card_layout.count() - 1,self.mirror_count)

    def get_setting(self):
        team_toggle_button_group.clear()
        for i in range(1,21):
            if self.findChild(MirrorTeamCombination, f"team_{i}") is not None:
                self.remove_team_card(f"team_{i}")
        for i in range(1,21):
            if cfg.get_value(f"team{i}_setting") is not None:
                self.vbox_general.insertWidget(self.vbox_general.count() - 1,
                                               MirrorTeamCombination(i, f"the_team_{i}", f"编队{i}", None,
                                                                     f"team{i}_setting"))
        self.refresh()

    def new_team(self):
        number = len(team_toggle_button_group)+1
        if number<20:
            self.vbox_general.insertWidget(self.vbox_general.count()-1, MirrorTeamCombination(number,f"the_team_{number}", f"编队{number}",None,f"team{number}_setting"))
            if cfg.get_value(f"team{number}_setting") is None:
                cfg.set_value(f"team{number}_setting", dict(team_setting_template))
                cfg.set_value(f"team{number}_remark_name", None)
                teams_be_select=cfg.get_value("teams_be_select")
                teams_be_select.append(False)
                teams_order=cfg.get_value("teams_order")
                teams_order.append(0)
                cfg.set_value("teams_be_select", teams_be_select)
                cfg.set_value("teams_order", teams_order)

    def remove_team_card(self, target:str):
        try:
            team = self.findChild(MirrorTeamCombination, target)
            self.vbox_general.removeWidget(team)
            team.setParent(None)
            team.deleteLater()
            team = None
        except Exception as e:
            print(f"【异常】delete_team 出错：{e}")

    def delete_team(self, target:str):
        try:
            team = self.findChild(MirrorTeamCombination, target)
            team_order_box = team.findChild(BaseCheckBox, f"the_team_{team.team_number}")
            team_order_box.set_check_false()
            self.remove_team_card(target)

            number = int(target.split("_")[-1])
            cfg.del_key(f"team{number}_setting")
            cfg.del_key(f"team{number}_remark_name")

            teams_be_select = cfg.get_value("teams_be_select")
            teams_be_select.pop(number-1)
            teams_order = cfg.get_value("teams_order")
            teams_order.pop(number-1)
            cfg.set_value("teams_be_select", teams_be_select)
            cfg.set_value("teams_order", teams_order)

            self.refresh_team_setting_card()
        except Exception as e:
            print(f"【异常】delete_team 出错：{e}")

    def refresh_team_setting_card(self):
        for i in range(1,21):
            if cfg.get_value(f"team{i}_setting") is None and cfg.get_value(f"team{i+1}_setting") is not None:
                cfg.set_value(f"team{i}_setting", cfg.get_value(f"team{i+1}_setting"))
                cfg.del_key(f"team{i+1}_setting")
                cfg.set_value(f"team{i}_remark_name", cfg.get_value(f"team{i+1}_remark_name"))
                cfg.del_key(f"team{i+1}_remark_name")
        self.get_setting()

    def refresh(self):
        mirror_teams = self.findChildren(MirrorTeamCombination)
        teams_order = cfg.get_value("teams_order")
        for team in mirror_teams:
            number = team.team_number
            if teams_order[number-1]!=0:
                team.order.setText(str(teams_order[number-1]))
            else:
                team.order.setText("")

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.delete_team_setting.connect(self.delete_team)
        mediator.refresh_teams_order.connect(self.refresh)


def transform_image_url(self, tokens, idx, options, env):
    token = tokens[idx]
    src = token.attrs["src"]
    if isinstance(src, str):
        url = QUrl(src)
        if url.path().startswith("/"):
            new_src = "." + url.path()
            tokens[idx].attrSet("src", new_src)

    return self.image(tokens, idx, options, env)

class MarkdownViewer(QWidget):
    def __init__(self, file_path: str):
        super().__init__()
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self.handle_link_clicked)
        self.text_browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu) # 禁用右键菜单

        css_path = "assets/styles/github-markdown-light.css"
        with open(css_path, "r", encoding="utf-8") as css_file:
            css_content = css_file.read()
            self.text_browser.setStyleSheet(css_content)

        self.md = (
            MarkdownIt("commonmark", {"html": True})
            .enable("linkify")
            .enable("table")
            .enable("strikethrough")
            .use(
                anchors_plugin,
                max_level=4,
                slug_func=lambda s: s.lower().replace(" ", "-"),
            )
        )
        self.md.add_render_rule("image", transform_image_url)
        self.md.use(imgdiv_plugin, class_name="figure", focusable=False, align="center")

        self.md.add_render_rule("div_open", render_div_open)
        self.md.add_render_rule("div_close", render_div_close)

        self.html = """
        <html>
            <body>
                <h1>帮助页面加载失败！</h1>
            </body>
        </html>
        """

        layout.addWidget(self.text_browser)
        self.help_path = file_path
        self.reset_viewer()
    
    def reset_viewer(self):
        if os.path.exists(self.help_path):
            self.load_markdown(self.help_path)
            self.text_browser.setHtml(self.html)
        else:
            self.text_browser.setPlainText(
                f"错误: 无法加载文件 {self.help_path}，请检查文件路径是否正确。"
            )

    def handle_link_clicked(self, url: QUrl):
        """
        Decides how to handle a clicked link in the QTextBrowser.
        """
        if url.scheme() in ["http", "https"]:
            # 用系统默认浏览器打开外部链接
            QDesktopServices.openUrl(url)
        elif url.scheme() != "":
            # 其他链接，不处理
            pass
        else:
            # 本地文件
            file_path = url.path()
            if file_path.startswith("/"):
                # 处理以项目根目录为base的路径
                file_path = file_path[1:]

            if os.path.exists(file_path) and file_path.endswith(".md"):
                # 如果是本地文件链接，尝试加载 Markdown 文件
                self.load_markdown(file_path)
                self.text_browser.setHtml(self.html)

                if url.hasFragment():
                    # 如果链接有锚点，滚动到对应的锚点
                    self.text_browser.scrollToAnchor(url.fragment())
                return

        self.text_browser.setHtml(self.html)

    def load_markdown(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

                html_body = self.md.render(markdown_text)

                # 添加 HTML 头部
                self.html = f"""
                <html>
                <body>
                    {html_body}
                </body>
                </html>
                """
        except Exception as e:
            self.text_browser.setPlainText(f"错误: 无法加载文件\n{str(e)}")
