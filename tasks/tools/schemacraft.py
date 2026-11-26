from pathlib import Path
from threading import Event
from time import monotonic

import cv2
import numpy as np
import win32gui
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from module.automation.input_handlers.input import BackgroundInput
from module.automation.screenshot import ScreenShot
from module.game_and_screen import screen
from module.logger import log
from tasks.tools.ui_style import apply_tool_window_theme
from utils.image_utils import ImageUtils

# 这些模板随程序发布，由当前流程使用，独立于在线图片同步目录。
TEMPLATE_DIR = Path("assets/schemacraft")
FRAME_SIZE = (1280, 720)

# 全屏参考坐标，读取时统一缩小到 1280×720。
TEMPLATE_BOXES = {
    "drive": (1916, 1252, 2010, 1394),
    "entrance": (779, 609, 986, 659),
    "lobby": (1796, 54, 1955, 118),
    "starting_team": (234, 44, 592, 112),
    "randomize_team": (840, 61, 1111, 107),
    "commence": (2143, 1230, 2440, 1289),
    "roll": (2156, 1094, 2320, 1158),
    "rolled": (1959, 1054, 2040, 1190),
    "regular": (580, 344, 668, 432),
    "regular_translucent": (1564, 674, 1652, 762),
    "respite_node": (908, 675, 994, 764),
    "danger_node": (574, 676, 673, 766),
    "encounter": (2128, 1244, 2374, 1324),
    "respite": (90, 230, 325, 313),
    "bonus_roll": (1446, 505, 1750, 574),
    "respite_select": (2221, 1290, 2361, 1344),
    "deploy": (2147, 1256, 2440, 1328),
    "battle": (2328, 36, 2400, 103),
    "report": (67, 64, 478, 146),
    "battle_retry": (2108, 1240, 2390, 1327),
    "schema_rewards": (75, 99, 765, 174),
    "sinner_packs": (946, 97, 1342, 176),
    "schema_confirm": (2192, 1291, 2401, 1350),
    "pack_choice": (90, 163, 881, 249),
    "open_pack": (2232, 1288, 2429, 1345),
    "reward": (500, 37, 652, 77),
    "boss_reward": (248, 40, 490, 79),
    "reward_team": (503, 375, 563, 398),
    "reward_sliver": (661, 373, 732, 398),
    "reward_ego": (1504, 439, 1531, 665),
    "reward_accept": (2170, 1291, 2351, 1343),
    "reward_id_zero": (2401, 1285, 2420, 1314),
    "reward_ego_zero": (2420, 1314, 2442, 1346),
    "replace_ego": (1162, 307, 1399, 359),
    "team_limit": (1043, 117, 1514, 181),
    "team_full": (564, 1118, 668, 1149),
}


class SchemacraftFrame:
    def __init__(self, image: Image.Image, templates: dict):
        self.color = np.asarray(image.convert("RGB").resize(FRAME_SIZE, Image.Resampling.BILINEAR))
        self.gray = cv2.cvtColor(self.color, cv2.COLOR_RGB2GRAY)
        self.templates = templates

    def find(self, name: str, area=None, threshold=0.84):
        template = self.templates[name]
        box = tuple(coord // 2 for coord in TEMPLATE_BOXES[name])
        if area is None:
            point, score = ImageUtils.match_template(self.gray, template, box)
            return tuple(coord * 2 for coord in point) if score >= threshold else None
        left, top, right, bottom = (coord // 2 for coord in area)
        crop = self.gray[top:bottom, left:right]
        matches = ImageUtils.match_template_with_multiple_targets(crop, template, threshold, min_dist=45)
        return [(2 * (x + left), 2 * (y + top)) for x, y in matches]

    def blue_fraction(self, box):
        left, top, right, bottom = (coord // 2 for coord in box)
        red, green, blue = self.color[top:bottom, left:right].astype(np.int16).transpose(2, 0, 1)
        return np.mean((blue > 125) & (blue - red > 50) & (blue - green > 45))

    def bright_fraction(self, box):
        left, top, right, bottom = (coord // 2 for coord in box)
        return np.mean(self.gray[top:bottom, left:right] > 170)

    def selected_tab(self, box):
        left, top, right, bottom = (coord // 2 for coord in box)
        tab = self.color[top:bottom, left:right].astype(np.int16)
        return np.mean(tab[:, :, 2] - tab[:, :, 0]) > 9

    def has_empty_counter(self, category):
        name = f"reward_{category}_zero"
        left, top, right, bottom = (coord // 2 for coord in TEMPLATE_BOXES[name])
        crop = self.gray[top - 2 : bottom + 2, left - 2 : right + 2]
        _, score = ImageUtils.match_template(crop, self.templates[name], None)
        return score > 0.9

    def reachable_node(self, name):
        nodes = self.find(name, (80, 156, 2470, 1180), threshold=0.79)
        reachable = [(x, y) for x, y in nodes if self.blue_fraction((x - 50, y - 50, x + 50, y + 50)) > 0.35]
        return min(reachable, key=lambda point: (point[1], point[0]), default=None)


class SchemacraftRun(QThread):
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_requested = Event()
        self.in_run = False
        self.waiting_for_battle = False
        self.reward_picks = set()

    def run(self):
        try:
            self._play()
        except Exception as error:
            log.exception("图式构筑运行出错")
            self.status.emit(f"图式构筑已停止（{error}）")

    def _play(self):
        hwnd = screen.handle.init_handle(screen.title)
        if not hwnd:
            raise RuntimeError("请先打开 Windows 游戏客户端")
        if screen.handle.isMinimized:
            screen.handle.restore()
        if not screen.handle.isActive:
            try:
                screen.handle.setForeground()
            except win32gui.error:
                self.status.emit("请将游戏切到前台")
        mouse = BackgroundInput()
        if mouse.is_pause:
            raise RuntimeError("请先恢复 AALC 的输入")
        templates = {}
        for name in TEMPLATE_BOXES:
            with Image.open(TEMPLATE_DIR / f"{name}.png") as image:
                templates[name] = np.asarray(image.convert("L"))

        last_action = None
        last_progress = monotonic()
        self.status.emit("正在识别游戏画面")
        while not self.stop_requested.is_set():
            if screen.handle.hwnd != hwnd:
                raise RuntimeError("游戏窗口已关闭")
            if screen.handle.isActive:
                image = ScreenShot.take_screenshot_gdi(gray=False)
                width, height = image.size
                if (width, height) != (screen.handle.width(True), screen.handle.height(True)):
                    raise RuntimeError("请让游戏窗口完整显示在同一块屏幕上")
                if abs(width * 9 - height * 16) > 16:
                    raise RuntimeError("请将游戏画面设为 16:9")
                action = self.next_action(SchemacraftFrame(image, templates))
                if action and action != last_action:
                    label, position = action
                    if position is None:
                        self.status.emit(label)
                        return
                    if self.stop_requested.is_set():
                        break
                    if screen.handle.isActive and screen.handle.hwnd == hwnd:
                        mouse.mouse_click(
                            round(position[0] * width / 2560), round(position[1] * height / 1440), move_back=False
                        )
                        self.status.emit(label)
                        log.info(f"图式构筑：{label}")
                        last_progress = monotonic()
                        last_action = action
            if monotonic() - last_progress > (300 if self.waiting_for_battle else 20):
                raise RuntimeError("等待下一步超时。请查看游戏当前画面，再点开始可继续")
            self.stop_requested.wait(0.75)
        self.status.emit("图式构筑已停止")

    def next_action(self, frame: SchemacraftFrame):
        if frame.find("battle_retry"):
            return "本场战斗未通过，请调整队伍后继续。", None
        if frame.find("replace_ego"):
            return "保留已有 E.G.O.", (1110, 1098)
        if frame.find("team_limit"):
            return "保留现有队伍", (1120, 1268)
        if frame.find("report"):
            self.waiting_for_battle = False
            self.in_run = True
            return "确认战斗报告", (2302, 1309)
        if frame.find("schema_rewards"):
            self.reward_picks.clear()
            self.in_run = True
            if self.schema_confirm_ready(frame):
                return "确认本层通关奖励", (2293, 1317)
            return "选择重抽次数和罪人包", (358, 536)
        if frame.find("sinner_packs"):
            self.reward_picks.clear()
            self.in_run = True
            if self.schema_confirm_ready(frame):
                return "确认罪人奖励包", (2293, 1317)
            return "选择第一位罪人的奖励包", (292, 550)
        if frame.find("pack_choice"):
            self.reward_picks.clear()
            self.in_run = True
            if frame.bright_fraction(TEMPLATE_BOXES["open_pack"]) > 0.21 and frame.find("open_pack"):
                return "打开选中的奖励包", (2330, 1319)
            return "选择中间奖励包", (1268, 550)
        if frame.find("boss_reward") or frame.find("reward", (240, 27, 840, 89), threshold=0.88):
            self.in_run = True
            if position := self.choose_reward(frame):
                return position
            if frame.bright_fraction(TEMPLATE_BOXES["reward_accept"]) > 0.23 and frame.find("reward_accept"):
                return "领取战后奖励", (2257, 1314)
            return None
        if frame.find("battle"):
            self.waiting_for_battle = True
            self.in_run = True
            return None
        if frame.find("respite") and (position := frame.find("bonus_roll")):
            self.in_run = True
            if frame.find("respite_select") and frame.bright_fraction(TEMPLATE_BOXES["respite_select"]) > 0.19:
                return "确认休整奖励", (2293, 1317)
            return "选择额外投掷次数", position
        if position := frame.find("deploy", threshold=0.78):
            if frame.blue_fraction(TEMPLATE_BOXES["deploy"]) > 0.15:
                self.waiting_for_battle = True
                self.in_run = True
                return "开始自动战斗，等待报告", position
        if position := frame.find("encounter"):
            self.in_run = True
            return "进入遭遇节点", position
        if frame.find("roll"):
            self.in_run = True
            for name, label in (
                ("regular", "选择可达的普通节点"),
                ("regular_translucent", "选择可达的普通节点"),
                ("respite_node", "选择休整节点"),
                ("danger_node", "选择首领节点"),
            ):
                if position := frame.reachable_node(name):
                    return label, position
            if not frame.find("rolled") and frame.blue_fraction((2140, 1080, 2320, 1168)) > 0.45:
                return "投掷骰子", (2085, 1115)
        if frame.find("starting_team") and frame.find("randomize_team"):
            if not frame.selected_tab((880, 94, 1080, 110)):
                return "切换到随机队伍", (975, 84)
            if frame.find("commence"):
                self.in_run = True
                return "使用随机队伍开局", (2278, 1275)
        if frame.find("lobby"):
            if self.in_run:
                return "已回到图式构筑入口", None
            return "进入或继续图式构筑", (2173, 1216)
        if position := frame.find("entrance"):
            return "打开图式构筑", position
        if position := frame.find("drive"):
            return "打开 Drive", position
        return None

    @staticmethod
    def schema_confirm_ready(frame):
        return frame.find("schema_confirm") and frame.bright_fraction(TEMPLATE_BOXES["schema_confirm"]) > 0.16

    def choose_reward(self, frame: SchemacraftFrame):
        area = (280, 340, 2020, 414)
        recruit = sorted(frame.find("reward_team", area, threshold=0.89))
        silver = sorted(frame.find("reward_sliver", area, threshold=0.91))
        ego = sorted(frame.find("reward_ego", (1100, 410, 2350, 690), threshold=0.83))
        needs_id = frame.has_empty_counter("id")
        needs_ego = frame.has_empty_counter("ego")
        if full := frame.find("team_full", (300, 1106, 2110, 1164), threshold=0.91):
            x, _ = full[0]
            return "队伍已满，改领人格碎片", (x + 82, 384)
        for label, options, x_offset in (
            ("招募新的人格", recruit if needs_id else [], 83),
            ("选取 E.G.O.", ego if needs_ego else [], 95),
            ("选取人格碎片", silver if needs_id else [], -83),
        ):
            for x, y in options:
                position = (x + x_offset, 600)
                if not any(abs(position[0] - picked) < 170 for picked in self.reward_picks):
                    if label == "选取人格碎片" and not frame.selected_tab((x - 54, y - 13, x + 54, y + 13)):
                        return "切换到碎片奖励", (x, y)
                    self.reward_picks.add(position[0])
                    return label, position
        return None


class SchemacraftTool(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.can_start = None
        self.closing = False
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("图式构筑")
        self.status = QLabel("请打开 Steam 版英文客户端，并保持游戏窗口可见。")
        self.status.setWordWrap(True)
        self.button = QPushButton("开始")
        self.button.clicked.connect(self.toggle_run)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.button)
        self.resize(380, 120)
        apply_tool_window_theme(self, "SchemacraftTool")

    def is_running(self):
        return self.worker is not None and self.worker.isRunning()

    def toggle_run(self):
        if self.worker is not None:
            self.worker.stop_requested.set()
            self.button.setEnabled(False)
            return
        if self.can_start is not None and not self.can_start():
            self.status.setText("请先停止主任务并关闭其他小工具。")
            return
        self.worker = SchemacraftRun(self)
        self.worker.status.connect(self.status.setText)
        self.worker.finished.connect(self.on_finished)
        self.button.setText("停止")
        self.worker.start()

    def on_finished(self):
        self.worker.deleteLater()
        self.worker = None
        if self.closing:
            self.close()
            return
        self.button.setText("开始")
        self.button.setEnabled(True)

    def closeEvent(self, event):
        if self.is_running():
            self.closing = True
            self.worker.stop_requested.set()
            event.ignore()
            return
        super().closeEvent(event)
