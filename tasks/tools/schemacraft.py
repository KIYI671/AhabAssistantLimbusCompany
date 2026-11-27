from dataclasses import dataclass
from pathlib import Path
from re import IGNORECASE, findall, search
from threading import Event
from time import monotonic, time_ns

import cv2
import numpy as np
import win32gui
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from win32con import WHEEL_DELTA

from module.automation.input_handlers.input import BackgroundInput, Input
from module.automation.screenshot import ScreenShot
from module.config import cfg
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
RESULT_CONFIRM = (2235, 1320)
PASS_CONFIRM = (1280, 1024)
REWARD_CONFIRM = (2257, 1314)
SCHEMA_CONFIRM = (2293, 1317)
START_CRAFT = (2285, 1305)
SCAN_MAP = (1200, 740)
SCAN_MAP_UP = (1200, 741)
MOVE_TO_CLEARED_NODE = "移动到已通关节点"
CONFIRM_CLEARED_MOVE = "确认移动到已通关节点"

# 全屏参考坐标，读取时统一缩小到 1280×720。
TEMPLATE_BOXES = {
    "drive": (1916, 1252, 2010, 1394),
    "drive_mobile": (1890, 1226, 2040, 1352),
    "entrance": (779, 609, 986, 659),
    "lobby": (1796, 54, 1955, 118),
    "starting_team": (234, 44, 592, 112),
    "randomize_team": (840, 61, 1111, 107),
    "commence": (2143, 1230, 2440, 1289),
    "roll": (2156, 1094, 2320, 1158),
    "rolled": (1959, 1054, 2040, 1190),
    "map_info": (2104, 66, 2152, 132),
    "schema_one": (392, 68, 460, 148),
    "schema_two": (392, 68, 460, 148),
    "schema_three": (392, 68, 460, 148),
    "regular": (580, 344, 668, 432),
    "respite_node": (908, 675, 994, 764),
    "danger_node": (574, 676, 673, 766),
    "boss_marker": (912, 332, 1008, 424),
    "event_node": (921, 343, 981, 439),
    "cleared_node": (1360, 334, 1536, 450),
    "map_player": (890, 652, 1014, 788),
    "encounter": (2128, 1244, 2374, 1324),
    "visited_encounter": (2292, 52, 2484, 152),
    "boss_encounter": (2150, 73, 2490, 133),
    "respite": (90, 230, 325, 313),
    "bonus_roll": (1446, 505, 1750, 574),
    "respite_select": (2221, 1290, 2361, 1344),
    "deploy": (2147, 1256, 2440, 1328),
    "battle": (2328, 36, 2400, 103),
    "ego_details": (1576, 506, 1754, 556),
    "report": (67, 64, 478, 146),
    "battle_retry": (2108, 1240, 2390, 1327),
    "forfeit_menu": (1025, 752, 1532, 811),
    "forfeit_dialog": (1000, 484, 1558, 544),
    "final_results": (50, 73, 431, 127),
    "pass_popup": (1156, 536, 1406, 588),
    "tutorial_back": (98, 32, 284, 158),
    "tutorial_back_mobile": (98, 32, 284, 158),
    "elite_reward": (212, 204, 732, 280),
    "elite_decline": (2098, 366, 2380, 450),
    "elite_confirm": (2138, 1348, 2370, 1420),
    "elite_unclaimed": (946, 474, 1613, 554),
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

    def find(self, name: str, area=None, threshold=0.84, scale=1):
        template = self.templates[name]
        box = tuple(coord // 2 for coord in TEMPLATE_BOXES[name])
        if area is None:
            point, score = ImageUtils.match_template(self.gray, template, box)
            return tuple(coord * 2 for coord in point) if score >= threshold else None
        left, top, right, bottom = (coord // 2 for coord in area)
        crop = self.gray[top:bottom, left:right]
        if name in ("regular", "event_node"):
            crop = image_edges(crop)
            template = template.astype(np.float32)
        elif name == "cleared_node":
            crop = image_edges(crop)
            template = image_edges(template)
        if scale != 1:
            template = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
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

    def read_ocr(self, box):
        left, top, right, bottom = (coord // 2 for coord in box)
        crop = Image.fromarray(self.color[top:bottom, left:right])
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        return ocr.run(crop)

    def read_text(self, box):
        return " ".join(self.read_ocr(box).txts or ())

    def text_positions(self, box):
        left, top = (coord // 2 for coord in box[:2])
        result = self.read_ocr(box)
        if not result.txts or result.boxes is None:
            return []
        return [
            (text, (round(2 * (left + x / 3)), round(2 * (top + y / 3))))
            for text, (x, y) in zip(result.txts, np.asarray(result.boxes).mean(axis=1))
        ]

    def schema_number(self):
        left, top, right, bottom = (coord // 2 for coord in TEMPLATE_BOXES["schema_one"])
        # 楼层数字是半透明的，保留文字边缘以减少移动背景的影响。
        crop = cv2.GaussianBlur(self.gray[top:bottom, left:right].astype(np.float32), (3, 3), 0)
        edges = image_edges(crop)
        scores = [
            cv2.matchTemplate(edges, self.templates[name].astype(np.float32), cv2.TM_CCOEFF_NORMED).max()
            for name in ("schema_one", "schema_two", "schema_three")
        ]
        schema = max(range(len(scores)), key=scores.__getitem__)
        if scores[schema] > 0.55 and scores[schema] - sorted(scores)[-2] > 0.12:
            return schema + 1
        return None

    def highlighted_map_node(self):
        # 路线也是蓝色，先滤掉细线，再选远离当前位置的节点色块。
        px, py = self.player_position() or (1280, 720)
        color = self.color[78:590, 40:1235].astype(np.int16)
        red, green, blue = color.transpose(2, 0, 1)
        mask = ((blue > 125) & (blue - red > 50) & (blue - green > 45)).astype(np.uint8)
        mask[417:, 930:] = 0
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        _, _, stats, centers = cv2.connectedComponentsWithStats(opened)
        nodes = []
        for region, center in zip(stats[1:], centers[1:]):
            x, y = (round(2 * (offset + value)) for offset, value in zip((40, 78), center))
            if 500 <= region[cv2.CC_STAT_AREA] <= 9000 and max(abs(x - px), abs(y - py)) > 120:
                nodes.append((x, y))
        return min(nodes, key=lambda point: (point[1], point[0]), default=None)

    def has_empty_counter(self, category):
        name = f"reward_{category}_zero"
        left, top, right, bottom = (coord // 2 for coord in TEMPLATE_BOXES[name])
        crop = self.gray[top - 2 : bottom + 2, left - 2 : right + 2]
        _, score = ImageUtils.match_template(crop, self.templates[name], None)
        return score > 0.9

    def reachable_node(self, name, scale=1):
        # 蓝色表示可达。普通节点按剑的轮廓识别，避免透过图标的地图背景干扰。
        threshold = {"regular": 0.55, "event_node": 0.48}.get(name, 0.79)
        nodes = self.find(name, (80, 156, 2470, 1180), threshold=threshold, scale=scale)
        radius = round(50 * scale)
        reachable = [
            (x, y) for x, y in nodes if self.blue_fraction((x - radius, y - radius, x + radius, y + radius)) > 0.35
        ]
        return min(reachable, key=lambda point: (point[1], point[0]), default=None)

    def player_position(self):
        players = self.find("map_player", (80, 156, 2470, 1180), threshold=0.83)
        return players[0] if players else None

    def map_route_above(self):
        # 蓝色竖线抵达画面上边时，优先把上方节点拉进显示区域。
        red, green, blue = self.color[12:70, 40:1235].astype(np.int16).transpose(2, 0, 1)
        mask = (blue > 125) & (blue - red > 50) & (blue - green > 45)
        return np.count_nonzero(mask.mean(axis=0) > 0.34) >= 6

    def reachable_cleared_node(self, previous_positions=(), target=None):
        # 已通关的格子保持黑色，骰点可达时只点亮连接线。
        nodes = self.find("cleared_node", (80, 80, 2470, 1180), threshold=0.72)

        def priority(point):
            x, y = point
            last_visit = max(
                (rank for rank, (px, py) in enumerate(previous_positions, 1) if max(abs(px - x), abs(py - y)) < 80),
                default=0,
            )
            distance = abs(x - target[0]) + abs(y - target[1]) if target else 0
            return last_visit, distance, y, x

        for x, y in sorted(nodes, key=priority):
            for dx, dy in ((126, 0), (-126, 0), (0, 126), (0, -126)):
                cx, cy = x + dx, y + dy
                if 22 <= cx <= 2538 and 22 <= cy <= 1158:
                    if self.blue_fraction((cx - 22, cy - 22, cx + 22, cy + 22)) > 0.25:
                        return x, y
        return None


@dataclass
class NodeTiming:
    floor: int
    started_at: float
    route_seconds: float | None
    kind: str = "未确认"
    outcome: str | None = None
    battle_started_at: float | None = None
    battle_ended_at: float | None = None
    foreground_wait: float = 0


@dataclass
class RewardChoice:
    label: str
    position: tuple[int, int]
    category: str
    count_before: int
    deadline: float


class SchemacraftRun(QThread):
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.completed_rounds = 0
        self.stop_requested = Event()
        self.waiting_for_battle = False
        self.reward_picks = set()
        self.missed_reward_picks = set()
        self.pending_reward: RewardChoice | None = None
        self.schema = None
        self.regular_wins = 0
        self.reward_counted = False
        self.boss_encounter = False
        self.cleared_moves = 0
        self.cleared_node_selected = False
        self.cleared_step = None
        self.previous_cleared_offsets = []
        self.entering_encounter = False
        self.settle_at_map = False
        self.settlement_confirmed = False
        self.round_exp = None
        self.empty_runs = 0
        self.weekly_limit_reached = False
        self.checked_lobby_limit = False
        self.reset_map_roll()
        self.excess_rolls = 0
        self.entering_event = False
        self.event_confirm = None
        self.run_id = time_ns()
        self.node_number = 0
        self.node_timing: NodeTiming | None = None
        self.map_since: float | None = None
        self.inactive_since: float | None = None

    def run(self):
        try:
            self._play()
        except Exception as error:
            log.exception("图式构筑运行出错")
            self.status.emit(f"图式构筑已停止（{error}）")
        finally:
            self.log_node(interrupted=True)

    def _play(self):
        hwnd = None
        if cfg.simulator:
            from module.automation import auto
            from tasks.base.script_task_scheme import init_game

            self.status.emit("正在连接模拟器")
            init_game()
            mouse = auto.input_handler
            capture = ScreenShot.take_screenshot
            log.info("图式构筑：已连接模拟器，使用截图和触控")
        else:
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
            capture = ScreenShot.take_screenshot_gdi
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
            if hwnd is not None and (screen.handle.hwnd != hwnd or not win32gui.IsWindow(hwnd)):
                raise RuntimeError("游戏窗口已关闭")
            if hwnd is not None and not screen.handle.isActive:
                if self.inactive_since is None:
                    self.inactive_since = monotonic()
                    log.info("图式构筑：等待游戏窗口回到前台")
                    self.status.emit("等待游戏窗口回到前台")
                self.stop_requested.wait(0.75)
                continue
            if self.inactive_since is not None:
                foreground_wait = monotonic() - self.inactive_since
                last_progress += foreground_wait
                if self.node_timing is not None:
                    self.node_timing.foreground_wait += foreground_wait
                if self.pending_reward is not None:
                    self.pending_reward.deadline += foreground_wait
                self.inactive_since = None
                self.status.emit("继续识别游戏画面")
            if (image := capture(gray=False)) is not None:
                width, height = image.size
                if hwnd is not None and (width, height) != (screen.handle.width(True), screen.handle.height(True)):
                    raise RuntimeError("请让游戏窗口完整显示在同一块屏幕上")
                if abs(width * 9 - height * 16) > 16:
                    raise RuntimeError("请将游戏画面设为 16:9")
                was_in_battle = self.waiting_for_battle
                action = self.next_action(SchemacraftFrame(image, templates))
                if was_in_battle and not self.waiting_for_battle:
                    last_progress = monotonic()
                # 战后界面先显示按钮，过场结束后才接收点击。
                retry = (
                    action
                    and (
                        action[1]
                        in (
                            MAP_SETTINGS,
                            REPORT_CONFIRM,
                            RESULT_CONFIRM,
                            PASS_CONFIRM,
                            REWARD_CONFIRM,
                            SCHEMA_CONFIRM,
                            START_CRAFT,
                        )
                        or action[0]
                        in (
                            "进入遭遇节点",
                            "进入事件节点",
                            "确认事件选项",
                            "开始自动战斗，等待报告",
                            "关闭 E.G.O. 详情，继续战斗",
                            "战斗失利，返回地图结算本局",
                            "关闭遭遇面板，准备结算",
                            "选择中间奖励包",
                            "打开选中的奖励包",
                            "选择重抽次数和罪人包",
                            "选择第一位罪人的奖励包",
                            "关闭图式构筑教程",
                            "跳过精英奖励",
                            "确认精英奖励",
                            "确认放弃精英奖励",
                            "切换到碎片奖励",
                            "队伍已满，改领人格碎片",
                            "招募新的人格",
                            "选取人格碎片",
                            "选取 E.G.O.",
                            "选择可达的普通节点",
                            MOVE_TO_CLEARED_NODE,
                            CONFIRM_CLEARED_MOVE,
                            "选择休整节点",
                            "选择可达的事件节点",
                            "选择地图高亮节点",
                        )
                        or action[0].endswith("层首领节点")
                    )
                    and monotonic() - last_click > 2
                )
                if action and (action != last_action or retry):
                    label, position = action
                    if position is None:
                        log.info(f"图式构筑：{label}")
                        self.status.emit(label)
                        return
                    if self.stop_requested.is_set():
                        break
                    if hwnd is None or (screen.handle.isActive and screen.handle.hwnd == hwnd):
                        x = round(position[0] * width / 2560)
                        y = round(position[1] * height / 1440)
                        if position in (SCAN_MAP, SCAN_MAP_UP):
                            if hwnd is None:
                                distance = height // (2 if self.map_scanned_both else 3)
                                mouse.mouse_drag(x, y, 0.3, 0, distance if position == SCAN_MAP_UP else -distance)
                            else:
                                foreground = Input()
                                foreground.mouse_move(foreground.pos_offset(x, y))
                                foreground.mouse_scroll(-5 * WHEEL_DELTA)
                        else:
                            mouse.mouse_click(x, y)
                        self.status.emit(label)
                        log.info(f"图式构筑：{label}")
                        last_click = monotonic()
                        if label != CONFIRM_CLEARED_MOVE:
                            self.cleared_node_selected = label == MOVE_TO_CLEARED_NODE
                        if action != last_action:
                            last_progress = last_click
                            if label == MOVE_TO_CLEARED_NODE:
                                self.cleared_moves += 1
                                self.reset_map_roll()
                            elif label == CONFIRM_CLEARED_MOVE and self.cleared_step is not None:
                                dx, dy = self.cleared_step
                                self.previous_cleared_offsets = [(x - dx, y - dy) for x, y in self.previous_cleared_offsets]
                                self.previous_cleared_offsets.append((-dx, -dy))
                                self.cleared_step = None
                        last_action = action
            timeout = 90 if hwnd is None and last_action is None else 20  # 模拟器冷启动时等待首个游戏画面。
            if self.waiting_for_battle:
                timeout = 300
            elif self.round_exp is not None:
                timeout = 60  # 结算后的黑屏加载可能超过普通页面切换时间。
            if monotonic() - last_progress > timeout:
                raise RuntimeError("等待下一步超时。请查看游戏当前画面，再点开始可继续")
            self.stop_requested.wait(0.75)
        self.status.emit("图式构筑已停止")

    def next_action(self, frame: SchemacraftFrame):
        if position := (
            frame.find("tutorial_back", threshold=0.93)
            or frame.find("tutorial_back_mobile", threshold=0.93)
        ):
            return "关闭图式构筑教程", position
        if frame.find("elite_reward", threshold=0.91):
            if self.node_timing is not None:
                self.node_timing.kind = "精英战"
            if frame.find("elite_unclaimed", threshold=0.92):
                return "确认放弃精英奖励", (1480, 916)
            if frame.bright_fraction(TEMPLATE_BOXES["elite_confirm"]) > 0.16:
                if position := frame.find("elite_confirm", threshold=0.85):
                    return "确认精英奖励", position
            if position := frame.find("elite_decline", threshold=0.88):
                return "跳过精英奖励", position
            return None
        if frame.find("pass_popup"):
            return "确认通行证经验", PASS_CONFIRM
        if frame.find("final_results"):
            self.log_node()
            self.waiting_for_battle = False
            self.checked_lobby_limit = False
            if self.round_exp is None:
                exp = search(r"[+＋]\s*(\d+)", frame.read_text((442, 82, 880, 122)))
                if exp is None:
                    return None
                self.round_exp = int(exp[1])
                self.completed_rounds += 1
                self.empty_runs = 0 if self.round_exp else self.empty_runs + 1
                self.weekly_limit_reached = self.at_weekly_limit(frame, (1307, 137, 1601, 177))
            return f"本局获得 {self.round_exp} 点通行证经验", RESULT_CONFIRM
        if frame.find("forfeit_dialog"):
            self.settlement_confirmed = True
            return "确认按当前进度结算", (1480, 916)
        if frame.find("lobby"):
            self.log_node(interrupted=True)
            if not self.checked_lobby_limit:
                self.checked_lobby_limit = True
                self.weekly_limit_reached = self.weekly_limit_reached or self.at_weekly_limit(
                    frame, (1930, 206, 2331, 256)
                )
            if self.weekly_limit_reached:
                return "本周图式构筑通行证经验已达上限", None
            if self.empty_runs >= 2:
                return "连续两局未获得通行证经验，已停止", None
            self.schema = None
            self.node_number = 0
            self.map_since = None
            self.regular_wins = 0
            self.reward_counted = False
            self.boss_encounter = False
            self.entering_encounter = False
            self.settle_at_map = False
            self.settlement_confirmed = False
            self.round_exp = None
            self.cleared_moves = 0
            self.cleared_node_selected = False
            self.cleared_step = None
            self.previous_cleared_offsets.clear()
            self.reset_map_roll()
            self.excess_rolls = 0
            self.entering_event = False
            self.event_confirm = None
            self.reset_reward_choices()
            return "进入图式构筑或开始下一局", (2173, 1216)
        if self.settlement_confirmed:
            return None
        if frame.find("forfeit_menu"):
            return "结束本局并结算经验", (1280, 780)
        if frame.find("battle_retry"):
            self.end_node_battle("失败")
            self.waiting_for_battle = False
            self.entering_encounter = False
            self.settle_at_map = True
            return "战斗失利，返回地图结算本局", (720, 430)
        if frame.find("replace_ego"):
            return "保留已有 E.G.O.", (1110, 1098)
        if frame.find("team_limit"):
            self.skip_pending_reward()
            return "保留现有队伍", (1120, 1268)
        if frame.find("report"):
            self.end_node_battle("胜利")
            self.waiting_for_battle = False
            self.entering_encounter = False
            return "确认战斗报告", REPORT_CONFIRM
        if frame.find("schema_rewards"):
            self.settle_at_map = True
            self.reset_reward_choices()
            if self.schema_confirm_ready(frame):
                return "确认本层通关奖励", SCHEMA_CONFIRM
            return "选择重抽次数和罪人包", (358, 536)
        if frame.find("sinner_packs"):
            self.reset_reward_choices()
            if self.schema_confirm_ready(frame):
                return "确认罪人奖励包", SCHEMA_CONFIRM
            return "选择第一位罪人的奖励包", (292, 550)
        if frame.find("pack_choice"):
            self.reset_reward_choices()
            self.record_regular_win()
            if frame.bright_fraction(TEMPLATE_BOXES["open_pack"]) > 0.21 and frame.find("open_pack"):
                return "打开选中的奖励包", (2330, 1319)
            return "选择中间奖励包", (1268, 550)
        boss_reward = frame.find("boss_reward")
        if boss_reward or frame.find("reward", (240, 27, 840, 89), threshold=0.88):
            if not boss_reward:
                self.record_regular_win()
            if frame.bright_fraction(TEMPLATE_BOXES["reward_accept"]) > 0.23 and frame.find("reward_accept"):
                return "领取战后奖励", REWARD_CONFIRM
            return self.choose_reward(frame)
        if frame.find("ego_details", threshold=0.91):
            # 移动端可能打开技能详情并暂停战斗，关闭后让当前战斗继续。
            self.waiting_for_battle = True
            return "关闭 E.G.O. 详情，继续战斗", (690, 280)
        if frame.find("battle"):
            self.waiting_for_battle = True
            if self.node_timing is not None and self.node_timing.battle_started_at is None:
                self.node_timing.kind = "首领战" if self.boss_encounter else "普通战"
                self.node_timing.battle_started_at = monotonic()
            return None
        if frame.find("respite") and (position := frame.find("bonus_roll")):
            self.entering_encounter = False
            self.reset_map_roll()
            if self.node_timing is not None:
                self.node_timing.kind = "休整"
            if frame.find("respite_select") and frame.bright_fraction(TEMPLATE_BOXES["respite_select"]) > 0.19:
                if self.node_timing is not None:
                    self.node_timing.outcome = "完成"
                return "确认休整奖励", SCHEMA_CONFIRM
            return "选择额外投掷次数", position
        if position := frame.find("deploy", threshold=0.78):
            if frame.blue_fraction(TEMPLATE_BOXES["deploy"]) > 0.15:
                self.waiting_for_battle = True
                return "开始自动战斗，等待报告", position
        if position := frame.find("encounter"):
            self.update_schema(frame)
            if self.should_settle():
                self.entering_encounter = False
                self.settle_at_map = True
                return "关闭遭遇面板，准备结算", (720, 430)
            if self.selected_cleared_node(frame):
                self.entering_encounter = False
                self.reset_map_roll()
                return CONFIRM_CLEARED_MOVE, position
            if self.schema is None:
                return None
            self.begin_node()
            self.entering_encounter = True
            self.reward_counted = False
            self.boss_encounter = bool(frame.find("boss_encounter", threshold=0.9))
            self.reset_map_roll()
            return "进入遭遇节点", position
        if self.entering_event:
            for text, position in frame.text_positions((2070, 1200, 2450, 1350)):
                if search(r"\benter (representation|event)\b", text, flags=IGNORECASE):
                    self.begin_node()
                    self.reset_map_roll()
                    return "进入事件节点", position
            if self.event_confirm:
                for text, position in frame.text_positions((2080, 720, 2470, 950)):
                    if text.strip().lower() == "confirm":
                        if self.node_timing is not None:
                            self.node_timing.kind = "事件"
                            self.node_timing.outcome = "跳过"
                        return "确认事件选项", position
            else:
                for text, position in frame.text_positions((1570, 395, 2460, 790)):
                    if search(r"\b(decline|leave|walk away|do nothing)\b", text, flags=IGNORECASE):
                        self.event_confirm = True
                        self.entering_encounter = False
                        return "选择离开事件", position
        if frame.find("map_info", threshold=0.92) and frame.find("roll"):
            if self.entering_encounter:
                return None
            self.log_node()
            if self.map_since is None:
                self.map_since = monotonic()
            self.entering_event = False
            self.event_confirm = None
            self.update_schema(frame)
            if self.should_settle():
                self.settle_at_map = True
                return "打开地图设置，准备结算", MAP_SETTINGS
            if self.schema is None:
                return None
            boss = self.map_node(frame, "danger_node")
            if boss and self.regular_wins >= 4:
                return "选择第 1 层首领节点", boss
            for name, label in (
                ("regular", "选择可达的普通节点"),
                ("respite_node", "选择休整节点"),
            ):
                if position := self.map_node(frame, name):
                    return label, position
            if boss:
                return "选择第 1 层首领节点", boss
            if position := self.map_node(frame, "event_node"):
                self.entering_event = True
                return "选择可达的事件节点", position
            if self.map_recovery and (position := frame.highlighted_map_node()):
                self.entering_event = True
                return "选择地图高亮节点", position
            rolled = frame.find("rolled") or self.rolled_at
            if not rolled and frame.blue_fraction((2140, 1080, 2320, 1168)) > 0.45:
                self.rolled_at = monotonic()
                return "投掷骰子", (2085, 1115)
            if rolled and not self.map_recovery and monotonic() - self.rolled_at > 2:
                self.map_recovery = monotonic()
                self.map_scan_started_up = frame.map_route_above()
                return "搜索地图上可达的节点", SCAN_MAP_UP if self.map_scan_started_up else SCAN_MAP
            if rolled and self.map_recovery and monotonic() - self.map_recovery > 1:
                if self.cleared_moves < 6 and (position := self.choose_cleared_node(frame)):
                    return MOVE_TO_CLEARED_NODE, position
            if self.map_recovery and monotonic() - self.map_recovery > 4:
                if not self.map_scanned_both:
                    self.map_scanned_both = True
                    self.map_recovery = monotonic()
                    return "反向搜索地图上可达的节点", SCAN_MAP if self.map_scan_started_up else SCAN_MAP_UP
                free = search(r"\b[1-9]\d*\b", frame.read_text((2324, 1085, 2396, 1167)))
                if self.recovery_rerolls < 2 and (free or self.excess_rolls < 2):
                    self.recovery_rerolls += 1
                    if not free:
                        self.excess_rolls += 1
                    self.map_recovery = monotonic()
                    return f"未识别到可达节点，尝试第 {self.recovery_rerolls} 次重投", (2085, 1115)
                raise RuntimeError("未识别到可达节点，已保留当前局。")
        if frame.find("starting_team") and frame.find("randomize_team"):
            if not frame.selected_tab((880, 94, 1080, 110)):
                return "切换到随机队伍", (975, 84)
            if frame.find("commence"):
                self.schema = 1
                return "使用随机队伍开局", START_CRAFT
        if position := frame.find("entrance"):
            return "打开图式构筑", position
        if position := frame.find("drive") or frame.find("drive_mobile", threshold=0.90):
            return "打开 Drive", position
        return None

    def update_schema(self, frame):
        schema = frame.schema_number()
        if self.schema is not None and schema is not None and schema < self.schema:
            return
        if schema is not None and schema != self.schema:
            if self.schema is not None:
                self.regular_wins = 0
                self.excess_rolls = 0
            self.schema = schema
            self.node_number = 0
            log.info(f"图式构筑：进入第 {schema} 层")

    def begin_node(self):
        if self.node_timing is None and self.schema is not None:
            self.cleared_moves = 0
            self.cleared_step = None
            self.previous_cleared_offsets.clear()
            started_at = monotonic()
            route_seconds = started_at - self.map_since if self.map_since is not None else None
            self.node_timing = NodeTiming(self.schema, started_at, route_seconds)
            self.map_since = None

    def end_node_battle(self, outcome):
        node = self.node_timing
        if node is not None and node.outcome is None:
            node.kind = "首领战" if self.boss_encounter else "普通战"
            node.outcome = outcome
            node.battle_ended_at = monotonic()
        elif node is not None and outcome == "失败":
            # 失败也会先显示战报，稍后出现重试界面。
            node.outcome = outcome

    def log_node(self, *, interrupted=False):
        node = self.node_timing
        if node is None:
            return
        self.node_timing = None
        self.node_number += 1
        now = monotonic()
        battle = after_battle = "-"
        if node.battle_ended_at is not None:
            after_battle = f"{now - node.battle_ended_at:.2f}"
            if node.battle_started_at is not None:
                battle = f"{node.battle_ended_at - node.battle_started_at:.2f}"
        foreground_wait = node.foreground_wait
        if self.inactive_since is not None:
            foreground_wait += now - self.inactive_since
        log.info(
            "图式构筑节点 运行=%s 局=%s 层=%s 节点=%s 类型=%s 结果=%s "
            "选路秒=%s 节点秒=%.2f 战斗秒=%s 战后秒=%s 前台等待秒=%.2f",
            self.run_id,
            self.completed_rounds + 1,
            node.floor,
            self.node_number,
            node.kind,
            "中断" if interrupted else (node.outcome or "中断"),
            f"{node.route_seconds:.2f}" if node.route_seconds is not None else "-",
            now - node.started_at,
            battle,
            after_battle,
            foreground_wait,
        )

    def should_settle(self):
        return self.settle_at_map or (self.schema is not None and self.schema >= 2)

    def reset_map_roll(self):
        self.map_recovery = 0
        self.map_scanned_both = False
        self.map_scan_started_up = False
        self.recovery_rerolls = 0
        self.rolled_at = 0

    def map_node(self, frame, name):
        if point := frame.reachable_node(name):
            return point
        if self.map_recovery:
            for scale in (0.8, 0.7, 0.6, 0.5):
                if point := frame.reachable_node(name, scale=scale):
                    return point
        return None

    def selected_cleared_node(self, frame):
        if self.cleared_node_selected or frame.find("visited_encounter", threshold=0.90):
            return True
        if self.map_since is None and not self.entering_encounter:
            title = frame.read_text((1770, 38, 2520, 176))
            return bool(search(r"\balready\s*visited\b", title, flags=IGNORECASE))
        return False

    def choose_cleared_node(self, frame):
        player = frame.player_position()
        bosses = frame.find("boss_marker", (80, 30, 2470, 1260), threshold=0.82)
        target = bosses[0] if bosses else None
        self.cleared_step = None
        if not player:
            return frame.reachable_cleared_node(target=target)
        px, py = player
        previous_positions = [(px + dx, py + dy) for dx, dy in self.previous_cleared_offsets]
        if position := frame.reachable_cleared_node(previous_positions, target):
            self.cleared_step = position[0] - px, position[1] - py
            return position
        return None

    def record_regular_win(self):
        if not self.boss_encounter and not self.reward_counted:
            self.regular_wins += 1
            self.reward_counted = True
            log.info(f"图式构筑：第 {self.schema or '?'} 层已赢 {self.regular_wins} 场普通战")

    @staticmethod
    def at_weekly_limit(frame, box):
        total = search(r"(\d+)\s*/\s*(\d+)", frame.read_text(box))
        return total is not None and int(total[2]) > 0 and int(total[1]) == int(total[2])

    @staticmethod
    def schema_confirm_ready(frame):
        return frame.find("schema_confirm") and frame.bright_fraction(TEMPLATE_BOXES["schema_confirm"]) > 0.16

    def reset_reward_choices(self):
        self.reward_picks.clear()
        self.missed_reward_picks.clear()
        self.pending_reward = None

    def skip_pending_reward(self):
        if self.pending_reward is not None:
            self.missed_reward_picks.add((self.pending_reward.label, self.pending_reward.position[0]))
            self.pending_reward = None

    def choose_reward(self, frame: SchemacraftFrame):
        if full := frame.find("team_full", (300, 1106, 2110, 1164), threshold=0.91):
            self.skip_pending_reward()
            x, _ = full[0]
            return "队伍已满，改领人格碎片", (x + 82, 384)
        counts = {category: (0, 1) for category in ("ID", "EGO") if frame.has_empty_counter(category.lower())}
        pending = self.pending_reward
        if not counts or (pending is not None and pending.category not in counts):
            text = frame.read_text((2344, 1276, 2497, 1358)).upper().replace(".", "").replace(" ", "")
            for category, count, total in findall(r"(ID|EG[O0])(\d+)/(\d+)", text):
                counts["EGO" if category == "EG0" else category] = int(count), int(total)
        if pending is not None:
            counter = counts.get(pending.category)
            if counter is not None and counter[0] > pending.count_before:
                self.reward_picks.add(pending.position[0])
                self.pending_reward = None
            elif monotonic() < pending.deadline:
                return (pending.label, pending.position) if counter is not None else None
            else:
                self.skip_pending_reward()

        area = (280, 340, 2200, 414)
        for label, category, image, box, threshold, x_offset in (
            ("招募新的人格", "ID", "reward_team", area, 0.89, 83),
            ("选取 E.G.O.", "EGO", "reward_ego", (1100, 410, 2350, 690), 0.83, 95),
            ("选取人格碎片", "ID", "reward_sliver", area, 0.91, -83),
        ):
            count, total = counts.get(category, (0, 0))
            if count >= total:
                continue
            for x, y in sorted(frame.find(image, box, threshold=threshold)):
                position = (x + x_offset, 600)
                if any(abs(position[0] - picked) < 170 for picked in self.reward_picks):
                    continue
                if any(
                    label == missed_label and abs(position[0] - missed_x) < 30
                    for missed_label, missed_x in self.missed_reward_picks
                ):
                    continue
                if label == "选取人格碎片" and not frame.selected_tab((x - 54, y - 13, x + 54, y + 13)):
                    return "切换到碎片奖励", (x, y)
                self.pending_reward = RewardChoice(label, position, category, count, monotonic() + 8)
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
        self.status = QLabel("击败第一层首领后结算并自动重开。请使用英文游戏界面。Steam 模式需保持游戏在前台。")
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
