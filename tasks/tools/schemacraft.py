from dataclasses import dataclass
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
from tasks.tools.schemacraft_map import FloorMap, read_map
from tasks.tools.ui_style import apply_tool_window_theme
from utils.image_utils import ImageUtils
from utils.path_manager import path_manager

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


def image_edges(image):
    gray = image.astype(np.float32)
    return gray - cv2.GaussianBlur(gray, (7, 7), 0)


class SchemacraftFrame:
    def __init__(self, image: Image.Image, templates: dict):
        self.color = np.asarray(image.convert("RGB").resize(FRAME_SIZE, Image.Resampling.BILINEAR))
        self.gray = cv2.cvtColor(self.color, cv2.COLOR_RGB2GRAY)
        self.templates = templates

    def template(self, name):
        if name not in self.templates:
            path = f"schemacraft/{name}.png"
            image = ImageUtils.load_image(path, resize=False)
            if image is None:
                raise FileNotFoundError(path)
            box = None
            if name.endswith(("_assets", "_bbox")):
                box = ImageUtils.get_bbox(image)
                image = ImageUtils.crop(image, box, copy=False)
            core = cv2.resize(image, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            self.templates[name] = core, box
        return self.templates[name]

    def box(self, name):
        return self.template(name)[1]

    def find(self, name: str, area=None, threshold=0.84, scale=1):
        template, box = self.template(name)
        if area is None:
            point, score = ImageUtils.match_template(self.gray, template, tuple(coord // 2 for coord in box))
            return tuple(coord * 2 for coord in point) if score >= threshold else None
        left, top, right, bottom = (coord // 2 for coord in area)
        crop = self.gray[top:bottom, left:right]
        if name.endswith("_node"):
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

    def bright_fraction(self, name):
        left, top, right, bottom = (coord // 2 for coord in self.box(name))
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
        left, top, right, bottom = (coord // 2 for coord in (392, 68, 460, 148))
        # 楼层数字是半透明的，保留文字边缘以减少移动背景的影响。
        crop = cv2.GaussianBlur(self.gray[top:bottom, left:right].astype(np.float32), (3, 3), 0)
        edges = image_edges(crop)
        scores = [
            cv2.matchTemplate(edges, self.template(name)[0].astype(np.float32), cv2.TM_CCOEFF_NORMED).max()
            for name in ("schema_1_assets", "schema_2_assets", "schema_3_assets")
        ]
        schema = max(range(len(scores)), key=scores.__getitem__)
        if scores[schema] > 0.55 and scores[schema] - sorted(scores)[-2] > 0.12:
            return schema + 1
        return None

    def has_empty_counter(self, category):
        name = f"reward_{category}_zero_assets"
        template, box = self.template(name)
        left, top, right, bottom = (coord // 2 for coord in box)
        crop = self.gray[top - 2 : bottom + 2, left - 2 : right + 2]
        _, score = ImageUtils.match_template(crop, template, None)
        return score > 0.9

    def map_route_above(self):
        # 蓝色竖线抵达画面上边时，优先把上方节点拉进显示区域。
        red, green, blue = self.color[12:70, 40:1235].astype(np.int16).transpose(2, 0, 1)
        mask = (blue > 125) & (blue - red > 50) & (blue - green > 45)
        return np.count_nonzero(mask.mean(axis=0) > 0.34) >= 6


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
        self.route = FloorMap()
        self.regular_wins = 0
        self.reward_counted = False
        self.boss_encounter = False
        self.entering_encounter = False
        self.settle_at_map = False
        self.settlement_confirmed = False
        self.round_exp = None
        self.empty_runs = 0
        self.weekly_limit_reached = False
        self.checked_lobby_limit = False
        self.reset_map_roll()
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
        path_manager.initialize_paths(reset_eliminations=False)
        templates = {}

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
                            "前往相邻的新节点",
                            "沿最短路回到已通关节点",
                            "确认移动到已通关节点",
                            "关闭节点详情，重新选路",
                            "投掷骰子",
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
                                distance = height // (3 if self.map_scans else 2)
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
                        if action != last_action:
                            last_progress = last_click
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
            frame.find("tutorial_back_assets", threshold=0.93)
            or frame.find("tutorial_back_mobile_assets", threshold=0.93)
        ):
            return "关闭图式构筑教程", position
        if frame.find("choose_elite_reward_assets", threshold=0.91):
            if self.node_timing is not None:
                self.node_timing.kind = "精英战"
            if frame.find("unclaimed_elite_rewards_assets", threshold=0.92):
                return "确认放弃精英奖励", (1480, 916)
            if frame.bright_fraction("confirm_elite_reward_assets") > 0.16:
                if position := frame.find("confirm_elite_reward_assets", threshold=0.85):
                    return "确认精英奖励", position
            if position := frame.find("decline_elite_reward_assets", threshold=0.88):
                return "跳过精英奖励", position
            return None
        if frame.find("pass_level_up_assets"):
            return "确认通行证经验", PASS_CONFIRM
        if frame.find("final_battle_results_assets"):
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
        if frame.find("forfeit_schemacraft_dialog_assets"):
            self.settlement_confirmed = True
            return "确认按当前进度结算", (1480, 916)
        if frame.find("schemacraft_pass_assets"):
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
            self.route = FloorMap()
            self.node_number = 0
            self.map_since = None
            self.regular_wins = 0
            self.reward_counted = False
            self.boss_encounter = False
            self.entering_encounter = False
            self.settle_at_map = False
            self.settlement_confirmed = False
            self.round_exp = None
            self.reset_map_roll()
            self.entering_event = False
            self.event_confirm = None
            self.reset_reward_choices()
            return "进入图式构筑或开始下一局", (2173, 1216)
        if self.settlement_confirmed:
            return None
        if frame.find("forfeit_schemacraft_assets"):
            return "结束本局并结算经验", (1280, 780)
        if frame.find("change_team_and_retry_assets"):
            self.end_node_battle("失败")
            self.waiting_for_battle = False
            self.entering_encounter = False
            self.settle_at_map = True
            return "战斗失利，返回地图结算本局", (720, 430)
        if frame.find("replace_ego_assets"):
            return "保留已有 E.G.O.", (1110, 1098)
        if frame.find("team_limit_exceeded_assets"):
            self.skip_pending_reward()
            return "保留现有队伍", (1120, 1268)
        if frame.find("battle_report_assets"):
            self.end_node_battle("胜利")
            self.waiting_for_battle = False
            self.entering_encounter = False
            return "确认战斗报告", REPORT_CONFIRM
        if frame.find("schema_clear_rewards_assets"):
            self.settle_at_map = True
            self.reset_reward_choices()
            if self.schema_confirm_ready(frame):
                return "确认本层通关奖励", SCHEMA_CONFIRM
            return "选择重抽次数和罪人包", (358, 536)
        if frame.find("sinner_packs_assets"):
            self.reset_reward_choices()
            if self.schema_confirm_ready(frame):
                return "确认罪人奖励包", SCHEMA_CONFIRM
            return "选择第一位罪人的奖励包", (292, 550)
        if frame.find("battle_reward_pack_choice_assets"):
            self.reset_reward_choices()
            self.record_regular_win()
            if frame.bright_fraction("open_pack_assets") > 0.21 and frame.find("open_pack_assets"):
                return "打开选中的奖励包", (2330, 1319)
            return "选择中间奖励包", (1268, 550)
        boss_reward = frame.find("boss_clear_reward_assets")
        if boss_reward or frame.find("clear_reward", (240, 27, 840, 89), threshold=0.88):
            if not boss_reward:
                self.record_regular_win()
            if full := frame.find("team_full", (300, 1106, 2110, 1164), threshold=0.80):
                self.skip_pending_reward()
                x, _ = full[0]
                return "队伍已满，改领人格碎片", (x + 82, 384)
            if frame.bright_fraction("confirm_battle_reward_assets") > 0.23 and frame.find(
                "confirm_battle_reward_assets"
            ):
                return "领取战后奖励", REWARD_CONFIRM
            return self.choose_reward(frame)
        if frame.find("ego_passives_assets", threshold=0.91):
            # 移动端可能打开技能详情并暂停战斗，关闭后让当前战斗继续。
            self.waiting_for_battle = True
            return "关闭 E.G.O. 详情，继续战斗", (690, 280)
        if frame.find("battle_pause_assets"):
            self.waiting_for_battle = True
            if self.node_timing is not None and self.node_timing.battle_started_at is None:
                self.node_timing.kind = "首领战" if self.boss_encounter else "普通战"
                self.node_timing.battle_started_at = monotonic()
            return None
        if frame.find("respite_title_assets") and (position := frame.find("bonus_rolls_assets")):
            self.entering_encounter = False
            self.reset_map_roll()
            if self.node_timing is not None:
                self.node_timing.kind = "休整"
            if frame.find("select_respite_assets") and frame.bright_fraction("select_respite_assets") > 0.19:
                if self.node_timing is not None:
                    self.node_timing.outcome = "完成"
                return "确认休整奖励", SCHEMA_CONFIRM
            return "选择额外投掷次数", position
        if position := frame.find("to_battle_assets", threshold=0.78):
            if frame.blue_fraction(frame.box("to_battle_assets")) > 0.15:
                self.waiting_for_battle = True
                return "开始自动战斗，等待报告", position
        if position := frame.find("enter_representation_assets"):
            return self.enter_node(frame, position)
        if frame.find("map_info_assets", threshold=0.92) and frame.find("remaining_rolls_assets"):
            if self.entering_encounter:
                return None
            self.log_node()
            if self.map_since is None:
                self.map_since = monotonic()
            self.event_confirm = None
            self.update_schema(frame)
            if self.should_settle():
                self.settle_at_map = True
                return "打开地图设置，准备结算", MAP_SETTINGS
            if self.schema is None:
                return None
            return self.next_map_action(frame)
        if self.entering_event and self.route.entered:
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
        if frame.find("starting_team_assets") and frame.find("randomize_team_assets"):
            if not frame.selected_tab((880, 94, 1080, 110)):
                return "切换到随机队伍", (975, 84)
            if frame.find("commence_craft_assets"):
                self.schema = 1
                return "使用随机队伍开局", START_CRAFT
        if position := frame.find("schemacraft_entry_assets"):
            return "打开图式构筑", position
        if position := frame.find("drive_assets") or frame.find("drive_mobile_assets", threshold=0.90):
            return "打开 Drive", position
        if not self.waiting_for_battle and (self.route.target is not None or frame.schema_number() is not None):
            button = frame.text_positions(frame.box("representation_action_bbox"))
            label = " ".join(text for text, _ in button)
            if search(r"\bunreachable\b", label, flags=IGNORECASE):
                self.route.reject_target()
                self.entering_event = False
                return "关闭节点详情，重新选路", (720, 430)
            if search(r"\benter (representation|event)\b", label, flags=IGNORECASE):
                return self.enter_node(frame, button[0][1])
        return None

    def update_schema(self, frame):
        schema = frame.schema_number()
        if self.schema is not None and schema is not None and schema < self.schema:
            return
        if schema is not None and schema != self.schema:
            if self.schema is not None:
                self.regular_wins = 0
                self.route = FloorMap()
                self.reset_map_roll()
            self.schema = schema
            self.node_number = 0
            log.info(f"图式构筑：进入第 {schema} 层")

    def begin_node(self):
        if self.node_timing is None and self.schema is not None:
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

    def next_map_action(self, frame):
        rolled = frame.blue_fraction(frame.box("rolled_dice_edge_bbox")) >= 0.5
        if self.route.entered:
            # 移动过场可能先露出旧地图，等本次投掷的高亮收起再更换地图原点。
            if rolled:
                return None
            self.route.arrive()
            self.entering_event = False
        view = read_map(frame, self.route.current)
        if view is not None and (target := self.route.choose(view)) is not None:
            self.route.target = target
            kind = self.route.kinds[target]
            self.entering_event = kind in ("event_node", "new")
            if kind == "boss_node":
                label = "选择第 1 层首领节点"
            elif kind == "cleared_node":
                label = "沿最短路回到已通关节点"
            else:
                label = "前往相邻的新节点"
            return label, view.nodes[target].point

        if not rolled and not (view and any(view.roads.values())):
            if frame.blue_fraction(frame.box("remaining_rolls_assets")) > 0.45:
                self.route.rejected.clear()
                self.reset_map_roll()
                return "投掷骰子", (2085, 1115)
            return None

        now = monotonic()
        if not self.map_scan_at:
            self.map_scan_at = now + 2
        elif now >= self.map_scan_at:
            if self.map_scans is None:
                self.map_scans = (SCAN_MAP_UP, SCAN_MAP) if frame.map_route_above() else (SCAN_MAP, SCAN_MAP_UP)
            if self.map_scans:
                position, self.map_scans = self.map_scans[0], self.map_scans[1:]
                self.map_scan_at = now + 4
                return "搜索地图上可达的节点", position
            raise RuntimeError("未识别到通往新节点的路线，已保留当前局")
        return None

    def reset_map_roll(self):
        self.map_scan_at = 0
        self.map_scans = None

    def enter_node(self, frame, position):
        self.update_schema(frame)
        if self.should_settle():
            self.entering_encounter = False
            return "关闭遭遇面板，准备结算", (720, 430)
        if self.schema is None:
            return None
        target = self.route.target
        kind = self.route.kinds.get(target)
        visited = kind == "cleared_node" or bool(frame.find("already_visited_assets", threshold=0.90))
        title = ""
        if not visited and (not self.entering_encounter or kind == "boss_node" or target is None):
            title = frame.read_text((1770, 38, 2520, 176))
            visited = bool(search(r"\balready\s*visited\b", title, flags=IGNORECASE))
        boss = bool(frame.find("boss_encounter_assets", threshold=0.9))
        boss = boss or bool(search(r"\bboss\s+encounter\b", title, flags=IGNORECASE))
        # 接手续局或跨多格点首领时，先从详情核实目标。
        if target is None and not boss:
            return "关闭节点详情，重新选路", (720, 430)
        if target is not None:
            x, y = self.route.current
            if abs(target[0] - x) + abs(target[1] - y) > 1 and not boss:
                self.route.reject_target()
                self.entering_event = False
                return "关闭节点详情，重新选路", (720, 430)
        self.route.entered = target is not None
        self.reset_map_roll()
        if target is not None and visited:
            self.route.kinds[target] = "cleared_node"
            self.entering_encounter = self.entering_event = False
            return "确认移动到已通关节点", position
        if target is not None and search(r"\bregular\s+encounter\b", title, flags=IGNORECASE):
            self.route.kinds[target] = "regular_encounter_node"
            self.entering_event = False
        elif target is not None and search(r"\bevent\b", title, flags=IGNORECASE):
            self.route.kinds[target] = "event_node"
            self.entering_event = True
        self.begin_node()
        self.boss_encounter = boss
        self.entering_encounter = True
        self.reward_counted = False
        return ("进入事件节点" if self.route.kinds.get(target) == "event_node" else "进入遭遇节点"), position

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
        return (
            frame.find("confirm_schema_reward_assets") and frame.bright_fraction("confirm_schema_reward_assets") > 0.16
        )

    def reset_reward_choices(self):
        self.reward_picks.clear()
        self.missed_reward_picks.clear()
        self.pending_reward = None

    def skip_pending_reward(self):
        if self.pending_reward is not None:
            self.missed_reward_picks.add((self.pending_reward.label, self.pending_reward.position[0]))
            self.pending_reward = None

    def choose_reward(self, frame: SchemacraftFrame):
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
            ("招募新的人格", "ID", "team_tab", area, 0.89, 83),
            ("选取 E.G.O.", "EGO", "ego_reward_pips", (1100, 410, 2350, 690), 0.83, 95),
            ("选取人格碎片", "ID", "sliver_tab", area, 0.91, -83),
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
