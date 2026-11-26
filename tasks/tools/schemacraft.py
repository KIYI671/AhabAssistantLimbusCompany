from pathlib import Path
from re import findall, search
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
from module.ocr import ocr
from tasks.tools.ui_style import apply_tool_window_theme
from utils.image_utils import ImageUtils

# 这些模板随程序发布，由当前流程使用，独立于在线图片同步目录。
TEMPLATE_DIR = Path("assets/schemacraft")
FRAME_SIZE = (1280, 720)
MAP_SETTINGS = (2442, 98)
REPORT_CONFIRM = (2302, 1309)

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
    "map_info": (2104, 66, 2152, 132),
    "schema_one": (392, 68, 460, 148),
    "cleared_node": (884, 680, 998, 716),
    "regular": (580, 344, 668, 432),
    "respite_node": (908, 675, 994, 764),
    "danger_node": (574, 676, 673, 766),
    "encounter": (2128, 1244, 2374, 1324),
    "boss_encounter": (2150, 73, 2490, 133),
    "respite": (90, 230, 325, 313),
    "bonus_roll": (1446, 505, 1750, 574),
    "respite_select": (2221, 1290, 2361, 1344),
    "deploy": (2147, 1256, 2440, 1328),
    "battle": (2328, 36, 2400, 103),
    "report": (67, 64, 478, 146),
    "battle_retry": (2108, 1240, 2390, 1327),
    "forfeit_menu": (1025, 752, 1532, 811),
    "forfeit_dialog": (1000, 484, 1558, 544),
    "final_results": (50, 73, 431, 127),
    "pass_popup": (1156, 536, 1406, 588),
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


def image_edges(image):
    gray = image.astype(np.float32)
    return gray - cv2.GaussianBlur(gray, (7, 7), 0)


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
        if name == "regular":
            crop = image_edges(crop)
            template = template.astype(np.float32)
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

    def read_text(self, box):
        left, top, right, bottom = (coord // 2 for coord in box)
        crop = Image.fromarray(self.color[top:bottom, left:right])
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        return " ".join(ocr.run(crop).txts or ())

    def first_schema_score(self):
        left, top, right, bottom = (coord // 2 for coord in TEMPLATE_BOXES["schema_one"])
        # 楼层数字是半透明的，保留文字边缘以减少移动背景的影响。
        crop = cv2.GaussianBlur(self.gray[top:bottom, left:right].astype(np.float32), (3, 3), 0)
        edges = image_edges(crop)
        template = self.templates["schema_one"].astype(np.float32)
        return cv2.matchTemplate(edges, template, cv2.TM_CCOEFF_NORMED).max()

    def has_empty_counter(self, category):
        name = f"reward_{category}_zero"
        left, top, right, bottom = (coord // 2 for coord in TEMPLATE_BOXES[name])
        crop = self.gray[top - 2 : bottom + 2, left - 2 : right + 2]
        _, score = ImageUtils.match_template(crop, self.templates[name], None)
        return score > 0.9

    def reachable_node(self, name):
        # 蓝色表示可达。普通节点按剑的轮廓识别，避免透过图标的地图背景干扰。
        nodes = self.find(name, (80, 156, 2470, 1180), threshold=0.55 if name == "regular" else 0.79)
        reachable = [(x, y) for x, y in nodes if self.blue_fraction((x - 50, y - 50, x + 50, y + 50)) > 0.35]
        return min(reachable, key=lambda point: (point[1], point[0]), default=None)


class SchemacraftRun(QThread):
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_requested = Event()
        self.waiting_for_battle = False
        self.reward_picks = set()
        self.first_schema = None
        self.started_from_team_screen = False
        self.entering_encounter = False
        self.settle_at_map = False
        self.settlement_confirmed = False
        self.round_exp = None
        self.empty_runs = 0
        self.weekly_limit_reached = False
        self.checked_lobby_limit = False

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
        last_click = last_progress
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
                was_in_battle = self.waiting_for_battle
                action = self.next_action(SchemacraftFrame(image, templates))
                if was_in_battle and not self.waiting_for_battle:
                    last_progress = monotonic()
                # 战后界面先显示按钮，过场结束后才接收点击。
                retry = action and action[1] in (MAP_SETTINGS, REPORT_CONFIRM) and monotonic() - last_click > 2
                if action and (action != last_action or retry):
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
                        last_click = monotonic()
                        if action != last_action:
                            last_progress = last_click
                        last_action = action
            if monotonic() - last_progress > (300 if self.waiting_for_battle else 20):
                raise RuntimeError("等待下一步超时。请查看游戏当前画面，再点开始可继续")
            self.stop_requested.wait(0.75)
        self.status.emit("图式构筑已停止")

    def next_action(self, frame: SchemacraftFrame):
        if frame.find("pass_popup"):
            return "确认通行证经验", (1280, 1024)
        if frame.find("final_results"):
            self.waiting_for_battle = False
            self.checked_lobby_limit = False
            if self.round_exp is None:
                exp = search(r"[+＋]\s*(\d+)", frame.read_text((442, 82, 880, 122)))
                if exp is None:
                    return None
                self.round_exp = int(exp[1])
                self.empty_runs = 0 if self.round_exp else self.empty_runs + 1
                self.weekly_limit_reached = self.at_weekly_limit(frame, (1307, 137, 1601, 177))
            return f"本局获得 {self.round_exp} 点通行证经验", (2235, 1320)
        if frame.find("forfeit_dialog"):
            self.settlement_confirmed = True
            return "确认按当前进度结算", (1480, 916)
        if frame.find("lobby"):
            if not self.checked_lobby_limit:
                self.checked_lobby_limit = True
                self.weekly_limit_reached = self.weekly_limit_reached or self.at_weekly_limit(
                    frame, (1930, 206, 2331, 256)
                )
            if self.weekly_limit_reached:
                return "本周图式构筑通行证经验已达上限", None
            if self.empty_runs >= 2:
                return "连续两局未获得通行证经验，已停止", None
            self.first_schema = None
            self.started_from_team_screen = False
            self.entering_encounter = False
            self.settle_at_map = False
            self.settlement_confirmed = False
            self.round_exp = None
            self.reward_picks.clear()
            return "进入图式构筑或开始下一局", (2173, 1216)
        if self.settlement_confirmed:
            return None
        if frame.find("forfeit_menu"):
            return "结束本局并结算经验", (1280, 780)
        if frame.find("battle_retry"):
            self.waiting_for_battle = False
            self.entering_encounter = False
            self.settle_at_map = True
            return "战斗失利，返回地图结算本局", (1550, 448)
        if frame.find("replace_ego"):
            return "保留已有 E.G.O.", (1110, 1098)
        if frame.find("team_limit"):
            return "保留现有队伍", (1120, 1268)
        if frame.find("report"):
            self.waiting_for_battle = False
            self.entering_encounter = False
            return "确认战斗报告", REPORT_CONFIRM
        if frame.find("schema_rewards"):
            self.reward_picks.clear()
            self.settle_at_map = True
            if self.schema_confirm_ready(frame):
                return "确认本层通关奖励", (2293, 1317)
            return "选择重抽次数和罪人包", (358, 536)
        if frame.find("sinner_packs"):
            self.reward_picks.clear()
            self.settle_at_map = True
            if self.schema_confirm_ready(frame):
                return "确认罪人奖励包", (2293, 1317)
            return "选择第一位罪人的奖励包", (292, 550)
        if frame.find("pack_choice"):
            self.reward_picks.clear()
            self.settle_at_map = True
            if frame.bright_fraction(TEMPLATE_BOXES["open_pack"]) > 0.21 and frame.find("open_pack"):
                return "打开选中的奖励包", (2330, 1319)
            return "选择中间奖励包", (1268, 550)
        if frame.find("boss_reward") or frame.find("reward", (240, 27, 840, 89), threshold=0.88):
            self.settle_at_map = True
            if frame.bright_fraction(TEMPLATE_BOXES["reward_accept"]) > 0.23 and frame.find("reward_accept"):
                return "领取战后奖励", (2257, 1314)
            return self.choose_reward(frame)
        if frame.find("battle"):
            self.waiting_for_battle = True
            return None
        if frame.find("respite") and (position := frame.find("bonus_roll")):
            if frame.find("respite_select") and frame.bright_fraction(TEMPLATE_BOXES["respite_select"]) > 0.19:
                return "确认休整奖励", (2293, 1317)
            return "选择额外投掷次数", position
        if position := frame.find("deploy", threshold=0.78):
            if frame.blue_fraction(TEMPLATE_BOXES["deploy"]) > 0.15:
                self.waiting_for_battle = True
                return "开始自动战斗，等待报告", position
        if position := frame.find("encounter"):
            if self.settle_at_map or self.past_first_schema(frame) or frame.find("boss_encounter", threshold=0.9):
                self.settle_at_map = True
                return "关闭遭遇面板，准备结算", (1550, 448)
            self.entering_encounter = True
            return "进入遭遇节点", position
        if frame.find("map_info", threshold=0.92) and frame.find("roll"):
            if self.entering_encounter:
                return None
            has_cleared_node = not self.started_from_team_screen and frame.find(
                "cleared_node", (80, 156, 2470, 1140), threshold=0.83
            )
            if self.settle_at_map or self.past_first_schema(frame) or has_cleared_node:
                self.settle_at_map = True
                return "打开地图设置，准备结算", MAP_SETTINGS
            for name, label in (
                ("regular", "选择可达的普通节点"),
                ("respite_node", "选择休整节点"),
            ):
                if position := frame.reachable_node(name):
                    return label, position
            if frame.reachable_node("danger_node"):
                self.settle_at_map = True
                return "打开地图设置，准备结算", MAP_SETTINGS
            if not frame.find("rolled") and frame.blue_fraction((2140, 1080, 2320, 1168)) > 0.45:
                return "投掷骰子", (2085, 1115)
        if frame.find("starting_team") and frame.find("randomize_team"):
            if not frame.selected_tab((880, 94, 1080, 110)):
                return "切换到随机队伍", (975, 84)
            if frame.find("commence"):
                self.first_schema = True
                self.started_from_team_screen = True
                return "使用随机队伍开局", (2278, 1275)
        if position := frame.find("entrance"):
            return "打开图式构筑", position
        if position := frame.find("drive"):
            return "打开 Drive", position
        return None

    def past_first_schema(self, frame):
        if self.first_schema is None:
            score = frame.first_schema_score()
            if score > 0.55 or score < 0.4:
                self.first_schema = score > 0.55
        return self.first_schema is False

    @staticmethod
    def at_weekly_limit(frame, box):
        total = search(r"(\d+)\s*/\s*(\d+)", frame.read_text(box))
        return total is not None and int(total[2]) > 0 and int(total[1]) == int(total[2])

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
        if not needs_id and not needs_ego:
            counters = frame.read_text((2344, 1276, 2497, 1358)).upper().replace(".", "").replace(" ", "")
            unfinished = {
                category
                for category, count, total in findall(r"(ID|EG[O0])(\d+)/(\d+)", counters)
                if int(count) < int(total)
            }
            needs_id = "ID" in unfinished
            needs_ego = bool(unfinished & {"EGO", "EG0"})
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
        self.status = QLabel("赢一场第一层普通战后自动结算并重开。请保持 Steam 英文游戏窗口可见。")
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
